import os
from decimal import Decimal
from django.core.management.base import BaseCommand
from dbfread import DBF
from productos.models import Producto, Categoria, Proveedor

class Command(BaseCommand):
    help = 'Carga datos desde el archivo DBF INVCOM.DBF ubicado en fixtures/'

    def handle(self, *args, **kwargs):
        path_dbf = os.path.join('dte', 'fixtures', 'INVCOM.DBF')

        if not os.path.exists(path_dbf):
            self.stderr.write(self.style.ERROR(f"Archivo no encontrado: {path_dbf}"))
            return

        # Obtener la primera categoría y proveedor
        categoria_default = Categoria.objects.first()
        proveedor_default = Proveedor.objects.first()

        if not categoria_default or not proveedor_default:
            self.stderr.write(self.style.ERROR("Debe haber al menos una categoría y un proveedor en la base de datos."))
            return

        dbf = DBF(path_dbf, load=True)
        count = 0

        for record in dbf:
            try:
                nombre = record.get('NOMBRE', '').strip() or 'Sin nombre'
                descripcion = record.get('OBSERVA', '') or ''

                codigos = [record.get('CODIGO', '').strip(),
                           record.get('CODIGO2', '').strip() if record.get('CODIGO2') else '',
                           '', '']

                precios = [record.get('PRECIO', 0.0),
                           record.get('PRECIO2', None),
                           record.get('TOTAL', None),
                           record.get('PROMEDIO', None)]

                producto = Producto(
                    nombre=nombre,
                    descripcion=descripcion,
                    codigo1=codigos[0] or f"GEN-{count}",
                    codigo2=codigos[1] or None,
                    codigo3=codigos[2] or None,
                    codigo4=codigos[3] or None,
                    precio1=Decimal(precios[0]) if precios[0] else Decimal('0.00'),
                    precio2=Decimal(precios[1]) if precios[1] else None,
                    precio3=Decimal(precios[2]) if precios[2] else None,
                    precio4=Decimal(precios[3]) if precios[3] else None,
                    descuento_por_defecto=int(record.get('DESCUENTO', 0) or 0),
                    existencias=int(record.get('CANT', 0)),
                    categoria=categoria_default or 1,
                    proveedor=proveedor_default or 1
                )
                producto.save()
                count += 1
            except Exception as e:
                self.stderr.write(self.style.WARNING(f"Error en registro {count}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"Se cargaron {count} productos desde el DBF."))