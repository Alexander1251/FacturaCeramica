# admin.py

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
import json
from .models import (
    AmbienteDestino,
    TipoDocumento,
    ModeloFacturacion,
    TipoTransmision,
    TipoContingencia,
    GeneracionDocumento,
    TipoEstablecimiento,
    TipoServicio,
    TipoItem,
    Departamento,
    Municipio,
    UnidadMedida,
    Tributo,
    CondicionOperacion,
    FormaPago,
    Plazo,
    ActividadEconomica,
    Pais,
    OtroDocumentoAsociado,
    TipoDocReceptor,
    DocumentoContingencia,
    TipoInvalidacion,
    Identificacion,
    DocumentoRelacionado,
    Emisor,
    Receptor,
    OtrosDocumentos,
    VentaTercero,
    CuerpoDocumentoItem,
    Resumen,
    TributoResumen,
    Pago,
    Extension,
    ApendiceItem,
    FacturaElectronica,
)


@admin.register(AmbienteDestino)
class AmbienteDestinoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "texto")
    search_fields = ("codigo", "texto")


@admin.register(TipoDocumento)
class TipoDocumentoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "texto")
    search_fields = ("codigo", "texto")


@admin.register(ModeloFacturacion)
class ModeloFacturacionAdmin(admin.ModelAdmin):
    list_display = ("codigo", "texto")


@admin.register(TipoTransmision)
class TipoTransmisionAdmin(admin.ModelAdmin):
    list_display = ("codigo", "texto")


@admin.register(TipoContingencia)
class TipoContingenciaAdmin(admin.ModelAdmin):
    list_display = ("codigo", "texto")


@admin.register(GeneracionDocumento)
class GeneracionDocumentoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "texto")


@admin.register(TipoEstablecimiento)
class TipoEstablecimientoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "texto")


@admin.register(TipoServicio)
class TipoServicioAdmin(admin.ModelAdmin):
    list_display = ("codigo", "texto")


@admin.register(TipoItem)
class TipoItemAdmin(admin.ModelAdmin):
    list_display = ("codigo", "texto")


@admin.register(Departamento)
class DepartamentoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "texto")
    search_fields = ("codigo", "texto")


@admin.register(Municipio)
class MunicipioAdmin(admin.ModelAdmin):
    list_display = ("codigo", "texto", "departamento")
    list_filter = ("departamento",)
    search_fields = ("codigo", "texto")


@admin.register(UnidadMedida)
class UnidadMedidaAdmin(admin.ModelAdmin):
    list_display = ("codigo", "texto")


@admin.register(Tributo)
class TributoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "texto")


@admin.register(CondicionOperacion)
class CondicionOperacionAdmin(admin.ModelAdmin):
    list_display = ("codigo", "texto")


@admin.register(FormaPago)
class FormaPagoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "texto")


@admin.register(Plazo)
class PlazoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "texto")


@admin.register(ActividadEconomica)
class ActividadEconomicaAdmin(admin.ModelAdmin):
    list_display = ("codigo", "texto")
    search_fields = ("codigo", "texto")


@admin.register(Pais)
class PaisAdmin(admin.ModelAdmin):
    list_display = ("codigo", "texto")


@admin.register(OtroDocumentoAsociado)
class OtroDocumentoAsociadoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "texto")


@admin.register(TipoDocReceptor)
class TipoDocReceptorAdmin(admin.ModelAdmin):
    list_display = ("codigo", "texto")


@admin.register(DocumentoContingencia)
class DocumentoContingenciaAdmin(admin.ModelAdmin):
    list_display = ("codigo", "texto")


@admin.register(TipoInvalidacion)
class TipoInvalidacionAdmin(admin.ModelAdmin):
    list_display = ("codigo", "texto")


@admin.register(Identificacion)
class IdentificacionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "version",
        "ambiente",
        "get_tipo_dte_display",
        "numeroControl",
        "tipoModelo",
        "tipoOperacion",
        "fecEmi",
        "horEmi",
        "tipoMoneda",
    )
    list_filter = ("tipoDte", "ambiente", "fecEmi")
    search_fields = ("numeroControl", "codigoGeneracion")
    readonly_fields = ("codigoGeneracion",)
    
    def get_tipo_dte_display(self, obj):
        if obj.tipoDte:
            return f"{obj.tipoDte.codigo} - {obj.tipoDte.texto}"
        return "N/A"
    get_tipo_dte_display.short_description = "Tipo DTE"


@admin.register(DocumentoRelacionado)
class DocumentoRelacionadoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "factura",
        "tipoDocumento",
        "tipoGeneracion",
        "numeroDocumento",
        "fechaEmision",
    )
    list_filter = ("tipoDocumento", "tipoGeneracion")
    search_fields = ("numeroDocumento",)


