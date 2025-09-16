# dte/management/commands/enviar_25_fse_simple.py

import time
import json
import uuid
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone

from dte.services import DTEService
from dte.models import Emisor


class Command(BaseCommand):
    help = 'Envía 25 FSE usando plantilla JSON exitosa - solo cambia correlativo, fecha, hora y códigos'

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
            self.style.SUCCESS('Iniciando envío de 25 FSE usando plantilla JSON exitosa')
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
            
            # Plantilla JSON base (tu ejemplo exitoso de FSE)
            plantilla_json = {
                "identificacion": {
                    "version": 1,
                    "ambiente": "00",
                    "tipoDte": "14",
                    "numeroControl": "DTE-14-00010001-000000000000006",  # Se cambiará
                    "codigoGeneracion": "9C7E54DB-3324-49C1-B6DC-50F995B21E24",  # Se cambiará
                    "tipoModelo": 1,
                    "tipoOperacion": 1,
                    "tipoContingencia": None,
                    "motivoContin": None,
                    "fecEmi": "2025-07-22",  # Se cambiará
                    "horEmi": "14:39:45",    # Se cambiará
                    "tipoMoneda": "USD"
                },
                "emisor": {
                    "nit": "07152710640010",
                    "nrc": "655139",
                    "nombre": "DANIEL DE JESUS LANDAVERDE",
                    "codActividad": "45301",
                    "descActividad": "Venta de partes, piezas y accesorios nuevos para vehiculos automotores",
                    "direccion": {
                        "departamento": "06",
                        "municipio": "23",
                        "complemento": "29 AVENIDA NORTE Y CALLE AL VOLCAN, LOCAL No 3, FRENTE A GASOLINERA UNO, COLONIA ZACAMIL, MEJICANOS, SAN SALVADOR"
                    },
                    "telefono": "22726991",
                    "codEstableMH": "0001",
                    "codEstable": "0001",
                    "codPuntoVentaMH": "0001",
                    "codPuntoVenta": "0001",
                    "correo": "landaverdedaniel184@gmail.com"
                },
                "sujetoExcluido": {
                    "tipoDocumento": "13",
                    "numDocumento": "000000009",
                    "nombre": "Juan Perez",
                    "codActividad": None,
                    "descActividad": None,
                    "direccion": {
                        "departamento": "01",
                        "municipio": "14",
                        "complemento": "Proveedor direccion"
                    },
                    "telefono": "70000000",
                    "correo": "alexanderalfaro1251@gmail.com"
                },
                "cuerpoDocumento": [
                    {
                        "numItem": 1,
                        "tipoItem": 1,
                        "cantidad": 1.0,
                        "codigo": "PROD-1",
                        "uniMedida": 59,
                        "descripcion": "Repuesto 1",
                        "precioUni": 100.0,
                        "montoDescu": 0.0,
                        "compra": 100.0
                    }
                ],
                "resumen": {
                    "totalCompra": 100.0,
                    "descu": 0.0,
                    "totalDescu": 0.0,
                    "subTotal": 100.0,
                    "ivaRete1": 0.0,
                    "reteRenta": 0.0,
                    "totalPagar": 100.0,
                    "totalLetras": "CIEN DÓLARES",
                    "condicionOperacion": 1,
                    "pagos": None,
                    "observaciones": ""
                },
                "apendice": None
            }
            
            # Calcular número inicial (después del 6 del ejemplo)
            numero_inicial = 8
            
            exitosas = 0
            fallidas = 0
            
            for i in range(25):
                try:
                    numero_correlativo = numero_inicial + i
                    
                    self.stdout.write(f'Enviando FSE {i+1}/25 (correlativo {numero_correlativo})...')
                    
                    # Crear copia del JSON plantilla
                    dte_json = json.loads(json.dumps(plantilla_json))  # Deep copy
                    
                    # Actualizar campos que cambian
                    ahora = timezone.now()
                    fecha_actual = ahora.strftime('%Y-%m-%d')
                    hora_actual = ahora.strftime('%H:%M:%S')
                    nuevo_codigo_generacion = str(uuid.uuid4()).upper()
                    nuevo_numero_control = f"DTE-14-00010001-{numero_correlativo:015d}"
                    
                    # Aplicar cambios
                    dte_json["identificacion"]["numeroControl"] = nuevo_numero_control
                    dte_json["identificacion"]["codigoGeneracion"] = nuevo_codigo_generacion
                    dte_json["identificacion"]["fecEmi"] = fecha_actual
                    dte_json["identificacion"]["horEmi"] = hora_actual
                    
                    # DEBUG: Mostrar campos cambiados
                    self.stdout.write(f'  Número Control: {nuevo_numero_control}')
                    self.stdout.write(f'  Código Generación: {nuevo_codigo_generacion}')
                    self.stdout.write(f'  Fecha: {fecha_actual} {hora_actual}')
                    
                    # Enviar a Hacienda
                    resultado = self._enviar_json_directo(dte_json, servicio, token, nuevo_codigo_generacion)
                    
                    if resultado['estado'] == 'PROCESADO':
                        exitosas += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'✓ FSE {nuevo_numero_control} enviada exitosamente'
                            )
                        )
                        self.stdout.write(
                            self.style.SUCCESS(f'  ✅ Sello: {resultado.get("sello", "N/A")}')
                        )
                    else:
                        fallidas += 1
                        error_msg = resultado.get("descripcion", "Error desconocido")
                        self.stdout.write(
                            self.style.ERROR(
                                f'✗ FSE RECHAZADA: {nuevo_numero_control}'
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
                            self.style.ERROR('\n🛑 SCRIPT DETENIDO: FSE rechazada por Hacienda')
                        )
                        self._mostrar_resumen_final(exitosas, fallidas)
                        return
                    
                    # Esperar antes del siguiente envío (excepto en la última)
                    if i < 24:
                        self.stdout.write(f'Esperando {delay} segundos...')
                        time.sleep(delay)
                        
                except Exception as e:
                    fallidas += 1
                    self.stdout.write(
                        self.style.ERROR(f'✗ EXCEPCIÓN EN FSE {i+1}: {str(e)}')
                    )
                    
                    # DETENER TAMBIÉN POR EXCEPCIONES CRÍTICAS
                    self.stdout.write(
                        self.style.ERROR('\n🛑 SCRIPT DETENIDO: Error crítico en el proceso')
                    )
                    self._mostrar_resumen_final(exitosas, fallidas)
                    return
            
            # Resumen final
            self._mostrar_resumen_final(exitosas, fallidas)
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error general: {str(e)}')
            )

    def _enviar_json_directo(self, dte_json, servicio, token, codigo_generacion):
        """Envía el JSON directamente a Hacienda"""
        try:
            # DEBUG: Mostrar solo la identificación y sujetoExcluido
            self.stdout.write('='*40)
            self.stdout.write('IDENTIFICACIÓN FSE:')
            self.stdout.write(json.dumps(dte_json["identificacion"], indent=2, ensure_ascii=False))
            self.stdout.write('SUJETO EXCLUIDO:')
            self.stdout.write(json.dumps(dte_json["sujetoExcluido"], indent=2, ensure_ascii=False))
            self.stdout.write('='*40)
            
            # Enviar a Hacienda usando el método existente
            respuesta = servicio.enviar_a_hacienda(
                token=token,
                codigo_generacion=codigo_generacion,
                tipo_dte='14',  # FSE
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

    def _mostrar_resumen_final(self, exitosas, fallidas):
        """Muestra resumen final"""
        self.stdout.write('\n' + '='*50)
        self.stdout.write(
            self.style.SUCCESS(f'RESUMEN FINAL FSE:')
        )
        self.stdout.write(f'FSE exitosas: {exitosas}')
        self.stdout.write(f'FSE fallidas: {fallidas}')
        self.stdout.write(f'Total procesadas: {exitosas + fallidas}')
        self.stdout.write('\n📄 SOLO ENVÍO DIRECTO:')
        self.stdout.write(f'   ✅ No se guardan en BD (solo envío a Hacienda)')
        self.stdout.write(f'   📊 JSON exacto del ejemplo exitoso')
        self.stdout.write('='*50)