# dte/urls.py

from django.urls import path
from .views import (
    FacturaListView,
    FacturaDetailView,
)
from .views import (
    ReceptorListView,
    ReceptorDetailView,
    ReceptorCreateView,
    ReceptorUpdateView,
    ReceptorDeleteView,
    receptor_datatable,
    validar_documento_ajax,
    obtener_municipios_ajax,
    obtener_municipios_ajax_r, 
)
from . import views
from django.conf import settings
from django.conf.urls.static import static

app_name = "dte"
# Agregar estas rutas al urlpatterns existente en urls.py

urlpatterns = [
    # Facturas existentes...
    path("facturas/",          FacturaListView.as_view(),   name="factura_list"),
    path("facturas/<int:pk>/", FacturaDetailView.as_view(), name="factura_detail"),
    
    # Vista principal para crear factura/CCF (existente)
    path('crear-factura/', views.crear_factura_electronica, name='crear_factura'),
    
    # NUEVAS RUTAS PARA NOTA DE CRÉDITO
    path('crear-nota-credito/', views.crear_nota_credito, name='crear_nota_credito'),
    path('crear-nc-desde-documento/<int:documento_id>/', views.crear_nota_credito_desde_documento, name='crear_nc_desde_documento'),
    
    # URLs AJAX para Nota de Crédito
    path('ajax/buscar-documentos-nc/', views.buscar_documentos_para_nc_ajax, name='buscar_documentos_nc_ajax'),
    path('ajax/obtener-items-documento/', views.obtener_items_documento_ajax, name='obtener_items_documento_ajax'),
    
    # Vistas AJAX para receptor (en factura) - existentes
    path('buscar-receptores/', views.buscar_receptores_ajax, name='buscar_receptores_ajax'),
    path('receptor/<int:receptor_id>/', views.obtener_receptor_ajax, name='obtener_receptor_ajax'),
    
    # Vistas AJAX para productos - existentes
    path('buscar-productos/', views.buscar_productos_ajax, name='buscar_productos_ajax'),
    path('producto/<int:producto_id>/', views.obtener_producto_ajax, name='obtener_producto_ajax'),
    
    # CRUD de Receptores - existentes
    path('receptores/', ReceptorListView.as_view(), name='receptor_list'),
    path('receptores/nuevo/', ReceptorCreateView.as_view(), name='receptor_create'),
    path('receptores/<int:pk>/', ReceptorDetailView.as_view(), name='receptor_detail'),
    path('receptores/<int:pk>/editar/', ReceptorUpdateView.as_view(), name='receptor_update'),
    path('receptores/<int:pk>/eliminar/', ReceptorDeleteView.as_view(), name='receptor_delete'),
    
    # DataTable para receptores - existente
    path('receptores/datatable/', receptor_datatable, name='receptor_datatable'),
    
    # Descargas y acciones de facturas - existentes
    path('facturas/<int:pk>/descargar-pdf/', views.descargar_factura_pdf, name='descargar_factura_pdf'),
    path('facturas/<int:pk>/descargar-json/', views.descargar_factura_json, name='descargar_factura_json'),
    path('facturas/<int:pk>/reenviar/', views.reenviar_factura_hacienda, name='reenviar_factura'),
    
    # AJAX utilities - existentes
    path('ajax/validar-documento/', validar_documento_ajax, name='validar_documento_ajax'),
    path('ajax/obtener-municipios/', obtener_municipios_ajax, name='obtener_municipios_ajax'),
    path('ajax/obtener-municipios-r/', obtener_municipios_ajax_r, name='obtener_municipios_ajax_r'),
    
    # Agregar esta línea a tus urlpatterns en urls.py
    path('facturas/datatable/', views.factura_datatable_view, name='factura_datatable'),

    # URLs para Anulación de Documentos
    path('anulaciones/', views.anulacion_list_view, name='anulacion_list'),
    path('anulaciones/crear/', views.anulacion_crear_view, name='anulacion_crear'),
    path('anulaciones/documento/<int:documento_id>/', views.anulacion_documento_view, name='anulacion_documento'),
    path('anulaciones/<int:pk>/', views.anulacion_detail_view, name='anulacion_detail'),
    path('anulaciones/<int:pk>/reenviar/', views.anulacion_reenviar_view, name='anulacion_reenviar'),
    path('anulaciones/<int:pk>/consultar-estado/', views.anulacion_consultar_estado_view, name='anulacion_consultar_estado'),
    path('search-receptors/', views.search_receptors, name='search_receptors'),
    path('search-items/',     views.search_items,     name='search_items'),
    # URLs para anular desde facturas
    path('facturas/<int:factura_id>/anular/', views.anular_desde_factura_view, name='anular_factura'),

    # URLs AJAX para anulación
    path('ajax/buscar-documentos-anular/', views.buscar_documentos_anular_ajax, name='buscar_documentos_anular_ajax'),
    # Agregar esta línea en la lista de urlpatterns
    path('actualizar-existencias-producto/', views.actualizar_existencias_producto_ajax, name='actualizar_existencias_producto'),
    path('facturas/<int:pk>/descargar-ticket/', views.descargar_factura_ticket, name='descargar_factura_ticket'),
    path('emisor-maestro/', views.emisor_maestro_view, name='emisor_maestro'),
    path('facturas/lista-excel/', views.descargar_lista_facturas_excel, name='descargar_lista_facturas_excel'),
    # AGREGAR estas rutas a urlpatterns
    path('sucursales/', views.sucursal_list, name='sucursal_list'),
    path('sucursales/nueva/', views.sucursal_create, name='sucursal_create'),
    path('sucursales/<int:pk>/editar/', views.sucursal_update, name='sucursal_update'),
    path('sucursales/<int:pk>/eliminar/', views.sucursal_delete, name='sucursal_delete'),
       path('facturas/lista-json/', views.descargar_lista_facturas_json, name='descargar_lista_facturas_json'),  # NUEVA LÍNEA

]