@admin.register(Emisor)
class EmisorAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "nit",
        "nrc",
        "nombre",
        "codActividad",
        "tipoEstablecimiento",
        "get_ubicacion",
    )
    search_fields = ("nit", "nombre", "nrc")
    list_filter = ("tipoEstablecimiento", "departamento")
    
    def get_ubicacion(self, obj):
        if obj.departamento and obj.municipio:
            return f"{obj.municipio.texto}, {obj.departamento.texto}"
        return "No definida"
    get_ubicacion.short_description = "Ubicación"


@admin.register(Receptor)
class ReceptorAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "get_tipo_doc_display",
        "numDocumento",
        "nombre",
        "codActividad",
        "get_ubicacion",
        "correo",
    )
    search_fields = ("numDocumento", "nombre", "correo")
    list_filter = ("tipoDocumento", "departamento")
    
    def get_tipo_doc_display(self, obj):
        if obj.tipoDocumento:
            return f"{obj.tipoDocumento.codigo} - {obj.tipoDocumento.texto}"
        return "Sin tipo"
    get_tipo_doc_display.short_description = "Tipo Doc"
    
    def get_ubicacion(self, obj):
        if obj.departamento and obj.municipio:
            return f"{obj.municipio.texto}, {obj.departamento.texto}"
        return "No definida"
    get_ubicacion.short_description = "Ubicación"


@admin.register(OtrosDocumentos)
class OtrosDocumentosAdmin(admin.ModelAdmin):
    list_display = ("id", "factura", "codDocAsociado")
    list_filter = ("codDocAsociado",)


@admin.register(VentaTercero)
class VentaTerceroAdmin(admin.ModelAdmin):
    list_display = ("id", "factura", "nit", "nombre")
    search_fields = ("nit", "nombre")


@admin.register(CuerpoDocumentoItem)
class CuerpoDocumentoItemAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "factura",
        "numItem",
        "get_tipo_item_display",
        "descripcion_corta",
        "cantidad",
        "precioUni",
        "ventaGravada",
        "ivaItem",
    )
    list_filter = ("tipoItem",)
    search_fields = ("codigo", "descripcion")
    
    def get_tipo_item_display(self, obj):
        if obj.tipoItem:
            return obj.tipoItem.codigo
        return "N/A"
    get_tipo_item_display.short_description = "Tipo"
    
    def descripcion_corta(self, obj):
        if obj.descripcion and len(obj.descripcion) > 50:
            return obj.descripcion[:50] + "..."
        return obj.descripcion or "Sin descripción"
    descripcion_corta.short_description = "Descripción"


@admin.register(Resumen)
class ResumenAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "factura",
        "totalGravada",
        "montoTotalOperacion",
        "totalPagar",
        "condicionOperacion",
    )
    list_filter = ("condicionOperacion",)


@admin.register(TributoResumen)
class TributoResumenAdmin(admin.ModelAdmin):
    list_display = ("id", "resumen", "codigo", "valor")
    list_filter = ("codigo",)


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ("id", "resumen", "codigo", "montoPago", "referencia")
    list_filter = ("codigo",)


@admin.register(Extension)
class ExtensionAdmin(admin.ModelAdmin):
    list_display = ("id", "factura", "nombEntrega", "nombRecibe")


@admin.register(ApendiceItem)
class ApendiceItemAdmin(admin.ModelAdmin):
    list_display = ("id", "factura", "campo", "etiqueta", "valor")


