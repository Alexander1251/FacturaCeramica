# dte/management/commands/verificar_certificado.py

from django.core.management.base import BaseCommand
from django.conf import settings
from dte.models import Emisor
import os
import requests

class Command(BaseCommand):
    help = 'Verifica la configuración del certificado para firma electrónica'

    def handle(self, *args, **options):
        self.stdout.write('=' * 60)
        self.stdout.write('VERIFICACIÓN DE CERTIFICADO DTE')
        self.stdout.write('=' * 60)
        
        # 1. Verificar emisor en base de datos
        self.stdout.write('\n1. VERIFICANDO EMISOR:')
        try:
            emisor = Emisor.objects.first()
            if emisor:
                self.stdout.write(f'  ✓ Emisor encontrado: {emisor.nombre}')
                self.stdout.write(f'  ✓ NIT: {emisor.nit}')
                nit_limpio = emisor.nit.replace('-', '')
                self.stdout.write(f'  ✓ NIT sin guiones: {nit_limpio}')
            else:
                self.stdout.write(self.style.ERROR('  ✗ No hay emisor configurado'))
                return
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  ✗ Error: {str(e)}'))
            return
            
        # 2. Verificar servicio de firma
        self.stdout.write('\n2. VERIFICANDO SERVICIO DE FIRMA:')
        firmador_url = getattr(settings, 'FIRMADOR_URL', 'http://localhost:8113/firmardocumento/')
        
        try:
            # Probar conectividad
            status_url = firmador_url.replace('/firmardocumento/', '/firmardocumento/status')
            response = requests.get(status_url, timeout=5)
            
            if response.status_code == 200:
                self.stdout.write(f'  ✓ Servicio activo en: {firmador_url}')
            else:
                self.stdout.write(self.style.WARNING(f'  ⚠ Servicio responde con código: {response.status_code}'))
                
        except requests.exceptions.ConnectionError:
            self.stdout.write(self.style.ERROR('  ✗ No se puede conectar al servicio de firma'))
            self.stdout.write('    Asegúrese de que el servicio esté ejecutándose:')
            self.stdout.write('    - Docker: docker-compose up -d')
            self.stdout.write('    - Windows Service: verificar en services.msc')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  ✗ Error: {str(e)}'))
            
        # 3. Verificar configuración del certificado
        self.stdout.write('\n3. VERIFICANDO CONFIGURACIÓN:')
        
        # Verificar variables de entorno
        password = getattr(settings, 'DTE_CERTIFICADO_PASSWORD', None)
        if password:
            self.stdout.write('  ✓ DTE_CERTIFICADO_PASSWORD configurado')
        else:
            self.stdout.write(self.style.ERROR('  ✗ DTE_CERTIFICADO_PASSWORD no configurado'))
            
        # 4. Instrucciones para verificar certificado
        self.stdout.write('\n4. VERIFICAR CERTIFICADO MANUALMENTE:')
        self.stdout.write(f'  El certificado debe llamarse: {nit_limpio}.crt')
        self.stdout.write('  Ubicaciones según instalación:')
        self.stdout.write('  - Docker: carpeta /temp/ del contenedor')
        self.stdout.write('  - Windows Service: carpeta configurada en CERTIFICATE_HOME')
        self.stdout.write('  - Proyecto Java: carpeta de certificados')
        
        # 5. Probar firma con datos de prueba
        self.stdout.write('\n5. PROBANDO FIRMA:')
        self.probar_firma(emisor, firmador_url)
        
    def probar_firma(self, emisor, firmador_url):
        """Prueba la firma con un documento de prueba"""
        try:
            # Documento de prueba mínimo
            dte_prueba = {
                "identificacion": {
                    "version": 1,
                    "ambiente": "00",
                    "tipoDte": "01",
                    "numeroControl": "DTE-01-00010001-000000000000001",
                    "codigoGeneracion": "00000000-0000-0000-0000-000000000000",
                    "tipoModelo": 1,
                    "tipoOperacion": 1,
                    "fecEmi": "2025-01-01",
                    "horEmi": "10:00:00",
                    "tipoMoneda": "USD"
                }
            }
            
            data = {
                'nit': emisor.nit,
                'activo': True,
                'passwordPri': getattr(settings, 'DTE_CERTIFICADO_PASSWORD', ''),
                'dteJson': dte_prueba
            }
            
            response = requests.post(
                firmador_url,
                json=data,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                resultado = response.json()
                if resultado.get('status') == 'OK':
                    self.stdout.write(self.style.SUCCESS('  ✓ Prueba de firma EXITOSA'))
                else:
                    error_msg = resultado.get('body', {})
                    if isinstance(error_msg, dict):
                        mensaje = error_msg.get('mensaje', ['Error desconocido'])
                        if isinstance(mensaje, list):
                            mensaje = ', '.join(mensaje)
                    else:
                        mensaje = str(error_msg)
                    self.stdout.write(self.style.ERROR(f'  ✗ Error en firma: {mensaje}'))
            else:
                self.stdout.write(self.style.ERROR(f'  ✗ Error HTTP {response.status_code}'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  ✗ Error en prueba: {str(e)}'))
            
        self.stdout.write('\n' + '=' * 60)