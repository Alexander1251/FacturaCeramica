from django.urls import path
from .views import (
    HomeView,
    CategoriaListView, CategoriaCreateView, CategoriaUpdateView, CategoriaDeleteView,
    ProveedorListView, ProveedorCreateView, ProveedorUpdateView, ProveedorDeleteView,
    ProductoListView, ProductoCreateView, ProductoUpdateView, ProductoDeleteView, ProductoDetailView,
    TerceroListView, TerceroCreateView, TerceroUpdateView, TerceroDeleteView,
    lista_reservas, crear_reserva, eliminar_reserva, editar_reserva
)
from . import views
urlpatterns = [
    # Home en blanco con sólo el navbar
    path('', HomeView.as_view(), name='home'),

    # CRUD Categorías
    path('categorias/',              CategoriaListView.as_view(),   name='categoria_list'),
    path('categorias/nuevo/',        CategoriaCreateView.as_view(), name='categoria_create'),
    path('categorias/<int:pk>/editar/',   CategoriaUpdateView.as_view(), name='categoria_update'),
    path('categorias/<int:pk>/eliminar/', CategoriaDeleteView.as_view(), name='categoria_delete'),

    # CRUD Proveedores
    path('proveedores/',             ProveedorListView.as_view(),   name='proveedor_list'),
    path('proveedores/nuevo/',       ProveedorCreateView.as_view(), name='proveedor_create'),
    path('proveedores/<int:pk>/editar/',   ProveedorUpdateView.as_view(), name='proveedor_update'),
    path('proveedores/<int:pk>/eliminar/', ProveedorDeleteView.as_view(), name='proveedor_delete'),

    # CRUD Productos
    path('productos/', views.ProductoListView.as_view(), name='producto_list'),
    path('productos/datatable/', views.producto_datatable_view, name='producto_datatable'),
    path('productos/nuevo/',         ProductoCreateView.as_view(), name='producto_create'),
    path('productos/<int:pk>/editar/',   ProductoUpdateView.as_view(), name='producto_update'),
    path('productos/<int:pk>/eliminar/', ProductoDeleteView.as_view(), name='producto_delete'),
    path('productos/<int:pk>/', ProductoDetailView.as_view(), name='producto_detail'),

    # CRUD Terceros
    path('terceros/',                TerceroListView.as_view(),   name='tercero_list'),
    path('terceros/nuevo/',          TerceroCreateView.as_view(), name='tercero_create'),
    path('terceros/<int:pk>/editar/',    TerceroUpdateView.as_view(), name='tercero_update'),
    path('terceros/<int:pk>/eliminar/',  TerceroDeleteView.as_view(), name='tercero_delete'),

    path('reservas/',           lista_reservas,               name='reserva_list'),
    path('reservas/nueva/',     crear_reserva,                name='reserva_create'),
    path('reservas/<int:pk>/editar/',  editar_reserva,       name='reserva_update'),
    path('reservas/<int:pk>/eliminar/',eliminar_reserva,      name='reserva_delete'),

    # CRUD Usuarios
    path('usuarios/', views.UsuarioListView.as_view(), name='usuario_list'),
    path('usuarios/datatable/', views.usuario_datatable_view, name='usuario_datatable'),
    path('usuarios/<int:pk>/editar/', views.UsuarioUpdateView.as_view(), name='usuario_update'),
    path('usuarios/<int:pk>/eliminar/', views.UsuarioDeleteView.as_view(), name='usuario_delete'),
    
    # Vista de acceso denegado
    path('acceso-denegado/', views.acceso_denegado_view, name='acceso_denegado'),
]
