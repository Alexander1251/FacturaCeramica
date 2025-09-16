import json, os
from io import BytesIO
from pathlib import Path
from django.conf import settings
from django.contrib import messages
from django.forms import modelform_factory
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.views.generic import ListView, DetailView, View
from jsonschema import validate, ValidationError as SchemaError
from django.views.decorators.http import require_http_methods
from django.core.mail import EmailMessage
from django.utils import timezone
from reportlab.pdfgen import canvas
from django.http import JsonResponse
from django.http import JsonResponse
from django.urls import reverse
from django.db.models import Q
from datetime import datetime
from django.contrib import messages
from django.db import transaction
from datetime import datetime
from io import BytesIO
from decimal import Decimal
from django.forms import model_to_dict
import json
from django.http        import JsonResponse
from django.db          import transaction
from jsonschema                import validate as jsonschema_validate
from jsonschema.exceptions     import ValidationError as JSONSchemaValidationError
from dte.schema import FE_SCHEMA as DTE_SCHEMA, get_schema_for_tipo_dte
from .models import (
    FacturaElectronica, Receptor, Identificacion, Resumen, CondicionOperacion, UnidadMedida,
    TributoResumen, TipoDocumento,AmbienteDestino, ModeloFacturacion, TipoTransmision, Departamento, Municipio,TipoDocReceptor, ActividadEconomica, TipoItem, Tributo, Emisor,Sucursal)
from .forms  import (
    IdentificacionForm, ReceptorForm,
    ItemFormset, ResumenForm, PagoFormset, _emisor_maestro, DocumentoOrigenForm, NotaCreditoDetalleForm, IdentificacionNotaCreditoForm, NotaCreditoSimplificadaForm, EmisorMaestroForm, _siguiente_numero_control, SucursalForm)

from .utils  import build_dte_json, numero_a_letras   # función existente
from productos.models import Producto
SCHEMA_PATH = Path(settings.BASE_DIR) / "dte" / "schemas" / "fe-fc-v1.json"
from django.forms.widgets import Select, SelectMultiple 

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from io import BytesIO
import qrcode
from .services import DTEService
from decimal import Decimal,  ROUND_HALF_UP
from datetime import datetime
# ─────────────────────────────────────
# vistas
# ─────────────────────────────────────
# Reemplazar tu FacturaListView existente con esta versión:

class FacturaListView(ListView):
    model = FacturaElectronica
    template_name = "dte/factura_list.html"
    context_object_name = "facturas"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['object_list'] = []  # Empty list for server-side processing
        context['sucursales'] = Sucursal.objects.filter(activa=True).order_by('nombre')
        context['sucursal_usuario'] = self.request.user.sucursal.id if hasattr(self.request.user, 'sucursal') and self.request.user.sucursal else None
        return context

# dte/views.py - Agregar esta vista mejorada

from django.views.generic import DetailView
from django.http import HttpResponse
import json

# Reemplazar la clase FacturaDetailView en dte/views.py

class FacturaDetailView(DetailView):
    model = FacturaElectronica
    template_name = 'dte/factura_detail.html'
    context_object_name = 'factura'
    
    def get_queryset(self):
        return super().get_queryset().select_related(
            'identificacion',
            'identificacion__ambiente',
            'identificacion__tipoDte',
            'identificacion__tipoModelo',
            'identificacion__tipoOperacion',
            'identificacion__tipoContingencia',
            'emisor',
            'emisor__departamento',
            'emisor__municipio',
            'emisor__codActividad',
            'emisor__tipoEstablecimiento',
            'receptor',
            'receptor__tipoDocumento',
            'receptor__departamento',
            'receptor__municipio',
            'receptor__codActividad',
            'resumen',
            'resumen__condicionOperacion'
        ).prefetch_related(
            'documentos_relacionados',
            'documentos_relacionados__tipoDocumento',
            'documentos_relacionados__tipoGeneracion',
            'otros_documentos',
            'otros_documentos__codDocAsociado',
            'cuerpo_documento',
            'cuerpo_documento__tipoItem',
            'cuerpo_documento__codTributo',
            'cuerpo_documento__uniMedida',
            'resumen__tributos',
            'resumen__tributos__codigo',
            'resumen__pagos',
            'resumen__pagos__codigo',
            'resumen__pagos__plazo',
            'apendice'
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        factura = self.object
        
        try:
            # Generar el JSON usando la función build_dte_json con firma y sello
            dte_json = build_dte_json(factura, incluir_firma_y_sello=True)
            context['json'] = json.dumps(dte_json, indent=2, ensure_ascii=False)
        except Exception as e:
            context['json'] = f"Error generando JSON: {str(e)}"
        
        # Información adicional
        context['tiene_sello'] = bool(factura.sello_recepcion)
        
        # URL para verificación en línea
        ambiente = "00" if settings.DTE_AMBIENTE == 'test' else "01"
        context['qr_url'] = (
                f"https://admin.factura.gob.sv/consultaPublica?"
                f"ambiente={ambiente}&codGen={factura.identificacion.codigoGeneracion}"
                f"&fechaEmi={factura.identificacion.fecEmi}"
            )
        
        # Generar código QR si tiene sello
        if factura.sello_recepcion:
            try:
                import qrcode
                from io import BytesIO
                import base64
                
                qr = qrcode.QRCode(version=1, box_size=10, border=5)
                qr.add_data(context['qr_url'])
                qr.make(fit=True)
                
                qr_image = qr.make_image(fill_color="black", back_color="white")
                buffer = BytesIO()
                qr_image.save(buffer, format='PNG')
                qr_image_base64 = base64.b64encode(buffer.getvalue()).decode()
                context['qr_code'] = qr_image_base64
            except ImportError:
                context['qr_code'] = None
        
        return context
        
        
def descargar_factura_json(request, pk):
    """Descarga el JSON de una factura - VERSIÓN SIMPLIFICADA que funciona"""
    try:
        factura = get_object_or_404(FacturaElectronica, pk=pk)
        
        # Usar la función build_dte_json original (que ya funcionaba antes)
        dte_json = build_dte_json(factura, incluir_firma_y_sello=True)
        
        # Usar el encoder JSON default de Django (sin custom encoder)
        # Django ya maneja Decimal automáticamente
        json_str = json.dumps(dte_json, indent=2, ensure_ascii=False, default=str)
        
        # Crear respuesta HTTP
        response = HttpResponse(json_str, content_type='application/json; charset=utf-8')
        filename = f"{factura.identificacion.numeroControl}_firmado.json"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
        
    except Exception as e:
        print(f"Error en descargar_factura_json: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return HttpResponse(f"Error generando JSON: {str(e)}", status=500)
    
    

def descargar_factura_pdf(request, pk):
    
    factura = get_object_or_404(FacturaElectronica, pk=pk)
    
    # Generar PDF
    pdf_data = generar_pdf_factura_mejorado(factura)
    
    # Crear respuesta HTTP
    response = HttpResponse(pdf_data, content_type='application/pdf')
    filename = f"{factura.identificacion.numeroControl}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response
def reenviar_factura_hacienda(request, pk):
    
    factura = get_object_or_404(FacturaElectronica, pk=pk)
    
    if factura.estado_hacienda != 'RECHAZADO':
        messages.error(request, 'Solo se pueden reenviar facturas rechazadas')
        return redirect('dte:factura_detail', pk=pk)
    
    try:
        dte_service = DTEService()
        
        # Generar JSON sin firma y sello (para Hacienda)
        dte_json = build_dte_json(factura, incluir_firma_y_sello=False)
        
        # Firmar documento
        documento_firmado = dte_service.firmar_documento(dte_json)
        factura.documento_firmado = documento_firmado
        
        # Enviar a Hacienda
        respuesta = dte_service.enviar_a_hacienda(documento_firmado, factura)
        
        if respuesta.get('estado') == 'PROCESADO':
            factura.estado_hacienda = 'ACEPTADO'
            factura.sello_recepcion = respuesta.get('selloRecibido')
            factura.fecha_procesamiento = respuesta.get('fhProcesamiento')
            factura.observaciones_hacienda = json.dumps(respuesta.get('observaciones', []))
            factura.save()
            
            messages.success(request, 'Factura reenviada y aceptada por Hacienda')
        else:
            factura.estado_hacienda = 'RECHAZADO'
            factura.observaciones_hacienda = json.dumps(respuesta.get('observaciones', []))
            factura.save()
            
            messages.error(request, f'Factura rechazada: {respuesta.get("descripcionMsg", "Error desconocido")}')
            
    except Exception as e:
        messages.error(request, f'Error al reenviar: {str(e)}')
        
    return redirect('dte:factura_detail', pk=pk)
    
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import qrcode
from decimal import Decimal

DTE_URLS = {
    'test': {
        'auth': 'https://apitest.dtes.mh.gob.sv/seguridad/auth',
        'recepcion': 'https://apitest.dtes.mh.gob.sv/fesv/recepciondte',
        'consulta': 'https://apitest.dtes.mh.gob.sv/fesv/recepcion/consultadte/'
    },
    'prod': {
        'auth': 'https://api.dtes.mh.gob.sv/seguridad/auth',
        'recepcion': 'https://api.dtes.mh.gob.sv/fesv/recepciondte',
        'consulta': 'https://api.dtes.mh.gob.sv/fesv/recepcion/consultadte/'
    }
}

# Configuración del firmador
FIRMADOR_URL = getattr(settings, 'FIRMADOR_URL', 'http://localhost:8113/firmardocumento/')
DTE_AMBIENTE = getattr(settings, 'DTE_AMBIENTE', 'test')  # 'test' o 'prod'
DTE_USER = getattr(settings, 'DTE_USER', '')
DTE_PASSWORD = getattr(settings, 'DTE_PASSWORD', '')

def generar_pdf_factura_mejorado(factura):
    """
    Genera un PDF profesional de la factura electrónica en blanco y negro
    con diseño limpio y estructura unificada
    CORREGIDO: Soporte completo para Nota de Crédito (tipo 05)
    """
    from io import BytesIO
    import json
    from django.conf import settings
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, 
                          leftMargin=15*mm, rightMargin=15*mm,
                          topMargin=12*mm, bottomMargin=12*mm)
    
    # Estilos mejorados - solo blanco y negro
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=6,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Heading2'],
        fontSize=12,
        spaceAfter=4,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    header_style = ParagraphStyle(
        'Header',
        parent=styles['Normal'],
        fontSize=9,
        fontName='Helvetica-Bold',
        alignment=TA_CENTER
    )
    
    normal_style = ParagraphStyle(
        'Normal',
        parent=styles['Normal'],
        fontSize=8,
        fontName='Helvetica',
        leading=10
    )
    
    small_style = ParagraphStyle(
        'Small',
        parent=styles['Normal'],
        fontSize=7,
        fontName='Helvetica',
        leading=8
    )
    
    bold_style = ParagraphStyle(
        'Bold',
        parent=styles['Normal'],
        fontSize=8,
        fontName='Helvetica-Bold'
    )
    
    story = []
    
    # ========================
    # ENCABEZADO CORREGIDO
    # ========================
    story.append(Paragraph("Ver.1", ParagraphStyle('version', fontSize=7, alignment=TA_RIGHT)))
    story.append(Spacer(1, 4*mm))
    
    story.append(Paragraph("DOCUMENTO TRIBUTARIO ELECTRÓNICO", title_style))
    
    # CORRECCIÓN PRINCIPAL: Agregar soporte para todos los tipos incluyendo NC
    tipo_doc = factura.identificacion.tipoDte.codigo
    if tipo_doc == "03":
        encabezado = "COMPROBANTE DE CREDITO FISCAL"
    elif tipo_doc == "01":
        encabezado = "FACTURA"
    elif tipo_doc == "14":
        encabezado = "FACTURA SUJETO EXCLUIDO"
    elif tipo_doc == "05":  # NUEVO: Soporte para Nota de Crédito
        encabezado = "NOTA DE CRÉDITO ELECTRÓNICA"
    else:
        # Fallback para tipos no reconocidos
        encabezado = f"DOCUMENTO ELECTRÓNICO TIPO {tipo_doc}"
        
    story.append(Paragraph(encabezado, subtitle_style))
    story.append(Spacer(1, 6*mm))
    
    # ========================
    # IDENTIFICACIÓN CON QR - Tabla compacta
    # ========================
    
    # Generar código QR si hay sello de recepción
    qr_image = None
    if factura.sello_recepcion:
        try:
            import qrcode
            
            # URL para el QR basada en el ambiente - CORREGIDO: Incluir codigoGeneracion
            ambiente = "00" if settings.DTE_AMBIENTE == 'test' else "01"
            qr_url = (
                f"https://admin.factura.gob.sv/consultaPublica?"
                f"ambiente={ambiente}&codGen={factura.identificacion.codigoGeneracion}"
                f"&fechaEmi={factura.identificacion.fecEmi}"
            )
            
            qr = qrcode.QRCode(version=1, box_size=3, border=2)
            qr.add_data(qr_url)
            qr.make(fit=True)
            
            qr_pil_image = qr.make_image(fill_color="black", back_color="white")
            qr_buffer = BytesIO()
            qr_pil_image.save(qr_buffer, format='PNG')
            qr_buffer.seek(0)
            
            # Crear imagen para ReportLab
            from reportlab.platypus import Image
            qr_image = Image(qr_buffer, width=25*mm, height=25*mm)
            
        except Exception as e:
            print(f"Error generando QR: {e}")
            qr_image = None
    
    # Crear tabla de identificación con o sin QR
    if qr_image:
        identificacion_data = [
            [Paragraph('<b>Código de Generación:</b>', normal_style), 
             Paragraph(f'{factura.identificacion.codigoGeneracion}', normal_style),
             qr_image, Paragraph('<b>IDENTIFICACIÓN</b>', header_style)],
            [Paragraph('<b>Número de Control:</b>', normal_style), 
             Paragraph(f'{factura.identificacion.numeroControl}', normal_style), '', ''],
            [Paragraph('<b>Modelo de Facturación:</b>', normal_style), 
             Paragraph(f'{factura.identificacion.tipoModelo}', normal_style), '', ''],
            [Paragraph('<b>Tipo de Transmisión:</b>', normal_style), 
             Paragraph(f'{factura.identificacion.tipoOperacion}', normal_style), '', ''],
            [Paragraph('<b>Fecha y Hora:</b>', normal_style), 
             Paragraph(f'{factura.identificacion.fecEmi} {factura.identificacion.horEmi}', normal_style), '', '']
        ]
        
        identificacion_table = Table(identificacion_data, colWidths=[45*mm, 65*mm, 25*mm, 45*mm])
        identificacion_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('SPAN', (3, 0), (3, 4)),  # Span para IDENTIFICACIÓN
            ('SPAN', (2, 0), (2, 4)),  # Span para QR
            ('ALIGN', (2, 0), (2, 4), 'CENTER'),  # Centrar QR
            ('ALIGN', (3, 0), (3, 4), 'CENTER'),  # Centrar IDENTIFICACIÓN
            ('BACKGROUND', (3, 0), (3, 4), colors.lightgrey),
        ]))
    else:
        # Sin QR - tabla original
        identificacion_data = [
            [Paragraph('<b>Código de Generación:</b>', normal_style), 
             Paragraph(f'{factura.identificacion.codigoGeneracion}', normal_style),
             Paragraph('<b>IDENTIFICACIÓN</b>', header_style)],
            [Paragraph('<b>Número de Control:</b>', normal_style), 
             Paragraph(f'{factura.identificacion.numeroControl}', normal_style), ''],
            [Paragraph('<b>Modelo de Facturación:</b>', normal_style), 
             Paragraph(f'{factura.identificacion.tipoModelo}', normal_style), ''],
            [Paragraph('<b>Tipo de Transmisión:</b>', normal_style), 
             Paragraph(f'{factura.identificacion.tipoOperacion}', normal_style), ''],
            [Paragraph('<b>Fecha y Hora:</b>', normal_style), 
             Paragraph(f'{factura.identificacion.fecEmi} {factura.identificacion.horEmi}', normal_style), '']
        ]
        
        identificacion_table = Table(identificacion_data, colWidths=[55*mm, 75*mm, 50*mm])
        identificacion_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('SPAN', (2, 0), (2, 4)),
            ('ALIGN', (2, 0), (2, 4), 'CENTER'),
            ('BACKGROUND', (2, 0), (2, 4), colors.lightgrey),
        ]))
    
    story.append(identificacion_table)
    story.append(Spacer(1, 4*mm))
    
    # ========================
    # NUEVO: INFORMACIÓN ESPECÍFICA PARA NOTA DE CRÉDITO
    # ========================
    if tipo_doc == "05":  # Solo para Nota de Crédito
        # Mostrar información del documento relacionado
        doc_relacionado = factura.documentos_relacionados.first()
        if doc_relacionado:
            nc_info_data = [
                [Paragraph('<b>INFORMACIÓN DE LA NOTA DE CRÉDITO</b>', header_style)],
                [Paragraph(f'<b>Documento Original:</b> {doc_relacionado.tipoDocumento.texto}', normal_style)],
                [Paragraph(f'<b>Número Documento:</b> {doc_relacionado.numeroDocumento}', normal_style)],
                [Paragraph(f'<b>Fecha Original:</b> {doc_relacionado.fechaEmision.strftime("%d/%m/%Y")}', normal_style)],
            ]
            
            # Agregar motivo si existe
            if hasattr(factura, 'nota_credito_detalle') and factura.nota_credito_detalle:
                motivo_text = factura.nota_credito_detalle.motivo_nota_credito[:100]
                if len(factura.nota_credito_detalle.motivo_nota_credito) > 100:
                    motivo_text += "..."
                nc_info_data.append([Paragraph(f'<b>Motivo:</b> {motivo_text}', normal_style)])
            
            nc_info_table = Table(nc_info_data, colWidths=[180*mm])
            nc_info_table.setStyle(TableStyle([
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BOX', (0, 0), (-1, -1), 1, colors.black),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('ALIGN', (0, 0), (0, 0), 'CENTER'),
                ('BACKGROUND', (0, 0), (0, 0), colors.yellow),  # Destacar para NC
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            
            story.append(nc_info_table)
            story.append(Spacer(1, 4*mm))
    
    # ========================
    # SELLO DE RECEPCIÓN - Información fija visible
    # ========================
    if factura.sello_recepcion:
        sello_data = [
            [Paragraph('<b>SELLO DE RECEPCIÓN</b>', header_style)],
            [Paragraph(f'<b>Sello:</b> {factura.sello_recepcion}', normal_style)],
            [Paragraph(f'<b>Fecha Procesamiento:</b> {factura.fecha_procesamiento or "N/A"}', normal_style)],
            [Paragraph(f'<b>Estado:</b> {factura.estado_hacienda}', normal_style)]
        ]
        
        sello_table = Table(sello_data, colWidths=[180*mm])
        sello_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('ALIGN', (0, 0), (0, 0), 'CENTER'),
            ('BACKGROUND', (0, 0), (0, 0), colors.lightgrey),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        
        story.append(sello_table)
        story.append(Spacer(1, 4*mm))
    
    # ========================
    # EMISOR Y RECEPTOR - Lado a lado
    # ========================
    # Construir dirección del emisor
    depto = factura.emisor.departamento.texto
    muni = factura.emisor.municipio.texto
    compl = factura.emisor.complemento
    direccion_emisor = f"{depto}, {muni}"
    if compl:
        direccion_emisor += f", {compl}"
    
    emisor_data = f"""
    <b>Nombre:</b> {factura.emisor.nombre}<br/>
    <b>NIT:</b> {factura.emisor.nit}<br/>
    <b>NRC:</b> {factura.emisor.nrc}<br/>
    <b>Actividad:</b> {factura.emisor.descActividad}<br/>
    <b>Dirección:</b> {direccion_emisor}<br/>
    <b>Teléfono:</b> {factura.emisor.telefono}<br/>
    <b>Email:</b> {factura.emisor.correo}
    """
    
    # CORRECCIÓN: Manejo seguro de campos del receptor para NC
    receptor_data = f"""
    <b>Nombre:</b> {factura.receptor.nombre or 'N/A'}<br/>
    <b>Tipo Doc:</b> {factura.receptor.tipoDocumento.texto if factura.receptor.tipoDocumento else 'N/A'}<br/>
    <b>N° Documento:</b> {factura.receptor.numDocumento or 'N/A'}<br/>
    <b>Email:</b> {factura.receptor.correo or 'N/A'}<br/>
    """
    
    # Para NC, cambiar el label del receptor
    receptor_label = "CLIENTE" if tipo_doc == "05" else "RECEPTOR"
    
    emisor_receptor_data = [
        [Paragraph('<b>EMISOR</b>', header_style), Paragraph(f'<b>{receptor_label}</b>', header_style)],
        [Paragraph(emisor_data, normal_style), Paragraph(receptor_data, normal_style)]
    ]
    
    emisor_receptor_table = Table(emisor_receptor_data, colWidths=[90*mm, 90*mm])
    emisor_receptor_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
    ]))
    
    story.append(emisor_receptor_table)
    story.append(Spacer(1, 4*mm))
    
    # ========================
    # TABLA UNIFICADA: CUERPO + RESUMEN + TRIBUTOS
    # ========================
    
    # Preparar datos del cuerpo
    cuerpo_items = []
    
    # Encabezado del cuerpo (adaptado para NC)
    if tipo_doc == "05":  # Nota de Crédito
        cuerpo_items.append([
            Paragraph('<b>N°</b>', small_style),
            Paragraph('<b>Cant.</b>', small_style),
            Paragraph('<b>Descripción</b>', small_style),
            Paragraph('<b>P.Unit</b>', small_style),
            Paragraph('<b>Desc.</b>', small_style),
            Paragraph('<b>Crédito</b>', small_style)  # Cambiar label para NC
        ])
    else:
        cuerpo_items.append([
            Paragraph('<b>N°</b>', small_style),
            Paragraph('<b>Cant.</b>', small_style),
            Paragraph('<b>Descripción</b>', small_style),
            Paragraph('<b>P.Unit</b>', small_style),
            Paragraph('<b>Desc.</b>', small_style),
            Paragraph('<b>V.Gravada</b>', small_style)
        ])
    
    # Items de la factura
    for item in factura.cuerpo_documento.all():
        cuerpo_items.append([
            Paragraph(str(item.numItem), small_style),
            Paragraph(str(item.cantidad), small_style),
            Paragraph(item.descripcion[:40] + ('...' if len(item.descripcion) > 40 else ''), small_style),
            Paragraph(f"${item.precioUni:.2f}", small_style),
            Paragraph(f"${getattr(item, 'montoDescu', 0):.2f}", small_style),
            Paragraph(f"${item.ventaGravada:.2f}", small_style)
        ])
    
    # Línea separadora
    cuerpo_items.append([
        Paragraph('', small_style), '', '', '', '', ''
    ])
    
    # RESUMEN - integrado en la misma tabla
    resumen = factura.resumen
    tipo_doc = factura.identificacion.tipoDte.codigo
    
    # Cálculo de IVA según tipo de documento
    if tipo_doc == "03":
        tributo = resumen.tributos.first()
        iva_val = tributo.valor if tributo else Decimal('0.00')
    elif tipo_doc == "05":  # Nota de Crédito
        tributo = resumen.tributos.first()
        iva_val = tributo.valor if tributo else Decimal('0.00')
    else:
        iva_val = resumen.totalIva or Decimal('0.00')
    
    # Labels del resumen según tipo de documento
    if tipo_doc == "05":  # Nota de Crédito
        resumen_items = [
            ['', '', Paragraph('<b>RESUMEN NOTA DE CRÉDITO</b>', bold_style), '', '', ''],
            ['', '', Paragraph('Subtotal Crédito:', normal_style), '', '', 
             Paragraph(f"${resumen.subTotalVentas:.2f}", normal_style)],
            ['', '', Paragraph('Descuentos:', normal_style), '', '', 
             Paragraph(f"${resumen.descuGravada:.2f}", normal_style)],
            ['', '', Paragraph('Sub-Total:', normal_style), '', '', 
             Paragraph(f"${resumen.subTotal:.2f}", normal_style)],
            ['', '', Paragraph('IVA (13%):', normal_style), '', '', 
             Paragraph(f"${iva_val:.2f}", normal_style)],
            ['', '', Paragraph('<b>TOTAL CRÉDITO:</b>', bold_style), '', '', 
             Paragraph(f"<b>${resumen.totalPagar:.2f}</b>", bold_style)],
        ]
    else:
        resumen_items = [
            ['', '', Paragraph('<b>RESUMEN</b>', bold_style), '', '', ''],
            ['', '', Paragraph('Suma de Ventas:', normal_style), '', '', 
             Paragraph(f"${resumen.subTotalVentas:.2f}", normal_style)],
            ['', '', Paragraph('Descuentos:', normal_style), '', '', 
             Paragraph(f"${resumen.descuGravada:.2f}", normal_style)],
            ['', '', Paragraph('Sub-Total:', normal_style), '', '', 
             Paragraph(f"${resumen.subTotal:.2f}", normal_style)],
            ['', '', Paragraph('IVA (13%):', normal_style), '', '', 
             Paragraph(f"${iva_val:.2f}", normal_style)],
            ['', '', Paragraph('<b>TOTAL A PAGAR:</b>', bold_style), '', '', 
             Paragraph(f"<b>${resumen.totalPagar:.2f}</b>", bold_style)],
        ]
    
    # Combinar cuerpo y resumen
    all_table_data = cuerpo_items + resumen_items
    
    # Crear tabla unificada
    unified_table = Table(all_table_data, colWidths=[10*mm, 15*mm, 80*mm, 20*mm, 20*mm, 25*mm])
    
    # Calcular número de filas del cuerpo
    num_cuerpo_rows = len(cuerpo_items)
    num_resumen_rows = len(resumen_items)
    
    unified_table.setStyle(TableStyle([
        # Estilos generales
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('INNERGRID', (0, 0), (-1, -1), 0.3, colors.black),
        
        # Encabezado del cuerpo
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        
        # Alineación de datos del cuerpo
        ('ALIGN', (0, 1), (1, num_cuerpo_rows-2), 'CENTER'),  # N° y Cantidad centrados
        ('ALIGN', (2, 1), (2, num_cuerpo_rows-2), 'LEFT'),    # Descripción a la izquierda
        ('ALIGN', (3, 1), (-1, num_cuerpo_rows-2), 'RIGHT'),  # Precios a la derecha
        
        # Separador
        ('LINEBELOW', (0, num_cuerpo_rows-2), (-1, num_cuerpo_rows-2), 2, colors.black),
        
        # Sección de resumen
        ('BACKGROUND', (2, num_cuerpo_rows), (2, num_cuerpo_rows), colors.lightgrey),
        ('ALIGN', (2, num_cuerpo_rows+1), (2, -1), 'RIGHT'),  # Labels del resumen
        ('ALIGN', (5, num_cuerpo_rows+1), (5, -1), 'RIGHT'),  # Valores del resumen
        ('SPAN', (2, num_cuerpo_rows), (4, num_cuerpo_rows)), # Span del título RESUMEN
        
        # Total final destacado
        ('BACKGROUND', (2, -1), (-1, -1), colors.lightgrey),
        ('LINEABOVE', (2, -1), (-1, -1), 2, colors.black),
    ]))
    
    story.append(unified_table)
    story.append(Spacer(1, 5*mm))
    
    # ========================
    # VALOR EN LETRAS Y CONDICIÓN
    # ========================
    letras_condicion_data = [
        [Paragraph(f'<b>Valor en letras:</b> {resumen.totalLetras}', normal_style)],
        [Paragraph(f'<b>Condición:</b> {resumen.condicionOperacion}', normal_style)]
    ]
    
    letras_condicion_table = Table(letras_condicion_data, colWidths=[170*mm])
    letras_condicion_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    
    story.append(letras_condicion_table)
    story.append(Spacer(1, 5*mm))
    
    # ========================
    # OBSERVACIONES - Solo si existen
    # ========================
    
    # Procesar observaciones desde observaciones_hacienda (JSON)
    observaciones_list = []
    if factura.observaciones_hacienda:
        try:
            observaciones_data = json.loads(factura.observaciones_hacienda)
            if isinstance(observaciones_data, list) and observaciones_data:
                observaciones_list = observaciones_data
        except (json.JSONDecodeError, TypeError):
            # Si hay texto pero no es JSON válido, tratarlo como una sola observación
            if factura.observaciones_hacienda.strip():
                observaciones_list = [factura.observaciones_hacienda.strip()]
    
    # Solo mostrar sección de observaciones si hay contenido
    if observaciones_list:
        # Crear el contenido de observaciones
        observaciones_text = "<br/>".join([f"• {obs}" for obs in observaciones_list])
        
        observaciones_data = [
            [Paragraph('<b>Observaciones:</b>', normal_style)],
            [Paragraph(observaciones_text, normal_style)]
        ]
        
        # Calcular altura dinámica basada en el número de observaciones
        obs_height = max(15*mm, len(observaciones_list) * 5*mm)
        
        observaciones_table = Table(observaciones_data, colWidths=[170*mm], rowHeights=[8*mm, obs_height])
        observaciones_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        
        story.append(observaciones_table)
        story.append(Spacer(1, 5*mm))
    
    # ========================
    # PIE DE PÁGINA
    # ========================
    story.append(Spacer(1, 8*mm))
    story.append(Paragraph("Página 1 de 1", 
                          ParagraphStyle('footer', fontSize=7, alignment=TA_CENTER)))
    story.append(Paragraph(f"Generado: {factura.identificacion.fecEmi}", 
                          ParagraphStyle('footer', fontSize=7, alignment=TA_CENTER)))
    
    # NUEVO: Para NC, agregar nota especial
    if tipo_doc == "05":
        story.append(Paragraph("DOCUMENTO DE CRÉDITO - Aplicar según corresponda", 
                              ParagraphStyle('nc_note', fontSize=7, alignment=TA_CENTER, textColor=colors.red)))
    
    # Construir el PDF
    doc.build(story)
    
    buffer.seek(0)
    return buffer.read()

