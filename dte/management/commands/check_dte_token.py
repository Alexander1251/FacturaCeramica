# dte/management/commands/check_dte_token.py

from django.core.management.base import BaseCommand
from django.conf import settings
from dte.services import DTEService
from dte.models import Emisor

class Command(BaseCommand):
    help = "Autentica contra Hacienda y muestra el token recibido"

    def add_arguments(self, parser):
        parser.add_argument(
            '--nit',
            type=str,
            help="Nit del emisor a usar para la autenticación (si no se indica, se toma el primero registrado)"
        )

    def handle(self, *args, **options):
        # 1) Seleccionar el emisor
        nit = options.get('nit')
        try:
            if nit:
                emisor = Emisor.objects.get(nit=nit)
            else:
                emisor = Emisor.objects.first()
            if not emisor:
                self.stderr.write(self.style.ERROR("No se encontró ningún Emisor en la base de datos."))
                return
        except Emisor.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"No existe un Emisor con NIT={nit}."))
            return

        # 2) Instanciar el servicio con la configuración correcta
        servicio = DTEService(
            emisor=emisor,
            ambiente=settings.DTE_AMBIENTE,
            firmador_url=settings.FIRMADOR_URL,
            dte_urls=settings.DTE_URLS[settings.DTE_AMBIENTE],
            dte_user=settings.DTE_USER,
            dte_password=settings.DTE_PASSWORD,
        )

        # 3) Intentar autenticarse y mostrar el token
        try:
            token = servicio.autenticar()
            self.stdout.write(self.style.SUCCESS(f"✅ Token recibido:\n{token}"))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"❌ Error al autenticar: {e}"))
