from django.core.management.base import BaseCommand
from dte.models import FacturaElectronica

class Command(BaseCommand):
    help = 'Elimina todas las facturas electrónicas de la base de datos'

    def handle(self, *args, **options):
        count = FacturaElectronica.objects.count()
        FacturaElectronica.objects.all().delete()
        self.stdout.write(
            self.style.SUCCESS(f'Se eliminaron {count} facturas correctamente')
        )