# dte/management/commands/enviar_50_ccf_simple.py

import time
import json
import uuid
import csv
import os
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from django.db import transaction

from dte.services import DTEService
from dte.models import (
    Emisor, FacturaElectronica, Identificacion, Receptor, CuerpoDocumentoItem, 
    Resumen, TipoDocumento, AmbienteDestino, ModeloFacturacion, 
    TipoTransmision, UnidadMedida, CondicionOperacion, TipoItem, 
    Tributo, TributoResumen, TipoDocReceptor
)
from dte.utils import build_dte_json, numero_a_letras
from dte.views import ajustar_precision_items, ajustar_precision_resumen
from productos.models import Producto


class Command(BaseCommand):
    help = 'Envía 50 CCF usando plantilla JSON existosa - solo cambia correlativo, fecha, hora y códigos'

    def add_arguments(self, parser):
        parser.add_argument(
            '--delay',
            type=int,
            default=3,
            help='Segundos de espera entre envíos (default: 3)',
        )

    def handle(self, *args, **options):
        delay = options['delay']
        
        self.stdout.write(
            self.style.SUCCESS('Iniciando envío de 50 CCF usando plantilla JSON')
        )
        
        # Preparar archivo CSV para guardar códigos de generación
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_filename = f'codigos_generacion_ccf_{timestamp}.csv'
        csv_path = os.path.join(settings.BASE_DIR, csv_filename)
        
        # Crear archivo CSV y escribir encabezados
        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            csv_writer = csv.writer(csvfile)
            csv_writer.writerow([
                'Numero_Factura', 
                'Numero_Control', 
                'Codigo_Generacion', 
                'Fecha_Emision', 
                'Hora_Emision',
                'Estado_Hacienda',
                'Sello_Recepcion',
                'Fecha_Envio'
            ])
        
        self.stdout.write(
            self.style.SUCCESS(f'📄 Archivo CSV creado: {csv_filename}')
        )
        
        try:
            # Obtener emisor para configurar servicio
            emisor = Emisor.objects.first()
            if not emisor:
                self.stdout.write(
                    self.style.ERROR('No se encontró emisor configurado')
                )
                return
            
            # Configurar servicio DTE
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
            
            # Plantilla JSON base (tu ejemplo exitoso)
            plantilla_json = {
                "identificacion": {
                    "version": 3,
                    "ambiente": "00",
                    "tipoDte": "03",
                    "numeroControl": "DTE-03-00010001-000000000000084",  # Se cambiará
                    "codigoGeneracion": "1DC66608-5C60-4505-AB8E-D4C93F2F9430",  # Se cambiará
                    "tipoModelo": 1,
                    "tipoOperacion": 1,
                    "tipoContingencia": None,
                    "motivoContin": None,
                    "fecEmi": "2025-08-02",  # Se cambiará
                    "horEmi": "08:41:43",    # Se cambiará
                    "tipoMoneda": "USD"
                },
                "documentoRelacionado": None,
                "emisor": {
                    "nit": "07152710640010",
                    "nrc": "655139",
                    "nombre": "DANIEL DE JESUS LANDAVERDE",
                    "codActividad": "45301",
                    "descActividad": "Venta de partes, piezas y accesorios nuevos para vehiculos automotores",
                    "nombreComercial": "Auto Repuestos Landes",
                    "tipoEstablecimiento": "02",
                    "direccion": {
                        "departamento": "06",
                        "municipio": "23",
                        "complemento": "29 AVENIDA NORTE Y CALLE AL VOLCAN, LOCAL No 3, FRENTE A GASOLINERA UNO, COLONIA ZACAMIL, MEJICANOS, SAN SALVADOR"
                    },
                    "telefono": "22726991",
                    "correo": "landaverdedaniel184@gmail.com",
                    "codEstableMH": "0001",
                    "codEstable": "0001",
                    "codPuntoVentaMH": "0001",
                    "codPuntoVenta": "0001"
                },
                "receptor": {
                    "nit": "06140803761068",
                    "nrc": "2711698",
                    "nombre": "MAURICIO ALEXANDER ROSALES MORAN",
                    "codActividad": "62090",
                    "descActividad": "Actividades de tecnologia",
                    "nombreComercial": None,
                    "direccion": {
                        "departamento": "06",
                        "municipio": "21",
                        "complemento": "San Salvador"
                    },
                    "telefono": "70000000",
                    "correo": "alexanderalfaro1251@gmail.com"
                },
                "otrosDocumentos": None,
                "ventaTercero": None,
                "cuerpoDocumento": [
                    {
                        "numItem": 1,
                        "tipoItem": 1,
                        "numeroDocumento": None,
                        "cantidad": 1.0,
                        "codigo": "PROD-1",
                        "codTributo": None,
                        "uniMedida": 59,
                        "descripcion": "Repuesto 1",
                        "precioUni": 88.5,
                        "montoDescu": 0.0,
                        "ventaNoSuj": 0.0,
                        "ventaExenta": 0.0,
                        "ventaGravada": 88.5,
                        "tributos": ["20"],
                        "psv": 0.0,
                        "noGravado": 0.0
                    }
                ],
                "resumen": {
                    "totalNoSuj": 0.0,
                    "totalExenta": 0.0,
                    "totalGravada": 88.5,
                    "subTotalVentas": 88.5,
                    "descuNoSuj": 0.0,
                    "descuExenta": 0.0,
                    "descuGravada": 0.0,
                    "porcentajeDescuento": 0.0,
                    "totalDescu": 0.0,
                    "tributos": [
                        {
                            "codigo": "20",
                            "descripcion": "Impuesto al Valor Agregado 13%",
                            "valor": 11.5
                        }
                    ],
                    "subTotal": 88.5,
                    "ivaRete1": 0.0,
                    "reteRenta": 0.0,
                    "montoTotalOperacion": 100.0,
                    "totalNoGravado": 0.0,
                    "totalPagar": 100.0,
                    "totalLetras": "CIEN DÓLARES",
                    "saldoFavor": 0.0,
                    "condicionOperacion": 1,
                    "pagos": None,
                    "numPagoElectronico": "",
                    "ivaPerci1": 0.0
                },
                "extension": None,
                "apendice": None
            }
            
            # Calcular número inicial (después del 34 del ejemplo)
            numero_inicial = 85
            
            exitosas = 0
            fallidas = 0
            
            for i in range(50):
                try:
                    numero_correlativo = numero_inicial + i
                    
                    # Generar campos únicos al inicio
                    ahora = timezone.now()
                    fecha_actual = ahora.strftime('%Y-%m-%d')
                    hora_actual = ahora.strftime('%H:%M:%S')
                    nuevo_codigo_generacion = str(uuid.uuid4()).upper()
                    nuevo_numero_control = f"DTE-03-00010001-{numero_correlativo:015d}"
                    
                    self.stdout.write(f'Enviando CCF {i+1}/50 (correlativo {numero_correlativo})...')
                    
                    # Crear registro en BD
                    factura = self._crear_factura_bd(
                        emisor, 
                        numero_correlativo, 
                        nuevo_codigo_generacion, 
                        fecha_actual, 
                        hora_actual
                    )
                    
                    # Generar JSON desde la BD (para consistencia)
                    dte_json = build_dte_json(factura)
                    
                    # Enviar a Hacienda
                    resultado = self._enviar_json_directo(dte_json, servicio, token, nuevo_codigo_generacion)
                    
                    # Actualizar estado en BD
                    estado_hacienda = 'ACEPTADO' if resultado['estado'] == 'PROCESADO' else 'RECHAZADO'
                    sello_recepcion = resultado.get('sello', '')
                    fecha_envio_actual = timezone.now()
                    
                    factura.estado_hacienda = estado_hacienda
                    factura.sello_recepcion = sello_recepcion
                    factura.observaciones_hacienda = json.dumps(resultado.get('observaciones', []))
                    factura.fecha_envio_hacienda = fecha_envio_actual
                    factura.intentos_envio = 1
                    factura.save(update_fields=[
                        'estado_hacienda', 'sello_recepcion', 'observaciones_hacienda',
                        'fecha_envio_hacienda', 'intentos_envio'
                    ])
                    
                    # Guardar en CSV
                    self._guardar_en_csv(
                        csv_path, 
                        i + 1, 
                        nuevo_numero_control, 
                        nuevo_codigo_generacion, 
                        fecha_actual, 
                        hora_actual,
                        estado_hacienda,
                        sello_recepcion,
                        fecha_envio_actual.strftime('%Y-%m-%d %H:%M:%S')
                    )
                    # DEBUG: Mostrar campos cambiados
                    self.stdout.write(f'  Número Control: {nuevo_numero_control}')
                    self.stdout.write(f'  Código Generación: {nuevo_codigo_generacion}')
                    self.stdout.write(f'  Fecha: {fecha_actual} {hora_actual}')
                    self.stdout.write(f'  ID en BD: {factura.id}')
                    
                    if resultado['estado'] == 'PROCESADO':
                        exitosas += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'✓ CCF {nuevo_numero_control} enviado exitosamente'
                            )
                        )
                        self.stdout.write(
                            self.style.SUCCESS(f'  💾 Guardado en BD (ID: {factura.id}) y CSV')
                        )
                    else:
                        fallidas += 1
                        error_msg = resultado.get("descripcion", "Error desconocido")
                        self.stdout.write(
                            self.style.ERROR(
                                f'✗ CCF RECHAZADO: {nuevo_numero_control}'
                            )
                        )
                        self.stdout.write(
                            self.style.ERROR(f'   Motivo: {error_msg}')
                        )
                        self.stdout.write(
                            self.style.ERROR(f'   Observaciones: {resultado.get("observaciones", [])}')
                        )
                        self.stdout.write(
                            self.style.WARNING(f'  💾 Guardado en BD (ID: {factura.id}) como RECHAZADO y en CSV')
                        )
                        
                        # DETENER EL SCRIPT SI HAY RECHAZO
                        self.stdout.write(
                            self.style.ERROR('\n🛑 SCRIPT DETENIDO: CCF rechazado por Hacienda')
                        )
                        self._mostrar_resumen_final(exitosas, fallidas, csv_path)
                        return
                    
                    # Esperar antes del siguiente envío (excepto en la última)
                    if i < 49:
                        self.stdout.write(f'Esperando {delay} segundos...')
                        time.sleep(delay)
                        
                except Exception as e:
                    fallidas += 1
                    error_msg = str(e)
                    fecha_envio_actual = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
                    
                    # Intentar guardar excepción en CSV
                    try:
                        numero_correlativo = numero_inicial + i
                        nuevo_numero_control = f"DTE-03-00010001-{numero_correlativo:015d}"
                        nuevo_codigo_generacion = "ERROR-" + str(uuid.uuid4()).upper()
                        ahora = timezone.now()
                        fecha_actual = ahora.strftime('%Y-%m-%d')
                        hora_actual = ahora.strftime('%H:%M:%S')
                        
                        self._guardar_en_csv(
                            csv_path, 
                            i + 1, 
                            nuevo_numero_control, 
                            nuevo_codigo_generacion, 
                            fecha_actual, 
                            hora_actual,
                            f'ERROR: {error_msg}',
                            '',
                            fecha_envio_actual
                        )
                    except:
                        pass  # Si no se puede guardar el error, continuar
                    
                    self.stdout.write(
                        self.style.ERROR(f'✗ EXCEPCIÓN EN CCF {i+1}: {error_msg}')
                    )
                    
                    # DETENER TAMBIÉN POR EXCEPCIONES CRÍTICAS
                    self.stdout.write(
                        self.style.ERROR('\n🛑 SCRIPT DETENIDO: Error crítico en el proceso')
                    )
                    self._mostrar_resumen_final(exitosas, fallidas, csv_path)
                    return
            
            # Resumen final
            self._mostrar_resumen_final(exitosas, fallidas, csv_path)
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error general: {str(e)}')
            )
            
    def _crear_factura_bd(self, emisor, numero_correlativo, codigo_generacion, fecha_actual, hora_actual):
        """Crea la factura completa en la base de datos usando los mismos datos del JSON exitoso"""
        
        with transaction.atomic():
            # 1. Obtener o crear producto
            producto, created = Producto.objects.get_or_create(
                codigo1='PROD-1',
                defaults={
                    'nombre': 'Repuesto 1',
                    'descripcion': 'Repuesto de prueba para CCF',
                    'precio1': 100.00,
                    'existencias': 1000
                }
            )
            
            # 2. Crear o obtener receptor CCF (datos del JSON exitoso)
            receptor, created = Receptor.objects.get_or_create(
                numDocumento='06140803761068',
                defaults={
                    'tipoDocumento': TipoDocReceptor.objects.get(codigo='36'),  # NIT
                    'nrc': '2711698',
                    'nombre': 'MAURICIO ALEXANDER ROSALES MORAN',
                    'codActividad': '62090',
                    'descActividad': 'Actividades de tecnologia',
                    'telefono': '70000000',
                    'correo': 'alexanderalfaro1251@gmail.com',
                    'departamento': '06',
                    'municipio': '21',
                    'complemento': 'San Salvador'
                }
            )
            
            # 3. Crear identificación
            establecimiento = emisor.codEstable or "0001"
            punto_venta = emisor.codPuntoVenta or "0001"
            numero_control = f"DTE-03-{establecimiento.zfill(4)}{punto_venta.zfill(4)}-{numero_correlativo:015d}"
            
            # Convertir fecha y hora de string a objetos datetime
            fecha_obj = datetime.strptime(fecha_actual, '%Y-%m-%d').date()
            hora_obj = datetime.strptime(hora_actual, '%H:%M:%S').time()
            
            identificacion = Identificacion.objects.create(
                version=3,
                ambiente=AmbienteDestino.objects.get(codigo="00"),
                tipoDte=TipoDocumento.objects.get(codigo="03"),
                numeroControl=numero_control,
                codigoGeneracion=codigo_generacion,
                tipoModelo=ModeloFacturacion.objects.get(codigo="1"),
                tipoOperacion=TipoTransmision.objects.get(codigo="1"),
                fecEmi=fecha_obj,
                horEmi=hora_obj,
                tipoMoneda="USD"
            )
            
            # 4. Crear factura
            factura = FacturaElectronica.objects.create(
                identificacion=identificacion,
                emisor=emisor,
                receptor=receptor
            )
            
            # 5. Crear item (datos exactos del JSON exitoso)
            cantidad = ajustar_precision_items(1.0)
            precio_unitario = ajustar_precision_items(88.5)  # Precio sin IVA del ejemplo
            venta_gravada = ajustar_precision_items(88.5)
            iva_item = ajustar_precision_items(0.0)  # Para CCF el IVA no va en el item
            
            item = CuerpoDocumentoItem.objects.create(
                factura=factura,
                numItem=1,
                tipoItem=TipoItem.objects.get(codigo="1"),
                cantidad=cantidad,
                codigo=producto.codigo1,
                uniMedida=UnidadMedida.objects.get(codigo="59"),
                descripcion=producto.nombre,
                precioUni=precio_unitario,
                montoDescu=ajustar_precision_items(0.0),
                ventaNoSuj=ajustar_precision_items(0.0),
                ventaExenta=ajustar_precision_items(0.0),
                ventaGravada=venta_gravada,
                psv=ajustar_precision_items(0.0),
                noGravado=ajustar_precision_items(0.0),
                ivaItem=iva_item  # AGREGADO: Campo ivaItem requerido
            )
            
            # Agregar tributo IVA al item
            tributo_iva = Tributo.objects.get(codigo="20")
            item.tributos.add(tributo_iva)
            
            # 6. Crear resumen (valores exactos del JSON exitoso)
            total_gravada = ajustar_precision_resumen(88.5)
            total_iva = ajustar_precision_resumen(11.5)
            monto_total_operacion = ajustar_precision_resumen(100.0)
            total_pagar = ajustar_precision_resumen(100.0)
            
            resumen = Resumen.objects.create(
                factura=factura,
                totalNoSuj=ajustar_precision_resumen(0.0),
                totalExenta=ajustar_precision_resumen(0.0),
                totalGravada=total_gravada,
                subTotalVentas=total_gravada,
                descuNoSuj=ajustar_precision_resumen(0.0),
                descuExenta=ajustar_precision_resumen(0.0),
                descuGravada=ajustar_precision_resumen(0.0),
                porcentajeDescuento=ajustar_precision_resumen(0.0),
                totalDescu=ajustar_precision_resumen(0.0),
                subTotal=total_gravada,
                ivaRete1=ajustar_precision_resumen(0.0),
                reteRenta=ajustar_precision_resumen(0.0),
                montoTotalOperacion=monto_total_operacion,
                totalNoGravado=ajustar_precision_resumen(0.0),
                totalPagar=total_pagar,
                totalLetras=numero_a_letras(total_pagar),
                saldoFavor=ajustar_precision_resumen(0.0),
                condicionOperacion=CondicionOperacion.objects.get(codigo="1"),
                numPagoElectronico="",
                ivaPerci1=ajustar_precision_resumen(0.0)
            )
            
            # 7. Crear tributo IVA en resumen
            TributoResumen.objects.create(
                resumen=resumen,
                codigo=tributo_iva,
                descripcion="Impuesto al Valor Agregado 13%",
                valor=total_iva
            )
            
            return factura

    def _enviar_json_directo(self, dte_json, servicio, token, codigo_generacion):
        """Envía el JSON directamente a Hacienda"""
        try:
            # DEBUG: Mostrar solo la identificación para no saturar
            self.stdout.write('='*40)
            self.stdout.write('IDENTIFICACIÓN DEL JSON ENVIADO:')
            self.stdout.write(json.dumps(dte_json["identificacion"], indent=2, ensure_ascii=False))
            self.stdout.write('='*40)
            
            # Enviar a Hacienda usando el método existente
            respuesta = servicio.enviar_a_hacienda(
                token=token,
                codigo_generacion=codigo_generacion,
                tipo_dte='03',
                dte_json=dte_json
            )
            
            # DEBUG: Mostrar respuesta
            self.stdout.write('RESPUESTA DE HACIENDA:')
            self.stdout.write('='*40)
            self.stdout.write(json.dumps(respuesta, indent=2, ensure_ascii=False, default=str))
            self.stdout.write('='*40)
            
            return respuesta
            
        except Exception as e:
            return {
                'estado': 'ERROR',
                'descripcion': str(e),
                'sello': '',
                'observaciones': [str(e)]
            }

    def _mostrar_resumen(self, exitosas, fallidas, csv_path):
        """Muestra resumen parcial"""
        self.stdout.write('\n' + '='*50)
        self.stdout.write(
            self.style.WARNING(f'RESUMEN HASTA EL MOMENTO:')
        )
        self.stdout.write(f'CCF exitosos: {exitosas}')
        self.stdout.write(f'CCF fallidos: {fallidas}')
        self.stdout.write(f'Total procesados: {exitosas + fallidas}')
        self.stdout.write(f'CCF restantes: {50 - (exitosas + fallidas)}')
        self.stdout.write(f'\n📄 Datos guardados en: {csv_path}')
        self.stdout.write('='*50)

    def _guardar_en_csv(self, csv_path, numero_factura, numero_control, codigo_generacion, 
                       fecha_emision, hora_emision, estado_hacienda, sello_recepcion, fecha_envio):
        """Guarda los datos de la factura en el archivo CSV"""
        try:
            with open(csv_path, 'a', newline='', encoding='utf-8') as csvfile:
                csv_writer = csv.writer(csvfile)
                csv_writer.writerow([
                    numero_factura,
                    numero_control,
                    codigo_generacion,
                    fecha_emision,
                    hora_emision,
                    estado_hacienda,
                    sello_recepcion,
                    fecha_envio
                ])
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'Error guardando en CSV: {str(e)}')
            )

    def _mostrar_resumen_final(self, exitosas, fallidas, csv_path):
        """Muestra resumen final con información del CSV y BD"""
        self.stdout.write('\n' + '='*50)
        self.stdout.write(
            self.style.SUCCESS(f'RESUMEN FINAL CCF:')
        )
        self.stdout.write(f'CCF exitosos: {exitosas}')
        self.stdout.write(f'CCF fallidos: {fallidas}')
        self.stdout.write(f'Total procesados: {exitosas + fallidas}')
        self.stdout.write('\n💾 GUARDADO COMPLETO:')
        self.stdout.write(f'   ✅ Base de Datos: {exitosas + fallidas} registros completos')
        self.stdout.write(f'   ✅ Archivo CSV: {csv_path}')
        self.stdout.write(f'   📊 Puedes consultar las facturas en tu aplicación web')
        self.stdout.write('\n📄 COLUMNAS DEL CSV:')
        self.stdout.write('   - Numero_Factura, Numero_Control, Codigo_Generacion,')
        self.stdout.write('   - Fecha_Emision, Hora_Emision, Estado_Hacienda,')
        self.stdout.write('   - Sello_Recepcion, Fecha_Envio')
        self.stdout.write('='*50)