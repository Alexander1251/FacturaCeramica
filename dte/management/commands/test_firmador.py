# dte/management/commands/test_firmador.py
# Crear este archivo para probar el servicio de firma

from django.core.management.base import BaseCommand
from django.conf import settings
import requests
import json


class Command(BaseCommand):
    help = 'Prueba la conectividad con el servicio de firmador'

    def handle(self, *args, **options):
        firmador_url = 'http://localhost:8113/firmardocumento/'
        
        # JSON de prueba basado en el ejemplo funcional de Postman
        test_json = {
            "identificacion": {
                "version": 1,
                "ambiente": "00",
                "tipoDte": "01",
                "numeroControl": "DTE-01-000100A1-000000000000005",
                "codigoGeneracion": "BB82C0CC-69C6-47CE-B828-81A2E80ABEA3",
                "tipoModelo": 1,
                "tipoOperacion": 1,
                "tipoContingencia": None,
                "motivoContin": None,
                "fecEmi": "2025-06-24",
                "horEmi": "15:20:46",
                "tipoMoneda": "USD"
            },
            "emisor": {
                "nit": "07152710640010",
                "nrc": "00012345",
                "nombre": "ACME S.A. de C.V."
            },
            "receptor": {
                "tipoDocumento": "13",
                "numDocumento": "12345678-9",
                "nombre": "Test Receptor"
            },
            "cuerpoDocumento": [],
            "resumen": {
                "totalNoSuj": 0.0,
                "totalExenta": 0.0,
                "totalGravada": 100.0,
                "subTotalVentas": 100.0,
                "totalPagar": 113.0
            }
        }
        
        # Preparar datos EXACTAMENTE como en tu ejemplo de Postman que funciona
        data = {
            'nit': '07152710640010',  # Usar tu NIT real
            'activo': True,
            'passwordPri': 'CpIvDjL$271064',  # Usar tu contraseña real
            'dteJson': test_json  # OBJETO JSON, no string
        }
        
        try:
            self.stdout.write('🔄 Probando conexión al firmador...')
            self.stdout.write(f'URL: {firmador_url}')
            self.stdout.write(f'NIT: {data["nit"]}')
            self.stdout.write(f'Formato dteJson: OBJETO (como en Postman)')
            
            response = requests.post(
                firmador_url,
                json=data,  # Esto enviará dteJson como objeto, no como string
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            self.stdout.write(f'📡 Status Code: {response.status_code}')
            self.stdout.write(f'📄 Response: {response.text[:200]}...')
            
            if response.status_code == 200:
                try:
                    resultado = response.json()
                    if resultado.get('status') == 'OK':
                        self.stdout.write(self.style.SUCCESS('✅ Firmador funcionando correctamente'))
                        self.stdout.write(f'📝 Documento firmado (JWS): {resultado["body"][:50]}...')
                    else:
                        self.stdout.write(self.style.ERROR(f'❌ Error del firmador: {resultado}'))
                except json.JSONDecodeError:
                    self.stdout.write(self.style.ERROR(f'❌ Respuesta no es JSON: {response.text}'))
            else:
                self.stdout.write(self.style.ERROR(f'❌ Error HTTP: {response.status_code}'))
                
        except requests.exceptions.ConnectionError:
            self.stdout.write(self.style.ERROR('❌ No se puede conectar al firmador. ¿Está ejecutándose en el puerto 8113?'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error: {str(e)}'))