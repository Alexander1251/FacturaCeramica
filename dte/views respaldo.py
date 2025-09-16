# dte/views.py
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
from reportlab.pdfgen import canvas
from django.http import JsonResponse
from django.contrib import messages
from django.db import transaction
from decimal import Decimal
from django.forms import model_to_dict
import json
from django.http        import JsonResponse
from django.db          import transaction
from jsonschema                import validate as jsonschema_validate
from jsonschema.exceptions     import ValidationError as JSONSchemaValidationError
from dte.schema import FE_SCHEMA as DTE_SCHEMA
from .models import (
    FacturaElectronica, Receptor, Identificacion, Resumen, CondicionOperacion,
    TributoResumen, TipoDocumento, Departamento, Municipio,TipoDocReceptor, ActividadEconomica, TipoItem
)
from .forms  import (
    IdentificacionForm, ReceptorForm,
    ItemFormset, ResumenForm, PagoFormset, _emisor_maestro
)
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
from decimal import Decimal
# ─────────────────────────────────────
# vistas
# ─────────────────────────────────────
class FacturaListView(ListView):
    model               = FacturaElectronica
    template_name       = "dte/factura_list.html"
    context_object_name = "facturas"
    paginate_by         = 20
    ordering            = "-identificacion__fecEmi"

class FacturaDetailView(DetailView):
    model         = FacturaElectronica
    template_name = "dte/factura_detail.html"
    context_object_name = "factura"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["json"] = json.dumps(self.object.to_json(), indent=2, ensure_ascii=False)
        return ctx

    
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
from decimal import Decimal

