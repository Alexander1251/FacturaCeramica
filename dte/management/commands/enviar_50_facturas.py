# dte/management/commands/enviar_50_facturas.py

import time
import json
from decimal import Decimal, ROUND_HALF_UP
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from datetime import datetime
import uuid

from dte.models import (
    FacturaElectronica, Identificacion, Receptor, CuerpoDocumentoItem, 
    Resumen, Emisor, TipoDocumento, AmbienteDestino, ModeloFacturacion, 
    TipoTransmision, UnidadMedida, CondicionOperacion, TipoItem, Sucursal, TipoDocReceptor, Municipio, Departamento
)
from dte.services import DTEService
from dte.utils import build_dte_json, numero_a_letras
from dte.views import ajustar_precision_items, ajustar_precision_resumen, generar_pdf_factura_mejorado
from productos.models import Producto


class Command(BaseCommand):
    help = 'Envía 50 facturas de prueba secuencialmente a Hacienda'

    def add_arguments(self, parser):
        parser.add_argument(
            '--tipo',
            type=str,
            default='01',
            help='Tipo de documento (01=FC, 03=CCF, 14=FSE)',
        )
        parser.add_argument(
            '--delay',
            type=int,
            default=3,
            help='Segundos de espera entre envíos (default: 3)',
        )
        parser.add_argument(
            '--desde',
            type=int,
            default=None,
            help='Número correlativo desde donde iniciar (opcional, si no se especifica continúa desde el último)',
        )

    def handle(self, *args, **options):
        tipo_dte = options['tipo']
        delay = options['delay']
        correlativo_inicial = options.get('desde') 
        
        self.stdout.write(
            self.style.SUCCESS(f'Iniciando envío de 50 facturas tipo {tipo_dte}')
        )

        if correlativo_inicial:
            self.stdout.write(
                self.style.SUCCESS(f'Iniciando desde correlativo: {correlativo_inicial}')
            )
        
        try:
            # Obtener datos base
            emisor = Emisor.objects.first()
            if not emisor:
                self.stdout.write(
                    self.style.ERROR('No se encontró emisor configurado')
                )
                return
            from dte.models import Sucursal
            sucursal = Sucursal.objects.filter(activa=True).first()
            if not sucursal:
                self.stdout.write(
                    self.style.ERROR('No se encontró ninguna sucursal activa')
                )
                return
            
            tipo_doc_receptor = TipoDocReceptor.objects.get(codigo='13')
            departamento = Departamento.objects.get(codigo='01')
            municipio = Municipio.objects.get(codigo='14', departamento=departamento)
            
            # Configurar datos base según tu ejemplo
            receptor_data = {
                'tipoDocumento': tipo_doc_receptor,  # CAMBIAR: instancia en vez de string
                'numDocumento': '00000000-9',
                'nombre': 'Juan Perez',
                'telefono': '70000000',
                'correo': 'alexanderalfaro1251@gmail.com',
                'departamento': departamento,  # CAMBIAR: instancia en vez de string
                'municipio': municipio,  # CAMBIAR: instancia en vez de string
                'complemento': 'Proveedor direccion'
            }
            
            # Obtener o crear producto de prueba
            producto, created = Producto.objects.get_or_create(
                codigo1='PROD-1',
                defaults={
                    'nombre': 'Repuesto 1',
                    'descripcion': 'Repuesto de prueba para facturas automaticas',
                    'precio1': Decimal('100.00'),
                    'precio2': Decimal('86.9565'),  # Para FSE (precio de compra)
                    'existencias': 1000
                }
            )
            
            # Calcular número de control inicial
            numero_base = self._calcular_siguiente_numero(tipo_dte, sucursal, correlativo_inicial)
            
            servicio = DTEService(
                emisor=emisor,
                ambiente='test',
                firmador_url=getattr(settings, 'FIRMADOR_URL', 'http://localhost:8113/firmardocumento/'),
                dte_urls=getattr(settings, 'DTE_URLS', {}).get('test', {}),
                dte_user=getattr(settings, 'DTE_USER', ''),
                dte_password=getattr(settings, 'DTE_PASSWORD', '')
            )
            
            # Obtener token una vez
            token = servicio.autenticar()
            if not token:
                self.stdout.write(
                    self.style.ERROR('No se pudo obtener token de autenticación')
                )
                return
            
            exitosas = 0
            fallidas = 0
            
            for i in range(50):
                try:
                    self.stdout.write(f'Enviando factura {i+1}/50...')
                    
                    # Crear factura
                    factura = self._crear_factura(
                        receptor_data, producto, tipo_dte, numero_base + i, sucursal
                    )
                    
                    # Enviar a Hacienda
                    resultado = self._enviar_factura(factura, servicio, token, tipo_dte)
                    
                    if resultado['estado'] == 'PROCESADO':
                        exitosas += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'✓ Factura {factura.identificacion.numeroControl} enviada exitosamente'
                            )
                        )
                        
                        # Enviar correo si fue aceptada
                        if resultado.get('estado') in ('PROCESADO', 'ACEPTADO'):
                            self._enviar_correo(factura, servicio)
                            
                    else:
                        fallidas += 1
                        error_msg = resultado.get("descripcion", "Error desconocido")
                        self.stdout.write(
                            self.style.ERROR(
                                f'✗ FACTURA RECHAZADA: {factura.identificacion.numeroControl}'
                            )
                        )
                        self.stdout.write(
                            self.style.ERROR(f'   Motivo: {error_msg}')
                        )
                        self.stdout.write(
                            self.style.ERROR(f'   Observaciones: {resultado.get("observaciones", [])}')
                        )
                        
                        # DETENER EL SCRIPT SI HAY RECHAZO
                        self.stdout.write(
                            self.style.ERROR('\n🛑 SCRIPT DETENIDO: Factura rechazada por Hacienda')
                        )
                        self.stdout.write('\n' + '='*50)
                        self.stdout.write(
                            self.style.WARNING(f'RESUMEN HASTA EL MOMENTO:')
                        )
                        self.stdout.write(f'Facturas exitosas: {exitosas}')
                        self.stdout.write(f'Facturas fallidas: {fallidas}')
                        self.stdout.write(f'Total procesadas: {exitosas + fallidas}')
                        self.stdout.write(f'Facturas restantes: {50 - (exitosas + fallidas)}')
                        self.stdout.write('='*50)
                        
                        return  # SALIR DEL COMANDO
                    
                    # Esperar antes del siguiente envío (excepto en la última)
                    if i < 49:
                        self.stdout.write(f'Esperando {delay} segundos...')
                        time.sleep(delay)
                        
                except Exception as e:
                    fallidas += 1
                    self.stdout.write(
                        self.style.ERROR(f'✗ EXCEPCIÓN EN FACTURA {i+1}: {str(e)}')
                    )
                    
                    # DETENER TAMBIÉN POR EXCEPCIONES CRÍTICAS
                    self.stdout.write(
                        self.style.ERROR('\n🛑 SCRIPT DETENIDO: Error crítico en el proceso')
                    )
                    self.stdout.write('\n' + '='*50)
                    self.stdout.write(
                        self.style.WARNING(f'RESUMEN HASTA EL MOMENTO:')
                    )
                    self.stdout.write(f'Facturas exitosas: {exitosas}')
                    self.stdout.write(f'Facturas fallidas: {fallidas}')
                    self.stdout.write(f'Total procesadas: {exitosas + fallidas}')
                    self.stdout.write(f'Facturas restantes: {50 - (exitosas + fallidas)}')
                    self.stdout.write('='*50)
                    
                    return  # SALIR DEL COMANDO
            
            # Resumen final
            self.stdout.write('\n' + '='*50)
            self.stdout.write(
                self.style.SUCCESS(f'RESUMEN FINAL:')
            )
            self.stdout.write(f'Facturas exitosas: {exitosas}')
            self.stdout.write(f'Facturas fallidas: {fallidas}')
            self.stdout.write(f'Total procesadas: {exitosas + fallidas}')
            self.stdout.write('='*50)
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error general: {str(e)}')
            )

    def _calcular_siguiente_numero(self, tipo_dte, sucursal, correlativo_inicial=None):
        """Calcula el siguiente número de control basado en la sucursal"""
        
        establecimiento = sucursal.codEstable
        punto_venta = sucursal.codPuntoVenta
        
        prefijo = f"DTE-{tipo_dte}-{establecimiento.zfill(4)}{punto_venta.zfill(4)}-"
        
        # Si se especificó un correlativo inicial, usarlo
        if correlativo_inicial is not None:
            return correlativo_inicial
        
        # Buscar el último número en la base de datos
        ultimo = (
            Identificacion.objects.filter(numeroControl__startswith=prefijo)
            .order_by("-numeroControl")
            .first()
        )
        
        if ultimo:
            ultimo_numero = int(ultimo.numeroControl[-15:])
            return ultimo_numero + 1
        else:
            return 1

    def _crear_factura(self, receptor_data, producto, tipo_dte, numero_correlativo, sucursal):
        """Crea una factura con los datos especificados"""
        
        # Obtener el emisor maestro
        from dte.forms import _emisor_maestro
        emisor = _emisor_maestro()
        if not emisor:
            raise Exception("No se encontró emisor maestro configurado")
        
        with transaction.atomic():
            # 1. Crear o obtener receptor
            receptor, created = Receptor.objects.get_or_create(
                numDocumento=receptor_data['numDocumento'],
                defaults={
                    'tipoDocumento': receptor_data['tipoDocumento'],
                    'nombre': receptor_data['nombre'],
                    'telefono': receptor_data['telefono'],
                    'correo': receptor_data['correo'],
                    'departamento': receptor_data['departamento'],
                    'municipio': receptor_data['municipio'],
                    'complemento': receptor_data['complemento']
                }
            )
            
            # 2. Crear identificación - USAR SUCURSAL para el número de control
            establecimiento = sucursal.codEstable
            punto_venta = sucursal.codPuntoVenta
            numero_control = f"DTE-{tipo_dte}-{establecimiento.zfill(4)}{punto_venta.zfill(4)}-{numero_correlativo:015d}"
            
            identificacion = Identificacion.objects.create(
                version=1,
                ambiente=AmbienteDestino.objects.get(codigo="00"),
                tipoDte=TipoDocumento.objects.get(codigo=tipo_dte),
                numeroControl=numero_control,
                codigoGeneracion=str(uuid.uuid4()).upper(),
                tipoModelo=ModeloFacturacion.objects.get(codigo="1"),
                tipoOperacion=TipoTransmision.objects.get(codigo="1"),
                fecEmi=timezone.now().date(),
                horEmi=timezone.now().time(),
                tipoMoneda="USD"
            )
            
            # 3. Crear factura - AGREGAR SUCURSAL
            factura = FacturaElectronica.objects.create(
                identificacion=identificacion,
                emisor=emisor,
                receptor=receptor,
                sucursal=sucursal  # CAMPO OBLIGATORIO
            )
            
            # 4. Crear item - cálculo correcto según tipo de documento
            cantidad = ajustar_precision_items(Decimal('1.0'))
            precio_unitario = ajustar_precision_items(Decimal(str(producto.precio1)))
            
            # Calcular valores base
            monto_descu = ajustar_precision_items(Decimal('0.00'))
            
            if tipo_dte == "14":  # FSE
                # Para FSE usar precio2 (precio de compra)
                precio_unitario = ajustar_precision_items(Decimal(str(producto.precio2 or '86.9565')))
                venta_gravada = ajustar_precision_items(precio_unitario * cantidad - monto_descu)
                iva_item = ajustar_precision_items(Decimal('0.00'))
            elif tipo_dte == "01":  # FC - Factura de Consumidor
                # Para FC: venta gravada = precio * cantidad
                venta_gravada = ajustar_precision_items(precio_unitario * cantidad - monto_descu)
                # IVA = precio / 1.13 * 0.13
                precio_total = precio_unitario * cantidad - monto_descu
                iva_item = ajustar_precision_items(precio_total / Decimal('1.13') * Decimal('0.13'))
            else:  # CCF y otros
                # Para CCF: IVA = precio / 1.13 * 0.13
                precio_total = precio_unitario * cantidad - monto_descu
                iva_item = ajustar_precision_items(precio_total / Decimal('1.13') * Decimal('0.13'))
                venta_gravada = ajustar_precision_items(precio_total - iva_item)
                
            # DEBUG: Mostrar cálculos
            self.stdout.write(f'DEBUG - Tipo DTE: {tipo_dte}')
            self.stdout.write(f'DEBUG - Precio unitario: {precio_unitario}')
            self.stdout.write(f'DEBUG - Cantidad: {cantidad}')
            self.stdout.write(f'DEBUG - Venta gravada: {venta_gravada}')
            self.stdout.write(f'DEBUG - IVA calculado: {iva_item}')
            
            item = CuerpoDocumentoItem.objects.create(
                factura=factura,
                numItem=1,
                tipoItem=TipoItem.objects.get(codigo="1"),  # Obtener instancia de TipoItem
                cantidad=cantidad,
                codigo=producto.codigo1,  # Usar codigo1 en lugar de codigo
                uniMedida=UnidadMedida.objects.get(codigo="59"),  # Unidad
                descripcion=producto.nombre,
                precioUni=precio_unitario,
                montoDescu=ajustar_precision_items(Decimal('0.00')),
                ventaNoSuj=ajustar_precision_items(Decimal('0.00')),
                ventaExenta=ajustar_precision_items(Decimal('0.00')),
                ventaGravada=venta_gravada,
                psv=ajustar_precision_items(Decimal('0.00')),
                noGravado=ajustar_precision_items(Decimal('0.00')),
                ivaItem=iva_item
            )
            
            # 5. Crear resumen - totales correctos según especificación
            # Para FC: totalGravada = suma de ventas gravadas de items
            # totalPagar = totalGravada + totalIva
            total_iva = ajustar_precision_resumen(iva_item)
            total_gravada = ajustar_precision_resumen(venta_gravada)
            total_pagar = ajustar_precision_resumen(total_gravada)
            
            # DEBUG: Mostrar cálculos del resumen
            self.stdout.write(f'DEBUG RESUMEN - Total gravada: {total_gravada}')
            self.stdout.write(f'DEBUG RESUMEN - Total IVA: {total_iva}')
            self.stdout.write(f'DEBUG RESUMEN - Total a pagar: {total_pagar}')
            
            resumen = Resumen.objects.create(
                factura=factura,
                totalNoSuj=ajustar_precision_resumen(Decimal('0.00')),
                totalExenta=ajustar_precision_resumen(Decimal('0.00')),
                totalGravada=total_gravada,  # Suma de ventas gravadas
                subTotalVentas=total_gravada,  # Mismo valor que totalGravada
                descuNoSuj=ajustar_precision_resumen(Decimal('0.00')),
                descuExenta=ajustar_precision_resumen(Decimal('0.00')),
                descuGravada=ajustar_precision_resumen(Decimal('0.00')),
                porcentajeDescuento=ajustar_precision_resumen(Decimal('0.00')),
                totalDescu=ajustar_precision_resumen(Decimal('0.00')),
                subTotal=total_gravada,  # Mismo valor que totalGravada
                ivaRete1=ajustar_precision_resumen(Decimal('0.00')),
                reteRenta=ajustar_precision_resumen(Decimal('0.00')),
                montoTotalOperacion=total_gravada,  # Mismo valor que totalGravada
                totalNoGravado=ajustar_precision_resumen(Decimal('0.00')),
                totalPagar=total_pagar,  # totalGravada + totalIva
                totalLetras=numero_a_letras(total_pagar),
                saldoFavor=ajustar_precision_resumen(Decimal('0.00')),
                condicionOperacion=CondicionOperacion.objects.get(codigo="1"),
                numPagoElectronico="",
                totalIva=total_iva  # IVA total
            )
            
            return factura

    def _enviar_factura(self, factura, servicio, token, tipo_dte):
        """Envía la factura a Hacienda y actualiza el estado"""
        try:
            # Construir JSON
            dte_json = build_dte_json(factura)
            
            # DEBUG: Mostrar el JSON que se envía
            self.stdout.write('='*60)
            self.stdout.write('JSON ENVIADO A HACIENDA:')
            self.stdout.write('='*60)
            self.stdout.write(json.dumps(dte_json, indent=2, ensure_ascii=False, default=str))
            self.stdout.write('='*60)
            
            # Enviar a Hacienda
            respuesta = servicio.enviar_a_hacienda(
                token=token,
                codigo_generacion=factura.identificacion.codigoGeneracion,
                tipo_dte=tipo_dte,
                dte_json=dte_json
            )
            
            # DEBUG: Mostrar respuesta completa
            self.stdout.write('RESPUESTA DE HACIENDA:')
            self.stdout.write('='*60)
            self.stdout.write(json.dumps(respuesta, indent=2, ensure_ascii=False, default=str))
            self.stdout.write('='*60)
            
            # Actualizar estado en la base de datos
            if respuesta.get('estado') == "PROCESADO":
                estado_hacienda = "ACEPTADO"
            else:
                estado_hacienda = "RECHAZADO"
                
            factura.estado_hacienda = estado_hacienda
            factura.sello_recepcion = respuesta.get('sello', '')
            factura.observaciones_hacienda = json.dumps(respuesta.get('observaciones', []))
            factura.fecha_envio_hacienda = timezone.now()
            factura.intentos_envio = 1
            factura.save(update_fields=[
                'estado_hacienda',
                'sello_recepcion', 
                'observaciones_hacienda',
                'fecha_envio_hacienda',
                'intentos_envio'
            ])
            
            return respuesta
            
        except Exception as e:
            # Actualizar estado de error
            factura.estado_hacienda = "RECHAZADO"
            factura.observaciones_hacienda = json.dumps([str(e)])
            factura.fecha_envio_hacienda = timezone.now()
            factura.intentos_envio = 1
            factura.save(update_fields=[
                'estado_hacienda',
                'observaciones_hacienda',
                'fecha_envio_hacienda',
                'intentos_envio'
            ])
            
            return {
                'estado': 'ERROR',
                'descripcion': str(e),
                'sello': '',
                'observaciones': [str(e)]
            }

    def _enviar_correo(self, factura, servicio):
        """Envía la factura por correo si fue aceptada"""
        try:
            # Generar PDF
            pdf_bytes = generar_pdf_factura_mejorado(factura)
            
            # Generar JSON con firma y sello
            json_str = json.dumps(
                build_dte_json(factura, incluir_firma_y_sello=True),
                indent=2,
                ensure_ascii=False
            )
            
            archivos = [
                {
                    'filename': f"{factura.identificacion.numeroControl}.pdf",
                    'content': pdf_bytes,
                    'mimetype': 'application/pdf'
                },
                {
                    'filename': f"{factura.identificacion.numeroControl}_firmado.json",
                    'content': json_str,
                    'mimetype': 'application/json'
                }
            ]
            
            servicio.enviar_correo_factura(factura, archivos)
            
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'Error al enviar correo: {str(e)}')
            )