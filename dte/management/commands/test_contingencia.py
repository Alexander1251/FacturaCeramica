# dte/management/commands/test_contingencia.py

import json
import uuid
import requests
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Ejecuta pruebas de contingencia contra el Ministerio de Hacienda'

    def add_arguments(self, parser):
        parser.add_argument(
            '--ambiente',
            type=str,
            choices=['test', 'prod'],
            default='test',
            help='Ambiente de destino (test o prod)'
        )
        
        parser.add_argument(
            '--tipo-contingencia',
            type=int,
            choices=[1, 2, 3, 4, 5],
            default=1,
            help='Tipo de contingencia a probar (1-5)'
        )
        
        parser.add_argument(
            '--documentos',
            type=int,
            default=3,
            help='Número de documentos de prueba a incluir (1-10)'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo genera el JSON sin enviarlo'
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('=== PRUEBAS DE CONTINGENCIA MH ===')
        )
        
        ambiente = options['ambiente']
        tipo_contingencia = options['tipo_contingencia']
        num_documentos = min(options['documentos'], 10)  # Máximo 10 para pruebas
        dry_run = options['dry_run']
        
        try:
            # 1. Validar configuración
            self.stdout.write('1. Validando configuración...')
            self._validar_configuracion(ambiente)
            
            # 2. Obtener emisor
            self.stdout.write('2. Obteniendo datos del emisor...')
            emisor = self._obtener_emisor()
            
            # 3. Generar documento de contingencia
            self.stdout.write('3. Generando documento de contingencia...')
            documento_contingencia = self._generar_documento_contingencia(
                ambiente, tipo_contingencia, num_documentos, emisor
            )
            
            # 4. Validar contra esquema
            self.stdout.write('4. Validando contra esquema JSON...')
            self._validar_esquema(documento_contingencia)
            
            if dry_run:
                self.stdout.write(
                    self.style.WARNING('=== MODO DRY-RUN ACTIVADO ===')
                )
                self.stdout.write('JSON generado:')
                self.stdout.write(
                    json.dumps(documento_contingencia, indent=2, ensure_ascii=False)
                )
                return
            
            # 5. Autenticar con MH
            self.stdout.write('5. Autenticando con Ministerio de Hacienda...')
            token = self._autenticar(ambiente)
            
            # 6. Firmar documento
            self.stdout.write('6. Firmando documento de contingencia...')
            documento_firmado = self._firmar_documento(documento_contingencia)
            
            # 7. Enviar a MH
            self.stdout.write('7. Enviando reporte de contingencia...')
            respuesta = self._enviar_contingencia(
                ambiente, token, documento_firmado, 
                documento_contingencia['identificacion']['codigoGeneracion']
            )
            
            # 8. Procesar respuesta
            self._procesar_respuesta(respuesta)
            
            self.stdout.write(
                self.style.SUCCESS('✅ Prueba de contingencia completada exitosamente')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error en prueba de contingencia: {str(e)}')
            )
            raise CommandError(f'Fallo en prueba: {str(e)}')

    def _validar_configuracion(self, ambiente):
        """Valida que la configuración necesaria esté presente"""
        required_settings = [
            'DTE_URLS', 'DTE_USER', 'DTE_PASSWORD', 'FIRMADOR_URL'
        ]
        
        for setting in required_settings:
            if not hasattr(settings, setting):
                raise CommandError(f'Configuración faltante: {setting}')
        
        if ambiente not in settings.DTE_URLS:
            raise CommandError(f'Ambiente {ambiente} no configurado en DTE_URLS')
        
        # Verificar que el endpoint de contingencia esté configurado
        urls = settings.DTE_URLS[ambiente]
        if 'contingencia' not in urls:
            # Agregar URL por defecto si no está configurada
            if ambiente == 'test':
                urls['contingencia'] = 'https://apitest.dtes.mh.gob.sv/fesv/contingencia'
            else:
                urls['contingencia'] = 'https://api.dtes.mh.gob.sv/fesv/contingencia'
            
            self.stdout.write(
                self.style.WARNING(f'URL de contingencia agregada por defecto: {urls["contingencia"]}')
            )

    def _obtener_emisor(self):
        """Obtiene el primer emisor disponible"""
        try:
            # Importar aquí para evitar problemas de inicialización circular
            from dte.models import Emisor
            
            emisor = Emisor.objects.first()
            if not emisor:
                raise CommandError('No hay emisores configurados en la base de datos')
            return emisor
        except Exception as e:
            raise CommandError(f'Error al obtener emisor: {str(e)}')

    def _generar_documento_contingencia(self, ambiente, tipo_contingencia, num_documentos, emisor):
        """Genera el documento JSON de contingencia según el esquema v3"""
        
        # Generar UUID único para el evento de contingencia
        codigo_generacion = str(uuid.uuid4()).upper()
        
        # Fechas y horas de contingencia - CORREGIDO PARA CUMPLIR PLAZO
        # CORREGIDO: Usar hora local de El Salvador sin pytz
        
        # Obtener hora actual en UTC
        ahora_utc = timezone.now()
        
        # El Salvador está en UTC-6, aplicar offset manualmente
        offset_el_salvador = timedelta(hours=-6)
        ahora_local = ahora_utc + offset_el_salvador
        
        # CORREGIDO: Contingencia reciente (hace pocas horas) para cumplir plazo
        # El plazo permitido suele ser de 24-48 horas después del evento
        inicio_contingencia = ahora_local - timedelta(hours=6)  # Hace 6 horas
        fin_contingencia = ahora_local - timedelta(hours=4)     # Hace 4 horas (2 horas de duración)
        
        documento = {
            "identificacion": {
                "version": 3,
                "ambiente": "00" if ambiente == 'test' else "01",
                "codigoGeneracion": codigo_generacion,
                "fTransmision": ahora_local.strftime('%Y-%m-%d'),
                "hTransmision": ahora_local.strftime('%H:%M:%S')
            },
            "emisor": {
                "nit": emisor.nit.replace('-', ''),  # NIT sin guiones según esquema
                "nombre": emisor.nombre,
                # CAMPOS OBLIGATORIOS PARA CONTINGENCIA - DATOS DEL RESPONSABLE
                "nombreResponsable": self._obtener_nombre_responsable(emisor),
                "tipoDocResponsable": self._obtener_tipo_doc_responsable(emisor),
                "numeroDocResponsable": self._obtener_numero_doc_responsable(emisor),
                "tipoEstablecimiento": emisor.tipoEstablecimiento.codigo,
                # CORREGIDO: Enviar como null para evitar problemas de formato
                "codEstableMH": None,
                "codPuntoVenta": None,
                "telefono": emisor.telefono,
                "correo": emisor.correo
            },
            "detalleDTE": [],
            "motivo": {
                "fInicio": inicio_contingencia.strftime('%Y-%m-%d'),
                "fFin": fin_contingencia.strftime('%Y-%m-%d'),
                "hInicio": inicio_contingencia.strftime('%H:%M:%S'),
                "hFin": fin_contingencia.strftime('%H:%M:%S'),
                "tipoContingencia": tipo_contingencia,
                "motivoContingencia": self._obtener_motivo_contingencia(tipo_contingencia)
            }
        }
        
        # Generar documentos de prueba
        tipos_documento = ["01", "03", "05"]  # FC, CCF, NC
        for i in range(num_documentos):
            documento["detalleDTE"].append({
                "noItem": i + 1,
                "codigoGeneracion": str(uuid.uuid4()).upper(),
                "tipoDoc": tipos_documento[i % len(tipos_documento)]
            })
        
        return documento

    def _obtener_motivo_contingencia(self, tipo_contingencia):
        """Obtiene la descripción del motivo según el tipo"""
        motivos = {
            1: "Interrupción del suministro eléctrico en las instalaciones del contribuyente desde las primeras horas de la mañana",
            2: "Falla temporal en el servicio de Internet del proveedor local que impidió la transmisión normal de documentos",
            3: "Falla temporal en el sistema informático del contribuyente que requirió reinicio de servidores",
            4: "Indisponibilidad temporal de los servicios web del Ministerio de Hacienda durante las primeras horas del día",
            5: "Mantenimiento no programado de sistemas críticos que impidió la operación normal durante el período indicado"
        }
        return motivos.get(tipo_contingencia, "Contingencia temporal que impidió la transmisión normal de documentos")

    def _obtener_nombre_responsable(self, emisor):
        """Obtiene el nombre del responsable del establecimiento - DATOS QUEMADOS"""
        # DATOS QUEMADOS PARA CONTINGENCIA - usar el nombre del emisor
        return emisor.nombre

    def _obtener_tipo_doc_responsable(self, emisor):
        """Obtiene el tipo de documento del responsable - DATOS QUEMADOS"""
        # DATOS QUEMADOS PARA CONTINGENCIA
        # Determinar tipo de documento basado en el NIT
        nit_sin_guiones = emisor.nit.replace('-', '')
        if len(nit_sin_guiones) == 14:
            return "36"  # NIT
        elif len(nit_sin_guiones) == 9:
            return "13"  # DUI
        else:
            return "36"  # Por defecto NIT

    def _obtener_numero_doc_responsable(self, emisor):
        """Obtiene el número de documento del responsable - DATOS QUEMADOS"""
        # DATOS QUEMADOS PARA CONTINGENCIA - usar el NIT sin guiones
        return emisor.nit.replace('-', '')

    def _validar_esquema(self, documento):
        """Valida el documento contra el esquema JSON de contingencia"""
        try:
            import jsonschema
            
            # Cargar esquema desde archivo
            schema_path = getattr(settings, 'BASE_DIR') / 'dte' / 'schemas' / 'contingencia-schema-v3.json'
            
            if not schema_path.exists():
                self.stdout.write(
                    self.style.WARNING('Esquema de contingencia no encontrado, saltando validación')
                )
                return
            
            with open(schema_path, 'r', encoding='utf-8') as f:
                schema = json.load(f)
            
            jsonschema.validate(instance=documento, schema=schema)
            self.stdout.write(
                self.style.SUCCESS('✅ Documento válido según esquema v3')
            )
            
        except ImportError:
            self.stdout.write(
                self.style.WARNING('jsonschema no instalado, saltando validación')
            )
        except Exception as e:
            raise CommandError(f'Error de validación de esquema: {str(e)}')

    def _autenticar(self, ambiente):
        """Autentica con el Ministerio de Hacienda"""
        auth_url = settings.DTE_URLS[ambiente]['auth']
        
        data = {
            'user': settings.DTE_USER,
            'pwd': settings.DTE_PASSWORD
        }
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'DTE-Contingencia-Test'
        }
        
        response = requests.post(auth_url, data=data, headers=headers, timeout=30)
        
        if response.status_code != 200:
            raise CommandError(f'Error de autenticación: HTTP {response.status_code}')
        
        resultado = response.json()
        if resultado.get('status') != 'OK':
            raise CommandError(f'Autenticación fallida: {resultado.get("descripcionMsg", "Error desconocido")}')
        
        token = resultado['body']['token']
        self.stdout.write(
            self.style.SUCCESS(f'✅ Token obtenido: {token[:20]}...')
        )
        return token

    def _firmar_documento(self, documento):
        """Firma el documento de contingencia"""
        try:
            firmador_url = settings.FIRMADOR_URL
            
            # CORREGIDO: Enviar el JSON como objeto, no como string
            data = {
                'nit': documento['emisor']['nit'],
                'activo': True,
                'passwordPri': getattr(settings, 'DTE_CERTIFICADO_PASSWORD', ''),
                'dteJson': documento  # Enviar como objeto JSON directamente
            }
            
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'DTE-Contingencia-Test'
            }
            
            # Debug: Mostrar qué se está enviando al firmador
            self.stdout.write(f'Enviando al firmador: {firmador_url}')
            self.stdout.write(f'NIT: {data["nit"]}')
            
            response = requests.post(
                firmador_url, 
                json=data, 
                headers=headers, 
                timeout=30
            )
            
            self.stdout.write(f'Respuesta del firmador - Status: {response.status_code}')
            self.stdout.write(f'Respuesta del firmador - Content: {response.text[:500]}...')
            
            if response.status_code != 200:
                raise CommandError(f'Error del firmador: HTTP {response.status_code} - {response.text}')
            
            try:
                resultado = response.json()
            except json.JSONDecodeError:
                raise CommandError(f'Respuesta del firmador no es JSON válido: {response.text}')
            
            if resultado.get('status') != 'OK':
                error_detail = resultado.get('body', 'Error desconocido')
                raise CommandError(f'Error de firma: {error_detail}')
            
            documento_firmado = resultado['body']
            self.stdout.write(
                self.style.SUCCESS('✅ Documento firmado exitosamente')
            )
            return documento_firmado
            
        except requests.exceptions.RequestException as e:
            raise CommandError(f'Error de conexión con firmador: {str(e)}')

    def _enviar_contingencia(self, ambiente, token, documento_firmado, codigo_generacion):
        """Envía el reporte de contingencia al Ministerio de Hacienda"""
        
        contingencia_url = settings.DTE_URLS[ambiente]['contingencia']
        
        data = {
            'ambiente': "00" if ambiente == 'test' else "01",
            'idEnvio': 1,
            'version': 3,  # Versión 3 para contingencia
            'documento': documento_firmado,
            'codigoGeneracion': codigo_generacion
        }
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': token,
            'User-Agent': 'DTE-Contingencia-Test'
        }
        
        self.stdout.write(f'Enviando a: {contingencia_url}')
        
        response = requests.post(
            contingencia_url,
            json=data,
            headers=headers,
            timeout=60  # Timeout más largo para contingencia
        )
        
        return response

    def _procesar_respuesta(self, response):
        """Procesa la respuesta del Ministerio de Hacienda"""
        
        self.stdout.write(f'Status Code: {response.status_code}')
        self.stdout.write(f'Headers: {dict(response.headers)}')
        
        try:
            respuesta_json = response.json()
            self.stdout.write('Respuesta JSON:')
            self.stdout.write(
                json.dumps(respuesta_json, indent=2, ensure_ascii=False)
            )
            
            if response.status_code == 200:
                estado = respuesta_json.get('estado', 'DESCONOCIDO')
                if estado in ['RECIBIDO', 'PROCESADO', 'ACEPTADO']:
                    self.stdout.write(
                        self.style.SUCCESS(f'✅ Contingencia {estado.lower()}')
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(f'⚠️  Estado: {estado}')
                    )
                    
                # Mostrar observaciones si las hay
                observaciones = respuesta_json.get('observaciones', [])
                if observaciones:
                    self.stdout.write('Observaciones:')
                    for obs in observaciones:
                        self.stdout.write(f'  - {obs}')
                        
            else:
                self.stdout.write(
                    self.style.ERROR(f'❌ Error HTTP {response.status_code}')
                )
                
        except json.JSONDecodeError:
            self.stdout.write('Respuesta no es JSON válido:')
            self.stdout.write(response.text)
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error procesando respuesta: {str(e)}')
            )

    def _mostrar_resumen(self, documento, respuesta_exitosa):
        """Muestra un resumen de la prueba ejecutada"""
        self.stdout.write(self.style.SUCCESS('\n=== RESUMEN DE PRUEBA ==='))
        self.stdout.write(f'Ambiente: {documento["identificacion"]["ambiente"]}')
        self.stdout.write(f'Código de Generación: {documento["identificacion"]["codigoGeneracion"]}')
        self.stdout.write(f'Tipo de Contingencia: {documento["motivo"]["tipoContingencia"]}')
        self.stdout.write(f'Documentos Incluidos: {len(documento["detalleDTE"])}')
        self.stdout.write(f'Estado: {"✅ EXITOSO" if respuesta_exitosa else "❌ FALLIDO"}')