# dte/views.py - Funciones corregidas

# Eliminar la función duplicada y usar esta versión mejorada
@require_http_methods(["GET"])
def obtener_municipios_ajax_r(request):
    """Vista AJAX para obtener municipios por departamento - VERSIÓN CORREGIDA"""
    departamento_codigo = request.GET.get('departamento_codigo')  # Cambiar a codigo en lugar de id
    
    if not departamento_codigo:
        return JsonResponse({'municipios': []})
    
    try:
        # Buscar por código del departamento, no por ID
        municipios = Municipio.objects.filter(
            departamento__codigo=departamento_codigo
        ).values('codigo', 'texto').order_by('texto')
        
        municipios_list = [
            {
                'codigo': m['codigo'],
                'texto': m['texto']
            }
            for m in municipios
        ]
        
        return JsonResponse({'municipios': municipios_list})
    except Exception as e:
        return JsonResponse({'municipios': [], 'error': str(e)})

# dte/views.py - Función crear_factura_electronica corregida
def ajustar_precision_items(valor):
    """Ajusta valor para items: multipleOf 1e-08 (8 decimales)"""
    if valor is None:
        return Decimal('0.00000000')
    if not isinstance(valor, Decimal):
        valor = Decimal(str(valor))
    return valor.quantize(Decimal('0.00000001'), rounding=ROUND_HALF_UP)

def ajustar_precision_resumen(valor):
    """Ajusta valor para resumen: multipleOf 0.01 (2 decimales)"""
    if valor is None:
        return Decimal('0.00')
    if not isinstance(valor, Decimal):
        valor = Decimal(str(valor))
    return valor.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

