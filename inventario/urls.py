from django.contrib import admin
from django.urls import path, include
from productos.views import CustomLoginView, CustomLogoutView, registro
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    # tus vistas de login / logout / register
    path('accounts/login/', CustomLoginView.as_view(), name='login'),
    path('accounts/logout/', CustomLogoutView.as_view(), name='logout'),
    path('accounts/register/', registro, name='register'),

    # después incluyes el resto de auth urls (password_reset, etc)
    path('accounts/', include('django.contrib.auth.urls')),

    # tus URLs de productos
    path('', include('productos.urls')),
    path('dte/', include('dte.urls', namespace='dte')),
]

# CRÍTICO: Esta configuración permite servir archivos media en desarrollo
# CORREGIDO: Verificar que esta línea esté presente y correcta
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)