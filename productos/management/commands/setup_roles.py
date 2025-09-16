from django.core.management.base import BaseCommand
from productos.models import Rol, Usuario

class Command(BaseCommand):
    help = 'Crea los roles iniciales del sistema y configura el primer administrador'

    def add_arguments(self, parser):
        parser.add_argument(
            '--admin-username',
            type=str,
            help='Username del primer administrador a activar',
        )

    def handle(self, *args, **options):
        # Crear roles
        roles = ['administrador', 'usuario']
        
        for rol_nombre in roles:
            rol, created = Rol.objects.get_or_create(nombre=rol_nombre)
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Rol "{rol_nombre}" creado exitosamente')
                )
            else:
                self.stdout.write(f'Rol "{rol_nombre}" ya existe')
        
        # Activar primer administrador si se especifica
        admin_username = options.get('admin_username')
        if admin_username:
            try:
                usuario = Usuario.objects.get(username=admin_username)
                admin_rol = Rol.objects.get(nombre='administrador')
                usuario.rol = admin_rol
                usuario.activo = True
                usuario.is_active = True
                usuario.save()
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Usuario "{admin_username}" configurado como administrador activo'
                    )
                )
            except Usuario.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Usuario "{admin_username}" no encontrado')
                )
            except Rol.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR('Rol "administrador" no encontrado')
                )