# dte/views.py - Función crear_factura_electronica CON DEBUGGING
@require_http_methods(["GET", "POST"])
def crear_factura_electronica(request):
    """
    Vista unificada para crear Facturas y CCF con firma y envío a Hacienda
    ACTUALIZADA: Descuentos aplicados al precio unitario, campos de descuento siempre en 0
    Permite al usuario decidir si enviar FC a Hacienda o generar solo imprimible
    """
    tipo_dte = request.GET.get('tipo', request.POST.get('tipo_dte', '01'))
    print(f"DEBUG: tipo_dte = {tipo_dte}")

    if request.method == 'POST':
        print("DEBUG: Procesando POST request")
        
        # NUEVO: Obtener opción de envío a Hacienda (solo para FC)
        enviar_hacienda = request.POST.get('enviar_hacienda') == '1' if tipo_dte == '01' else True
        print(f"DEBUG: enviar_hacienda = {enviar_hacienda}")
        
        try:
            # Formularios
            print("DEBUG: Creando formularios...")
            if not request.user.sucursal:
                return JsonResponse({
                    'success': False,
                    'message': 'Su usuario no tiene una sucursal asignada. Contacte al administrador.'
                })

            sucursal = request.user.sucursal
            identificacion_form = IdentificacionForm(request.POST, tipo_dte=tipo_dte, sucursal=sucursal)
            item_formset = ItemFormset(request.POST)

            # Datos del receptor
            print("DEBUG: Extrayendo datos del receptor...")
            receptor_data = {
                key.replace('receptor_', ''): val
                for key, val in request.POST.items()
                if key.startswith('receptor_')
            }
            receptor_data['tipo_dte'] = tipo_dte
            print(f"DEBUG: receptor_data keys = {list(receptor_data.keys())}")

            # Validaciones por tipo de documento
            print("DEBUG: Validando por tipo de documento...")
            if tipo_dte == "03":  # CCF
                print("DEBUG: Validando CCF...")
                campos_obligatorios = [
                    'tipoDocumento', 'numDocumento', 'nrc', 'nombre',
                    'codActividad', 'descActividad', 'departamento',
                    'municipio', 'complemento', 'telefono', 'correo'
                ]
                faltantes = [c for c in campos_obligatorios if not receptor_data.get(c)]
                print(f"DEBUG: Campos faltantes para CCF: {faltantes}")
                
                if faltantes:
                    print(f"ERROR: Faltan campos obligatorios para CCF: {faltantes}")
                    messages.error(
                        request,
                        f'Para Crédito Fiscal son obligatorios: {", ".join(faltantes)}'
                    )
                    context = get_context_data(tipo_dte)
                    context.update({
                        'identificacion_form': identificacion_form,
                        'item_formset': item_formset,
                    })
                    return render(request, 'dte/factura_form.html', context)

                if receptor_data.get('tipoDocumento') != "36":
                    print("ERROR: CCF debe ser NIT")
                    messages.error(request, 'Para Crédito Fiscal solo se permite NIT')
                    context = get_context_data(tipo_dte)
                    context.update({
                        'identificacion_form': identificacion_form,
                        'item_formset': item_formset,
                    })
                    return render(request, 'dte/factura_form.html', context)

            else:  # Factura
                print("DEBUG: Validando Factura...")
                if not all([
                    receptor_data.get('tipoDocumento'),
                    receptor_data.get('numDocumento'),
                    receptor_data.get('nombre')
                ]):
                    print("ERROR: Faltan campos mínimos para Factura")
                    messages.error(
                        request,
                        'Debe completar al menos tipo documento, número y nombre del receptor'
                    )
                    context = get_context_data(tipo_dte)
                    context.update({
                        'identificacion_form': identificacion_form,
                        'item_formset': item_formset,
                    })
                    return render(request, 'dte/factura_form.html', context)

            # Validación de formularios
            print("DEBUG: Validando formularios...")
            identificacion_valido = identificacion_form.is_valid()
            item_formset_valido = item_formset.is_valid()
            
            print(f"DEBUG: identificacion_form.is_valid() = {identificacion_valido}")
            print(f"DEBUG: item_formset.is_valid() = {item_formset_valido}")
            
            if not identificacion_valido:
                print(f"ERROR: identificacion_form errors = {identificacion_form.errors}")
            
            if not item_formset_valido:
                print(f"ERROR: item_formset errors = {item_formset.errors}")
                print(f"ERROR: item_formset non_form_errors = {item_formset.non_form_errors()}")
                for i, form in enumerate(item_formset):
                    if form.errors:
                        print(f"ERROR: item_form[{i}] errors = {form.errors}")

            if not (identificacion_valido and item_formset_valido):
                print("ERROR: Formularios no válidos, mostrando errores...")
                context = get_context_data(tipo_dte)
                context.update({
                    'identificacion_form': identificacion_form,
                    'item_formset': item_formset,
                })
                return render(request, 'dte/factura_form.html', context)

            print("DEBUG: Iniciando transacción...")
            with transaction.atomic():
                # 1. Guardar identificación
                print("DEBUG: Guardando identificación...")
                identificacion = identificacion_form.save()
                print(f"DEBUG: Identificación guardada: {identificacion.numeroControl}")

                # 2. Procesar receptor
                print("DEBUG: Procesando receptor...")
                receptor = procesar_receptor_desde_factura(receptor_data)
                print(f"DEBUG: Receptor procesado: {receptor.nombre}")

                # 3. Crear factura
                print("DEBUG: Creando factura...")
                emisor = _emisor_maestro()
                if not emisor:
                    raise Exception("No hay emisor configurado en el sistema")

                factura = FacturaElectronica.objects.create(
                    identificacion=identificacion,
                    receptor=receptor,
                    emisor=emisor,
                    sucursal=sucursal
                )
                print(f"DEBUG: Factura creada: {factura.pk}")

                # 4. Guardar items con descuento aplicado al precio unitario
                print("DEBUG: Guardando items...")
                items = item_formset.save(commit=False)
                print(f"DEBUG: Número de items: {len(items)}")
                
                # Variables para acumular totales SIN redondear
                total_gravada_acumulada = Decimal('0.00')
                
                for i, it in enumerate(items):
                    print(f"DEBUG: Procesando item {i+1}: {it.descripcion}")
                    it.factura = factura

                    try:
                        from productos.models import Producto
                        from django.db.models import Q
                        
                        # Buscar el producto por código
                        producto = Producto.objects.filter(
                            Q(codigo1=it.codigo) |
                            Q(codigo2=it.codigo) |
                            Q(codigo3=it.codigo) |
                            Q(codigo4=it.codigo)
                        ).first()
                        
                        if not producto:
                            print(f"WARNING: Producto no encontrado con código {it.codigo}")
                        else:
                            # Verificar stock y actualizar
                            cantidad_solicitada = it.cantidad
                            existencias_actuales = producto.existencias
                            
                            if cantidad_solicitada > existencias_actuales:
                                raise Exception(f"No hay suficiente stock para {producto.descripcion} (código: {it.codigo}). "
                                            f"Solicitado: {cantidad_solicitada}, Disponible: {existencias_actuales}")
                            
                            producto.existencias -= cantidad_solicitada
                            producto.save()
                            
                            print(f"DEBUG: Stock actualizado para {producto.descripcion}: "
                                f"{existencias_actuales} -> {producto.existencias}")
                        
                    except Exception as e:
                        print(f"ERROR: Error actualizando stock para item {it.codigo}: {str(e)}")
                        raise Exception(f"Error actualizando inventario para {it.descripcion}: {str(e)}")
                    
                    # CAMBIO PRINCIPAL: Aplicar descuento al precio unitario
                    precio_original = it.precioUni
                    descuento_pct = Decimal('0.00')
                    
                    # Calcular porcentaje de descuento del montoDescu original
                    if hasattr(it, 'montoDescu') and it.montoDescu > 0:
                        subtotal_original = precio_original * it.cantidad
                        if subtotal_original > 0:
                            descuento_pct = (it.montoDescu / subtotal_original) * Decimal('100')
                    
                    print(f"DEBUG: Precio original: {precio_original}, Descuento: {descuento_pct}%")
                    
                    # Calcular precio unitario CON descuento aplicado
                    factor_descuento = Decimal('1') - (descuento_pct / Decimal('100'))
                    precio_con_descuento = precio_original * factor_descuento
                    
                    # Almacenar el descuento aplicado para NC (NUEVO CAMPO)
                    it.descuentoAplicado = descuento_pct

                    precio_idx = 1  # Por defecto
                    for form in item_formset:
                        if form.cleaned_data.get('codigo') == it.codigo:
                            precio_idx = int(form.cleaned_data.get('precio_idx', 1))
                            break
                    it.precioIndiceUsado = precio_idx

                    print(f"DEBUG: Precio índice usado: {precio_idx}, Descuento aplicado: {descuento_pct}%")
                    
                    if tipo_dte == "03":  # CCF
                        # Para CCF: El precio viene con IVA, aplicar descuento y calcular
                        precio_con_iva_y_descuento = precio_con_descuento
                        precio_sin_iva_con_descuento = precio_con_iva_y_descuento / Decimal('1.13')
                        
                        # Calcular totales con el precio ya descontado
                        subtotal_sin_iva = precio_sin_iva_con_descuento * it.cantidad
                        venta_gravada_sin_iva = subtotal_sin_iva  # Ya no hay descuento adicional
                        
                        # Acumular en variables de precisión completa
                        total_gravada_acumulada += venta_gravada_sin_iva
                        
                        # Asignar valores REDONDEADOS solo para almacenamiento
                        it.precioUni = precio_sin_iva_con_descuento.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                        it.montoDescu = Decimal('0.00')  # CAMBIO: Siempre cero
                        it.ventaGravada = venta_gravada_sin_iva.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                        it.ivaItem = Decimal('0.00')
                        
                        print(f"DEBUG CCF: Precio con descuento aplicado:")
                        print(f"  - Precio original: {precio_original}")
                        print(f"  - Descuento aplicado: {descuento_pct}%")
                        print(f"  - Precio final sin IVA: {it.precioUni}")
                        
                    elif tipo_dte == "14":  # FSE
                        # Para FSE: precio viene CON IVA, pero FSE trabaja SIN IVA
                        precio_con_iva = precio_original
                        precio_sin_iva = precio_con_iva / Decimal('1.13')  # Extraer precio sin IVA
                        
                        # Aplicar descuento al precio con IVA primero, luego extraer sin IVA
                        precio_con_iva_y_descuento = precio_con_descuento
                        precio_sin_iva_con_descuento = precio_con_iva_y_descuento / Decimal('1.13')
                        
                        # Calcular totales con el precio sin IVA ya descontado
                        subtotal_sin_iva = precio_sin_iva_con_descuento * it.cantidad
                        compra = subtotal_sin_iva  # Para FSE no hay descuento adicional, ya está aplicado
                        
                        total_gravada_acumulada += compra
                        
                        it.precioUni = precio_sin_iva_con_descuento.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                        it.montoDescu = Decimal('0.00')  # CAMBIO: Siempre cero
                        it.ventaGravada = compra.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                        it.ivaItem = Decimal('0.00')  # FSE no tiene IVA
                        
                        print(f"DEBUG FSE: Precio con descuento aplicado:")
                        print(f"  - Precio original con IVA: {precio_original}")
                        print(f"  - Descuento aplicado: {descuento_pct}%")
                        print(f"  - Precio final sin IVA: {it.precioUni}")
                        
                    else:  # Factura normal
                        # Para Factura: aplicar descuento y calcular IVA
                        subtotal_con_descuento = precio_con_descuento * it.cantidad
                        iva_sobre_precio_descontado = ((subtotal_con_descuento / Decimal('1.13')) * Decimal('0.13')) if subtotal_con_descuento > 0 else Decimal('0.00')
                        
                        it.precioUni = precio_con_descuento.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                        it.montoDescu = Decimal('0.00')  # CAMBIO: Siempre cero
                        it.ventaGravada = subtotal_con_descuento.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                        it.ivaItem = iva_sobre_precio_descontado.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                        
                        # Acumular para factura
                        total_gravada_acumulada += subtotal_con_descuento
                    
                    # Asignar tributos según tipo de documento
                    if tipo_dte == "03" and it.ventaGravada > Decimal('0'):
                        it.save()
                        tributo_iva = Tributo.objects.get(codigo="20")
                        it.tributos.add(tributo_iva)
                        print(f"DEBUG: Asignado tributo IVA al item {i+1} para CCF")
                    else:
                        it.save()
                    print(f"DEBUG: Item {i+1} guardado con descuento aplicado")

                # 5. Cálculo de totales PRECISOS diferenciado por tipo
                print("DEBUG: Calculando totales...")
                
                if tipo_dte == "03":  # CCF
                    # Usar valores acumulados SIN redondear para el cálculo final
                    print(f"DEBUG CCF: Total gravada acumulada (sin redondear): {total_gravada_acumulada}")
                    
                    # Calcular IVA sobre el total acumulado SIN redondear
                    total_iva_preciso = total_gravada_acumulada * Decimal('0.13')
                    print(f"DEBUG CCF: IVA calculado (sin redondear): {total_iva_preciso}")
                    
                    # Total a pagar = subtotal + IVA (ambos con precisión completa)
                    total_pagar_preciso = total_gravada_acumulada + total_iva_preciso
                    print(f"DEBUG CCF: Total a pagar (sin redondear): {total_pagar_preciso}")
                    
                    # AHORA SÍ redondear para almacenamiento final
                    total_gravada = total_gravada_acumulada.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    total_iva = total_iva_preciso.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    total_pagar = total_pagar_preciso.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    
                    print(f"DEBUG CCF: Valores finales redondeados:")
                    print(f"  - Total gravada (sin IVA): ${total_gravada}")
                    print(f"  - IVA calculado (13%): ${total_iva}")
                    print(f"  - Total a pagar: ${total_pagar}")
                    
                elif tipo_dte == "14":  # FSE
                    print("DEBUG FSE: Creando resumen FSE...")
                    total_compra = total_gravada_acumulada.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    total_descuento_fse = Decimal('0.00')  # CAMBIO: Siempre cero
                    total_pagar = total_compra
                    
                    # Usar variables compatibles con el resto del código
                    total_gravada = total_compra
                    total_iva = Decimal('0.00')
                    
                    print(f"DEBUG FSE: Total compra: ${total_compra}, Total pagar: ${total_pagar}")
                    
                else:  # Factura
                    # Para Factura: usar valores ya calculados con descuento aplicado
                    total_gravada = total_gravada_acumulada.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    total_iva = sum(i.ivaItem for i in factura.cuerpo_documento.all())
                    total_pagar = total_gravada
                    
                    print(f"DEBUG FC: Total gravada: ${total_gravada}")
                    print(f"DEBUG FC: IVA de items: ${total_iva}")
                    print(f"DEBUG FC: Total a pagar: ${total_pagar}")

                # Calcular otros valores del resumen
                total_letras = numero_a_letras(total_pagar)
                subtotal = total_gravada
                descu_gravada = Decimal('0.00')  # CAMBIO: Siempre cero
                porcentaje_desc = Decimal('0.00')  # CAMBIO: Siempre cero
                total_descu = Decimal('0.00')  # CAMBIO: Siempre cero

                # 6. Crear resumen diferenciado por tipo
                print("DEBUG: Creando resumen...")
                resumen_data = {
                    'factura': factura,
                    'totalNoSuj': Decimal('0.00'),
                    'totalExenta': Decimal('0.00'),
                    'totalGravada': total_gravada,
                    'subTotal': subtotal,
                    'subTotalVentas': total_gravada,
                    'descuNoSuj': Decimal('0.00'),
                    'descuExenta': Decimal('0.00'),
                    'descuGravada': descu_gravada,
                    'porcentajeDescuento': porcentaje_desc,
                    'totalDescu': total_descu,
                    'ivaRete1': Decimal('0.00'),
                    'reteRenta': Decimal('0.00'),
                    'totalNoGravado': Decimal('0.00'),
                    'saldoFavor': Decimal('0.00'),
                    'condicionOperacion': CondicionOperacion.objects.get(pk=1),
                    'numPagoElectronico': "",
                    'totalLetras': total_letras
                }
                
                # DIFERENCIA CLAVE en resumen según tipo de documento
                if tipo_dte == "03":  # CCF
                    resumen_data.update({
                        'montoTotalOperacion': total_pagar,
                        'totalPagar': total_pagar,
                        'ivaPerci1': Decimal('0.00')
                    })
                elif tipo_dte == "14":  # FSE
                    resumen_data.update({
                        'total_compra': total_compra,
                        'descu': total_descuento_fse,
                        'observaciones_fse': receptor_data.get('observaciones_fse', ''),
                        'montoTotalOperacion': total_pagar,
                        'totalPagar': total_pagar,
                        'totalIva': Decimal('0.00')
                    })
                else:  # Factura
                    resumen_data.update({
                        'montoTotalOperacion': subtotal,
                        'totalPagar': total_pagar,
                        'totalIva': total_iva
                    })

                resumen = Resumen.objects.create(**resumen_data)
                print(f"DEBUG: Resumen creado")
                
                # 7. Crear tributo de IVA en resumen solo para CCF con valor PRECISO
                if tipo_dte == "03" and total_iva > 0:
                    tributo_iva = Tributo.objects.get(codigo="20")
                    TributoResumen.objects.create(
                        resumen=resumen,
                        codigo=tributo_iva,
                        descripcion="Impuesto al Valor Agregado 13%",
                        valor=total_iva
                    )
                    print(f"DEBUG: Agregado tributo IVA al resumen de CCF: ${total_iva}")

                # NUEVO: Procesar según la opción del usuario
                if enviar_hacienda:
                    # PROCESO COMPLETO: Firmar y enviar a Hacienda (lógica existente)
                    print("DEBUG: Procesando con envío a Hacienda...")
                    
                    # 8. Generar y validar JSON
                    print("DEBUG: Generando JSON...")
                    dte_json = build_dte_json(factura)
                    print(f"DEBUG: JSON generado correctamente")
                    print(dte_json)
                    
                    esquema = get_schema_for_tipo_dte(tipo_dte)
                    print("DEBUG: Validando JSON contra esquema...")
                    jsonschema_validate(instance=dte_json, schema=esquema)
                    print("DEBUG: JSON válido según esquema")

                    # 9. Firmar y enviar a Hacienda
                    print("DEBUG: Configurando servicio DTE...")
                    servicio = DTEService(
                        emisor=factura.emisor,
                        ambiente=settings.DTE_AMBIENTE,
                        firmador_url=settings.FIRMADOR_URL,
                        dte_urls=settings.DTE_URLS[settings.DTE_AMBIENTE],
                        dte_user=settings.DTE_USER,
                        dte_password=settings.DTE_PASSWORD,
                    )
                    
                    print("DEBUG: Firmando documento...")
                    factura.documento_firmado = servicio.firmar_documento(dte_json)
                    factura.save(update_fields=['documento_firmado'])
                    print("DEBUG: Documento firmado")

                    print("DEBUG: Autenticando con Hacienda...")
                    token = servicio.autenticar()
                    print("DEBUG: Token obtenido")
                    
                    print("DEBUG: Enviando a Hacienda...")
                    respuesta = servicio.enviar_a_hacienda(
                        token=token,
                        codigo_generacion=factura.identificacion.codigoGeneracion,
                        tipo_dte=tipo_dte,
                        dte_json=dte_json
                    )
                    print(f"DEBUG: Respuesta de Hacienda: {respuesta}")
                    if respuesta.get('estado') == "PROCESADO":
                        estado_hacienda = "ACEPTADO"
                    else:
                        estado_hacienda = "RECHAZADO"
                    factura.estado_hacienda = estado_hacienda
                    factura.sello_recepcion = respuesta.get('sello', '')
                    factura.observaciones_hacienda = json.dumps(respuesta.get('observaciones', []))
                    factura.save(update_fields=[
                        'estado_hacienda',
                        'sello_recepcion',
                        'observaciones_hacienda'
                    ])
                    
                    # — Sólo enviar correo si Hacienda procesó o aceptó correctamente —
                    if respuesta.get('estado') in ('PROCESADO', 'ACEPTADO'):
                        # Generar PDF
                        pdf_bytes = generar_pdf_factura_mejorado(factura)
                        # Generar JSON con firma y sello
                        json_str = json.dumps(
                            build_dte_json(factura, incluir_firma_y_sello=True),
                            indent=2,
                            ensure_ascii=False
                        )
                        archivos = [
                            {
                                'filename': f"{factura.identificacion.numeroControl}.pdf",
                                'content': pdf_bytes,
                                'mimetype': 'application/pdf'
                            },
                            {
                                'filename': f"{factura.identificacion.numeroControl}_firmado.json",
                                'content': json_str,
                                'mimetype': 'application/json'
                            }
                        ]
                        servicio.enviar_correo_factura(factura, archivos)
                        messages.success(request, 'Factura enviada por correo al receptor.')

                    print("DEBUG: Proceso completado exitosamente")
                    
                    tipo_nombre = {
                        "01": "Factura",
                        "03": "Crédito Fiscal", 
                        "14": "Sujeto Excluido"
                    }.get(tipo_dte, "Documento")
                    
                    messages.success(
                        request,
                        f"{tipo_nombre} {factura.identificacion.numeroControl} enviada exitosamente."
                    )
                
                else:
                    # NUEVO: PROCESO SIMPLIFICADO - Solo generar imprimible
                    print("DEBUG: Procesando sin envío a Hacienda (solo imprimible)...")
                    
                    # Generar PDF simplificado y enviarlo por correo
                    if factura.receptor.correo:
                        pdf_bytes = generar_pdf_factura_simplificado(factura)
                        
                        archivos = [
                            {
                                'filename': f"{factura.identificacion.numeroControl}_imprimible.pdf",
                                'content': pdf_bytes,
                                'mimetype': 'application/pdf'
                            }
                        ]
                        
                        # Crear servicio solo para envío de correo
                        servicio = DTEService(emisor=factura.emisor)
                        servicio.enviar_correo_factura_simplificado(factura, archivos)
                        messages.success(request, 'Factura (imprimible) enviada por correo al receptor.')
                    
                    messages.success(
                        request,
                        f"Factura {factura.identificacion.numeroControl} generada como imprimible (sin validez fiscal)."
                    )
                
                return redirect('dte:factura_detail', pk=factura.pk)

        except Exception as e:
            print(f"ERROR: Excepción capturada: {str(e)}")
            print(f"ERROR: Tipo de excepción: {type(e).__name__}")
            import traceback
            print(f"ERROR: Traceback completo:")
            traceback.print_exc()
            
            messages.error(request, f"Error al procesar el documento: {e}")
            context = get_context_data(tipo_dte)
            context.update({
                'identificacion_form': IdentificacionForm(request.POST, tipo_dte=tipo_dte),
                'item_formset': ItemFormset(request.POST),
            })
            return render(request, 'dte/factura_form.html', context)

    # GET request
    print("DEBUG: Procesando GET request")
    identificacion_form = IdentificacionForm(tipo_dte=tipo_dte)
    item_formset = ItemFormset()
    context = get_context_data(tipo_dte)
    context.update({
        'identificacion_form': identificacion_form,
        'item_formset': item_formset,
    })
    return render(request, 'dte/factura_form.html', context)


def get_context_data(tipo_dte='01'):
    """Función auxiliar para obtener contexto según tipo de documento"""
    context = {
        'tipos_documento': TipoDocReceptor.objects.all(),
        'departamentos': Departamento.objects.all(),
        'municipios': Municipio.objects.all(),
        'actividades_economicas': ActividadEconomica.objects.all(),
        'tipos_items': TipoItem.objects.all(),
        'tipo_dte': tipo_dte,
        'es_ccf': tipo_dte == "03",
        'es_fse': tipo_dte == "14",  # NUEVO
        'titulo': "Sujeto Excluido" if tipo_dte == "14" else ("Crédito Fiscal" if tipo_dte == "03" else "Factura")
    }
    
    # Para CCF, filtrar solo NIT
    if tipo_dte == "03":
        context['tipos_documento'] = TipoDocReceptor.objects.filter(codigo="36")
    
    return context

def generar_pdf_factura_simplificado(factura):
    """
    Genera un PDF simplificado de la factura sin sección de identificación completa
    Solo muestra el número de control y omite el sello de recepción
    """
    from io import BytesIO
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, 
                          leftMargin=15*mm, rightMargin=15*mm,
                          topMargin=12*mm, bottomMargin=12*mm)
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=6,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Heading2'],
        fontSize=12,
        spaceAfter=4,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    normal_style = ParagraphStyle(
        'Normal',
        parent=styles['Normal'],
        fontSize=8,
        fontName='Helvetica',
        leading=10
    )
    
    story = []
    
    # Encabezado
    story.append(Paragraph("FACTURA ELECTRÓNICA", title_style))
    story.append(Paragraph("(DOCUMENTO NO OFICIAL)", subtitle_style))
    story.append(Spacer(1, 6*mm))
    
    # Solo número de control (identificación simplificada)
    story.append(Paragraph(f"<b>Número de Control:</b> {factura.identificacion.numeroControl}", normal_style))
    story.append(Spacer(1, 4*mm))
    
    # Emisor - CORREGIDA la dirección
    story.append(Paragraph("<b>EMISOR</b>", ParagraphStyle('Bold', fontSize=10, fontName='Helvetica-Bold')))
    story.append(Paragraph(f"<b>Nombre:</b> {factura.emisor.nombre}", normal_style))
    story.append(Paragraph(f"<b>NIT:</b> {factura.emisor.nit}", normal_style))
    
    # Construir dirección correctamente
    direccion_completa = f"{factura.emisor.departamento.texto}, {factura.emisor.municipio.texto}"
    if factura.emisor.complemento:
        direccion_completa += f", {factura.emisor.complemento}"
    
    story.append(Paragraph(f"<b>Dirección:</b> {direccion_completa}", normal_style))
    story.append(Spacer(1, 4*mm))
    
    # Receptor
    story.append(Paragraph("<b>RECEPTOR</b>", ParagraphStyle('Bold', fontSize=10, fontName='Helvetica-Bold')))
    story.append(Paragraph(f"<b>Nombre:</b> {factura.receptor.nombre}", normal_style))
    if factura.receptor.numDocumento:
        story.append(Paragraph(f"<b>Documento:</b> {factura.receptor.numDocumento}", normal_style))
    story.append(Spacer(1, 4*mm))
    
    # Items
    items_data = [['Cant.', 'Descripción', 'Precio Unit.', 'Total']]
    for item in factura.cuerpo_documento.all():
        items_data.append([
            str(item.cantidad),
            item.descripcion[:50] + ('...' if len(item.descripcion) > 50 else ''),
            f"${item.precioUni:.2f}",
            f"${item.ventaGravada:.2f}"
        ])
    
    items_table = Table(items_data, colWidths=[20*mm, 80*mm, 30*mm, 30*mm])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 7),
        ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),
    ]))
    
    story.append(items_table)
    story.append(Spacer(1, 6*mm))
    
    # Totales
    story.append(Paragraph(f"<b>TOTAL A PAGAR: ${factura.resumen.totalPagar:.2f}</b>", 
                          ParagraphStyle('Total', fontSize=12, fontName='Helvetica-Bold', alignment=TA_RIGHT)))
    
    story.append(Spacer(1, 10*mm))
    story.append(Paragraph("DOCUMENTO NO OFICIAL - SIN VALIDEZ FISCAL", 
                          ParagraphStyle('Footer', fontSize=8, alignment=TA_CENTER, textColor=colors.red)))
    
    doc.build(story)
    buffer.seek(0)
    return buffer.read()


def procesar_receptor_desde_factura(receptor_data):
    """
    Procesa los datos del receptor desde el formulario de factura.
    CORREGIDO: Validación mejorada de departamentos y municipios
    """
    try:
        tipo_dte = receptor_data.get('tipo_dte', '01')
        receptor_id = receptor_data.get('id')
        receptor_modificado = receptor_data.get('modificado') == 'true'
        
        print(f"DEBUG: Procesando receptor para tipo_dte: {tipo_dte}")
        
        # Validaciones específicas según tipo de DTE (sin cambios)
        if tipo_dte == "03":  # CCF
            if receptor_data.get('tipoDocumento') != "36":
                raise Exception("Para Crédito Fiscal solo se permite NIT")
            
            num_documento = receptor_data.get('numDocumento', '').strip()
            import re
            if not re.match(r"^(\d{9}|\d{14})$", num_documento):
                raise Exception("Para CCF, el NIT debe tener 9 o 14 dígitos")
            
            campos_obligatorios = {
                'numDocumento': 'Número de NIT',
                'nrc': 'NRC',
                'nombre': 'Nombre',
                'codActividad': 'Código de Actividad',
                'descActividad': 'Descripción de Actividad',
                'departamento': 'Departamento',
                'municipio': 'Municipio',
                'complemento': 'Dirección Complementaria',
                'telefono': 'Teléfono',
                'correo': 'Correo Electrónico'
            }
            
        elif tipo_dte == "14":  # FSE
            campos_obligatorios = {
                'numDocumento': 'Número de Documento',
                'nombre': 'Nombre',
                'departamento': 'Departamento',
                'municipio': 'Municipio',
                'complemento': 'Dirección Complementaria',
                'correo': 'Correo Electrónico'
            }
            
            if receptor_data.get('tipoDocumento') == '13':
                num_documento = receptor_data.get('numDocumento', '').strip()
                import re
                if not re.match(r"^[0-9]{8}-[0-9]$", num_documento):
                    raise Exception("Para DUI en FSE, el formato debe ser XXXXXXXX-X")
            
        else:  # Factura
            campos_obligatorios = {
                'tipoDocumento': 'Tipo de Documento',
                'numDocumento': 'Número de Documento', 
                'nombre': 'Nombre',
                'correo': 'Correo Electrónico'
            }
            
            tipo_doc = receptor_data.get('tipoDocumento')
            num_doc = receptor_data.get('numDocumento', '').strip()
            
            if tipo_doc == "36":
                import re
                if not re.match(r"^(\d{9}|\d{14})$", num_doc):
                    raise Exception("Para NIT, el número debe tener 9 o 14 dígitos")
            elif tipo_doc == "13":
                import re
                if not re.match(r"^[0-9]{8}-[0-9]$", num_doc):
                    raise Exception("Para DUI, el formato debe ser XXXXXXXX-X")

        # Validar campos obligatorios
        faltantes = []
        for campo, descripcion in campos_obligatorios.items():
            valor = receptor_data.get(campo)
            if not valor or not str(valor).strip():
                faltantes.append(descripcion)
        
        if faltantes:
            raise Exception(f"Campos obligatorios faltantes para {tipo_dte}: {', '.join(faltantes)}")

        # Si existe un receptor y no fue modificado, usarlo
        if receptor_id and not receptor_modificado:
            receptor = Receptor.objects.get(id=receptor_id)
            return receptor

        def clean_optional_field(value):
            if value is None or value == '':
                return None
            return value.strip() if isinstance(value, str) and value.strip() else None

        # Preparar datos limpios del receptor
        datos_receptor = {
            'tipoDocumento_id': receptor_data['tipoDocumento'],
            'numDocumento': receptor_data['numDocumento'].strip(),
            'nombre': receptor_data['nombre'].strip(),
        }

        # CAMBIO CRÍTICO: Validación de departamento y municipio antes de asignar
        if tipo_dte in ["03", "14"]:
            datos_receptor.update({
                'nrc': receptor_data['nrc'].strip(),
                'correo': receptor_data['correo'].strip(),
                'complemento': receptor_data['complemento'].strip(),
            })
            
            # Validar y asignar departamento
            departamento_codigo = receptor_data.get('departamento')
            if departamento_codigo:
                try:
                    departamento = Departamento.objects.get(codigo=departamento_codigo)
                    datos_receptor['departamento'] = departamento
                except Departamento.DoesNotExist:
                    raise Exception(f"Departamento con código {departamento_codigo} no existe")
            
            # Validar y asignar municipio
            municipio_codigo = receptor_data.get('municipio')
            if municipio_codigo and departamento_codigo:
                try:
                    municipio = Municipio.objects.get(
                        codigo=municipio_codigo,
                        departamento__codigo=departamento_codigo
                    )
                    datos_receptor['municipio'] = municipio
                except Municipio.DoesNotExist:
                    raise Exception(f"Municipio {municipio_codigo} no válido para el departamento {departamento_codigo}")
            
            # Otros campos
            if tipo_dte == "03":
                datos_receptor['telefono'] = receptor_data['telefono'].strip()
                datos_receptor['codActividad_id'] = receptor_data['codActividad']
                datos_receptor['descActividad'] = receptor_data['descActividad'].strip()
            else:  # FSE
                datos_receptor['telefono'] = clean_optional_field(receptor_data.get('telefono'))
                if receptor_data.get('codActividad'):
                    datos_receptor['codActividad_id'] = receptor_data['codActividad']
                datos_receptor['descActividad'] = clean_optional_field(receptor_data.get('descActividad'))
                
        else:  # Factura
            datos_receptor['correo'] = receptor_data['correo'].strip()
            
            datos_receptor.update({
                'nrc': clean_optional_field(receptor_data.get('nrc')),
                'telefono': clean_optional_field(receptor_data.get('telefono')),
                'complemento': clean_optional_field(receptor_data.get('complemento')),
                'descActividad': clean_optional_field(receptor_data.get('descActividad')),
            })
            
            # Validación similar para FC con departamento/municipio opcionales
            departamento_codigo = receptor_data.get('departamento')
            municipio_codigo = receptor_data.get('municipio')
            
            if departamento_codigo:
                try:
                    departamento = Departamento.objects.get(codigo=departamento_codigo)
                    datos_receptor['departamento'] = departamento
                except Departamento.DoesNotExist:
                    raise Exception(f"Departamento con código {departamento_codigo} no existe")
            
            if municipio_codigo and departamento_codigo:
                try:
                    municipio = Municipio.objects.get(
                        codigo=municipio_codigo,
                        departamento__codigo=departamento_codigo
                    )
                    datos_receptor['municipio'] = municipio
                except Municipio.DoesNotExist:
                    raise Exception(f"Municipio {municipio_codigo} no válido para el departamento {departamento_codigo}")
            
            if receptor_data.get('codActividad'):
                datos_receptor['codActividad_id'] = receptor_data['codActividad']

        # Buscar receptor existente por tipo y número de documento
        receptor, created = Receptor.objects.get_or_create(
            tipoDocumento_id=datos_receptor['tipoDocumento_id'],
            numDocumento=datos_receptor['numDocumento'],
            defaults=datos_receptor
        )

        # Si el receptor ya existía y fue modificado, actualizarlo
        if not created and receptor_modificado:
            for field, value in datos_receptor.items():
                if hasattr(receptor, field):
                    setattr(receptor, field, value)
            
            # REMOVER full_clean() que causaba errores de validación
            receptor.save()
            
            print(f"DEBUG: Receptor actualizado: {receptor.nombre} ({receptor.numDocumento})")

        elif created:
            print(f"DEBUG: Nuevo receptor creado para {tipo_dte}: {receptor.nombre} ({receptor.numDocumento})")

        return receptor
        
    except Receptor.DoesNotExist:
        raise Exception(f"No se encontró el receptor con ID {receptor_id}")
    except Exception as e:
        raise Exception(f"Error al procesar receptor: {str(e)}")


