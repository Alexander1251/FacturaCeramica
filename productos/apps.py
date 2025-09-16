from django.apps import AppConfig

class ProductosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'productos'
    
    def ready(self):
        pass  # No need to import signals since they're defined in models.py