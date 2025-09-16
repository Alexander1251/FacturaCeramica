# productos/management/commands/delete_products.py

from django.core.management.base import BaseCommand
from productos.models import Producto

class Command(BaseCommand):
    help = 'Elimina todos los productos (sin confirmación)'

    def handle(self, *args, **options):
        count = Producto.objects.count()
        Producto.objects.all().delete()
        self.stdout.write(
            self.style.SUCCESS(f'Se eliminaron {count} productos')
        )