@require_http_methods(["GET"])
def buscar_receptores_ajax(request):
    """Vista AJAX para buscar receptores - adaptada para tipo de documento"""
    tipo_doc = request.GET.get('tipo_documento')
    numero_parcial = request.GET.get('numero', '').strip()
    tipo_dte = request.GET.get('tipo_dte', '01')  # Nuevo parámetro
    
    if not tipo_doc or not numero_parcial:
        return JsonResponse({'receptores': []})
    
    # Para CCF, solo buscar en receptores con NIT completo
    if tipo_dte == "03":
        if tipo_doc != "36":
            return JsonResponse({'receptores': []})
        # Para CCF buscar solo coincidencias exactas de NIT
        receptores = Receptor.objects.filter(
            tipoDocumento_id=tipo_doc,
            numDocumento__exact=numero_parcial
        )
    else:
        # Para Factura, búsqueda normal
        receptores = Receptor.objects.filter(
            Q(tipoDocumento_id=tipo_doc) & (
                Q(numDocumento__iexact=numero_parcial) |
                Q(numDocumento__icontains=numero_parcial)
            )
        )
    
    receptores = receptores.select_related(
        'tipoDocumento', 'departamento', 'municipio', 'codActividad'
    )[:10]
    
    data = []
    for receptor in receptores:
        # Para CCF, validar que tenga todos los campos obligatorios
        if tipo_dte == "03":
            campos_completos = all([
                receptor.numDocumento, receptor.nrc, receptor.nombre,
                receptor.codActividad, receptor.descActividad,
                receptor.departamento, receptor.municipio, receptor.complemento,
                receptor.telefono, receptor.correo
            ])
            if not campos_completos:
                continue  # Saltar receptores incompletos para CCF
        
        departamento_codigo = receptor.departamento.codigo if receptor.departamento else ''
        municipio_codigo = receptor.municipio.codigo if receptor.municipio else ''
        actividad_codigo = receptor.codActividad.codigo if receptor.codActividad else ''
        
        data.append({
            'id': receptor.id,
            'numDocumento': receptor.numDocumento,
            'nrc': receptor.nrc or '',
            'nombre': receptor.nombre,
            'codActividad': actividad_codigo,
            'descActividad': receptor.descActividad or '',
            'departamento': departamento_codigo,
            'departamento_nombre': receptor.departamento.texto if receptor.departamento else '',
            'municipio': municipio_codigo,
            'municipio_nombre': receptor.municipio.texto if receptor.municipio else '',
            'complemento': receptor.complemento or '',
            'telefono': receptor.telefono or '',
            'correo': receptor.correo or '',
            'tipoDocumento': receptor.tipoDocumento.codigo,
            'tipoDocumento_descripcion': f"{receptor.tipoDocumento.codigo} - {receptor.tipoDocumento.texto}",
            'completo_ccf': tipo_dte == "03" and campos_completos  # Indicador para CCF
        })
    
    return JsonResponse({'receptores': data})

@require_http_methods(["GET"])
def obtener_receptor_ajax(request, receptor_id):
    """Vista AJAX para obtener datos completos de un receptor"""
    try:
        receptor = get_object_or_404(Receptor, id=receptor_id)
        data = model_to_dict(receptor)
        # Convertir foreign keys a IDs
        if data.get('tipoDocumento'):
            data['tipoDocumento'] = data['tipoDocumento'].codigo
        return JsonResponse({'success': True, 'receptor': data})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


# Reemplazar la función buscar_productos_ajax en dte/views.py

@require_http_methods(["GET"])
def buscar_productos_ajax(request):
    """Vista AJAX para buscar productos por código"""
    codigo_parcial = request.GET.get('codigo', '').strip()
    
    if not codigo_parcial:
        return JsonResponse({'productos': []})
    
    # Buscar en los 4 campos de código
    productos = Producto.objects.filter(
        codigo1__icontains=codigo_parcial
    ).union(
        Producto.objects.filter(codigo2__icontains=codigo_parcial),
        Producto.objects.filter(codigo3__icontains=codigo_parcial),
        Producto.objects.filter(codigo4__icontains=codigo_parcial)
    )[:10]  # Limitar a 10 resultados
    
    data = []
    for producto in productos:
        # Determinar qué código coincide
        codigo_usado = producto.codigo1
        if codigo_parcial.upper() in (producto.codigo2 or '').upper():
            codigo_usado = producto.codigo2
        elif codigo_parcial.upper() in (producto.codigo3 or '').upper():
            codigo_usado = producto.codigo3
        elif codigo_parcial.upper() in (producto.codigo4 or '').upper():
            codigo_usado = producto.codigo4
            
        data.append({
            'id': producto.id,
            'codigo': codigo_usado,
            'nombre': producto.nombre,
            'descripcion': producto.descripcion,
            'precio1': str(producto.precio1) if producto.precio1 else None,
            'precio2': str(producto.precio2) if producto.precio2 else None,
            'precio3': str(producto.precio3) if producto.precio3 else None,
            'precio4': str(producto.precio4) if producto.precio4 else None,
            'precios_disponibles': producto.get_precios_disponibles(),
            'descuento_por_defecto': producto.descuento_por_defecto,
            'existencias': producto.existencias,
        })
    
    return JsonResponse({'productos': data})


@require_http_methods(["GET"])
def obtener_producto_ajax(request, producto_id):
    """Vista AJAX para obtener datos completos de un producto"""
    try:
        producto = get_object_or_404(Producto, id=producto_id)
        data = {
            'id': producto.id,
            'codigo1': producto.codigo1,
            'codigo2': producto.codigo2 or '',
            'codigo3': producto.codigo3 or '',
            'codigo4': producto.codigo4 or '',
            'nombre': producto.nombre,
            'descripcion': producto.descripcion,
            'precio1': str(producto.precio1),
            'precio2': str(producto.precio2) if producto.precio2 else '',
            'precio3': str(producto.precio3) if producto.precio3 else '',
            'precio4': str(producto.precio4) if producto.precio4 else '',
            'descuento_por_defecto': producto.descuento_por_defecto,
            'existencias': producto.existencias,
        }
        return JsonResponse({'success': True, 'producto': data})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


def factura_detalle(request, pk):
    """Vista para mostrar el detalle de una factura creada"""
    factura = get_object_or_404(FacturaElectronica, pk=pk)
    context = {
        'factura': factura,
    }
    return render(request, 'dte/factura_detalle.html', context)

# dte/views_receptor.py
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy, reverse
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from django.views.decorators.http import require_http_methods
from django.db import IntegrityError
from django.core.exceptions import ValidationError

from .models import Receptor, TipoDocReceptor, ActividadEconomica, Departamento, Municipio
from .forms import ReceptorCRUDForm

# ─────────────────────────────────────
# CRUD de Receptores - CORREGIDO
# ─────────────────────────────────────

class ReceptorListView(ListView):
    model = Receptor
    template_name = 'receptor/list.html'
    context_object_name = 'receptores'
    paginate_by = 25
    ordering = ['nombre']

    def get_queryset(self):
        queryset = super().get_queryset().select_related(
            'tipoDocumento', 'codActividad', 'departamento', 'municipio'
        )
        
        # Filtros de búsqueda
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(nombre__icontains=search) |
                Q(numDocumento__icontains=search) |
                Q(nrc__icontains=search) |
                Q(correo__icontains=search)
            )
        
        tipo_documento = self.request.GET.get('tipo_documento')
        if tipo_documento:
            queryset = queryset.filter(tipoDocumento_id=tipo_documento)
        
        departamento = self.request.GET.get('departamento')
        if departamento:
            queryset = queryset.filter(departamento_id=departamento)
            
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tipos_documento'] = TipoDocReceptor.objects.all()
        context['departamentos'] = Departamento.objects.all()
        context['search'] = self.request.GET.get('search', '')
        context['selected_tipo_documento'] = self.request.GET.get('tipo_documento', '')
        context['selected_departamento'] = self.request.GET.get('departamento', '')
        return context


