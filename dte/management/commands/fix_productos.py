from django.core.management.base import BaseCommand
from productos.models import Producto

class Command(BaseCommand):
    help = 'Actualiza las descripciones vacías de productos a "Sin descripción"'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo mostrar qué productos se actualizarían sin hacer cambios',
        )

    def handle(self, *args, **options):
        # Buscar productos sin descripción o con descripción vacía
        productos_sin_descripcion = Producto.objects.filter(
            descripcion__in=['', None]
        ) | Producto.objects.filter(descripcion__isnull=True)
        
        count = productos_sin_descripcion.count()
        
        if count == 0:
            self.stdout.write(
                self.style.SUCCESS('✅ No hay productos sin descripción')
            )
            return
        
        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING(f'🔍 SIMULACIÓN: Se actualizarían {count} productos:')
            )
            for producto in productos_sin_descripcion:
                self.stdout.write(f'   - {producto.nombre} (ID: {producto.id})')
        else:
            # Actualizar productos
            updated = productos_sin_descripcion.update(descripcion='Sin descripción')
            
            self.stdout.write(
                self.style.SUCCESS(f'✅ {updated} productos actualizados con "Sin descripción"')
            )
            
            # Mostrar algunos ejemplos
            if updated > 0:
                ejemplos = Producto.objects.filter(descripcion='Sin descripción')[:5]
                self.stdout.write('\n📋 Ejemplos de productos actualizados:')
                for producto in ejemplos:
                    self.stdout.write(f'   - {producto.nombre} (ID: {producto.id})')
                
                if updated > 5:
                    self.stdout.write(f'   ... y {updated - 5} más')