@admin.register(FacturaElectronica)
class FacturaElectronicaAdmin(admin.ModelAdmin):
    list_display = (
        "id", 
        "get_numero_control", 
        "get_tipo_dte",
        "get_receptor_info",
        "get_total",
        "get_estado_hacienda_display", 
        "get_sello_status",
        "fecha_envio_hacienda",
        "intentos_envio"
    )
    list_filter = (
        "estado_hacienda", 
        "identificacion__tipoDte", 
        "fecha_envio_hacienda",
        "enviado_por_correo"
    )
    search_fields = (
        "identificacion__numeroControl", 
        "identificacion__codigoGeneracion",
        "receptor__nombre",
        "receptor__numDocumento"
    )
    readonly_fields = (
        "get_estado_hacienda_display",
        "get_sello_status", 
        "get_observaciones_formatted",
        "get_json_preview"
    )
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('identificacion', 'emisor', 'receptor')
        }),
        ('Estado en Hacienda', {
            'fields': (
                'estado_hacienda',
                'get_estado_hacienda_display',
                'sello_recepcion',
                'get_sello_status',
                'fecha_procesamiento',
                'fecha_envio_hacienda',
                'intentos_envio'
            )
        }),
        ('Observaciones', {
            'fields': ('get_observaciones_formatted',),
            'classes': ('collapse',)
        }),
        ('Correo Electrónico', {
            'fields': ('enviado_por_correo', 'fecha_envio_correo')
        }),
        ('Documentos Técnicos', {
            'fields': ('documento_firmado', 'get_json_preview'),
            'classes': ('collapse',)
        }),
    )
    
    def get_numero_control(self, obj):
        if obj.identificacion:
            return obj.identificacion.numeroControl
        return "Sin número"
    get_numero_control.short_description = "Número Control"
    get_numero_control.admin_order_field = "identificacion__numeroControl"
    
    def get_tipo_dte(self, obj):
        if obj.identificacion and obj.identificacion.tipoDte:
            tipo_map = {
                '01': 'FC',
                '03': 'CCF', 
                '05': 'NC',
                '14': 'FSE'
            }
            codigo = obj.identificacion.tipoDte.codigo
            return format_html(
                '<span class="badge badge-{}>{}</span>',
                'primary' if codigo == '01' else 'success' if codigo == '03' else 'warning' if codigo == '05' else 'info',
                tipo_map.get(codigo, codigo)
            )
        return "N/A"
    get_tipo_dte.short_description = "Tipo"
    
    def get_receptor_info(self, obj):
        if obj.receptor:
            nombre = obj.receptor.nombre[:30] + "..." if len(obj.receptor.nombre or "") > 30 else obj.receptor.nombre
            doc = obj.receptor.numDocumento or "Sin doc"
            return format_html('{}<br><small>{}</small>', nombre, doc)
        return "Sin receptor"
    get_receptor_info.short_description = "Receptor"
    
    def get_total(self, obj):
        if hasattr(obj, 'resumen') and obj.resumen:
            return f"${obj.resumen.totalPagar:.2f}"
        return "$0.00"
    get_total.short_description = "Total"
    get_total.admin_order_field = "resumen__totalPagar"
    
    def get_estado_hacienda_display(self, obj):
        """Obtiene el estado formateado con color para el admin"""
        colores = {
            'ACEPTADO': '#28a745',                    # Verde
            'ACEPTADO CON OBSERVACIONES': '#fd7e14',  # Naranja
            'RECHAZADO': '#dc3545',                   # Rojo
        }
        color = colores.get(obj.estado_hacienda, '#6c757d')  # Gris por defecto
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_estado_hacienda_display()
        )
    get_estado_hacienda_display.short_description = 'Estado Hacienda'
    
    def get_sello_status(self, obj):
        if obj.sello_recepcion and obj.sello_recepcion.strip():
            return format_html(
                '<span style="color: #28a745;">✓ Con Sello</span><br><small>{}</small>',
                obj.sello_recepcion[:20] + "..." if len(obj.sello_recepcion) > 20 else obj.sello_recepcion
            )
        return format_html('<span style="color: #dc3545;">✗ Sin Sello</span>')
    get_sello_status.short_description = "Sello"
    
    def get_observaciones_formatted(self, obj):
        if not obj.observaciones_hacienda:
            return "Sin observaciones"
        
        try:
            # Intentar parsear como JSON
            observaciones = json.loads(obj.observaciones_hacienda)
            if isinstance(observaciones, list):
                html_obs = "<ul>"
                for obs in observaciones:
                    html_obs += f"<li>{obs}</li>"
                html_obs += "</ul>"
                return format_html(html_obs)
            else:
                return obj.observaciones_hacienda
        except (json.JSONDecodeError, TypeError):
            # Si no es JSON válido, mostrar como texto
            return obj.observaciones_hacienda
    get_observaciones_formatted.short_description = "Observaciones de Hacienda"
    
    def get_json_preview(self, obj):
        if obj.documento_firmado:
            preview = obj.documento_firmado[:200] + "..." if len(obj.documento_firmado) > 200 else obj.documento_firmado
            return format_html('<pre style="font-size: 10px;">{}</pre>', preview)
        return "No disponible"
    get_json_preview.short_description = "Vista Previa JSON"
    
    actions = ['marcar_como_aceptado', 'marcar_como_rechazado', 'resetear_estado']
    
    def marcar_como_aceptado(self, request, queryset):
        count = queryset.update(estado_hacienda='ACEPTADO')
        self.message_user(request, f'{count} facturas marcadas como ACEPTADO.')
    marcar_como_aceptado.short_description = "Marcar como ACEPTADO"
    
    def marcar_como_rechazado(self, request, queryset):
        count = queryset.update(estado_hacienda='RECHAZADO')
        self.message_user(request, f'{count} facturas marcadas como RECHAZADO.')
    marcar_como_rechazado.short_description = "Marcar como RECHAZADO"
    
    def resetear_estado(self, request, queryset):
        count = queryset.update(estado_hacienda='PENDIENTE')
        self.message_user(request, f'{count} facturas marcadas como PENDIENTE.')
    resetear_estado.short_description = "Resetear a PENDIENTE"