class ReceptorDetailView(DetailView):
    model = Receptor
    template_name = 'receptor/detail.html'
    context_object_name = 'receptor'

    def get_queryset(self):
        return super().get_queryset().select_related(
            'tipoDocumento', 'codActividad', 'departamento', 'municipio'
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Obtener facturas asociadas al receptor
        context['facturas_count'] = self.object.facturas.count()
        context['facturas_recientes'] = self.object.facturas.select_related(
            'identificacion'
        ).order_by('-identificacion__fecEmi')[:5]
        
        # Calcular completitud de información
        completitud = 0
        if self.object.nombre and self.object.tipoDocumento and self.object.numDocumento:
            completitud = 100
        elif self.object.nombre:
            completitud = 75
        elif self.object.tipoDocumento:
            completitud = 25
        
        context['completitud'] = completitud
        
        # Estado de la información
        context['tiene_email'] = bool(self.object.correo)
        context['tiene_direccion_completa'] = bool(
            self.object.departamento and 
            self.object.municipio and 
            self.object.complemento
        )
        
        return context


class ReceptorCreateView(View):
    template_name = 'receptor/form.html'
    
    def get(self, request):
        form = ReceptorCRUDForm()
        context = {
            'form': form,
            'tipos_documento': TipoDocReceptor.objects.all(),
            'departamentos': Departamento.objects.all(),
            'municipios': Municipio.objects.none(),
            'actividades_economicas': ActividadEconomica.objects.all(),
            'title': 'Nuevo Receptor'
        }
        return render(request, self.template_name, context)
    
    def post(self, request):
        form = ReceptorCRUDForm(request.POST)
        
        if form.is_valid():
            try:
                receptor = form.save()
                messages.success(
                    request, 
                    f'Receptor "{receptor.nombre}" creado exitosamente.'
                )
                return redirect('dte:receptor_detail', pk=receptor.pk)
            except IntegrityError:
                messages.error(
                    request, 
                    'Ya existe un receptor con ese tipo y número de documento.'
                )
            except ValidationError as e:
                messages.error(request, f'Error de validación: {e}')
        else:
            messages.error(
                request, 
                'Por favor corrige los errores en el formulario.'
            )
        
        context = {
            'form': form,
            'tipos_documento': TipoDocReceptor.objects.all(),
            'departamentos': Departamento.objects.all(),
            'municipios': Municipio.objects.all(),
            'actividades_economicas': ActividadEconomica.objects.all(),
            'title': 'Nuevo Receptor'
        }
        return render(request, self.template_name, context)


class ReceptorUpdateView(View):
    template_name = 'receptor/form.html'
    
    def get_object(self, pk):
        return get_object_or_404(Receptor, pk=pk)
    
    def get(self, request, pk):
        receptor = self.get_object(pk)
        form = ReceptorCRUDForm(instance=receptor)
        
        context = {
            'form': form,
            'object': receptor,
            'tipos_documento': TipoDocReceptor.objects.all(),
            'departamentos': Departamento.objects.all(),
            'municipios': Municipio.objects.all(),
            'actividades_economicas': ActividadEconomica.objects.all(),
             'title': f'Editar Receptor: {receptor.nombre}'
        }
        return render(request, self.template_name, context)
    
    def post(self, request, pk):
        receptor = self.get_object(pk)
        form = ReceptorCRUDForm(request.POST, instance=receptor)
        
        if form.is_valid():
            try:
                receptor = form.save()
                messages.success(
                    request, 
                    f'Receptor "{receptor.nombre}" actualizado exitosamente.'
                )
                return redirect('dte:receptor_detail', pk=receptor.pk)
            except IntegrityError:
                messages.error(
                    request, 
                    'Ya existe un receptor con ese tipo y número de documento.'
                )
            except ValidationError as e:
                messages.error(request, f'Error de validación: {e}')
        else:
            messages.error(
                request, 
                'Por favor corrige los errores en el formulario.'
            )
        
        context = {
            'form': form,
            'object': receptor,
            'tipos_documento': TipoDocReceptor.objects.all(),
            'departamentos': Departamento.objects.all(),
            'municipios': Municipio.objects.all(),
            'actividades_economicas': ActividadEconomica.objects.all(),
            'title': f'Editar Receptor: {receptor.nombre}'
        }
        return render(request, self.template_name, context)


class ReceptorDeleteView(View):
    template_name = 'receptor/confirm_delete.html'
    
    def get_object(self, pk):
        return get_object_or_404(Receptor, pk=pk)
    
    def get(self, request, pk):
        receptor = self.get_object(pk)
        context = {
            'receptor': receptor,
            'object': receptor  # Para compatibilidad con template
        }
        return render(request, self.template_name, context)
    
    def post(self, request, pk):
        receptor = self.get_object(pk)
        
        # Verificar si tiene facturas asociadas
        if receptor.facturas.exists():
            messages.error(
                request,
                f'No se puede eliminar el receptor "{receptor.nombre}" porque tiene facturas asociadas.'
            )
            return redirect('dte:receptor_detail', pk=receptor.pk)
        
        nombre = receptor.nombre
        receptor.delete()
        
        messages.success(
            request,
            f'Receptor "{nombre}" eliminado exitosamente.'
        )
        return redirect('dte:receptor_list')


# Agregar al final del archivo las vistas AJAX que faltan:

# Reemplazar la función receptor_datatable en views.py con esta versión mejorada:

# Reemplazar la función receptor_datatable en views.py con esta versión mejorada:

# Reemplazar la función receptor_datatable en views.py con esta versión mejorada:

@require_http_methods(["GET"])
def receptor_datatable(request):
    """Vista para DataTables AJAX"""
    from django.urls import reverse
    
    # Parámetros de DataTables
    draw = int(request.GET.get('draw', 1))
    start = int(request.GET.get('start', 0))
    length = int(request.GET.get('length', 25))
    search_value = request.GET.get('search[value]', '')
    order_column = int(request.GET.get('order[0][column]', 0))
    order_dir = request.GET.get('order[0][dir]', 'asc')

    # Columnas para ordenamiento
    columns = [
        'id', 'nombre', 'numDocumento', 'tipoDocumento__texto', 
        'nrc', 'correo', 'estado', 'actions'  # Ajustado para coincidir con la tabla
    ]
    
    # Query base
    queryset = Receptor.objects.select_related(
        'tipoDocumento', 'codActividad', 'departamento', 'municipio'
    )

    # Filtro de búsqueda
    if search_value:
        queryset = queryset.filter(
            Q(nombre__icontains=search_value) |
            Q(numDocumento__icontains=search_value) |
            Q(nrc__icontains=search_value) |
            Q(correo__icontains=search_value) |
            Q(telefono__icontains=search_value)
        )

    # Total de registros
    total_records = Receptor.objects.count()
    filtered_records = queryset.count()

    # Ordenamiento (evitar columnas no ordenables)
    if 0 <= order_column < len(columns) and order_column not in [6, 7]:  # estado y actions no son ordenables
        order_field = columns[order_column]
        if order_dir == 'desc':
            order_field = f'-{order_field}'
        queryset = queryset.order_by(order_field)
    else:
        queryset = queryset.order_by('nombre')  # Orden por defecto

    # Paginación
    receptores = queryset[start:start + length]

    # Preparar datos
    data = []
    for receptor in receptores:
        # Tipo de documento
        tipo_doc = receptor.tipoDocumento.codigo if receptor.tipoDocumento else 'N/A'
        
        # Estado basado en completitud de información
        estado_completitud = 0
        if receptor.nombre and receptor.tipoDocumento and receptor.numDocumento:
            estado_completitud = 100
        elif receptor.nombre:
            estado_completitud = 75
        elif receptor.tipoDocumento:
            estado_completitud = 25
            
        # Badge de estado
        if estado_completitud >= 75:
            estado_badge = '<span class="status-badge status-complete">Completo</span>'
        elif estado_completitud >= 50:
            estado_badge = '<span class="status-badge status-incomplete">Parcial</span>'
        else:
            estado_badge = '<span class="status-badge status-minimal">Mínimo</span>'
        
        # Botones de acción
        actions = f'''
            <div class="btn-group" role="group">
                <a href="{reverse('dte:receptor_detail', args=[receptor.id])}" 
                   class="btn btn-sm btn-info" title="Ver">
                    <i class="fas fa-eye"></i>
                </a>
                <a href="{reverse('dte:receptor_update', args=[receptor.id])}" 
                   class="btn btn-sm btn-warning" title="Editar">
                    <i class="fas fa-edit"></i>
                </a>
                <a href="{reverse('dte:receptor_delete', args=[receptor.id])}" 
                   class="btn btn-sm btn-danger" title="Eliminar">
                    <i class="fas fa-trash"></i>
                </a>
            </div>
        '''

        data.append([
            receptor.id,
            receptor.nombre or 'Sin nombre',
            receptor.numDocumento or 'N/A',
            tipo_doc,
            receptor.nrc or 'N/A',
            receptor.correo or 'N/A',
            estado_badge,
            actions
        ])

    return JsonResponse({
        'draw': draw,
        'recordsTotal': total_records,
        'recordsFiltered': filtered_records,
        'data': data
    })



# También agregar esta función auxiliar para obtener municipios por AJAX:

@require_http_methods(["GET"])
def obtener_municipios_ajax(request):
    """Vista AJAX para obtener municipios por departamento"""
    departamento_id = request.GET.get('departamento_id')
    
    if not departamento_id:
        return JsonResponse({'municipios': []})
    
    try:
        municipios = Municipio.objects.filter(
            departamento_id=departamento_id
        ).values('id', 'codigo', 'texto').order_by('texto')
        
        return JsonResponse({'municipios': list(municipios)})
    except Exception as e:
        return JsonResponse({'municipios': [], 'error': str(e)})




@require_http_methods(["GET"])
def validar_documento_ajax(request):
    """Vista AJAX para validar si ya existe un documento"""
    tipo_documento = request.GET.get('tipo_documento')
    num_documento = request.GET.get('num_documento')
    receptor_id = request.GET.get('receptor_id')  # Para excluir en edición
    
    if not tipo_documento or not num_documento:
        return JsonResponse({'existe': False})
    
    queryset = Receptor.objects.filter(
        tipoDocumento_id=tipo_documento,
        numDocumento=num_documento
    )
    
    # Excluir el receptor actual en caso de edición
    if receptor_id:
        queryset = queryset.exclude(id=receptor_id)
    
    existe = queryset.exists()
    
    return JsonResponse({'existe': existe})


# Agregar estas funciones al archivo views.py existente
# Agregar esta función al archivo views.py existente

# views.py - Todas las funciones relacionadas con Nota de Crédito
# Imports necesarios (agregar a la parte superior del archivo si no están)






from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from decimal import Decimal, ROUND_HALF_UP
from django.utils import timezone
from num2words import num2words
import uuid

# Importar modelos y formularios necesarios
from .models import (
    FacturaElectronica, Identificacion, TipoDocumento, CuerpoDocumentoItem, 
    Resumen, DocumentoRelacionado, GeneracionDocumento, NotaCreditoDetalle,
    Tributo, TributoResumen, CondicionOperacion
)
from .forms import (
    DocumentoOrigenForm, NotaCreditoSimplificadaForm
)
from .services import DTEService


def crear_nota_credito(request):
    """
    Vista principal para crear Nota de Crédito - OPTIMIZADA
    Basada en el patrón de crear_factura_electronica para consistencia
    """
    if request.method == "GET":
        # Paso 1: Mostrar formulario para seleccionar documento original
        documento_form = DocumentoOrigenForm()
        context = {
            'documento_form': documento_form,
            'paso': 'seleccionar_documento',
            'title': 'Crear Nota de Crédito - Seleccionar Documento Original'
        }
        return render(request, 'dte/nota_credito_form.html', context)
    
    elif request.method == "POST":
        # Verificar qué tipo de POST es (igual que crear_factura_electronica maneja pasos)
        if 'documento_origen' in request.POST and 'seleccionar_items' not in request.POST:
            # Paso 2: Documento seleccionado, mostrar items para seleccionar
            documento_form = DocumentoOrigenForm(request.POST)
            if documento_form.is_valid():
                documento_origen = documento_form.cleaned_data['documento_origen']
                return mostrar_seleccion_items(request, documento_origen)
            else:
                context = {
                    'documento_form': documento_form,
                    'paso': 'seleccionar_documento',
                    'title': 'Crear Nota de Crédito - Seleccionar Documento Original'
                }
                return render(request, 'dte/nota_credito_form.html', context)
        
        elif 'seleccionar_items' in request.POST:
            # Paso 3: Items seleccionados, crear la nota de crédito
            return procesar_creacion_nc_simplificada(request)
        
        else:
            messages.error(request, 'Solicitud inválida')
            return redirect('dte:crear_nota_credito')

def mostrar_seleccion_items(request, documento_origen):
    """
    ACTUALIZADA: Mostrar solo items disponibles del CCF para seleccionar en la NC
    Excluye items que ya fueron completamente acreditados
    """
    from .forms import obtener_datos_precisos_item_nc
    
    # CAMBIO PRINCIPAL: Solo obtener items con cantidad disponible
    items_originales_disponibles = documento_origen.get_items_disponibles_para_nc()
    
    if not items_originales_disponibles:
        messages.error(
            request, 
            f"El documento {documento_origen.identificacion.numeroControl} "
            f"no tiene items disponibles para acreditar. Todos los items ya han sido "
            f"procesados en notas de crédito anteriores."
        )
        return redirect('dte:crear_nota_credito')
    
    nc_detalle_form = NotaCreditoSimplificadaForm()
    
    # Pre-calcular datos precisos solo para items disponibles
    items_disponibles = []
    for item in items_originales_disponibles:
        
        # Obtener información de disponibilidad
        cantidad_original = item.cantidad
        cantidad_acreditada = item.get_cantidad_acreditada()
        cantidad_disponible = item.get_cantidad_disponible_para_nc()
        
        # Obtener datos precisos del producto de BD
        datos_precisos = obtener_datos_precisos_item_nc(item)
        
        if datos_precisos:
            precio_mostrar = datos_precisos['precio_sin_iva']
            precio_info = f"Basado en {datos_precisos['precio_usado']} (BD: ${datos_precisos['precio_con_iva']:.2f})"
        else:
            precio_mostrar = item.precioUni
            precio_info = "Precio original del CCF (fallback)"
        
        # NUEVA INFORMACIÓN DE DISPONIBILIDAD
        info_disponibilidad = ""
        if cantidad_acreditada > 0:
            notas_aplicadas = item.get_notas_credito_aplicadas()
            nc_numeros = [nc.nota_credito.identificacion.numeroControl for nc in notas_aplicadas]
            info_disponibilidad = f"Ya acreditadas {cantidad_acreditada} en: {', '.join(nc_numeros)}"
        
        # Preparar datos para el template con información de disponibilidad
        item_data = {
            'id': item.id,
            'numItem': item.numItem,
            'descripcion': item.descripcion,
            'codigo': item.codigo,
            # CAMBIO: usar cantidad disponible en lugar de original
            'cantidad_original': f"{cantidad_original:.2f}",
            'cantidad_acreditada': f"{cantidad_acreditada:.2f}",
            'cantidad_disponible': f"{cantidad_disponible:.2f}",
            'cantidad': f"{cantidad_disponible:.2f}",  # Para compatibilidad con JS
            'precioUni': f"{precio_mostrar:.8f}",
            'precioUniDisplay': f"{precio_mostrar:.2f}",
            'ventaGravada': f"{item.ventaGravada:.2f}",
            'uniMedida': item.uniMedida.texto if item.uniMedida else '',
            'precio_info': precio_info,
            'info_disponibilidad': info_disponibilidad,
            'tiene_nc_anteriores': cantidad_acreditada > 0,
        }
        
        items_disponibles.append(item_data)
    
    print(f"DEBUG mostrar_seleccion: {len(items_disponibles)} items disponibles de {documento_origen.cuerpo_documento.count()} totales")
    
    # Datos del receptor (sin cambios)
    receptor_readonly_data = {
        'tipoDocumento': documento_origen.receptor.tipoDocumento.texto if documento_origen.receptor.tipoDocumento else '',
        'numDocumento': documento_origen.receptor.numDocumento,
        'nrc': documento_origen.receptor.nrc,
        'nombre': documento_origen.receptor.nombre,
        'departamento': documento_origen.receptor.departamento.texto if documento_origen.receptor.departamento else '',
        'municipio': documento_origen.receptor.municipio.texto if documento_origen.receptor.municipio else '',
        'complemento': documento_origen.receptor.complemento,
        'telefono': documento_origen.receptor.telefono,
        'correo': documento_origen.receptor.correo,
    }
    
    # NUEVO: Información de estado del documento
    porcentaje_acreditado = float(documento_origen.get_porcentaje_acreditado())
    porcentaje_disponible = 100.0 - porcentaje_acreditado
    resumen_documento = {
        'subtotal_original': f"{documento_origen.resumen.subTotalVentas:.2f}",
        'iva_original': f"{(documento_origen.resumen.totalPagar - documento_origen.resumen.subTotalVentas):.2f}",
        'total_original': f"{documento_origen.resumen.totalPagar:.2f}",
        'items_count': documento_origen.cuerpo_documento.count(),
        'items_disponibles_count': len(items_disponibles),
        'porcentaje_ya_acreditado': f"{porcentaje_acreditado:.1f}",
        'porcentaje_disponible': f"{porcentaje_disponible:.1f}"
    }
    
    context = {
        'paso': 'seleccionar_items',
        'title': f'Crear Nota de Crédito – {documento_origen.identificacion.numeroControl}',
        'documento_origen': documento_origen,
        'items_originales': items_disponibles,  # Cambio: solo items disponibles
        'receptor_readonly_data': receptor_readonly_data,
        'nc_detalle_form': nc_detalle_form,
        'resumen_documento': resumen_documento,
    }
    return render(request, 'dte/nota_credito_form.html', context)

# En views.py, reemplazar la función procesar_creacion_nc_simplificada

# dte/views.py - Función procesar_creacion_nc_simplificada ACTUALIZADA

def procesar_creacion_nc_simplificada(request):
    """
    Procesa la creación de la nota de crédito completa - basada en crear_factura_electronica
    COMPLETA: Incluye validación de esquema, firma, envío a Hacienda y correo
    """
    try:
        from django.db.models import Q
        from productos.models import Producto
        from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
        from django.utils import timezone
        from jsonschema import validate as jsonschema_validate
        from jsonschema.exceptions import ValidationError as JSONSchemaValidationError
        import json
        import uuid
        
        documento_origen_id = request.POST.get('documento_origen_id')
        documento_origen = FacturaElectronica.objects.get(id=documento_origen_id)
        
        print(f"DEBUG NC: Procesando NC para documento {documento_origen.identificacion.numeroControl}")
        
        # Validar formulario de detalles NC usando el mismo patrón que crear_factura_electronica
        nc_detalle_form = NotaCreditoSimplificadaForm(request.POST)
        
        # Procesar selección de items desde POST
        items_originales = documento_origen.cuerpo_documento.all()
        items_seleccionados = []
        
        for item in items_originales:
            checkbox_name = f'seleccionar_{item.id}'
            cantidad_name = f'cantidad_{item.id}'
            
            if request.POST.get(checkbox_name):
                try:
                    cantidad_str = request.POST.get(cantidad_name, '0').strip()
                    cantidad_nc = Decimal(cantidad_str) if cantidad_str else Decimal('0')
                    
                    if cantidad_nc > 0:
                        items_seleccionados.append({
                            'item_id': item.id,
                            'cantidad': cantidad_nc
                        })
                except (ValueError, TypeError, InvalidOperation):
                    messages.error(request, f"Cantidad inválida para el item {item.descripcion}")
                    return mostrar_seleccion_items(request, documento_origen)
        
        if not items_seleccionados:
            messages.error(request, 'Debe seleccionar al menos un item para la nota de crédito')
            return mostrar_seleccion_items(request, documento_origen)
        
        # Validar formulario NC
        if not nc_detalle_form.is_valid():
            for field, errors in nc_detalle_form.errors.items():
                for error in errors:
                    messages.error(request, f"Error en {field}: {error}")
            return mostrar_seleccion_items(request, documento_origen)
        
        print(f"DEBUG NC: Formularios válidos, creando NC con {len(items_seleccionados)} items")
        
        # Crear la nota de crédito usando el patrón de crear_factura_electronica
        with transaction.atomic():
            # 1. Crear identificación manualmente con datos válidos
            emisor = _emisor_maestro()
            if not emisor:
                raise Exception("No hay emisor configurado en el sistema")
            
            now = timezone.localtime()

            if not request.user.sucursal:
                return JsonResponse({
                    'success': False,
                    'message': 'Su usuario no tiene una sucursal asignada. Contacte al administrador.'
                })

            sucursal = request.user.sucursal
            
            # Generar número de control para NC (tipo 05)
            establecimiento = sucursal.codEstable
            punto_venta = sucursal.codPuntoVenta
            prefijo = f"DTE-05-{establecimiento.zfill(4)}{punto_venta.zfill(4)}-"

            ultimo = (
                Identificacion.objects
                .filter(numeroControl__startswith=prefijo)
                .order_by("-numeroControl")
                .first()
            )
            correlativo = 1 if not ultimo else int(ultimo.numeroControl[-15:]) + 1
            numero_control = f"{prefijo}{correlativo:015d}"
            
            # Crear identificación directamente con todos los campos requeridos
            identificacion = Identificacion.objects.create(
                version=3,  # NC usa versión 3
                ambiente=AmbienteDestino.objects.get(codigo="00" if settings.DTE_AMBIENTE == 'test' else "01"),  # Ambiente de prueba
                tipoDte=TipoDocumento.objects.get(codigo="05"),  # Nota de Crédito
                numeroControl=_siguiente_numero_control('05', sucursal), 
                codigoGeneracion=str(uuid.uuid4()).upper(),
                tipoModelo=ModeloFacturacion.objects.get(codigo="1"),
                tipoOperacion=TipoTransmision.objects.get(codigo="1"),
                tipoContingencia=None,
                motivoContin=None,
                fecEmi=now.date(),  # CRÍTICO: Establecer fecha actual
                horEmi=now.time(),  # CRÍTICO: Establecer hora actual
                tipoMoneda="USD"
            )
            
            print(f"DEBUG NC: Identificación creada: {identificacion.numeroControl}")
            
            # 2. Crear factura base para NC
            factura = FacturaElectronica()
            factura.identificacion = identificacion
            factura.receptor = documento_origen.receptor
            factura.emisor = emisor
            if not request.user.sucursal:
                return JsonResponse({
                    'success': False,
                    'message': 'Su usuario no tiene una sucursal asignada. Contacte al administrador.'
                })

            factura.sucursal = request.user.sucursal
            factura.save()
            print(f"DEBUG NC: Factura NC creada: {factura.pk}")
            
            # 3. Crear documento relacionado (obligatorio para NC)
            documento_relacionado = DocumentoRelacionado()
            documento_relacionado.factura = factura
            documento_relacionado.tipoDocumento = documento_origen.identificacion.tipoDte
            documento_relacionado.tipoGeneracion = GeneracionDocumento.objects.get(codigo="2")  # Electrónico
            documento_relacionado.numeroDocumento = documento_origen.identificacion.codigoGeneracion
            documento_relacionado.fechaEmision = documento_origen.identificacion.fecEmi
            documento_relacionado.save()
            print(f"DEBUG NC: Documento relacionado creado")
            
            # 4. Crear detalle específico de NC
            nc_detalle = nc_detalle_form.save(commit=False)
            nc_detalle.factura = factura
            nc_detalle.documento_origen_uuid = documento_origen.identificacion.codigoGeneracion
            nc_detalle.save()
            print(f"DEBUG NC: Detalle NC creado: {nc_detalle.motivo_nota_credito}")
            
            # 5. Crear items con cálculos precisos usando precios exactos de productos de BD
            total_gravada_sin_iva_acumulada = Decimal('0.00000000')  # Precisión máxima durante cálculos
            total_iva_acumulado = Decimal('0.00000000')  # Precisión máxima durante cálculos
            numero_item = 1

            from .forms import obtener_datos_precisos_item_nc
            
            for item_data in items_seleccionados:
                item_original = CuerpoDocumentoItem.objects.get(id=item_data['item_id'])
                cantidad_nc = item_data['cantidad']
                
                print(f"DEBUG NC: Procesando item - {item_original.descripcion}")
                
                # CORRECCIÓN MÍNIMA: Usar índice de precio almacenado
                try:
                    datos_precisos = obtener_datos_precisos_item_nc(item_original)
                    
                    if datos_precisos and not datos_precisos.get('es_fallback', False):
                        # Usar datos precisos del producto en BD
                        precio_sin_iva_exacto = datos_precisos['precio_sin_iva']
                        iva_unitario_exacto = datos_precisos['iva_unitario']
                        print(f"DEBUG NC: Usando precios precisos - Sin IVA: ${precio_sin_iva_exacto}, IVA: ${iva_unitario_exacto}")
                    else:
                        # Fallback: usar precios originales del CCF
                        precio_sin_iva_exacto = item_original.precioUni
                        iva_unitario_exacto = precio_sin_iva_exacto * Decimal('0.13')
                        print(f"DEBUG NC: Usando precios fallback - Sin IVA: ${precio_sin_iva_exacto}, IVA: ${iva_unitario_exacto}")
                    
                    # Calcular totales para la cantidad de NC manteniendo precisión
                    venta_gravada_nc_precisa = precio_sin_iva_exacto * cantidad_nc
                    iva_total_nc_preciso = iva_unitario_exacto * cantidad_nc
                    
                    # Acumular en variables de precisión máxima
                    total_gravada_sin_iva_acumulada += venta_gravada_nc_precisa
                    total_iva_acumulado += iva_total_nc_preciso
                    
                    # Crear item de NC con valores redondeados SOLO para almacenamiento
                    nuevo_item = CuerpoDocumentoItem()
                    nuevo_item.factura = factura
                    nuevo_item.numItem = numero_item
                    nuevo_item.tipoItem = item_original.tipoItem
                    nuevo_item.numeroDocumento = documento_origen.identificacion.codigoGeneracion
                    nuevo_item.cantidad = cantidad_nc
                    nuevo_item.codigo = item_original.codigo
                    nuevo_item.codTributo = None
                    nuevo_item.uniMedida = item_original.uniMedida
                    nuevo_item.descripcion = item_original.descripcion
                    
                    # REDONDEAR SOLO para almacenamiento
                    nuevo_item.precioUni = precio_sin_iva_exacto.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    nuevo_item.montoDescu = Decimal('0.00')  # Sin descuentos para evitar más discrepancias
                    nuevo_item.ventaNoSuj = Decimal('0.00')
                    nuevo_item.ventaExenta = Decimal('0.00')
                    nuevo_item.ventaGravada = venta_gravada_nc_precisa.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    nuevo_item.psv = Decimal('0.00')
                    nuevo_item.noGravado = Decimal('0.00')
                    nuevo_item.ivaItem = Decimal('0.00')  # Para NC, ivaItem debe ser 0 según esquema
                    
                    # Guardar item
                    nuevo_item.save()

                    from .models import ItemNotaCredito
        
                    ItemNotaCredito.objects.create(
                        item_original=item_original,
                        item_nota_credito=nuevo_item,
                        nota_credito=factura,
                        cantidad_acreditada=cantidad_nc
                    )
                    
                    print(f"DEBUG NC: Registrado control NC para item {item_original.descripcion}: {cantidad_nc} unidades")
                    
                    # Asignar tributo IVA si hay venta gravada
                    if nuevo_item.ventaGravada > Decimal('0'):
                        tributo_iva = Tributo.objects.get(codigo="20")  # IVA
                        nuevo_item.tributos.add(tributo_iva)
                        print(f"DEBUG NC: Asignado tributo IVA al item")
                    
                    numero_item += 1
                    
                except Exception as e:
                    print(f"ERROR procesando item {item_original.codigo}: {str(e)}")
                    raise Exception(f"Error procesando item {item_original.descripcion}: {str(e)}")
            
            
            # 7. Crear resumen de NC usando valores acumulados con precisión máxima
            print(f"DEBUG NC: Creando resumen con totales acumulados")
            
            # REDONDEAR SOLO AL FINAL para el resumen
            total_gravada_final = total_gravada_sin_iva_acumulada.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            total_iva_final = total_iva_acumulado.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            total_pagar_final = (total_gravada_sin_iva_acumulada + total_iva_acumulado).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            resumen = Resumen()
            resumen.factura = factura
            resumen.totalNoSuj = Decimal('0.00')
            resumen.totalExenta = Decimal('0.00')
            resumen.totalGravada = total_gravada_final
            resumen.subTotalVentas = total_gravada_final
            resumen.descuNoSuj = Decimal('0.00')
            resumen.descuExenta = Decimal('0.00')
            resumen.descuGravada = Decimal('0.00')
            resumen.porcentajeDescuento = Decimal('0.00')
            resumen.totalDescu = Decimal('0.00')
            resumen.subTotal = total_gravada_final
            resumen.ivaRete1 = Decimal('0.00')
            resumen.reteRenta = Decimal('0.00')
            resumen.montoTotalOperacion = total_pagar_final
            resumen.totalNoGravado = Decimal('0.00')
            resumen.totalPagar = total_pagar_final
            resumen.saldoFavor = Decimal('0.00')
            resumen.condicionOperacion = CondicionOperacion.objects.get(codigo="1")  # Contado
            resumen.numPagoElectronico = ""
            resumen.totalLetras = numero_a_letras(total_pagar_final)
            resumen.ivaPerci1 = Decimal('0.00')  # Campo obligatorio para NC según esquema
            resumen.save()
            
            # 8. Crear tributo de IVA en el resumen
            if total_iva_final > Decimal('0.00'):
                tributo_iva_resumen = TributoResumen()
                tributo_iva_resumen.resumen = resumen
                tributo_iva_resumen.codigo = Tributo.objects.get(codigo="20")
                tributo_iva_resumen.descripcion = "Impuesto al Valor Agregado 13%"
                tributo_iva_resumen.valor = total_iva_final
                tributo_iva_resumen.save()
                print(f"DEBUG NC: Tributo IVA creado en resumen: ${total_iva_final}")
            
            print(f"DEBUG NC: Resumen creado exitosamente")
            
            # ═══════════════════════════════════════════════════════════════════════════
            # PROCESO COMPLETO DE HACIENDA - IGUAL QUE crear_factura_electronica
            # ═══════════════════════════════════════════════════════════════════════════
            
            # 9. Generar y validar JSON
            print("DEBUG NC: Generando JSON...")
            dte_json = build_dte_json(factura)
            print(f"DEBUG NC: JSON generado correctamente")
            
            # Validar contra esquema específico de NC
            esquema = get_schema_for_tipo_dte('05')  # Esquema específico para NC
            print("DEBUG NC: Validando JSON contra esquema NC...")
            jsonschema_validate(instance=dte_json, schema=esquema)
            print("DEBUG NC: JSON válido según esquema NC")

            # 10. Configurar servicio DTE
            print("DEBUG NC: Configurando servicio DTE...")
            servicio = DTEService(
                emisor=factura.emisor,
                ambiente=settings.DTE_AMBIENTE,
                firmador_url=settings.FIRMADOR_URL,
                dte_urls=settings.DTE_URLS[settings.DTE_AMBIENTE],
                dte_user=settings.DTE_USER,
                dte_password=settings.DTE_PASSWORD,
            )
            
            # 11. Firmar documento
            print("DEBUG NC: Firmando documento...")
            factura.documento_firmado = servicio.firmar_documento(dte_json)
            factura.save(update_fields=['documento_firmado'])
            print("DEBUG NC: Documento firmado exitosamente")

            # 12. Autenticar con Hacienda
            print("DEBUG NC: Autenticando con Hacienda...")
            token = servicio.autenticar()
            print("DEBUG NC: Token obtenido exitosamente")
            
            # 13. Enviar a Hacienda
            print("DEBUG NC: Enviando NC a Hacienda...")
            respuesta = servicio.enviar_a_hacienda(
                token=token,
                codigo_generacion=factura.identificacion.codigoGeneracion,
                tipo_dte='05',  # Tipo específico para NC
                dte_json=dte_json
            )
            print(f"DEBUG NC: Respuesta de Hacienda: {respuesta}")
            
            # 14. Procesar respuesta de Hacienda
            if respuesta.get('estado') == "PROCESADO":
                estado_hacienda = "ACEPTADO"
                print("DEBUG NC: NC aceptada por Hacienda")
            else:
                estado_hacienda = "RECHAZADO"
                print(f"DEBUG NC: NC rechazada por Hacienda: {respuesta.get('descripcion', 'Error desconocido')}")
            
            # Actualizar estado de la factura
            factura.estado_hacienda = estado_hacienda
            factura.sello_recepcion = respuesta.get('sello', '')
            factura.fecha_procesamiento = respuesta.get('fecha_procesamiento', '')
            factura.observaciones_hacienda = json.dumps(respuesta.get('observaciones', []))
            factura.save(update_fields=[
                'estado_hacienda',
                'sello_recepcion',
                'fecha_procesamiento',
                'observaciones_hacienda'
            ])
            
            print(f"DEBUG NC: Estado actualizado en BD: {estado_hacienda}")
            
            # 15. Enviar correo SOLO si fue aceptada por Hacienda
            if respuesta.get('estado') in ('PROCESADO', 'ACEPTADO'):
                print("DEBUG NC: Generando archivos para correo...")
                
                # Generar PDF usando la función existente
                pdf_bytes = generar_pdf_factura_mejorado(factura)
                
                # Generar JSON con firma y sello usando la función existente
                json_str = json.dumps(
                    build_dte_json(factura, incluir_firma_y_sello=True),
                    indent=2,
                    ensure_ascii=False,
                    default=str
                )
                
                # Preparar archivos adjuntos
                archivos = [
                    {
                        'filename': f"{factura.identificacion.numeroControl}.pdf",
                        'content': pdf_bytes,
                        'mimetype': 'application/pdf'
                    },
                    {
                        'filename': f"{factura.identificacion.numeroControl}_firmado.json",
                        'content': json_str.encode('utf-8'),
                        'mimetype': 'application/json'
                    }
                ]
                
                # Enviar correo usando el servicio existente
                try:
                    servicio.enviar_correo_factura(factura, archivos)
                    print("DEBUG NC: Correo enviado exitosamente")
                    messages.success(request, 'Nota de Crédito enviada por correo al receptor.')
                except Exception as e:
                    print(f"WARNING NC: Error enviando correo: {str(e)}")
                    # No fallar por error de correo
                    messages.warning(request, 'NC procesada pero no se pudo enviar el correo.')
            
            print("DEBUG NC: Proceso completado exitosamente")
            
            # Mensaje de éxito personalizado para NC
            if estado_hacienda == "ACEPTADO":
                messages.success(
                    request,
                    f"Nota de Crédito {factura.identificacion.numeroControl} procesada y aceptada por Hacienda."
                )
            else:
                messages.error(
                    request,
                    f"Nota de Crédito {factura.identificacion.numeroControl} fue rechazada por Hacienda: "
                    f"{respuesta.get('descripcion', 'Error desconocido')}"
                )
            
            return redirect('dte:factura_detail', pk=factura.pk)
        
    except JSONSchemaValidationError as e:
        print(f"ERROR NC: Validación de esquema falló: {str(e)}")
        messages.error(request, f'Error de validación de esquema: {str(e)}')
        if 'documento_origen' in locals():
            return mostrar_seleccion_items(request, documento_origen)
        else:
            return redirect('dte:crear_nota_credito')
            
    except Exception as e:
        print(f"ERROR NC: Excepción general: {str(e)}")
        import traceback
        traceback.print_exc()
        messages.error(request, f'Error al crear la Nota de Crédito: {str(e)}')
        if 'documento_origen' in locals():
            return mostrar_seleccion_items(request, documento_origen)
        else:
            return redirect('dte:crear_nota_credito')


def crear_nota_credito_desde_documento(request, documento_id):
    """
    Vista para crear Nota de Crédito directamente desde un documento específico
    Acceso directo desde el detalle de un CCF
    """
    try:
        documento_origen = FacturaElectronica.objects.get(
            id=documento_id,
            identificacion__tipoDte__codigo='03',  # Solo CCF
            estado_hacienda__in=['ACEPTADO', 'ACEPTADO CON OBSERVACIONES']
        )
        
        estado_actual = (documento_origen.estado_hacienda or '').strip()
        
        if estado_actual not in ['ACEPTADO', 'ACEPTADO CON OBSERVACIONES']:
            messages.error(
                request, 
                f'El documento debe estar ACEPTADO o ACEPTADO CON OBSERVACIONES para crear una nota de crédito. '
                f'Estado actual: {estado_actual}'
            )
            return redirect('dte:factura_detail', pk=documento_id)
        
        # AGREGAR ESTA LÓGICA PARA MANEJAR POST IGUAL QUE crear_nota_credito:
        if request.method == "POST":
            if 'seleccionar_items' in request.POST:
                # Paso 3: Items seleccionados, crear la nota de crédito
                return procesar_creacion_nc_simplificada(request)
            else:
                messages.error(request, 'Solicitud inválida')
                return redirect('dte:factura_detail', pk=documento_id)
        
        # Usar la función simplificada para mostrar items
        return mostrar_seleccion_items(request, documento_origen)
        
    except FacturaElectronica.DoesNotExist:
        messages.error(request, 'Documento no encontrado')
        return redirect('dte:factura_list')
    except Exception as e:
        print(f"ERROR crear_nota_credito_desde_documento: {str(e)}")
        import traceback
        traceback.print_exc()
        messages.error(request, f'Error al acceder al documento: {str(e)}')
        return redirect('dte:factura_list')


# ═══════════════════════════════════════════════════════════════════════════════
# FUNCIONES AUXILIARES Y DE SOPORTE
# ═══════════════════════════════════════════════════════════════════════════════

# NOTA: TributoResumen ya existe en models.py - no necesita redefinirse
@require_http_methods(["GET"])
def buscar_documentos_para_nc_ajax(request):
    """
    Vista AJAX MEJORADA para buscar CCF que pueden tener NC
    Solo muestra documentos con items disponibles
    """
    query = request.GET.get('q', '')
    
    if len(query) < 3:
        return JsonResponse({'results': []})
    
    from django.db.models import Q
    
    # Buscar CCF base que puedan ser referenciados
    documentos_base = FacturaElectronica.objects.filter(
        Q(identificacion__numeroControl__icontains=query) |
        Q(receptor__nombre__icontains=query) |
        Q(receptor__numDocumento__icontains=query),
        identificacion__tipoDte__codigo='03',  # Solo CCF
        estado_hacienda__in=['ACEPTADO', 'ACEPTADO CON OBSERVACIONES']
    ).select_related('identificacion', 'receptor', 'resumen').order_by('-identificacion__fecEmi')[:20]
    
    results = []
    for doc in documentos_base:
        # FILTRO CRÍTICO: Solo incluir si tiene items disponibles
        if doc.tiene_items_disponibles_para_nc():
            items_disponibles = len(doc.get_items_disponibles_para_nc())
            porcentaje_acreditado = doc.get_porcentaje_acreditado()
            
            # Información de disponibilidad
            info_disponibilidad = ""
            if porcentaje_acreditado > 0:
                info_disponibilidad = f" ({100-porcentaje_acreditado:.0f}% disponible)"
            
            results.append({
                'id': doc.id,
                'text': f"{doc.identificacion.numeroControl} - {doc.receptor.nombre} - ${doc.resumen.totalPagar:.2f}{info_disponibilidad}",
                'numeroControl': doc.identificacion.numeroControl,
                'receptor': doc.receptor.nombre,
                'total': str(doc.resumen.totalPagar),
                'fecha': doc.identificacion.fecEmi.strftime('%d/%m/%Y'),
                'items_disponibles': items_disponibles,
                'porcentaje_acreditado': float(porcentaje_acreditado)
            })
    
    return JsonResponse({'results': results})

@require_http_methods(["GET"])
def obtener_items_documento_ajax(request):
    """
    Vista AJAX ACTUALIZADA para obtener items disponibles de un documento
    Solo devuelve items que pueden ser acreditados
    """
    documento_id = request.GET.get('documento_id')
    
    if not documento_id:
        return JsonResponse({'items': []})
    
    try:
        documento = FacturaElectronica.objects.get(
            id=documento_id,
            identificacion__tipoDte__codigo='03'
        )
        
        # CAMBIO: Solo items disponibles
        items_disponibles = documento.get_items_disponibles_para_nc()
        
        items = []
        for item in items_disponibles:
            cantidad_disponible = item.get_cantidad_disponible_para_nc()
            cantidad_acreditada = item.get_cantidad_acreditada()
            
            items.append({
                'id': item.id,
                'numItem': item.numItem,
                'descripcion': item.descripcion,
                'cantidad_original': str(item.cantidad),
                'cantidad_disponible': str(cantidad_disponible),
                'cantidad_acreditada': str(cantidad_acreditada),
                'precioUni': str(item.precioUni),
                'ventaGravada': str(item.ventaGravada),
                'puede_acreditar': cantidad_disponible > 0
            })
        
        return JsonResponse({
            'items': items,
            'documento': {
                'numeroControl': documento.identificacion.numeroControl,
                'receptor': documento.receptor.nombre,
                'total': str(documento.resumen.totalPagar),
                'items_disponibles': len(items_disponibles),
                'porcentaje_acreditado': float(documento.get_porcentaje_acreditado())
            }
        })
        
    except FacturaElectronica.DoesNotExist:
        return JsonResponse({'error': 'Documento no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ═══════════════════════════════════════════════════════════════════════════════
# FUNCIONES EXISTENTES (CONSERVADAS PARA COMPATIBILIDAD)
# ═══════════════════════════════════════════════════════════════════════════════

def crear_nc_desde_documento(request, documento_id):
    """
    Vista original para crear NC - CONSERVADA para compatibilidad
    """
    try:
        documento_origen = FacturaElectronica.objects.get(
            id=documento_id,
            identificacion__tipoDte__codigo__in=['03', '05']  # CCF o NC
        )
        
        if documento_origen.identificacion.tipoDte.codigo == '05':
            messages.info(request, 'Este documento ya es una Nota de Crédito')
            return redirect('dte:factura_detail', pk=documento_id)
        
        estado_actual = (documento_origen.estado_hacienda or '').strip().upper()
        estados_permitidos = ['PROCESADO', 'AUTORIZADO', 'ACEPTADO']
        
        if estado_actual not in estados_permitidos:
            messages.error(
                request, 
                f'El documento debe estar PROCESADO o AUTORIZADO para crear una nota de crédito. '
                f'Estado actual: {estado_actual}'
            )
            return redirect('dte:factura_detail', pk=documento_id)
        
        # Usar la función simplificada
        return mostrar_seleccion_items(request, documento_origen)
        
    except FacturaElectronica.DoesNotExist:
        messages.error(request, 'Documento no encontrado')
        return redirect('dte:factura_list')


def procesar_creacion_nc(request):
    """
    Función original - REDIRIGE a la nueva función simplificada
    """
    return procesar_creacion_nc_simplificada(request)
  

# En views.py, actualizar la función factura_datatable_view para ordenar por fecha y hora:

# En views.py, actualizar la función factura_datatable_view para ordenar por fecha y hora:

# En views.py, reemplazar la función factura_datatable_view con esta versión corregida:

# En views.py, reemplazar la función factura_datatable_view con esta versión corregida:

# En views.py, reemplazar la función factura_datatable_view con esta versión que incluye Estado Correo:
# En views.py, reemplazar la función factura_datatable_view con esta versión que incluye Estado Correo:

@require_http_methods(["GET"])
def factura_datatable_view(request):
    """Vista AJAX para DataTables - CON ESTADO CORREO"""
    try:
        # Parámetros de DataTables
        draw = int(request.GET.get('draw', 1))
        start = int(request.GET.get('start', 0))
        length = int(request.GET.get('length', 25))
        search_value = request.GET.get('search[value]', '')
        order_column = int(request.GET.get('order[0][column]', 2))  # Por defecto ordenar por fecha
        order_dir = request.GET.get('order[0][dir]', 'desc')

        # Columnas para ordenamiento - ACTUALIZADO con Estado Correo
        columns = ['identificacion__tipoDte__codigo', 'identificacion__numeroControl', 'identificacion__fecEmi', 'receptor__nombre', 'estado_hacienda', 'resumen__totalPagar', 'sello_recepcion', 'enviado_por_correo', 'acciones']

        # Filtros adicionales - AGREGADO filtro_correo
        filtro_tipo = request.GET.get('filtro_tipo', '')
        filtro_estado = request.GET.get('filtro_estado', '')
        filtro_sello = request.GET.get('filtro_sello', '')
        filtro_correo = request.GET.get('filtro_correo', '')
        filtro_sucursal = request.GET.get('filtro_sucursal', '') 
        fecha_desde = request.GET.get('fecha_desde', '')
        fecha_hasta = request.GET.get('fecha_hasta', '')

        # Query base con select_related para optimizar
        queryset = FacturaElectronica.objects.select_related(
            'identificacion', 'identificacion__tipoDte', 'receptor', 'resumen'
        )

        # Aplicar filtros
        if search_value:
            queryset = queryset.filter(
                Q(identificacion__numeroControl__icontains=search_value) |
                Q(receptor__nombre__icontains=search_value)
            )

        if filtro_sucursal:
            queryset = queryset.filter(sucursal_id=filtro_sucursal)

        if filtro_tipo:
            queryset = queryset.filter(identificacion__tipoDte__codigo=filtro_tipo)

        if filtro_estado:
            queryset = queryset.filter(estado_hacienda=filtro_estado)

        if filtro_sello:
            if filtro_sello == 'con_sello':
                queryset = queryset.filter(sello_recepcion__isnull=False).exclude(sello_recepcion='')
            elif filtro_sello == 'sin_sello':
                queryset = queryset.filter(Q(sello_recepcion__isnull=True) | Q(sello_recepcion=''))

        # NUEVO: Filtro de estado correo
        if filtro_correo:
            if filtro_correo == 'enviado':
                queryset = queryset.filter(enviado_por_correo=True)
            elif filtro_correo == 'no_enviado':
                queryset = queryset.filter(enviado_por_correo=False)

        if fecha_desde:
            try:
                fecha_desde_obj = datetime.strptime(fecha_desde, '%Y-%m-%d').date()
                queryset = queryset.filter(identificacion__fecEmi__gte=fecha_desde_obj)
            except ValueError:
                pass

        if fecha_hasta:
            try:
                fecha_hasta_obj = datetime.strptime(fecha_hasta, '%Y-%m-%d').date()
                queryset = queryset.filter(identificacion__fecEmi__lte=fecha_hasta_obj)
            except ValueError:
                pass

        # Count total records
        total_records = FacturaElectronica.objects.count()
        filtered_records = queryset.count()

        # *** CAMBIO PRINCIPAL: Aplicar ordenamiento - CORREGIDO ***
        if 0 <= order_column < len(columns):
            order_field = columns[order_column]
            if order_dir == 'desc':
                order_field = f'-{order_field}'
            # Para ordenamiento por fecha, incluir también hora
            if order_column == 2:  # Columna de fecha
                if order_dir == 'desc':
                    queryset = queryset.order_by('-identificacion__fecEmi', '-identificacion__horEmi')
                else:
                    queryset = queryset.order_by('identificacion__fecEmi', 'identificacion__horEmi')
            else:
                queryset = queryset.order_by(order_field)
        else:
            # *** ORDEN POR DEFECTO: por fecha y hora de emisión descendente (más recientes primero) ***
            queryset = queryset.order_by('-identificacion__fecEmi', '-identificacion__horEmi')

        # Apply pagination
        facturas = queryset[start:start + length]

        # Preparar data - ACTUALIZADO con Estado Correo
        data = []
        for factura in facturas:
            try:
                # 1. TIPO DE DTE
                tipo_badge = '<span class="badge bg-secondary">N/A</span>'
                tipo_codigo = None
                
                if hasattr(factura, 'identificacion') and factura.identificacion and hasattr(factura.identificacion, 'tipoDte') and factura.identificacion.tipoDte:
                    tipo_codigo = factura.identificacion.tipoDte.codigo
                    if tipo_codigo == '01':
                        tipo_badge = '<span class="badge bg-primary">FC</span>'
                    elif tipo_codigo == '03':
                        tipo_badge = '<span class="badge bg-success">CCF</span>'
                    elif tipo_codigo == '05':
                        tipo_badge = '<span class="badge bg-warning text-dark">NC</span>'
                    elif tipo_codigo == '14':
                        tipo_badge = '<span class="badge bg-info">FSE</span>'
                    else:
                        tipo_badge = f'<span class="badge bg-secondary">{tipo_codigo}</span>'

                # 2. NÚMERO DE CONTROL
                numero_control = 'N/A'
                if hasattr(factura, 'identificacion') and factura.identificacion:
                    numero_control = factura.identificacion.numeroControl or 'N/A'

                # 3. FECHA DE EMISIÓN
                fecha_emision = 'N/A'
                if hasattr(factura, 'identificacion') and factura.identificacion and factura.identificacion.fecEmi:
                    fecha_emision = factura.identificacion.fecEmi.strftime('%d/%m/%Y')

                # 4. RECEPTOR
                receptor_nombre = 'N/A'
                if hasattr(factura, 'receptor') and factura.receptor:
                    receptor_nombre = factura.receptor.nombre or 'Sin nombre'

                # 5. ESTADO HACIENDA
                estado = factura.estado_hacienda or 'N/A'
                if estado == 'ACEPTADO':
                    estado_badge = '<span class="badge bg-success">Aceptado</span>'
                elif estado == 'ACEPTADO CON OBSERVACIONES':
                    estado_badge = '<span class="badge bg-warning text-dark">ACEPTADO OBS</span>'
                elif estado == 'RECHAZADO':
                    estado_badge = '<span class="badge bg-danger">Rechazado</span>'
                elif estado == 'NO_ENVIADO':
                    estado_badge = '<span class="badge bg-secondary">No Enviado</span>'
                else:
                    estado_badge = f'<span class="badge bg-secondary">{estado}</span>'

                # 6. TOTAL
                total = 'N/A'
                if hasattr(factura, 'resumen') and factura.resumen and factura.resumen.totalPagar:
                    total = f"${factura.resumen.totalPagar:,.2f}"

                # 7. SELLO DE RECEPCIÓN
                sello_badge = '<span class="badge bg-danger">Sin Sello</span>'
                if factura.sello_recepcion:
                    sello_badge = '<span class="badge bg-success">Con Sello</span>'

                # *** 8. NUEVO: ESTADO CORREO ***
                if factura.enviado_por_correo:
                    fecha_envio = ''
                    if factura.fecha_envio_correo:
                        fecha_envio = factura.fecha_envio_correo.strftime('%d/%m/%Y %H:%M')
                    correo_badge = f'<span class="badge bg-success" title="Enviado: {fecha_envio}">Enviado</span>'
                else:
                    correo_badge = '<span class="badge bg-warning text-dark">No Enviado</span>'

                # *** 9. ACCIONES - BOTONES HORIZONTALES ***
                acciones = f'<div class="d-flex gap-1">'
                
                # Botón Ver (siempre visible)
                acciones += f'<a href="/dte/facturas/{factura.pk}/" class="btn btn-primary btn-sm" title="Ver detalle"><i class="fas fa-eye"></i></a>'

                acciones += f'<a href="/dte/facturas/{factura.pk}/descargar-ticket/" class="btn btn-secondary btn-sm" title="Descargar Ticket"><i class="fas fa-receipt"></i></a>'
                
                # Botones de descarga para facturas ACEPTADAS o ACEPTADAS CON OBSERVACIONES
                if estado in ['ACEPTADO', 'ACEPTADO CON OBSERVACIONES']:
                    acciones += f'<a href="/dte/facturas/{factura.pk}/descargar-pdf/" class="btn btn-success btn-sm" title="Descargar PDF"><i class="fas fa-file-pdf"></i></a>'
                    acciones += f'<a href="/dte/facturas/{factura.pk}/descargar-json/" class="btn btn-info btn-sm" title="Descargar JSON"><i class="fas fa-file-code"></i></a>'
                
                # Botón crear Nota de Crédito para CCF aceptado
                if tipo_codigo == '03' and estado in ['ACEPTADO', 'ACEPTADO CON OBSERVACIONES']:
                    acciones += f'<a href="/dte/crear-nc-desde-documento/{factura.pk}/" class="btn btn-warning btn-sm" title="Crear Nota de Crédito"><i class="fas fa-minus-circle"></i></a>'
                
                acciones += '</div>'

                # ACTUALIZADO: Agregar Estado Correo en posición 7 (antes de Acciones)
                data.append([
                    tipo_badge,          # 0: Tipo
                    numero_control,      # 1: Número Control
                    fecha_emision,       # 2: Fecha
                    receptor_nombre,     # 3: Receptor
                    estado_badge,        # 4: Estado
                    total,               # 5: Total
                    sello_badge,         # 6: Sello
                    correo_badge,        # 7: Estado Correo
                    acciones             # 8: Acciones
                ])

            except Exception as e:
                print(f"Error procesando factura {factura.pk}: {e}")
                # Agregar registro de error pero continuar
                data.append([
                    '<span class="badge bg-danger">Error</span>',
                    'Error',
                    'Error',
                    'Error',
                    '<span class="badge bg-danger">Error</span>',
                    'Error',
                    '<span class="badge bg-danger">Error</span>',
                    '<span class="badge bg-danger">Error</span>',
                    '<span class="text-danger">Error</span>'
                ])

        response_data = {
            'draw': draw,
            'recordsTotal': total_records,
            'recordsFiltered': filtered_records,
            'data': data
        }

        return JsonResponse(response_data)

    except Exception as e:
        print(f"Error en factura_datatable_view: {e}")
        import traceback
        traceback.print_exc()
        
        return JsonResponse({
            'draw': int(request.GET.get('draw', 1)),
            'recordsTotal': 0,
            'recordsFiltered': 0,
            'data': [],
            'error': str(e)
        })
    

#Aqui comienzan los cambios para anulacion 
# dte/views.py - AGREGAR estas vistas al archivo views.py existente

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView, DetailView
from django.urls import reverse
from django.conf import settings
from .models import AnulacionDocumento, FacturaElectronica
from .forms import AnulacionDocumentoForm, BuscarDocumentoAnularForm
from .services import DTEService
import logging
from django.db.models import Q  # ← AGREGAR ESTA LÍNEA
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.db import models
# ... resto de importaciones existentes ...

logger = logging.getLogger(__name__)

# =====================================================
# VISTAS PARA ANULACIÓN DE DOCUMENTOS
# =====================================================

@login_required
def anulacion_list_view(request):
    """
    Vista para listar las anulaciones existentes
    """
    anulaciones = AnulacionDocumento.objects.select_related(
        'documento_anular__identificacion',
        'documento_anular__identificacion__tipoDte',
        'documento_anular__receptor',
        'emisor',
        'ambiente'
    ).order_by('-creado_en')
    
    context = {
        'anulaciones': anulaciones,
        'title': 'Anulaciones de Documentos'
    }
    
    return render(request, 'dte/anulacion/anulacion_list.html', context)

@login_required
def anulacion_crear_view(request):
    """
    Vista para crear una nueva anulación - Paso 1: Buscar documento
    """
    buscar_form = BuscarDocumentoAnularForm()
    documentos_encontrados = []
    
    if request.method == 'POST':
        buscar_form = BuscarDocumentoAnularForm(request.POST)
        if buscar_form.is_valid():
            documentos_encontrados = buscar_form.buscar_documentos()
            
            if not documentos_encontrados:
                messages.warning(request, 'No se encontraron documentos que cumplan los criterios de búsqueda.')
    
    context = {
        'buscar_form': buscar_form,
        'documentos_encontrados': documentos_encontrados,
        'title': 'Crear Anulación de Documento'
    }
    
    return render(request, 'dte/anulacion/anulacion_crear.html', context)

# dte/views.py - REEMPLAZAR la función anulacion_documento_view con esta versión con debug

# dte/views.py - REEMPLAZAR la función anulacion_documento_view con esta versión que envía a Hacienda

# dte/views.py - REEMPLAZAR la función anulacion_documento_view con esta versión con debug

# dte/views.py - REEMPLAZAR la función anulacion_documento_view con esta versión con debug

@login_required
def anulacion_documento_view(request, documento_id):
    """
    Vista para anular un documento específico - Paso 2: Formulario de anulación
    """
    print(f"DEBUG: Iniciando anulación para documento ID: {documento_id}")
    
    # Obtener el documento a anular
    documento = get_object_or_404(
        FacturaElectronica.objects.select_related(
            'identificacion__tipoDte',
            'receptor',
            'emisor',
            'resumen'
        ),
        pk=documento_id
    )
    
    print(f"DEBUG: Documento encontrado: {documento.identificacion.numeroControl}")
    
    # Verificar que el documento se puede anular
    estados_anulables = ['ACEPTADO', 'ACEPTADO CON OBSERVACIONES']
    if documento.estado_hacienda not in estados_anulables:
        messages.error(
            request, 
            f'No se puede anular este documento. Estado actual: {documento.estado_hacienda}. '
            f'Solo se pueden anular documentos con estado ACEPTADO o ACEPTADO CON OBSERVACIONES.'
        )
        return redirect('dte:anulacion_crear')
    
    # Verificar que no esté ya anulado
    if hasattr(documento, 'anulaciones') and documento.anulaciones.filter(estado='ACEPTADO').exists():
        messages.error(request, 'Este documento ya ha sido anulado.')
        return redirect('dte:anulacion_crear')
    
    if request.method == 'POST':
        print("DEBUG: Procesando formulario POST")
        
        form = AnulacionDocumentoForm(
            request.POST, 
            documento_anular=documento
        )
        
        if form.is_valid():
            print("DEBUG: Formulario válido, iniciando procesamiento")
            
            try:
                with transaction.atomic():
                    print("DEBUG: Creando objeto de anulación")
                    
                    # Crear la anulación
                    anulacion = form.save(commit=False)
                    anulacion.creado_por = request.user.username if hasattr(request.user, 'username') else 'Sistema'
                    anulacion.save()
                    
                    print(f"DEBUG: Anulación creada con ID: {anulacion.pk}")
                    print(f"DEBUG: Código de generación: {anulacion.codigo_generacion}")
                    
                    # PROCESAMIENTO REAL CON ENVÍO A HACIENDA
                    print("DEBUG: Configurando servicio DTE")
                    
                    # Verificar configuraciones necesarias
                    if not hasattr(settings, 'DTE_AMBIENTE'):
                        raise Exception("DTE_AMBIENTE no configurado en settings.py")
                    
                    if not hasattr(settings, 'FIRMADOR_URL'):
                        raise Exception("FIRMADOR_URL no configurado en settings.py")
                    
                    if not hasattr(settings, 'DTE_URLS'):
                        raise Exception("DTE_URLS no configurado en settings.py")
                    
                    # Configurar servicio DTE
                    servicio = DTEService(
                        emisor=documento.emisor,
                        ambiente=settings.DTE_AMBIENTE,
                        firmador_url=settings.FIRMADOR_URL,
                        dte_urls=settings.DTE_URLS.get(settings.DTE_AMBIENTE, {}),
                        dte_user=getattr(settings, 'DTE_USER', ''),
                        dte_password=getattr(settings, 'DTE_PASSWORD', ''),
                    )
                    
                    print("DEBUG: Procesando anulación con Hacienda")
                    
                    # Procesar anulación
                    resultado = servicio.anular_documento(anulacion)
                    
                    print(f"DEBUG: Resultado de Hacienda: {resultado}")
                    
                    # CORREGIDO: Verificar estados exitosos de Hacienda
                    if resultado['estado'] in ['RECIBIDO', 'ACEPTADO', 'PROCESADO']:
                        messages.success(
                            request, 
                            f'¡Anulación procesada exitosamente! '
                            f'Estado: {resultado["estado"]} - '
                            f'Sello de recepción: {resultado["sello"]}'
                        )
                        return redirect('dte:anulacion_detail', pk=anulacion.pk)
                    else:
                        messages.error(
                            request,
                            f'Error al procesar anulación: {resultado["descripcion"]}'
                        )
                        
                        # Mostrar observaciones si existen
                        if resultado.get('observaciones'):
                            for obs in resultado['observaciones']:
                                messages.warning(request, f'Observación: {obs}')
                        
                        # Aún redirigir al detalle para ver el error
                        return redirect('dte:anulacion_detail', pk=anulacion.pk)
                        
            except Exception as e:
                print(f"DEBUG: Error en procesamiento: {str(e)}")
                import traceback
                traceback.print_exc()
                
                messages.error(request, f'Error interno al procesar anulación: {str(e)}')
        else:
            print(f"DEBUG: Formulario inválido: {form.errors}")
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        print("DEBUG: Mostrando formulario GET")
        form = AnulacionDocumentoForm(documento_anular=documento)
    
    context = {
        'form': form,
        'documento': documento,
        'title': f'Anular Documento {documento.identificacion.numeroControl}'
    }
    
    return render(request, 'dte/anulacion/anulacion_form.html', context)

@login_required  
def anulacion_detail_view(request, pk):
    """
    Vista para ver el detalle de una anulación
    """
    anulacion = get_object_or_404(
        AnulacionDocumento.objects.select_related(
            'documento_anular__identificacion__tipoDte',
            'documento_anular__receptor',
            'emisor',
            'ambiente'
        ),
        pk=pk
    )
    
    context = {
        'anulacion': anulacion,
        'title': f'Anulación {anulacion.codigo_generacion}'
    }
    
    return render(request, 'dte/anulacion/anulacion_detail.html', context)

@login_required
def anular_desde_factura_view(request, factura_id):
    """
    Vista para anular directamente desde la lista de facturas
    """
    # Redirigir a la vista de anulación con el documento específico
    return redirect('dte:anulacion_documento', documento_id=factura_id)

@require_http_methods(["POST"])
@login_required
def anulacion_reenviar_view(request, pk):
    """
    Vista AJAX para reenviar una anulación rechazada a Hacienda
    """
    try:
        anulacion = get_object_or_404(AnulacionDocumento, pk=pk)
        
        # Solo se puede reenviar si está en estado RECHAZADO o ERROR
        if anulacion.estado not in ['RECHAZADO', 'ERROR']:
            return JsonResponse({
                'success': False,
                'message': f'No se puede reenviar. Estado actual: {anulacion.estado}'
            })
        
        # Configurar servicio
        servicio = DTEService(
            emisor=anulacion.emisor,
            ambiente=settings.DTE_AMBIENTE,
            firmador_url=settings.FIRMADOR_URL,
            dte_urls=settings.DTE_URLS[settings.DTE_AMBIENTE],
            dte_user=settings.DTE_USER,
            dte_password=settings.DTE_PASSWORD,
        )
        
        # Reenviar
        resultado = servicio.anular_documento(anulacion)
        
        if resultado['estado'] in ['RECIBIDO', 'ACEPTADO']:
            return JsonResponse({
                'success': True,
                'message': f'Anulación reenviada exitosamente. Sello: {resultado["sello"]}',
                'nuevo_estado': resultado['estado'],
                'sello': resultado['sello']
            })
        else:
            return JsonResponse({
                'success': False,
                'message': f'Error al reenviar: {resultado["descripcion"]}',
                'observaciones': resultado.get('observaciones', [])
            })
            
    except Exception as e:
        logger.error(f"Error al reenviar anulación: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Error interno: {str(e)}'
        })

@require_http_methods(["GET"])
@login_required
def anulacion_consultar_estado_view(request, pk):
    """
    Vista AJAX para consultar el estado de una anulación en Hacienda
    """
    try:
        anulacion = get_object_or_404(AnulacionDocumento, pk=pk)
        
        # Configurar servicio
        servicio = DTEService(
            emisor=anulacion.emisor,
            ambiente=settings.DTE_AMBIENTE,
            dte_urls=settings.DTE_URLS[settings.DTE_AMBIENTE],
            dte_user=settings.DTE_USER,
            dte_password=settings.DTE_PASSWORD,
        )
        
        # Consultar estado
        resultado = servicio.consultar_estado_anulacion(anulacion.codigo_generacion)
        
        return JsonResponse({
            'success': True,
            'estado_hacienda': resultado.get('estado', 'DESCONOCIDO'),
            'descripcion': resultado.get('descripcion', ''),
            'resultado_completo': resultado
        })
        
    except Exception as e:
        logger.error(f"Error al consultar estado: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Error al consultar estado: {str(e)}'
        })

@require_http_methods(["GET"])
def buscar_documentos_anular_ajax(request):
    """
    Vista AJAX para buscar documentos que pueden ser anulados
    """
    query = request.GET.get('q', '')
    
    if len(query) < 3:
        return JsonResponse({'results': []})
    
    # Buscar documentos anulables
    estados_anulables = ['ACEPTADO', 'ACEPTADO CON OBSERVACIONES']
    
    documentos = FacturaElectronica.objects.filter(
        estado_hacienda__in=estados_anulables
    ).filter(
        # Buscar por múltiples campos
        models.Q(identificacion__numeroControl__icontains=query) |
        models.Q(identificacion__codigoGeneracion__icontains=query) |
        models.Q(receptor__nombre__icontains=query) |
        models.Q(receptor__numDocumento__icontains=query)
    ).select_related(
        'identificacion__tipoDte',
        'receptor',
        'resumen'
    ).order_by('-identificacion__fecEmi')[:10]
    
    results = []
    for doc in documentos:
        # Verificar que no esté ya anulado
        if not hasattr(doc, 'anulaciones') or not doc.anulaciones.filter(estado='ACEPTADO').exists():
            results.append({
                'id': doc.id,
                'text': f"{doc.identificacion.numeroControl} - {doc.receptor.nombre}",
                'numero_control': doc.identificacion.numeroControl,
                'tipo_dte': doc.identificacion.tipoDte.texto,
                'receptor': doc.receptor.nombre,
                'fecha': doc.identificacion.fecEmi.strftime('%d/%m/%Y'),
                'total': float(doc.resumen.totalPagar),
                'estado': doc.estado_hacienda
            })
    
    return JsonResponse({'results': results})

#Aqui terminan

from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.db.models import Q
from .models import Receptor
from productos.models import Producto

@require_GET
def search_receptors(request):
    """
    Endpoint: /dte/search-receptors/?q=<texto>&tipo=<codigo_tipo>
    Busca receptores por número de documento o nombre, y filtra por tipoDocumento.
    """
    q    = request.GET.get('q',    '').strip()
    tipo = request.GET.get('tipo', '').strip()

    if not q:
        return JsonResponse({'results': []})

    # 1) Base queryset con join sobre tipoDocumento
    qs = Receptor.objects.select_related('tipoDocumento')

    # 2) Si viene tipo, filtrar
    if tipo:
        qs = qs.filter(tipoDocumento__codigo=tipo)

    # 3) Filtrar por texto en número o nombre
    qs = qs.filter(
        Q(numDocumento__icontains=q) |
        Q(nombre__icontains=q)
    )[:10]

    # 4) Formatear salida
    data = [
        {
            'id':         r.id,
            'numDocumento': r.numDocumento,
            'nombre':     r.nombre
        }
        for r in qs
    ]
    return JsonResponse({'results': data})


@require_GET
def search_items(request):
    """
    Busca productos por código (cualquiera de los 4) o descripción.  
    Endpoint: /dte/search-items/?q=<texto>
    """
    q = request.GET.get('q', '').strip()
    if not q:
        return JsonResponse({'results': []})

    # Un solo filter con OR para eficiencia
    qs = Producto.objects.filter(
        Q(codigo1__icontains=q) |
        Q(codigo2__icontains=q) |
        Q(codigo3__icontains=q) |
        Q(codigo4__icontains=q) |
        Q(descripcion__icontains=q)
    ).distinct()[:10]

    data = []
    for p in qs:
        # decidir qué código mostrar
        codigo = next(
            (c for c in (p.codigo1, p.codigo2, p.codigo3, p.codigo4)
             if c and q.upper() in c.upper()),
            p.codigo1
        )
        data.append({
            'id': p.id,
            'codigo': codigo,
            'descripcion': p.descripcion
        })
    return JsonResponse({'results': data})


@require_http_methods(["POST"])
def actualizar_existencias_producto_ajax(request):
    """Vista AJAX para actualizar existencias de un producto en tiempo real"""
    try:
        producto_id = request.POST.get('producto_id')
        nuevas_existencias = request.POST.get('existencias')
        
        if not producto_id or nuevas_existencias is None:
            return JsonResponse({'success': False, 'error': 'Parámetros faltantes'})
        
        try:
            nuevas_existencias = Decimal(str(nuevas_existencias))
        except (ValueError, TypeError):
            return JsonResponse({'success': False, 'error': 'Valor de existencias inválido'})
        
        if nuevas_existencias < 0:
            return JsonResponse({'success': False, 'error': 'Las existencias no pueden ser negativas'})
        
        producto = Producto.objects.get(id=producto_id)
        existencias_anteriores = producto.existencias
        
        producto.existencias = nuevas_existencias
        producto.save()
        
        return JsonResponse({
            'success': True,
            'producto_id': producto_id,
            'producto_nombre': producto.descripcion,
            'existencias_anteriores': float(existencias_anteriores),
            'existencias_nuevas': float(producto.existencias),
            'mensaje': f'Existencias actualizadas: {existencias_anteriores} → {nuevas_existencias}'
        })
        
    except Producto.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Producto no encontrado'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Error interno: {str(e)}'})
    
