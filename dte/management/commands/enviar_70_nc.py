# dte/management/commands/enviar_70_nc.py

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
    Tributo, TributoResumen, TipoDocReceptor, DocumentoRelacionado,
    GeneracionDocumento
)
from dte.utils import build_dte_json, numero_a_letras
from dte.views import ajustar_precision_items, ajustar_precision_resumen
from productos.models import Producto


class Command(BaseCommand):
    help = 'Envía 50 Notas de Crédito usando los CCF del CSV como documentos relacionados'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv-file',
            type=str,
            required=True,
            help='Nombre del archivo CSV con los CCF (ej: codigos_generacion_ccf_20250802_111902.csv)',
        )
        parser.add_argument(
            '--delay',
            type=int,
            default=3,
            help='Segundos de espera entre envíos (default: 3)',
        )

    def handle(self, *args, **options):
        csv_filename = options['csv_file']
        delay = options['delay']
        
        self.stdout.write(
            self.style.SUCCESS('Iniciando envío de 50 Notas de Crédito')
        )
        
        # Verificar que existe el archivo CSV
        csv_path = os.path.join(settings.BASE_DIR, csv_filename)
        if not os.path.exists(csv_path):
            self.stdout.write(
                self.style.ERROR(f'Archivo CSV no encontrado: {csv_path}')
            )
            return
        
        # Leer CCF del CSV
        ccf_datos = self._leer_ccf_del_csv(csv_path)
        if len(ccf_datos) < 50:
            self.stdout.write(
                self.style.ERROR(f'El CSV solo tiene {len(ccf_datos)} CCF, necesitas al menos 50')
            )
            return
        
        self.stdout.write(
            self.style.SUCCESS(f'📄 Leídos {len(ccf_datos)} CCF del archivo {csv_filename}')
        )
        
        # Preparar archivo CSV para guardar códigos de NC
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        nc_csv_filename = f'codigos_generacion_nc_{timestamp}.csv'
        nc_csv_path = os.path.join(settings.BASE_DIR, nc_csv_filename)
        
        # Crear archivo CSV para NC
        with open(nc_csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            csv_writer = csv.writer(csvfile)
            csv_writer.writerow([
                'Numero_NC', 
                'Numero_Control_NC', 
                'Codigo_Generacion_NC', 
                'Fecha_Emision_NC', 
                'Hora_Emision_NC',
                'Estado_Hacienda',
                'Sello_Recepcion',
                'Fecha_Envio',
                'CCF_Relacionado',
                'Fecha_CCF_Relacionado'
            ])
        
        self.stdout.write(
            self.style.SUCCESS(f'📄 Archivo CSV para NC creado: {nc_csv_filename}')
        )
        
        try:
            # Obtener datos base
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
            
            # Calcular número inicial para NC (después del 36 del ejemplo)
            numero_inicial = 87
            
            exitosas = 0
            fallidas = 0
            
            for i in range(50):
                try:
                    numero_correlativo = numero_inicial + i
                    ccf_relacionado = ccf_datos[i]  # Usar CCF del CSV
                    
                    # Generar campos únicos para la NC
                    ahora = timezone.now()
                    fecha_actual = ahora.strftime('%Y-%m-%d')
                    hora_actual = ahora.strftime('%H:%M:%S')
                    nuevo_codigo_generacion = str(uuid.uuid4()).upper()
                    nuevo_numero_control = f"DTE-05-00010001-{numero_correlativo:015d}"
                    
                    self.stdout.write(f'Enviando NC {i+1}/50 (correlativo {numero_correlativo})...')
                    self.stdout.write(f'  CCF relacionado: {ccf_relacionado["codigo_generacion"]}')
                    
                    # Crear registro en BD
                    factura = self._crear_nc_bd(
                        emisor, 
                        numero_correlativo, 
                        nuevo_codigo_generacion, 
                        fecha_actual, 
                        hora_actual,
                        ccf_relacionado
                    )
                    
                    # DEBUG: Mostrar campos cambiados
                    self.stdout.write(f'  Número Control NC: {nuevo_numero_control}')
                    self.stdout.write(f'  Código Generación NC: {nuevo_codigo_generacion}')
                    self.stdout.write(f'  Fecha: {fecha_actual} {hora_actual}')
                    self.stdout.write(f'  ID en BD: {factura.id}')
                    
                    # Generar JSON desde la BD
                    dte_json = build_dte_json(factura)
                    
                    # Enviar a Hacienda
                    resultado = self._enviar_nc_directo(dte_json, servicio, token, nuevo_codigo_generacion)
                    
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
                        nc_csv_path, 
                        i + 1, 
                        nuevo_numero_control, 
                        nuevo_codigo_generacion, 
                        fecha_actual, 
                        hora_actual,
                        estado_hacienda,
                        sello_recepcion,
                        fecha_envio_actual.strftime('%Y-%m-%d %H:%M:%S'),
                        ccf_relacionado["codigo_generacion"],
                        ccf_relacionado["fecha_emision"]
                    )
                    
                    if resultado['estado'] == 'PROCESADO':
                        exitosas += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'✓ NC {nuevo_numero_control} enviada exitosamente'
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
                                f'✗ NC RECHAZADA: {nuevo_numero_control}'
                            )
                        )
                        self.stdout.write(
                            self.style.ERROR(f'   Motivo: {error_msg}')
                        )
                        self.stdout.write(
                            self.style.ERROR(f'   Observaciones: {resultado.get("observaciones", [])}')
                        )
                        self.stdout.write(
                            self.style.WARNING(f'  💾 Guardado en BD (ID: {factura.id}) como RECHAZADA y en CSV')
                        )
                        
                        # DETENER EL SCRIPT SI HAY RECHAZO
                        self.stdout.write(
                            self.style.ERROR('\n🛑 SCRIPT DETENIDO: NC rechazada por Hacienda')
                        )
                        self._mostrar_resumen_final(exitosas, fallidas, nc_csv_path)
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
                        nuevo_numero_control = f"DTE-05-00010001-{numero_correlativo:015d}"
                        nuevo_codigo_generacion = "ERROR-" + str(uuid.uuid4()).upper()
                        ahora = timezone.now()
                        fecha_actual = ahora.strftime('%Y-%m-%d')
                        hora_actual = ahora.strftime('%H:%M:%S')
                        ccf_relacionado = ccf_datos[i] if i < len(ccf_datos) else {"codigo_generacion": "N/A", "fecha_emision": "N/A"}
                        
                        self._guardar_en_csv(
                            nc_csv_path, 
                            i + 1, 
                            nuevo_numero_control, 
                            nuevo_codigo_generacion, 
                            fecha_actual, 
                            hora_actual,
                            f'ERROR: {error_msg}',
                            '',
                            fecha_envio_actual,
                            ccf_relacionado["codigo_generacion"],
                            ccf_relacionado["fecha_emision"]
                        )
                    except:
                        pass  # Si no se puede guardar el error, continuar
                    
                    self.stdout.write(
                        self.style.ERROR(f'✗ EXCEPCIÓN EN NC {i+1}: {error_msg}')
                    )
                    
                    # DETENER TAMBIÉN POR EXCEPCIONES CRÍTICAS
                    self.stdout.write(
                        self.style.ERROR('\n🛑 SCRIPT DETENIDO: Error crítico en el proceso')
                    )
                    self._mostrar_resumen_final(exitosas, fallidas, nc_csv_path)
                    return
            
            # Resumen final
            self._mostrar_resumen_final(exitosas, fallidas, nc_csv_path)
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error general: {str(e)}')
            )

    def _leer_ccf_del_csv(self, csv_path):
        """Lee los datos de CCF del archivo CSV"""
        ccf_datos = []
        try:
            with open(csv_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    # Solo incluir CCF aceptados
                    if row['Estado_Hacienda'] == 'ACEPTADO':
                        ccf_datos.append({
                            'numero_control': row['Numero_Control'],
                            'codigo_generacion': row['Codigo_Generacion'],
                            'fecha_emision': row['Fecha_Emision']
                        })
            
            self.stdout.write(
                self.style.SUCCESS(f'✅ {len(ccf_datos)} CCF aceptados encontrados en el CSV')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error leyendo CSV: {str(e)}')
            )
            
        return ccf_datos

    def _crear_nc_bd(self, emisor, numero_correlativo, codigo_generacion, fecha_actual, hora_actual, ccf_relacionado):
        """Crea la Nota de Crédito completa en la base de datos"""
        
        with transaction.atomic():
            # 1. Obtener o crear producto
            producto, created = Producto.objects.get_or_create(
                codigo1='PROD-1',
                defaults={
                    'nombre': 'Repuesto 1',
                    'descripcion': 'Repuesto de prueba para NC',
                    'precio1': 100.00,
                    'existencias': 1000
                }
            )
            
            # 2. Crear o obtener receptor (mismo que CCF)
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
            
            # 3. Crear identificación NC
            establecimiento = emisor.codEstable or "0001"
            punto_venta = emisor.codPuntoVenta or "0001"
            numero_control = f"DTE-05-{establecimiento.zfill(4)}{punto_venta.zfill(4)}-{numero_correlativo:015d}"
            
            # Convertir fecha y hora de string a objetos datetime
            fecha_obj = datetime.strptime(fecha_actual, '%Y-%m-%d').date()
            hora_obj = datetime.strptime(hora_actual, '%H:%M:%S').time()
            
            identificacion = Identificacion.objects.create(
                version=3,  # NC usa versión 3
                ambiente=AmbienteDestino.objects.get(codigo="00"),
                tipoDte=TipoDocumento.objects.get(codigo="05"),  # Nota de Crédito
                numeroControl=numero_control,
                codigoGeneracion=codigo_generacion,
                tipoModelo=ModeloFacturacion.objects.get(codigo="1"),
                tipoOperacion=TipoTransmision.objects.get(codigo="1"),
                fecEmi=fecha_obj,
                horEmi=hora_obj,
                tipoMoneda="USD"
            )
            
            # 4. Crear factura NC
            factura = FacturaElectronica.objects.create(
                identificacion=identificacion,
                emisor=emisor,
                receptor=receptor
            )
            
            # 5. Crear documento relacionado (CCF original)
            DocumentoRelacionado.objects.create(
                factura=factura,
                tipoDocumento=TipoDocumento.objects.get(codigo="03"),  # CCF
                tipoGeneracion=GeneracionDocumento.objects.get(codigo="2"),  # Código de generación
                numeroDocumento=ccf_relacionado["codigo_generacion"],  # UUID del CCF
                fechaEmision=datetime.strptime(ccf_relacionado["fecha_emision"], '%Y-%m-%d').date()
            )
            
            # 6. Crear detalle de NC (sin modelo específico, se manejará en el JSON)
            # NotaCreditoDetalle se creará automáticamente o se manejará en build_dte_json
            
            # 7. Crear item (datos exactos del JSON exitoso de NC)
            cantidad = ajustar_precision_items(1.0)
            precio_unitario = ajustar_precision_items(88.5)  # Precio sin IVA
            venta_gravada = ajustar_precision_items(88.5)
            
            item = CuerpoDocumentoItem.objects.create(
                factura=factura,
                numItem=1,
                tipoItem=TipoItem.objects.get(codigo="1"),
                numeroDocumento=ccf_relacionado["codigo_generacion"],  # IMPORTANTE: UUID del CCF relacionado
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
                ivaItem=ajustar_precision_items(0.0)  # NC no lleva ivaItem
            )
            
            # Agregar tributo IVA al item
            tributo_iva = Tributo.objects.get(codigo="20")
            item.tributos.add(tributo_iva)
            
            # 8. Crear resumen NC (valores exactos del JSON exitoso)
            total_gravada = ajustar_precision_resumen(88.5)
            total_iva = ajustar_precision_resumen(11.5)
            monto_total_operacion = ajustar_precision_resumen(100.0)
            
            resumen = Resumen.objects.create(
                factura=factura,
                totalNoSuj=ajustar_precision_resumen(0.0),
                totalExenta=ajustar_precision_resumen(0.0),
                totalGravada=total_gravada,
                subTotalVentas=total_gravada,
                descuNoSuj=ajustar_precision_resumen(0.0),
                descuExenta=ajustar_precision_resumen(0.0),
                descuGravada=ajustar_precision_resumen(0.0),
                porcentajeDescuento=ajustar_precision_resumen(0.0),  # AGREGADO: Campo requerido
                totalDescu=ajustar_precision_resumen(0.0),
                subTotal=total_gravada,
                ivaPerci1=ajustar_precision_resumen(0.0),
                ivaRete1=ajustar_precision_resumen(0.0),
                reteRenta=ajustar_precision_resumen(0.0),
                montoTotalOperacion=monto_total_operacion,
                totalNoGravado=ajustar_precision_resumen(0.0),  # AGREGADO: Campo posiblemente requerido
                totalPagar=monto_total_operacion,  # AGREGADO: Campo posiblemente requerido
                totalLetras=numero_a_letras(monto_total_operacion),
                saldoFavor=ajustar_precision_resumen(0.0),  # AGREGADO: Campo posiblemente requerido
                condicionOperacion=CondicionOperacion.objects.get(codigo="1"),
                numPagoElectronico=""  # AGREGADO: Campo posiblemente requerido
            )
            
            # 9. Crear tributo IVA en resumen
            TributoResumen.objects.create(
                resumen=resumen,
                codigo=tributo_iva,
                descripcion="Impuesto al Valor Agregado 13%",
                valor=total_iva
            )
            
            return factura

    def _enviar_nc_directo(self, dte_json, servicio, token, codigo_generacion):
        """Envía la NC a Hacienda"""
        try:
            # DEBUG: Mostrar identificación y documento relacionado
            self.stdout.write('='*40)
            self.stdout.write('IDENTIFICACIÓN DE LA NC:')
            self.stdout.write(json.dumps(dte_json["identificacion"], indent=2, ensure_ascii=False))
            self.stdout.write('DOCUMENTO RELACIONADO:')
            self.stdout.write(json.dumps(dte_json.get("documentoRelacionado", []), indent=2, ensure_ascii=False))
            self.stdout.write('='*40)
            
            # Enviar a Hacienda
            respuesta = servicio.enviar_a_hacienda(
                token=token,
                codigo_generacion=codigo_generacion,
                tipo_dte='05',  # Nota de Crédito
                dte_json=dte_json
            )
            
            # DEBUG: Mostrar respuesta
            self.stdout.write('RESPUESTA DE HACIENDA PARA NC:')
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

    def _guardar_en_csv(self, csv_path, numero_nc, numero_control, codigo_generacion, 
                       fecha_emision, hora_emision, estado_hacienda, sello_recepcion, 
                       fecha_envio, ccf_relacionado, fecha_ccf):
        """Guarda los datos de la NC en el archivo CSV"""
        try:
            with open(csv_path, 'a', newline='', encoding='utf-8') as csvfile:
                csv_writer = csv.writer(csvfile)
                csv_writer.writerow([
                    numero_nc,
                    numero_control,
                    codigo_generacion,
                    fecha_emision,
                    hora_emision,
                    estado_hacienda,
                    sello_recepcion,
                    fecha_envio,
                    ccf_relacionado,
                    fecha_ccf
                ])
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'Error guardando en CSV: {str(e)}')
            )

    def _mostrar_resumen_final(self, exitosas, fallidas, csv_path):
        """Muestra resumen final con información del CSV y BD"""
        self.stdout.write('\n' + '='*50)
        self.stdout.write(
            self.style.SUCCESS(f'RESUMEN FINAL NOTAS DE CRÉDITO:')
        )
        self.stdout.write(f'NC exitosas: {exitosas}')
        self.stdout.write(f'NC fallidas: {fallidas}')
        self.stdout.write(f'Total procesadas: {exitosas + fallidas}')
        self.stdout.write('\n💾 GUARDADO COMPLETO:')
        self.stdout.write(f'   ✅ Base de Datos: {exitosas + fallidas} NC completas')
        self.stdout.write(f'   ✅ Archivo CSV: {csv_path}')
        self.stdout.write(f'   📊 Puedes consultar las NC en tu aplicación web')
        self.stdout.write('\n📄 COLUMNAS DEL CSV:')
        self.stdout.write('   - Numero_NC, Numero_Control_NC, Codigo_Generacion_NC,')
        self.stdout.write('   - Fecha_Emision_NC, Hora_Emision_NC, Estado_Hacienda,')
        self.stdout.write('   - Sello_Recepcion, Fecha_Envio, CCF_Relacionado, Fecha_CCF_Relacionado')
        self.stdout.write('='*50)