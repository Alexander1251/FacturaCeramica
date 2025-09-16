# dte/management/commands/check_dte_services.py

from django.core.management.base import BaseCommand
from django.conf import settings
from dte.services import DTEService
from dte.models import Emisor
import requests


class Command(BaseCommand):
    help = 'Verifica que los servicios necesarios para DTE estén funcionando'

    def handle(self, *args, **options):
        self.stdout.write('=' * 50)
        self.stdout.write('VERIFICACIÓN DE SERVICIOS DTE')
        self.stdout.write('=' * 50)
        
        # 1. Verificar configuración
        self.stdout.write('\n1. CONFIGURACIÓN:')
        self.check_config()
        
        # 2. Verificar servicio de firma
        self.stdout.write('\n2. SERVICIO DE FIRMA:')
        self.check_firmador()
        
        # 3. Verificar conexión con Hacienda
        self.stdout.write('\n3. CONEXIÓN CON HACIENDA:')
        self.check_hacienda()
        
        # 4. Verificar emisor
        self.stdout.write('\n4. EMISOR CONFIGURADO:')
        self.check_emisor()
        
        self.stdout.write('\n' + '=' * 50)
        
    def check_config(self):
        """Verifica que la configuración esté completa"""
        configs = {
            'DTE_AMBIENTE': getattr(settings, 'DTE_AMBIENTE', None),
            'DTE_USER': getattr(settings, 'DTE_USER', None),
            'DTE_PASSWORD': '***' if getattr(settings, 'DTE_PASSWORD', None) else None,
            'FIRMADOR_URL': getattr(settings, 'FIRMADOR_URL', None),
            'DTE_CERTIFICADO_PASSWORD': '***' if getattr(settings, 'DTE_CERTIFICADO_PASSWORD', None) else None,
        }
        
        all_configured = True
        for key, value in configs.items():
            if value:
                self.stdout.write(f'  ✓ {key}: {value}')
            else:
                self.stdout.write(self.style.ERROR(f'  ✗ {key}: NO CONFIGURADO'))
                all_configured = False
                
        if all_configured:
            self.stdout.write(self.style.SUCCESS('  Estado: CONFIGURACIÓN COMPLETA'))
        else:
            self.stdout.write(self.style.ERROR('  Estado: CONFIGURACIÓN INCOMPLETA'))
            
    def check_firmador(self):
        """Verifica que el servicio de firma esté activo"""
        try:
            firmador_url = getattr(settings, 'FIRMADOR_URL', 'http://localhost:8113/firmardocumento/')
            status_url = firmador_url.replace('/firmardocumento/', '/firmardocumento/status')
            
            response = requests.get(status_url, timeout=5)
            if response.status_code == 200:
                self.stdout.write(self.style.SUCCESS(f'  ✓ Servicio activo en: {firmador_url}'))
                self.stdout.write(self.style.SUCCESS('  Estado: FUNCIONANDO'))
            else:
                self.stdout.write(self.style.ERROR(f'  ✗ Servicio responde con código: {response.status_code}'))
                
        except requests.exceptions.ConnectionError:
            self.stdout.write(self.style.ERROR('  ✗ No se puede conectar al servicio de firma'))
            self.stdout.write(self.style.WARNING('  Asegúrese de que el servicio esté ejecutándose'))
            self.stdout.write(self.style.WARNING('  Docker: docker-compose up -d'))
            self.stdout.write(self.style.WARNING('  Windows Service: verificar en services.msc'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  ✗ Error: {str(e)}'))
            
    def check_hacienda(self):
        """Verifica la conexión con los servicios de Hacienda"""
        ambiente = getattr(settings, 'DTE_AMBIENTE', 'test')
        
        urls = {
            'test': {
                'auth': 'https://apitest.dtes.mh.gob.sv/seguridad/auth',
                'recepcion': 'https://apitest.dtes.mh.gob.sv/fesv/recepciondte',
            },
            'prod': {
                'auth': 'https://api.dtes.mh.gob.sv/seguridad/auth',
                'recepcion': 'https://api.dtes.mh.gob.sv/fesv/recepciondte',
            }
        }
        
        self.stdout.write(f'  Ambiente: {ambiente.upper()}')
        
        for servicio, url in urls[ambiente].items():
            try:
                # Solo verificar que el servidor responde
                response = requests.head(url, timeout=5)
                self.stdout.write(f'  ✓ {servicio}: Servidor disponible')
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ✗ {servicio}: No disponible'))
                
    def check_emisor(self):
        """Verifica que exista un emisor configurado"""
        try:
            emisor = Emisor.objects.first()
            if emisor:
                self.stdout.write(f'  ✓ Emisor: {emisor.nombre}')
                self.stdout.write(f'  ✓ NIT: {emisor.nit}')
                self.stdout.write(f'  ✓ NRC: {emisor.nrc}')
                self.stdout.write(self.style.SUCCESS('  Estado: EMISOR CONFIGURADO'))
            else:
                self.stdout.write(self.style.ERROR('  ✗ No hay emisor configurado'))
                self.stdout.write(self.style.WARNING('  Cree un emisor en el admin de Django'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  ✗ Error: {str(e)}'))