def descargar_factura_ticket(request, pk):
    """Descarga el ticket de una factura (8cm x 28cm)"""
    factura = get_object_or_404(FacturaElectronica, pk=pk)
    
    # Generar PDF del ticket
    pdf_data = generar_pdf_ticket_factura(factura)
    
    # Crear respuesta HTTP
    response = HttpResponse(pdf_data, content_type='application/pdf')
    filename = f"{factura.identificacion.numeroControl}_ticket.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response

def generar_pdf_ticket_factura(factura):
    """Genera un PDF de ticket (8cm x 28cm) para impresión con diseño vertical por secciones"""
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm, mm
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.lib import colors
    from io import BytesIO
    from decimal import Decimal
    
    # Dimensiones del ticket: 8cm x 28cm
    ticket_width = 8*cm
    ticket_height = 28*cm
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=(ticket_width, ticket_height),
        rightMargin=2*mm,
        leftMargin=2*mm,
        topMargin=2*mm,
        bottomMargin=2*mm,
    )
    
    story = []
    
    # Estilos para ticket
    ticket_style = ParagraphStyle(
        'ticket',
        fontSize=9,
        fontName='Helvetica',
        alignment=TA_CENTER,
        leading=11
    )
    
    ticket_left = ParagraphStyle(
        'ticket_left',
        fontSize=9,
        fontName='Helvetica',
        alignment=TA_LEFT,
        leading=11
    )
    
    ticket_bold = ParagraphStyle(
        'ticket_bold',
        fontSize=11,
        fontName='Helvetica-Bold',
        alignment=TA_CENTER,
        leading=13
    )
    
    section_header = ParagraphStyle(
        'section_header',
        fontSize=10,
        fontName='Helvetica-Bold',
        alignment=TA_LEFT,
        leading=12
    )
    
    # === SECCIÓN 1: IDENTIFICACIÓN ===
    story.append(Paragraph("=== IDENTIFICACIÓN ===", section_header))
    
    tipo_doc = {
        "01": "FACTURA",
        "03": "CREDITO FISCAL", 
        "05": "NOTA DE CREDITO",
        "14": "SUJETO EXCLUIDO"
    }.get(factura.identificacion.tipoDte, "DOCUMENTO")
    
    story.append(Paragraph(f"<b>{tipo_doc}</b>", ticket_bold))
    story.append(Paragraph(f"No. Control: {factura.identificacion.numeroControl}", ticket_left))
    story.append(Paragraph(f"Fecha Emisión: {factura.identificacion.fecEmi}", ticket_left))
    if factura.identificacion.codigoGeneracion:
        story.append(Paragraph(f"Código Gen: {factura.identificacion.codigoGeneracion}", ticket_left))
    story.append(Spacer(1, 2*mm))
    
    # === SECCIÓN 2: EMISOR ===
    story.append(Paragraph("=== EMISOR ===", section_header))
    story.append(Paragraph(f"<b>{factura.emisor.nombre}</b>", ticket_left))
    story.append(Paragraph(f"NIT: {factura.emisor.nit}", ticket_left))
    if factura.emisor.correo:
        story.append(Paragraph(f"Email: {factura.emisor.correo}", ticket_left))
    if factura.emisor.telefono:
        story.append(Paragraph(f"Tel: {factura.emisor.telefono}", ticket_left))
    story.append(Spacer(1, 2*mm))
    
    # === SECCIÓN 3: RECEPTOR ===
    story.append(Paragraph("=== RECEPTOR ===", section_header))
    story.append(Paragraph(f"{factura.receptor.nombre}", ticket_left))
    
    if factura.receptor.numDocumento and factura.receptor.numDocumento != "0":
        tipo_doc_texto = factura.receptor.tipoDocumento.texto if factura.receptor.tipoDocumento else "Doc"
        story.append(Paragraph(f"{tipo_doc_texto}: {factura.receptor.numDocumento}", ticket_left))
    
    if factura.receptor.correo:
        story.append(Paragraph(f"Email: {factura.receptor.correo}", ticket_left))
    story.append(Spacer(1, 2*mm))
    
    # === SECCIÓN 4: ITEMS ===
    story.append(Paragraph("=== ITEMS ===", section_header))
    
    for item in factura.cuerpo_documento.all():
        story.append(Paragraph(f"<b>{item.descripcion}</b>", ticket_left))
        story.append(Paragraph(f"Cant: {int(item.cantidad)} x ${item.precioUni:.2f}", ticket_left))
        story.append(Paragraph(f"Subtotal: ${item.ventaGravada:.2f}", ticket_left))
        story.append(Spacer(1, 1*mm))
    
    story.append(Spacer(1, 2*mm))
    
    # === SECCIÓN 5: RESUMEN ===
    story.append(Paragraph("=== RESUMEN ===", section_header))
    resumen = factura.resumen
    tipo_doc_codigo = factura.identificacion.tipoDte.codigo
    
    # Calcular IVA según tipo de documento (igual que en generar_pdf_factura_mejorado)
    if tipo_doc_codigo == "03":  # CCF
        tributo = resumen.tributos.first()
        iva_val = tributo.valor if tributo else Decimal('0.00')
    elif tipo_doc_codigo == "05":  # Nota de Crédito
        tributo = resumen.tributos.first()
        iva_val = tributo.valor if tributo else Decimal('0.00')
    else:  # Factura y FSE
        iva_val = getattr(resumen, 'totalIva', Decimal('0.00')) or Decimal('0.00')
    
    # Mostrar campos según tipo de documento
    if tipo_doc_codigo == "05":  # Nota de Crédito
        story.append(Paragraph(f"Subtotal Crédito: ${resumen.subTotalVentas:.2f}", ticket_left))
        story.append(Paragraph(f"Descuentos: ${resumen.descuGravada:.2f}", ticket_left))
        story.append(Paragraph(f"Sub-Total: ${resumen.subTotal:.2f}", ticket_left))
        story.append(Paragraph(f"IVA (13%): ${iva_val:.2f}", ticket_left))
        story.append(Paragraph(f"<b>TOTAL CRÉDITO: ${resumen.totalPagar:.2f}</b>", ticket_bold))
    else:  # Factura, CCF, FSE
        story.append(Paragraph(f"Suma de Ventas: ${resumen.subTotalVentas:.2f}", ticket_left))
        if resumen.descuGravada and resumen.descuGravada > 0:
            story.append(Paragraph(f"Descuentos: ${resumen.descuGravada:.2f}", ticket_left))
        story.append(Paragraph(f"Sub-Total: ${resumen.subTotal:.2f}", ticket_left))
        if iva_val > 0:
            story.append(Paragraph(f"IVA (13%): ${iva_val:.2f}", ticket_left))
        story.append(Paragraph(f"<b>TOTAL: ${resumen.totalPagar:.2f}</b>", ticket_bold))
    
    story.append(Spacer(1, 2*mm))
    
    # === SECCIÓN 6: CÓDIGO QR ===
 
    # === SECCIÓN 6: CÓDIGO QR ===
    story.append(Paragraph("=== CÓDIGO QR ===", section_header))
    
    # Generar código QR si hay sello de recepción
    qr_image = None
    if factura.sello_recepcion:
        try:
            import qrcode
            from reportlab.platypus import Image
            from django.conf import settings
            
            # URL para el QR basada en el ambiente
            ambiente = "00" if settings.DTE_AMBIENTE == 'test' else "01"
            qr_url = (
                f"https://admin.factura.gob.sv/consultaPublica?"
                f"ambiente={ambiente}&codGen={factura.identificacion.codigoGeneracion}"
                f"&fechaEmi={factura.identificacion.fecEmi}"
            )
            
            qr = qrcode.QRCode(version=1, box_size=3, border=2)
            qr.add_data(qr_url)
            qr.make(fit=True)
            
            qr_pil_image = qr.make_image(fill_color="black", back_color="white")
            qr_buffer = BytesIO()
            qr_pil_image.save(qr_buffer, format='PNG')
            qr_buffer.seek(0)
            
            # Crear imagen para ReportLab con tamaño apropiado para ticket
            qr_image = Image(qr_buffer, width=20*mm, height=20*mm)
            story.append(qr_image)
            
        except Exception as e:
            print(f"Error generando QR: {e}")
            story.append(Paragraph("[Error generando QR]", ticket_style))
    else:
        story.append(Paragraph("[Sin sello - No hay QR]", ticket_style))
    
    story.append(Spacer(1, 2*mm))
    
    # === SECCIÓN 7: SELLO DE RECEPCIÓN ===
    if factura.sello_recepcion:
        story.append(Paragraph("=== SELLO RECEPCIÓN ===", section_header))
        story.append(Paragraph(f"Sello: {factura.sello_recepcion}", ticket_left))
        story.append(Spacer(1, 2*mm))
    
    # === SECCIÓN 8: FECHA DE PROCESAMIENTO ===
    if factura.fecha_procesamiento:
        story.append(Paragraph("=== PROC. HACIENDA ===", section_header))
        story.append(Paragraph(f"Fecha: {factura.fecha_procesamiento}", ticket_left))
        if factura.estado_hacienda:
            story.append(Paragraph(f"Estado: {factura.get_estado_hacienda_display()}", ticket_left))
    
    doc.build(story)
    buffer.seek(0)
    return buffer.read()