def generar_pdf_factura_mejorado(factura):
    """
    Genera un PDF profesional de la factura electrónica en blanco y negro
    con diseño limpio y estructura unificada
    """
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
    # ENCABEZADO
    # ========================
    story.append(Paragraph("Ver.1", ParagraphStyle('version', fontSize=7, alignment=TA_RIGHT)))
    story.append(Spacer(1, 4*mm))
    
    story.append(Paragraph("DOCUMENTO TRIBUTARIO ELECTRÓNICO", title_style))
    story.append(Paragraph("FACTURA", subtitle_style))
    story.append(Spacer(1, 6*mm))
    
    # ========================
    # IDENTIFICACIÓN - Tabla compacta
    # ========================
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
    
    receptor_data = f"""
    <b>Nombre:</b> {factura.receptor.nombre}<br/>
    <b>Tipo Doc:</b> {factura.receptor.tipoDocumento}<br/>
    <b>N° Documento:</b> {factura.receptor.numDocumento}<br/>
    <b>Email:</b> {factura.receptor.correo}<br/>
    """
    
    emisor_receptor_data = [
        [Paragraph('<b>EMISOR</b>', header_style), Paragraph('<b>RECEPTOR</b>', header_style)],
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
    
    # Encabezado del cuerpo
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
    
    resumen_items = [
        ['', '', Paragraph('<b>RESUMEN</b>', bold_style), '', '', ''],
        ['', '', Paragraph('Suma de Ventas:', normal_style), '', '', 
         Paragraph(f"${resumen.subTotalVentas:.2f}", normal_style)],
        ['', '', Paragraph('Descuentos:', normal_style), '', '', 
         Paragraph(f"${resumen.descuGravada:.2f}", normal_style)],
        ['', '', Paragraph('Sub-Total:', normal_style), '', '', 
         Paragraph(f"${resumen.subTotal:.2f}", normal_style)],
        ['', '', Paragraph('IVA (13%):', normal_style), '', '', 
         Paragraph(f"${resumen.totalIva:.2f}", normal_style)],
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
    # OBSERVACIONES (opcional)
    # ========================
    observaciones_data = [
        [Paragraph('<b>Observaciones:</b>', normal_style)],
        [Paragraph('', normal_style)]  # Espacio para observaciones
    ]
    
    observaciones_table = Table(observaciones_data, colWidths=[170*mm], rowHeights=[8*mm, 15*mm])
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
    
    # ========================
    # PIE DE PÁGINA
    # ========================
    story.append(Spacer(1, 8*mm))
    story.append(Paragraph("Página 1 de 1", 
                          ParagraphStyle('footer', fontSize=7, alignment=TA_CENTER)))
    story.append(Paragraph(f"Generado: {factura.identificacion.fecEmi}", 
                          ParagraphStyle('footer', fontSize=7, alignment=TA_CENTER)))
    
    # Construir el PDF
    doc.build(story)
    
    buffer.seek(0)
    return buffer.read()

def crear_factura_electronica(request):
    """
    Función principal mejorada que usa el nuevo generador de PDF
    """
    print('*** LLEGÓ petición en crear_factura_electronica:', request.method)
    print(request.POST)
    if request.method == 'POST':
        identificacion_form = IdentificacionForm(request.POST)
        receptor_form       = ReceptorForm(request.POST)
        item_formset        = ItemFormset(request.POST)

        if not (identificacion_form.is_valid() and receptor_form.is_valid() and item_formset.is_valid()):
            print("Identificación errores:", identificacion_form.errors)
            print("Receptor errores:    ", receptor_form.errors)
            print("ItemFormset errores: ", item_formset.errors)
            print("ItemFormset no-form: ", item_formset.non_form_errors())
            context = {
                'identificacion_form': identificacion_form,
                'receptor_form'      : receptor_form,
                'item_formset'       : item_formset,
                'tipos_documento'    : TipoDocReceptor.objects.all(),
                'departamentos'      : Departamento.objects.all(),
                'municipios'         : Municipio.objects.all(),
                'actividades_economicas': ActividadEconomica.objects.all(),
                'tipos_items'        : TipoItem.objects.all(),
            }
            return render(request, 'dte/factura_form.html', context)

        with transaction.atomic():
            # ... (mantener todo el código de guardado igual hasta la generación del PDF)
            
            # Guardar identificación
            identificacion = identificacion_form.save()

            # Guardar o reutilizar receptor
            data   = receptor_form.cleaned_data
            receptor, _ = Receptor.objects.get_or_create(
                tipoDocumento = data['tipoDocumento'],
                numDocumento  = data['numDocumento'],
                defaults      = {
                    'nombre':        data['nombre'],
                    'nrc':           data.get('nrc',''),
                    'codActividad':  data.get('codActividad'),
                    'descActividad': data.get('descActividad',''),
                    'departamento':  data.get('departamento'),
                    'municipio':     data.get('municipio'),
                    'telefono':      data.get('telefono',''),
                    'correo':        data.get('correo',''),
                    'complemento':   data.get('complemento',''),
                }
            )

            # Crear factura
            factura = FacturaElectronica.objects.create(
                identificacion = identificacion,
                receptor       = receptor,
                emisor         = _emisor_maestro()
            )

            # Guardar items
            items = item_formset.save(commit=False)
            for it in items:
                it.factura = factura
                it.save()

            # Cálculo de totales
            total_gravada = sum(i.ventaGravada for i in factura.cuerpo_documento.all())
            total_iva     = sum(i.ivaItem     for i in factura.cuerpo_documento.all())
            total_pagar   = total_gravada + total_iva
            total_letras  = numero_a_letras(total_pagar)

            descu_gravada   = sum(i.montoDescu for i in items)
            porcentaje_desc = (descu_gravada / total_gravada * Decimal('100')) if total_gravada else Decimal('0')
            total_descu     = descu_gravada

            # Crear resumen
            resumen = Resumen.objects.create(
                factura             = factura,
                totalNoSuj          = Decimal('0'),
                totalExenta         = Decimal('0'),
                totalGravada        = total_gravada,
                subTotal            = total_gravada,
                subTotalVentas      = total_gravada,
                descuNoSuj          = Decimal('0'),
                descuExenta         = Decimal('0'),
                descuGravada        = descu_gravada,
                porcentajeDescuento = porcentaje_desc,
                totalDescu          = total_descu,
                ivaRete1            = Decimal('0'),
                reteRenta           = Decimal('0'),
                montoTotalOperacion = total_pagar,
                totalNoGravado      = Decimal('0'),
                totalIva            = total_iva,
                totalPagar          = total_pagar,
                saldoFavor          = Decimal('0'),
                condicionOperacion  = CondicionOperacion.objects.get(pk=1),
                numPagoElectronico  = "",
                totalLetras         = total_letras
            )

            # Tributo IVA
            TributoResumen.objects.create(
                resumen     = resumen,
                codigo_id   = "20",
                descripcion = "Impuesto al Valor Agregado 13%",
                valor       = total_iva
            )

            # Generar y validar JSON
            dte_json = build_dte_json(factura)
            try:
                jsonschema_validate(instance=dte_json, schema=DTE_SCHEMA)
                validation = {'valid': True, 'errors': None}
            except JSONSchemaValidationError as e:
                validation = {'valid': False, 'errors': str(e)}

            if not validation['valid']:
                messages.error(request, f"Error de validación JSON: {validation['errors']}")
                context = {
                    'identificacion_form': identificacion_form,
                    'receptor_form'      : receptor_form,
                    'item_formset'       : item_formset,
                    'tipos_documento'    : TipoDocReceptor.objects.all(),
                    'departamentos'      : Departamento.objects.all(),
                    'municipios'         : Municipio.objects.all(),
                    'actividades_economicas': ActividadEconomica.objects.all(),
                    'tipos_items'        : TipoItem.objects.all(),
                }
                return render(request, 'dte/factura_form.html', context)

            # ===== AQUÍ ESTÁ EL CAMBIO PRINCIPAL =====
            # Generar PDF mejorado usando la nueva función
            pdf_data = generar_pdf_factura_mejorado(factura)

            # Enviar correo con adjuntos
            email = EmailMessage(
                subject=f"Factura {factura.identificacion.numeroControl}",
                body="Adjunto su factura en PDF y el JSON.",
                to=[receptor.correo]
            )
            email.attach(f"{factura.identificacion.numeroControl}.pdf", pdf_data, 'application/pdf')
            email.attach(
                f"{factura.identificacion.numeroControl}.json",
                json.dumps(dte_json, indent=2, ensure_ascii=False),
                'application/json'
            )
            email.send(fail_silently=False)

            return redirect('dte:factura_list')

    # GET
    identificacion_form = IdentificacionForm()
    receptor_form       = ReceptorForm()
    item_formset        = ItemFormset()
    return render(request, 'dte/factura_form.html', {
        'identificacion_form': identificacion_form,
        'receptor_form'      : receptor_form,
        'item_formset'       : item_formset,
        'tipos_documento'    : TipoDocReceptor.objects.all(),
        'departamentos'      : Departamento.objects.all(),
        'municipios'         : Municipio.objects.all(),
        'actividades_economicas': ActividadEconomica.objects.all(),
        'tipos_items'        : TipoItem.objects.all(),
    })

@require_http_methods(["GET"])
def buscar_receptores_ajax(request):
    """Vista AJAX para buscar receptores por número de documento"""
    tipo_doc = request.GET.get('tipo_documento')
    numero_parcial = request.GET.get('numero', '').strip()
    
    if not tipo_doc or not numero_parcial:
        return JsonResponse({'receptores': []})
    
    # Buscar receptores que coincidan
    receptores = Receptor.objects.filter(
        tipoDocumento_id=tipo_doc,
        numDocumento__icontains=numero_parcial
    ).select_related('tipoDocumento', 'departamento', 'municipio')[:10]
    
    data = []
    for receptor in receptores:
        data.append({
            'id': receptor.id,
            'numDocumento': receptor.numDocumento,
            'nrc': receptor.nrc or '',
            'nombre': receptor.nombre,
            'codActividad': receptor.codActividad.codigo if receptor.codActividad else '',
            'descActividad': receptor.descActividad or '',
            'departamento': receptor.departamento.codigo if receptor.departamento else '',
            'departamento_nombre': receptor.departamento.texto if receptor.departamento else '',
            'municipio': receptor.municipio_id,
            'municipio_nombre': receptor.municipio.texto if receptor.municipio else '',
            'complemento': receptor.complemento or '',
            'telefono': receptor.telefono or '',
            'correo': receptor.correo or '',
            'tipoDocumento': receptor.tipoDocumento.codigo,
            'tipoDocumento_descripcion': f"{receptor.tipoDocumento.codigo} - {receptor.tipoDocumento.texto}"
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
            codigo_used = producto.codigo3
        elif codigo_parcial.upper() in (producto.codigo4 or '').upper():
            codigo_usado = producto.codigo4
            
        data.append({
            'id': producto.id,
            'codigo': codigo_usado,
            'nombre': producto.nombre,
            'descripcion': producto.descripcion,
            'precio1': str(producto.precio1),
            'precio2': str(producto.precio2) if producto.precio2 else '',
            'precio3': str(producto.precio3) if producto.precio3 else '',
            'precio4': str(producto.precio4) if producto.precio4 else '',
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