# dte/admin.py - AGREGAR configuración para el admin de Django

from django.contrib import admin
from .models import AnulacionDocumento

@admin.register(AnulacionDocumento)
class AnulacionDocumentoAdmin(admin.ModelAdmin):
    """
    Configuración del admin para AnulacionDocumento
    """
    list_display = [
        'codigo_generacion_corto',
        'documento_anular',
        'fecha_anulacion',
        'estado',
        'emisor',
        'nombre_responsable',
        'sello_recepcion_corto',
        'creado_en'
    ]
    
    list_filter = [
        'estado',
        'tipo_anulacion',
        'ambiente',
        'fecha_anulacion',
        'creado_en',
        'documento_anular__identificacion__tipoDte'
    ]
    
    search_fields = [
        'codigo_generacion',
        'documento_anular__identificacion__numeroControl',
        'documento_anular__receptor__nombre',
        'nombre_responsable',
        'nombre_solicita',
        'motivo_anulacion'
    ]
    
    readonly_fields = [
        'codigo_generacion',
        'sello_recepcion',
        'fecha_procesamiento',
        'respuesta_hacienda',
        'creado_en',
        'actualizado_en'
    ]
    
    fieldsets = (
        ('Información General', {
            'fields': (
                'codigo_generacion',
                'ambiente',
                'documento_anular',
                'emisor',
                'estado'
            )
        }),
        ('Fechas y Tiempos', {
            'fields': (
                'fecha_anulacion',
                'hora_anulacion',
                'fecha_procesamiento'
            )
        }),
        ('Motivo de Anulación', {
            'fields': (
                'tipo_anulacion',
                'motivo_anulacion'
            )
        }),
        ('Responsable', {
            'fields': (
                'nombre_responsable',
                'tipo_doc_responsable',
                'num_doc_responsable'
            )
        }),
        ('Solicitante', {
            'fields': (
                'nombre_solicita',
                'tipo_doc_solicita',
                'num_doc_solicita'
            )
        }),
        ('Respuesta de Hacienda', {
            'fields': (
                'sello_recepcion',
                'observaciones',
                'respuesta_hacienda'
            ),
            'classes': ('collapse',)
        }),
        ('Auditoría', {
            'fields': (
                'creado_por',
                'creado_en',
                'actualizado_en'
            ),
            'classes': ('collapse',)
        })
    )
    
    def codigo_generacion_corto(self, obj):
        """Muestra solo los primeros 8 caracteres del código"""
        return f"{obj.codigo_generacion[:8]}..." if obj.codigo_generacion else "-"
    codigo_generacion_corto.short_description = "Código"
    
    def sello_recepcion_corto(self, obj):
        """Muestra solo los primeros caracteres del sello"""
        if obj.sello_recepcion:
            return f"{obj.sello_recepcion[:10]}..."
        return "-"
    sello_recepcion_corto.short_description = "Sello"
    
    def get_queryset(self, request):
        """Optimizar consultas con select_related"""
        return super().get_queryset(request).select_related(
            'documento_anular__identificacion__tipoDte',
            'documento_anular__receptor',
            'emisor',
            'ambiente'
        )
    
    actions = ['marcar_como_enviado', 'consultar_estado_hacienda']
    
    def marcar_como_enviado(self, request, queryset):
        """Acción personalizada para marcar como enviado"""
        updated = queryset.filter(estado='PENDIENTE').update(estado='ENVIADO')
        self.message_user(request, f'{updated} anulaciones marcadas como enviadas.')
    marcar_como_enviado.short_description = "Marcar como enviado"
    
    def consultar_estado_hacienda(self, request, queryset):
        """Acción personalizada para consultar estado en Hacienda"""
        # Aquí se podría implementar consulta automática
        self.message_user(request, 'Función de consulta automática pendiente de implementar.')
    consultar_estado_hacienda.short_description = "Consultar estado en Hacienda"
    
    def has_delete_permission(self, request, obj=None):
        """Solo permitir eliminar anulaciones pendientes o con error"""
        if obj and obj.estado in ['ACEPTADO']:
            return False
        return super().has_delete_permission(request, obj)
    
    def save_model(self, request, obj, form, change):
        """Guardar el usuario que crea/modifica"""
        if not change:  # Si es creación
            obj.creado_por = request.user.username
        super().save_model(request, obj, form, change)