@login_required
def emisor_maestro_view(request):
    """Vista para ver y editar los datos del emisor maestro"""
    try:
        emisor = _emisor_maestro()
        if not emisor:
            # Si no existe emisor, crear uno nuevo
            emisor = Emisor()
    except:
        emisor = Emisor()
    
    if request.method == 'POST':
        from .forms import EmisorMaestroForm
        form = EmisorMaestroForm(request.POST, instance=emisor)
        if form.is_valid():
            form.save()
            messages.success(request, 'Datos del emisor actualizados correctamente')
            return redirect('dte:emisor_maestro')
        else:
            messages.error(request, 'Hay errores en el formulario')
    else:
        from .forms import EmisorMaestroForm
        form = EmisorMaestroForm(instance=emisor)
    
    context = {
        'form': form,
        'emisor': emisor,
        'titulo': 'Emisor Maestro'
    }
    
    return render(request, 'dte/emisor_maestro.html', context)

@require_http_methods(["GET"])
def descargar_lista_facturas_excel(request):
    """Vista para descargar Excel con la lista de facturas filtrada"""
    import openpyxl
    from openpyxl.styles import Font, Alignment, PatternFill
    from openpyxl.utils import get_column_letter
    from django.http import HttpResponse
    from io import BytesIO
    import datetime
    
    try:
        # Obtener los mismos filtros que usa la DataTable
        filtro_tipo = request.GET.get('filtro_tipo', '')
        filtro_estado = request.GET.get('filtro_estado', '')
        filtro_sello = request.GET.get('filtro_sello', '')
        filtro_correo = request.GET.get('filtro_correo', '')
        filtro_sucursal = request.GET.get('filtro_sucursal', '') 
        fecha_desde = request.GET.get('fecha_desde', '')
        fecha_hasta = request.GET.get('fecha_hasta', '')
        search_value = request.GET.get('search', '')

        # Query base - misma lógica que factura_datatable_view
        queryset = FacturaElectronica.objects.select_related(
            'identificacion', 'identificacion__tipoDte', 'receptor', 'resumen'
        )

        # Aplicar los mismos filtros
        if search_value:
            queryset = queryset.filter(
                Q(identificacion__numeroControl__icontains=search_value) |
                Q(receptor__nombre__icontains=search_value)
            )

        if filtro_tipo:
            queryset = queryset.filter(identificacion__tipoDte__codigo=filtro_tipo)

        if filtro_estado:
            queryset = queryset.filter(estado_hacienda=filtro_estado)

        if filtro_sello:
            if filtro_sello == 'con_sello':
                queryset = queryset.filter(sello_recepcion__isnull=False).exclude(sello_recepcion='')
            elif filtro_sello == 'sin_sello':
                queryset = queryset.filter(Q(sello_recepcion__isnull=True) | Q(sello_recepcion=''))

        if filtro_correo:
            if filtro_correo == 'enviado':
                queryset = queryset.filter(enviado_por_correo=True)
            elif filtro_correo == 'no_enviado':
                queryset = queryset.filter(enviado_por_correo=False)
        
        if filtro_sucursal:
            queryset = queryset.filter(sucursal_id=filtro_sucursal)

        if fecha_desde:
            try:
                fecha_desde_dt = datetime.datetime.strptime(fecha_desde, '%Y-%m-%d').date()
                queryset = queryset.filter(identificacion__fecEmi__gte=fecha_desde_dt)
            except ValueError:
                pass

        if fecha_hasta:
            try:
                fecha_hasta_dt = datetime.datetime.strptime(fecha_hasta, '%Y-%m-%d').date()
                queryset = queryset.filter(identificacion__fecEmi__lte=fecha_hasta_dt)
            except ValueError:
                pass

        # Ordenar por fecha descendente
        queryset = queryset.order_by('-identificacion__fecEmi', '-identificacion__horEmi')

        # Crear libro de Excel
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Lista de Facturas"

        # Encabezados
        headers = [
            'Fecha',
            'Tipo (FCF, CCF, NC)',
            'Nombre de Cliente',
            'NIT Cliente',
            'NRC Cliente',
            'Sello de Recepción',
            'Código de Generación',
            'Número de Control',
            'Venta Exenta',
            'Venta Gravada',
            'IVA 13%',
            'Retención',
            'Total Venta',
            'Estatus'
        ]

        # Escribir encabezados
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
            cell.alignment = Alignment(horizontal="center", vertical="center")

        # Escribir datos
        row_num = 2
        facturas_procesadas = 0
        
        for factura in queryset:
            try:
                # Verificar que tiene los datos básicos
                if not factura.identificacion:
                    continue
                    
                if not factura.receptor:
                    continue

                # Obtener datos del resumen usando los nombres correctos de los campos
                resumen = factura.resumen
                if resumen:
                    # Usar getattr para evitar errores de atributos que no existen
                    venta_exenta = getattr(resumen, 'ventaExenta', None) or getattr(resumen, 'totalExenta', None) or Decimal('0.00')
                    venta_gravada = getattr(resumen, 'ventaGravada', None) or getattr(resumen, 'totalGravada', None) or Decimal('0.00')
                    iva = getattr(resumen, 'totalIva', None) or getattr(resumen, 'ivaPerci1', None) or Decimal('0.00')
                    retencion = getattr(resumen, 'reteRenta', None) or getattr(resumen, 'ivaRete1', None) or Decimal('0.00')
                    total = getattr(resumen, 'totalPagar', None) or getattr(resumen, 'montoTotalOperacion', None) or Decimal('0.00')
                else:
                    venta_exenta = venta_gravada = iva = retencion = total = Decimal('0.00')
                
                # Mapear tipo de documento
                tipo_map = {'01': 'FCF', '03': 'CCF', '05': 'NC', '14': 'FSE'}
                tipo_doc = tipo_map.get(factura.identificacion.tipoDte.codigo, factura.identificacion.tipoDte.codigo)
                
                # Mapear estado
                estado_map = {
                    'PROCESADO': 'Procesado',
                    'RECHAZADO': 'Rechazado', 
                    'INVALIDADO': 'Invalidado',
                    'PROCESADO_CON_OBSERVACIONES': 'Procesado c/Obs',
                    'PENDIENTE': 'Pendiente'
                }
                estado = estado_map.get(factura.estado_hacienda, factura.estado_hacienda or 'Pendiente')
                
                # Escribir fila
                data_row = [
                    factura.identificacion.fecEmi if factura.identificacion.fecEmi else None,
                    tipo_doc,
                    factura.receptor.nombre if factura.receptor.nombre else 'N/A',
                    factura.receptor.numDocumento if factura.receptor.numDocumento else 'N/A',
                    factura.receptor.nrc if factura.receptor.nrc else 'N/A',
                    factura.sello_recepcion if factura.sello_recepcion else 'N/A',
                    factura.identificacion.codigoGeneracion if factura.identificacion.codigoGeneracion else 'N/A',
                    factura.identificacion.numeroControl if factura.identificacion.numeroControl else 'N/A',
                    float(venta_exenta),
                    float(venta_gravada),
                    float(iva),
                    float(retencion),
                    float(total),
                    estado
                ]
                
                for col, value in enumerate(data_row, 1):
                    ws.cell(row=row_num, column=col, value=value)
                
                row_num += 1
                facturas_procesadas += 1
                
            except Exception as e:
                print(f"Error procesando factura {factura.pk}: {e}")
                continue

        # Si no hay datos, agregar una fila indicando que no hay datos
        if facturas_procesadas == 0:
            ws.cell(row=2, column=1, value="No hay datos que coincidan con los filtros aplicados")

        # Ajustar ancho de columnas
        for col in range(1, len(headers) + 1):
            column_letter = get_column_letter(col)
            ws.column_dimensions[column_letter].width = 15

        # Aplicar formato solo si hay datos
        if facturas_procesadas > 0:
            # Aplicar formato a columnas de dinero (columnas 9-13)
            for row in range(2, row_num):
                for col in [9, 10, 11, 12, 13]:  # Columnas de dinero
                    cell = ws.cell(row=row, column=col)
                    cell.number_format = '"$"#,##0.00'

            # Aplicar formato a columna de fecha
            for row in range(2, row_num):
                cell = ws.cell(row=row, column=1)  # Columna fecha
                cell.number_format = 'DD/MM/YYYY'

        # Guardar en memoria
        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        
        # Crear response
        response = HttpResponse(
            buffer.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
        # Nombre del archivo con timestamp
        filename = f"lista_facturas_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
        
    except Exception as e:
        print(f"Error generando Excel: {e}")
        import traceback
        traceback.print_exc()
        messages.error(request, f'Error al generar el Excel: {str(e)}')
        return redirect('dte:factura_list')
    
@login_required
def sucursal_list(request):
    """Vista para listar sucursales"""
    sucursales = Sucursal.objects.all().order_by('nombre')
    return render(request, 'dte/sucursal/list.html', {
        'sucursales': sucursales,
        'titulo': 'Gestión de Sucursales'
    })

@login_required
def sucursal_create(request):
    """Vista para crear sucursal"""
    if request.method == 'POST':
        form = SucursalForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Sucursal creada exitosamente')
            return redirect('dte:sucursal_list')
    else:
        form = SucursalForm()
    
    return render(request, 'dte/sucursal/form.html', {
        'form': form,
        'titulo': 'Nueva Sucursal'
    })

@login_required
def sucursal_update(request, pk):
    """Vista para editar sucursal"""
    sucursal = get_object_or_404(Sucursal, pk=pk)
    
    if request.method == 'POST':
        form = SucursalForm(request.POST, instance=sucursal)
        if form.is_valid():
            form.save()
            messages.success(request, 'Sucursal actualizada exitosamente')
            return redirect('dte:sucursal_list')
    else:
        form = SucursalForm(instance=sucursal)
    
    return render(request, 'dte/sucursal/form.html', {
        'form': form,
        'sucursal': sucursal,
        'titulo': 'Editar Sucursal'
    })

@login_required
def sucursal_delete(request, pk):
    """Vista para eliminar sucursal"""
    sucursal = get_object_or_404(Sucursal, pk=pk)
    
    if request.method == 'POST':
        nombre = sucursal.nombre
        sucursal.delete()
        messages.success(request, f'Sucursal {nombre} eliminada exitosamente')
        return redirect('dte:sucursal_list')
    
    return render(request, 'dte/sucursal/confirm_delete.html', {
        'sucursal': sucursal,
        'titulo': 'Eliminar Sucursal'
    })


@require_http_methods(["GET"])
def descargar_lista_facturas_json(request):
    """Vista para descargar JSON con la lista de facturas filtrada"""
    import json
    from django.http import HttpResponse
    from .utils import build_dte_json
    
    try:
        # Obtener los mismos filtros que usa la DataTable
        filtro_tipo = request.GET.get('filtro_tipo', '')
        filtro_estado = request.GET.get('filtro_estado', '')
        filtro_sello = request.GET.get('filtro_sello', '')
        filtro_correo = request.GET.get('filtro_correo', '')
        filtro_sucursal = request.GET.get('filtro_sucursal', '')
        fecha_desde = request.GET.get('fecha_desde', '')
        fecha_hasta = request.GET.get('fecha_hasta', '')
        search_value = request.GET.get('search', '')

        # Query base - misma lógica que factura_datatable_view
        queryset = FacturaElectronica.objects.select_related(
            'identificacion', 'identificacion__tipoDte', 'receptor', 'resumen', 'emisor', 'sucursal'
        ).prefetch_related(
            'cuerpo_documento', 'resumen__pagos', 'resumen__tributos'
        )

        # Aplicar los mismos filtros
        if search_value:
            queryset = queryset.filter(
                Q(identificacion__numeroControl__icontains=search_value) |
                Q(receptor__nombre__icontains=search_value)
            )

        if filtro_tipo:
            queryset = queryset.filter(identificacion__tipoDte__codigo=filtro_tipo)

        if filtro_estado:
            queryset = queryset.filter(estado_hacienda=filtro_estado)

        if filtro_sello:
            if filtro_sello == 'con_sello':
                queryset = queryset.filter(sello_recepcion__isnull=False).exclude(sello_recepcion='')
            elif filtro_sello == 'sin_sello':
                queryset = queryset.filter(Q(sello_recepcion__isnull=True) | Q(sello_recepcion=''))

        if filtro_correo:
            if filtro_correo == 'enviado':
                queryset = queryset.filter(enviado_por_correo=True)
            elif filtro_correo == 'no_enviado':
                queryset = queryset.filter(enviado_por_correo=False)

        if filtro_sucursal:
            queryset = queryset.filter(sucursal_id=filtro_sucursal)

        if fecha_desde:
            try:
                fecha_desde_dt = datetime.strptime(fecha_desde, '%Y-%m-%d').date() 
                queryset = queryset.filter(identificacion__fecEmi__gte=fecha_desde_dt)
            except ValueError:
                pass

        if fecha_hasta:
            try:
                fecha_hasta_dt = datetime.strptime(fecha_hasta, '%Y-%m-%d').date()
                queryset = queryset.filter(identificacion__fecEmi__lte=fecha_hasta_dt)
            except ValueError:
                pass

        # Ordenar por fecha descendente
        queryset = queryset.order_by('-identificacion__fecEmi', '-identificacion__horEmi')

        # Generar JSONs de todas las facturas
        facturas_json = []
        for factura in queryset:
            try:
                json_data = build_dte_json(factura)
                facturas_json.append({
                    'numeroControl': factura.identificacion.numeroControl,
                    'codigoGeneracion': factura.identificacion.codigoGeneracion,
                    'fechaEmision': factura.identificacion.fecEmi.isoformat(),
                    'receptor': factura.receptor.nombre,
                    'total': str(factura.resumen.totalPagar) if factura.resumen else '0.00',
                    'estado': factura.estado_hacienda,
                    'dte_json': json_data
                })
            except Exception as e:
                # Si hay error con una factura específica, añadir error al registro
                facturas_json.append({
                    'numeroControl': factura.identificacion.numeroControl,
                    'error': f'Error al generar JSON: {str(e)}'
                })

        # Crear respuesta JSON
        response_data = {
            'total_facturas': len(facturas_json),
            'filtros_aplicados': {
                'tipo': filtro_tipo,
                'estado': filtro_estado,
                'sello': filtro_sello,
                'correo': filtro_correo,
                'sucursal': filtro_sucursal,
                'fecha_desde': fecha_desde,
                'fecha_hasta': fecha_hasta,
                'busqueda': search_value
            },
            'fecha_generacion': datetime.now().isoformat(), 
            'facturas': facturas_json
        }

        # Crear respuesta HTTP
        response = HttpResponse(
            json.dumps(response_data, indent=2, ensure_ascii=False),
            content_type='application/json; charset=utf-8'
        )
        
        # Nombre del archivo
        filename = f"facturas_json_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response

    except Exception as e:
        messages.error(request, f'Error al generar el JSON: {str(e)}')
        return redirect('dte:factura_list')