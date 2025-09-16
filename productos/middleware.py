from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages

class AdminRequiredMiddleware:
    """
    Middleware que bloquea el acceso a todas las URLs:
    - Solo login y registro para usuarios no autenticados
    - Solo administradores activos para el resto del sistema
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # URLs permitidas SIN autenticación (solo login y registro)
        self.public_urls = [
            '/accounts/login/',
            '/accounts/logout/',  # Logout debe estar disponible
            '/accounts/register/',
            '/login/',
            '/logout/',
            '/registro/',
         
        ]
        
        # URLs permitidas para usuarios autenticados sin permisos
        self.authenticated_urls = [
            '/acceso-denegado/',
            '/accounts/logout/',
            '/logout/',
        ]
        
        # Patrones siempre permitidos (archivos estáticos)
        self.always_allowed_patterns = [
            '/static/',
            '/media/',
        ]

    def __call__(self, request):
        path = request.path
        
        # Siempre permitir archivos estáticos y media
        if self.is_static_url(path):
            return self.get_response(request)
        
        # CASO 1: Usuario NO autenticado
        if not request.user.is_authenticated:
            # Solo permitir URLs públicas
            if path in self.public_urls:
                return self.get_response(request)
            else:
                # Cualquier otra URL -> redirigir al login
                return redirect('login')
        
        # CASO 2: Usuario autenticado pero SIN permisos de administrador
        if not request.user.puede_acceder():
            # Permitir solo URLs básicas para usuarios autenticados
            if path in self.authenticated_urls:
                return self.get_response(request)
            else:
                # Cualquier otra URL -> redirigir a acceso denegado
                return redirect('acceso_denegado')
        
        # CASO 3: Usuario administrador activo -> acceso completo
        return self.get_response(request)
    
    def is_static_url(self, path):
        """Verifica si es una URL de archivos estáticos"""
        for pattern in self.always_allowed_patterns:
            if path.startswith(pattern):
                return True
        return False