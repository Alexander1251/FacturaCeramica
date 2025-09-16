# dte/forms.py
from decimal import Decimal, ROUND_HALF_UP
import uuid

from django import forms
from django.forms import inlineformset_factory, BaseInlineFormSet
from django.utils import timezone

from .models import (
    Identificacion, Receptor, FacturaElectronica, CuerpoDocumentoItem,
    Resumen, Pago, TributoResumen, Emisor, UnidadMedida,
    TipoDocumento, AmbienteDestino, ModeloFacturacion, TipoTransmision, NotaCreditoDetalle, Sucursal
)
from productos.models import Producto
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Div, Field
from django.conf import settings
# ───────── utilidades ────────────────────────────────────
def _emisor_maestro() -> Emisor:
    return Emisor.objects.first()


# dte/forms.py - Función y clase completas corregidas

def _siguiente_numero_control(tipo_dte='01', sucursal=None) -> str:
    """
    Genera el siguiente número de control según el tipo de documento y sucursal
    ACTUALIZADO: Usa códigos de sucursal en lugar del emisor maestro
    Args:
        tipo_dte: '01' para Factura, '03' para CCF, '05' para NC, etc.
        sucursal: Instancia de Sucursal para usar sus códigos
    Returns:
        str: Número de control en formato DTE-XX-XXXXXXXX-XXXXXXXXXXXXXXX
    """
    if sucursal:
        # Usar códigos de la sucursal específica
        establecimiento = sucursal.codEstable
        punto_venta = sucursal.codPuntoVenta
    else:
        # Fallback al emisor maestro (para compatibilidad temporal)
        emisor = _emisor_maestro()
        if not emisor:
            raise Exception("No hay emisor configurado")
        establecimiento = emisor.codEstable or "0001"
        punto_venta = emisor.codPuntoVenta or "0001"
    
    # Generar prefijo con códigos correspondientes
    prefijo = f"DTE-{tipo_dte}-{establecimiento.zfill(4)}{punto_venta.zfill(4)}-"
    
    ultimo = (
        Identificacion.objects.filter(numeroControl__startswith=prefijo)
        .order_by("-numeroControl")
        .first()
    )
    correlativo = 1 if not ultimo else int(ultimo.numeroControl[-15:]) + 1
    return f"{prefijo}{correlativo:015d}"


class IdentificacionForm(forms.ModelForm):
    ambiente = forms.ModelChoiceField(
        queryset=AmbienteDestino.objects.all(),
        initial=lambda: AmbienteDestino.objects.get(codigo="00" if settings.DTE_AMBIENTE == 'test' else "01"),
        label="Ambiente destino",
    )

    class Meta:
        model = Identificacion
        fields = ["fecEmi", "horEmi", "ambiente"]

    def __init__(self, *args, **kwargs):
        # Extraemos el tipo de DTE (por defecto '01' = factura)
        self.tipo_dte = kwargs.pop('tipo_dte', '01')
        # NUEVO: Extraer sucursal para generar número de control
        self.sucursal = kwargs.pop('sucursal', None)
        super().__init__(*args, **kwargs)

        now = timezone.localtime()
        self.fields["fecEmi"].initial = now.date()
        self.fields["horEmi"].initial = now.strftime("%H:%M:%S")

    def clean(self):
        cleaned_data = super().clean()

        # 1) Tipo de documento
        try:
            td = TipoDocumento.objects.get(codigo=self.tipo_dte)
        except TipoDocumento.DoesNotExist:
            raise forms.ValidationError(f"Tipo de documento '{self.tipo_dte}' no existe")
        self.instance.tipoDte = td

        # 2) Moneda
        self.instance.tipoMoneda = "USD"

        # 3) Versión según tipo
        if self.tipo_dte == "01":
            self.instance.version = 1
        elif self.tipo_dte == "03":
            self.instance.version = 3
        elif self.tipo_dte == "05":  # NC
            self.instance.version = 3
        elif self.tipo_dte == "14":  # FSE
            self.instance.version = 1

        # 4) Modelo de facturación (siempre '1')
        try:
            modelo = ModeloFacturacion.objects.get(codigo="1")
        except ModeloFacturacion.DoesNotExist:
            raise forms.ValidationError("Modelo de facturación '1' no existe")
        self.instance.tipoModelo = modelo

        # 5) Tipo de operación (siempre '1')
        try:
            transm = TipoTransmision.objects.get(codigo="1")
        except TipoTransmision.DoesNotExist:
            raise forms.ValidationError("Tipo de transmisión '1' no existe")
        self.instance.tipoOperacion = transm

        # 6) Número de control - ACTUALIZADO PARA USAR SUCURSAL
        if not self.instance.numeroControl:
            self.instance.numeroControl = _siguiente_numero_control(self.tipo_dte, self.sucursal)

        return cleaned_data

    def save(self, commit=True):
        # Generar código de generación si no existe
        if not self.instance.codigoGeneracion:
            self.instance.codigoGeneracion = str(uuid.uuid4()).upper()
        
        return super().save(commit)


class ReceptorForm(forms.ModelForm):
    buscar = forms.BooleanField(required=False, label="Buscar receptor existente")
    tipo_dte = forms.CharField(widget=forms.HiddenInput(), required=False)

    class Meta:
        model = Receptor
        exclude = []

    def __init__(self, *args, **kwargs):
        tipo_dte = kwargs.pop('tipo_dte', '01')
        super().__init__(*args, **kwargs)
        self.fields['tipo_dte'].initial = tipo_dte
        
        # Para CCF, solo permitir NIT (tipo 36)
        if tipo_dte == "03":
            self.fields['tipoDocumento'].queryset = TipoDocReceptor.objects.filter(codigo="36")
            self.fields['tipoDocumento'].initial = TipoDocReceptor.objects.get(codigo="36")
            self.fields['tipoDocumento'].widget.attrs['readonly'] = True
        
    def clean(self):
        data = super().clean()
        tipo_dte = data.get('tipo_dte', '01')
        
        # Validación específica para CCF
        if tipo_dte == "03":
            tipo_doc = data.get('tipoDocumento')
            if not tipo_doc or tipo_doc.codigo != "36":
                raise forms.ValidationError("Para Crédito Fiscal solo se permite NIT")
                
            # Campos obligatorios para CCF
            campos_obligatorios = ['numDocumento', 'nrc', 'nombre', 'codActividad', 
                                 'descActividad', 'departamento', 'municipio', 
                                 'complemento', 'telefono', 'correo']
            for campo in campos_obligatorios:
                if not data.get(campo):
                    raise forms.ValidationError(f"Para Crédito Fiscal, el campo {campo} es obligatorio")
        
        if data.get("buscar"):
            tipo = data.get("tipoDocumento")
            num = data.get("numDocumento")
            if not (tipo and num):
                raise forms.ValidationError("Indique tipo y número de documento.")
            try:
                self.instance = Receptor.objects.get(
                    tipoDocumento=tipo, numDocumento=num
                )
            except Receptor.DoesNotExist:
                raise forms.ValidationError("No existe un receptor con ese documento.")
        return data


# dte/forms.py - CuerpoDocumentoItemForm CORREGIDO - Manteniendo funcionalidad original + FSE

class CuerpoDocumentoItemForm(forms.ModelForm):
    # Campos auxiliares (no en el modelo) - MANTENIDOS
    producto = forms.ModelChoiceField(
        queryset=Producto.objects.all(), label="Producto"
    )
    precio_idx = forms.ChoiceField(
        choices=[(1, "Precio 1"), (2, "Precio 2"), (3, "Precio 3"), (4, "Precio 4")],
        initial=1,
        label="Precio",
    )
    descuento = forms.ChoiceField(
        choices=[(i, f"{i}%") for i in range(0, 55, 5)],
        initial=0,
        label="Descuento %",
    )

    class Meta:
        model = CuerpoDocumentoItem
        exclude = ["factura", "numeroDocumento", "numItem"]
        widgets = {
            "uniMedida": forms.Select(attrs={"class": "form-select"}),
            "tipoItem": forms.Select(attrs={"class": "form-select"}),
            # los campos calculados los volvemos de solo–lectura (HTML) ↓
            "precioUni": forms.NumberInput(attrs={"readonly": "readonly"}),
            "montoDescu": forms.NumberInput(attrs={"readonly": "readonly"}),
            "ventaGravada": forms.NumberInput(attrs={"readonly": "readonly"}),
            "ivaItem": forms.NumberInput(attrs={"readonly": "readonly"}),
            "descuentoAplicado": forms.HiddenInput(),
            "precioIndiceUsado": forms.HiddenInput(),
        }

    field_order = (
        "producto",
        "precio_idx", 
        "descuento",
        "tipoItem",
        "cantidad",
        "codigo",
        "descripcion",
        "precioUni",
        "montoDescu",
        "ventaGravada",
        "ivaItem",
    )

    # -------------- INIT ----------------- MANTENIDO + FSE
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Configuración original MANTENIDA
        for f in [
            'uniMedida',
            'ventaNoSuj',
            'ventaExenta'
        ]:
            self.fields[f].required = False
            
        # Unidad 59 (unidad) por defecto MANTENIDO
        self.helper = FormHelper()
        self.helper.form_tag = False  # el tag <form> lo tiene la vista principal
        self.helper.layout = Layout(
            Row(
                Div("producto",        css_class="col-md-4"),
                Div("precio_idx",      css_class="col-md-2"),
                Div("descuento",       css_class="col-md-2"),
                Div("cantidad",        css_class="col-md-2"),
                Div("tipoItem",        css_class="col-md-2"),
            ),
            Row(
                Div("descripcion", css_class="col-md-4"),
                Div("codigo",          css_class="col-md-2"),
                Div("precioUni",       css_class="col-md-2"),
                Div("montoDescu",      css_class="col-md-2"),
                Div("ventaGravada",    css_class="col-md-2"),
            ),
            Row(
                Div("ivaItem",         css_class="col-md-2"),
                Div("codTributo",      css_class="col-md-2"),
                Div("tributos",         css_class="col-md-2"),
                Div("ventaExenta",     css_class="col-md-2"),
                Div("ventaNoSuj",      css_class="col-md-2"),
                Div("noGravado",       css_class="col-md-2"),
            ),
        )
        self.initial.setdefault(
            "uniMedida", UnidadMedida.objects.filter(codigo="59").first()
        )
        
        # NUEVA FUNCIONALIDAD FSE: Detectar tipo de DTE y ajustar labels/campos
        tipo_dte = self._detectar_tipo_dte()
        if tipo_dte == "14":  # FSE
            # Cambiar label de ventaGravada para FSE
            self.fields['ventaGravada'].label = "Compra (Total)"
            self.fields['ventaGravada'].help_text = "Total de compra para este ítem (FSE)"
            
            # Ocultar campos no usados en FSE en el layout si es posible
            # (mantenemos los campos pero los ocultamos visualmente)
            pass  # El layout se mantiene igual para compatibilidad

    def _detectar_tipo_dte(self):
        """Detectar tipo de DTE desde la instancia de factura"""
        if self.instance and self.instance.pk and hasattr(self.instance, 'factura'):
            if hasattr(self.instance.factura, 'identificacion') and self.instance.factura.identificacion:
                if hasattr(self.instance.factura.identificacion, 'tipoDte') and self.instance.factura.identificacion.tipoDte:
                    return self.instance.factura.identificacion.tipoDte.codigo
        
        # Si no hay factura asignada aún, intentar obtener del contexto del formulario
        if hasattr(self, 'parent') and hasattr(self.parent, 'tipo_dte'):
            return self.parent.tipo_dte
            
        return "01"  # Default: Factura

    # -------------- CLEAN ----------------- MANTENIDO + FSE
    def clean(self):
        cd = super().clean()

        # Lectura de datos básicos - MANTENIDO
        prod = cd.get("producto")
        precio_idx = int(cd.get("precio_idx", 1))
        descuento_pct = Decimal(cd.get("descuento", 0)) / Decimal("100")
        cantidad = cd.get("cantidad") or Decimal("0")

        # Autocompletar código, descripción y precio - MANTENIDO
        if prod:
            cd["codigo"] = prod.codigo1
            cd["descripcion"] = prod.descripcion
            cd["precioUni"] = prod.precio_por_indice(precio_idx)

        precio_uni = cd.get("precioUni", Decimal("0"))
        
        # Detectar tipo de DTE - MEJORADO
        tipo_dte = self._detectar_tipo_dte()
        
        # También verificar el método original para compatibilidad
        es_ccf = False
        if hasattr(self, 'instance') and self.instance and hasattr(self.instance, 'factura'):
            factura = self.instance.factura
            if factura and hasattr(factura, 'identificacion'):
                es_ccf = factura.identificacion.tipoDte.codigo == "03"
        
        # Si no hay factura asignada aún, intentar obtener del contexto del formulario
        # (esto ocurre durante la creación) - MANTENIDO
        if not es_ccf and hasattr(self, 'parent') and hasattr(self.parent, 'tipo_dte'):
            es_ccf = self.parent.tipo_dte == "03"

        # NUEVO: Lógica para FSE
        if tipo_dte == "14":  # FSE
            # Para FSE: compra = precio * cantidad - descuento (absoluto)
            subtotal = precio_uni * cantidad
            descuento_abs = subtotal * descuento_pct  # Convertir % a absoluto
            compra = subtotal - descuento_abs

            cd["montoDescu"] = descuento_abs.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            cd["ventaGravada"] = compra.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)  # Reutilizar como 'compra'
            cd["ivaItem"] = Decimal("0.00")  # FSE no tiene IVA
            
        # Cálculos diferenciados por tipo de documento - MANTENIDO
        elif es_ccf:
            # Para CCF: El precio viene con IVA incluido desde el frontend
            # Calcular precio sin IVA CON MÁXIMA PRECISIÓN - MANTENIDO
            precio_sin_iva = precio_uni / Decimal('1.13')
            subtotal_sin_iva = precio_sin_iva * cantidad
            descuento_abs = subtotal_sin_iva * descuento_pct
            venta_gravada = subtotal_sin_iva - descuento_abs
            
            # Los valores se redondean SOLO para almacenamiento - MANTENIDO
            cd["precioUni"] = precio_sin_iva.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            cd["montoDescu"] = descuento_abs.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            cd["ventaGravada"] = venta_gravada.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            # Para CCF, ivaItem no se usa - MANTENIDO
            cd["ivaItem"] = Decimal("0.00")
            
        else:
            # Para Factura: Lógica original - MANTENIDO COMPLETAMENTE
            subtotal = precio_uni * cantidad
            descuento_abs = subtotal * descuento_pct
            venta_gravada = subtotal - descuento_abs

            # Montos calculados - MANTENIDO
            cd["montoDescu"] = descuento_abs.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            cd["ventaGravada"] = venta_gravada.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            # IVA solo si hay venta gravada > 0 - MANTENIDO
            if venta_gravada > Decimal("0"):
                iva = ((venta_gravada / Decimal('1.13')) * Decimal('0.13')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            else:
                iva = Decimal("0.00")
            cd['ivaItem'] = iva

        # Campos estructurales - MANTENIDO
        if self.instance.pk is None:
            cd["numeroDocumento"] = None

        # Defaults para campos no usados - MANTENIDO
        cd.setdefault("ventaExenta", Decimal("0"))
        cd.setdefault("ventaNoSuj", Decimal("0"))
        cd.setdefault("noGravado", Decimal("0"))

        # Reglas de tributos según esquema - MANTENIDO
        tipo = cd.get("tipoItem")
        cd["tributos"] = None

        # Regla específica: tipoItem == 4 ("Otro") - MANTENIDO
        if tipo == 4:
            # Forzar unidad de medida 99
            cd["uniMedida"] = UnidadMedida.objects.get(codigo=99)

        # PSV siempre cero - MANTENIDO
        cd["psv"] = Decimal("0")

        return cd


# Formulario específico para resumen FSE
class ResumenFSEForm(forms.ModelForm):
    """Formulario específico para el resumen de FSE"""
    
    class Meta:
        model = Resumen
        fields = ['total_compra', 'descu', 'totalPagar', 'condicionOperacion', 'observaciones_fse']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.fields['total_compra'].widget.attrs.update({
            'class': 'form-control',
            'step': '0.01',
            'readonly': True  # Se calcula automáticamente
        })
        
        self.fields['descu'].widget.attrs.update({
            'class': 'form-control',
            'step': '0.01',
            'readonly': True  # Se calcula automáticamente
        })
        
        self.fields['totalPagar'].widget.attrs.update({
            'class': 'form-control', 
            'step': '0.01',
            'readonly': True  # Se calcula automáticamente
        })
        
        self.fields['observaciones_fse'].widget = forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Observaciones adicionales para la Factura de Sujeto Excluido'
        })

    def clean(self):
        cd = super().clean()
        
        # Validaciones específicas para FSE
        total_compra = cd.get('total_compra', Decimal('0'))
        if total_compra <= Decimal('0'):
            raise forms.ValidationError('El total de compra debe ser mayor a 0 para FSE')
            
        return cd


# ───────── Formsets ──────────────────────────────────────
class BaseItemFormset(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if self.total_form_count() == 0:
            raise forms.ValidationError("Debe agregar al menos un ítem.")
        contador = 1
        for form in self.forms:
            if form.cleaned_data.get("DELETE"):
                continue
            form.instance.numItem = contador
            contador += 1


class PagoForm(forms.ModelForm):
    class Meta:
        model = Pago
        exclude = ["resumen"]


class BasePagoFormset(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if all(f.cleaned_data.get("DELETE", False) for f in self.forms):
            raise forms.ValidationError("Debe registrar al menos una forma de pago.")


ItemFormset = inlineformset_factory(
    FacturaElectronica,
    CuerpoDocumentoItem,
    form=CuerpoDocumentoItemForm,
    formset=BaseItemFormset,
    extra=1,
    can_delete=True,
)

PagoFormset = inlineformset_factory(
    Resumen,
    Pago,
    form=PagoForm,
    formset=BasePagoFormset,
    extra=1,
    can_delete=True,
)

# ───────── Resumen de factura ───────────────────────────
class ResumenForm(forms.ModelForm):
    """Formulario mínimo para el modelo Resumen.

    Sólo ocultamos el ForeignKey 'factura'; los demás campos los
    mostrará el formulario o los calcularás en la vista.
    """
    class Meta:
        model = Resumen
        exclude = ["factura"]

# dte/forms_receptor.py
from django import forms
from django.core.exceptions import ValidationError
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Div, Field, HTML

from .models import Receptor, TipoDocReceptor, ActividadEconomica, Departamento, Municipio


class ReceptorCRUDForm(forms.ModelForm):
    """Formulario para CRUD de Receptores"""
    
    class Meta:
        model = Receptor
        fields = [
            'tipoDocumento', 'numDocumento', 'nrc', 'nombre', 
            'codActividad', 'descActividad', 'departamento', 
            'municipio', 'complemento', 'telefono', 'correo'
        ]
        
        widgets = {
            'tipoDocumento': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'numDocumento': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: 123456789 o 12345678-9',
                'required': True
            }),
            'nrc': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: 123456',
                'maxlength': 8
            }),
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre completo del receptor',
                'required': True,
                'maxlength': 250
            }),
            'codActividad': forms.Select(attrs={
                'class': 'form-select'
            }),
            'descActividad': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Descripción de la actividad económica',
                'maxlength': 150
            }),
            'departamento': forms.Select(attrs={
                'class': 'form-select'
            }),
            'municipio': forms.Select(attrs={
                'class': 'form-select'
            }),
            'complemento': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Dirección detallada',
                'maxlength': 200
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: +503 2222-3333',
                'maxlength': 30
            }),
            'correo': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'correo@ejemplo.com',
                'maxlength': 100
            })
        }
        
        labels = {
            'tipoDocumento': 'Tipo de Documento',
            'numDocumento': 'Número de Documento',
            'nrc': 'NRC',
            'nombre': 'Nombre Completo',
            'codActividad': 'Actividad Económica',
            'descActividad': 'Descripción de Actividad',
            'departamento': 'Departamento',
            'municipio': 'Municipio',
            'complemento': 'Dirección Complementaria',
            'telefono': 'Teléfono',
            'correo': 'Correo Electrónico'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Configurar Crispy Forms
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'needs-validation'
        self.helper.attrs = {'novalidate': True}
        
        # Layout del formulario
        self.helper.layout = Layout(
            HTML('<div class="row">'),
            HTML('<div class="col-md-6">'),
            HTML('<h5 class="mb-3">Información del Documento</h5>'),
            Row(
                Div('tipoDocumento', css_class='col-md-6'),
                Div('numDocumento', css_class='col-md-6'),
            ),
            Row(
                Div('nrc', css_class='col-md-6'),
                Div('nombre', css_class='col-md-6'),
            ),
            HTML('</div>'),
            
            HTML('<div class="col-md-6">'),
            HTML('<h5 class="mb-3">Actividad Económica</h5>'),
            'codActividad',
            'descActividad',
            HTML('</div>'),
            HTML('</div>'),
            
            HTML('<hr class="my-4">'),
            HTML('<h5 class="mb-3">Información de Contacto</h5>'),
            
            Row(
                Div('departamento', css_class='col-md-4'),
                Div('municipio', css_class='col-md-4'),
                Div('complemento', css_class='col-md-4'),
            ),
            Row(
                Div('telefono', css_class='col-md-6'),
                Div('correo', css_class='col-md-6'),
            ),
        )
        
        # CAMBIO PRINCIPAL: Mostrar todos los municipios ordenados por departamento
        self.fields['municipio'].queryset = Municipio.objects.select_related('departamento').order_by('departamento__texto', 'texto')
        
        # Los campos mínimos obligatorios son: nombre, tipoDocumento, numDocumento, correo
        self.fields['nombre'].required = True
        self.fields['tipoDocumento'].required = True  
        self.fields['numDocumento'].required = True
        self.fields['correo'].required = True
        
        # Hacer campos opcionales según las reglas de negocio
        self.fields['nrc'].required = False
        self.fields['codActividad'].required = False
        self.fields['descActividad'].required = False
        self.fields['departamento'].required = False
        self.fields['municipio'].required = False
        self.fields['complemento'].required = False
        self.fields['telefono'].required = False

    def clean_numDocumento(self):
        """Validación del número de documento según el tipo"""
        tipo_documento = self.cleaned_data.get('tipoDocumento')
        num_documento = self.cleaned_data.get('numDocumento')
        
        if not tipo_documento or not num_documento:
            return num_documento
        
        # Limpiar espacios
        num_documento = num_documento.strip()
        
        # Validaciones según tipo de documento
        if tipo_documento.codigo == "36":  # NIT
            import re
            if not re.match(r"^(\d{9}|\d{14})$", num_documento):
                raise ValidationError(
                    "Para NIT (tipo 36), el número debe tener 9 o 14 dígitos."
                )
        elif tipo_documento.codigo == "13":  # DUI
            import re
            if not re.match(r"^[0-9]{8}-[0-9]$", num_documento):
                raise ValidationError(
                    "Para DUI (tipo 13), el formato debe ser XXXXXXXX-X."
                )
        
        return num_documento

    def clean_nrc(self):
        """Validación del NRC"""
        nrc = self.cleaned_data.get('nrc')
        tipo_documento = self.cleaned_data.get('tipoDocumento')
        
        if nrc:
            # NRC solo válido para tipo documento 36 (NIT)
            if tipo_documento and tipo_documento.codigo != "36":
                raise ValidationError(
                    "NRC solo es válido para documentos tipo NIT (36)."
                )
            
            # Validar formato de NRC
            import re
            if not re.match(r"^\d{2,8}$", nrc):
                raise ValidationError(
                    "NRC debe tener entre 2 y 8 dígitos."
                )
        
        return nrc

    def clean(self):
        """Validaciones generales del formulario"""
        cleaned_data = super().clean()
        
        # Validar unicidad de tipo + número de documento
        tipo_documento = cleaned_data.get('tipoDocumento')
        num_documento = cleaned_data.get('numDocumento')
        
        if tipo_documento and num_documento:
            queryset = Receptor.objects.filter(
                tipoDocumento=tipo_documento,
                numDocumento=num_documento
            )
            
            # Excluir el receptor actual en caso de edición
            if self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            
            if queryset.exists():
                tipo_texto = getattr(tipo_documento, 'texto', str(tipo_documento)) if tipo_documento else 'Desconocido'
                raise ValidationError(
                    f"Ya existe un receptor con {tipo_texto} "
                    f"número {num_documento}."
                )
        
        # NUEVA VALIDACIÓN: Si se proporciona algún campo de dirección, todos deben estar presentes
        departamento = cleaned_data.get('departamento')
        municipio = cleaned_data.get('municipio')
        complemento = cleaned_data.get('complemento')
        
        direccion_fields = [departamento, municipio, complemento]
        campos_con_valor = [field for field in direccion_fields if field]
        
        # Si hay algún campo de dirección con valor, todos deben tener valor
        if campos_con_valor and len(campos_con_valor) != 3:
            raise ValidationError(
                "Si proporciona información de dirección, debe completar departamento, "
                "municipio y complemento."
            )
        
        # VALIDACIÓN CORRECTA: Usar el mismo mapa que en el modelo
        if departamento and municipio:
            DEPARTAMENTO_MUNICIPIO_MAP = {
                "00": ["00"],
                "01": ["13", "14", "15"],
                "02": ["14", "15", "16", "17"],
                "03": ["17", "18", "19", "20"],
                "04": ["34", "35", "36"],
                "05": ["23", "24", "25", "26", "27", "28"],
                "06": ["20", "21", "22", "23", "24"],
                "07": ["17", "18"],
                "08": ["23", "24", "25"],
                "09": ["10", "11"],
                "10": ["14", "15"],
                "11": ["24", "25", "26"],
                "12": ["21", "22", "23"],
                "13": ["27", "28"],
                "14": ["19", "20"],
            }
            
            try:
                depto_code = departamento.codigo
                muni_code = municipio.codigo
                
                if depto_code in DEPARTAMENTO_MUNICIPIO_MAP:
                    allowed_municipios = DEPARTAMENTO_MUNICIPIO_MAP[depto_code]
                    if muni_code not in allowed_municipios:
                        depto_texto = getattr(departamento, 'texto', str(departamento))
                        muni_texto = getattr(municipio, 'texto', str(municipio))
                        raise ValidationError(
                            f"El municipio {muni_texto} (código {muni_code}) no es válido "
                            f"para el departamento {depto_texto} (código {depto_code}). "
                            f"Municipios válidos: {', '.join(allowed_municipios)}"
                        )
            except AttributeError:
                # Si departamento o municipio no tienen codigo
                raise ValidationError(
                    "Error al validar departamento y municipio. "
                    "Verifique que ambos estén seleccionados correctamente."
                )
        
        return cleaned_data


class ReceptorSearchForm(forms.Form):
    """Formulario para búsqueda de receptores"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Buscar por nombre, documento, NRC o correo...',
            'autocomplete': 'off'
        }),
        label='Búsqueda'
    )
    
    tipo_documento = forms.ModelChoiceField(
        queryset=TipoDocReceptor.objects.all(),
        required=False,
        empty_label='Todos los tipos',
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label='Tipo de Documento'
    )
    
    departamento = forms.ModelChoiceField(
        queryset=Departamento.objects.all(),
        required=False,
        empty_label='Todos los departamentos',
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label='Departamento'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'get'
        self.helper.form_class = 'row g-3 align-items-end'
        
        self.helper.layout = Layout(
            Row(
                Div('search', css_class='col-md-6'),
                Div('tipo_documento', css_class='col-md-3'),
                Div('departamento', css_class='col-md-3'),
            ),
            HTML('''
                <div class="col-12">
                    <button type="submit" class="btn btn-primary me-2">
                        <i class="fas fa-search me-1"></i>Buscar
                    </button>
                    <a href="{% url 'dte:receptor_list' %}" class="btn btn-secondary">
                        <i class="fas fa-times me-1"></i>Limpiar
                    </a>
                </div>
            ''')
        )

# Agregar estas clases al archivo forms.py existente
# CONSERVAR las clases existentes y agregar las nuevas

def _siguiente_numero_control_nc() -> str:
    """
    Genera el siguiente número de control específico para Nota de Crédito (tipo 05)
    """
    return _siguiente_numero_control(tipo_dte='05')

class NotaCreditoDetalleForm(forms.ModelForm):
    """
    Formulario para los detalles específicos de la Nota de Crédito
    """
    class Meta:
        model = NotaCreditoDetalle
        fields = ['motivo_nota_credito', 'tipo_nota_credito']
        widgets = {
            'motivo_nota_credito': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describa el motivo de la nota de crédito...',
                'required': True
            }),
            'tipo_nota_credito': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            })
        }


class DocumentoOrigenForm(forms.Form):
    """
    Formulario para seleccionar el documento original (CCF) del cual se creará la NC
    ACTUALIZADO: Solo muestra CCF con items disponibles para NC
    """
    documento_origen = forms.ModelChoiceField(
        queryset=FacturaElectronica.objects.none(),  # Se configura en __init__
        empty_label="Seleccione el documento original...",
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'id_documento_origen',
            'data-placeholder': 'Escriba aquí para buscar...',
        }),
        label="Documento Original (CCF)"
    )
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # FILTRO MEJORADO: Solo CCF aceptados CON items disponibles
        ccf_base = FacturaElectronica.objects.filter(
            identificacion__tipoDte__codigo='03',  # Solo CCF
            estado_hacienda__in=['ACEPTADO', 'ACEPTADO CON OBSERVACIONES']
        ).select_related('identificacion', 'receptor', 'resumen').order_by('-identificacion__fecEmi')
        
        # Filtrar solo los que tienen items disponibles
        ccf_disponibles = []
        for ccf in ccf_base:
            if ccf.tiene_items_disponibles_para_nc():
                ccf_disponibles.append(ccf.id)
        
        # Configurar queryset final
        self.fields['documento_origen'].queryset = FacturaElectronica.objects.filter(
            id__in=ccf_disponibles
        ).select_related('identificacion', 'receptor', 'resumen').order_by('-identificacion__fecEmi')
        
        # Personalizar la representación del queryset
        self.fields['documento_origen'].label_from_instance = self._label_documento
        
    def _label_documento(self, obj):
        """
        MEJORADO: Mostrar información de disponibilidad
        """
        receptor_nombre = obj.receptor.nombre if obj.receptor else "Sin receptor"
        fecha = obj.identificacion.fecEmi.strftime('%d/%m/%Y')
        porcentaje_acreditado = obj.get_porcentaje_acreditado()
        items_disponibles = len(obj.get_items_disponibles_para_nc())
        
        disponibilidad = ""
        if porcentaje_acreditado > 0:
            disponibilidad = f" ({100-porcentaje_acreditado:.0f}% disponible, {items_disponibles} items)"
        else:
            disponibilidad = f" (100% disponible, {items_disponibles} items)"
        
        return f"{obj.identificacion.numeroControl} - {receptor_nombre} - ${obj.resumen.totalPagar:.2f} ({fecha}){disponibilidad}"

class IdentificacionNotaCreditoForm(IdentificacionForm):
    """
    Formulario de identificación específico para Nota de Crédito
    ACTUALIZADO: Usa sucursal para generar número de control
    """
    def __init__(self, *args, **kwargs):
        # Asegurar que el tipo sea NC
        kwargs['tipo_dte'] = '05'
        super().__init__(*args, **kwargs)
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Configuración automática específica para NC (tipo 05)
        try:
            tipo_documento = TipoDocumento.objects.get(codigo='05')
        except TipoDocumento.DoesNotExist:
            raise forms.ValidationError("Tipo de documento Nota de Crédito (05) no existe")
        
        instance.tipoDte = tipo_documento
        instance.version = 3  # NC usa versión 3
        instance.tipoModelo = ModeloFacturacion.objects.get(codigo="1")
        instance.tipoOperacion = TipoTransmision.objects.get(codigo="1")
        instance.tipoMoneda = "USD"
        
        # Código de generación automático
        if not instance.codigoGeneracion:
            instance.codigoGeneracion = str(uuid.uuid4()).upper()
        
        # Número de control automático para NC usando sucursal
        if not instance.numeroControl:
            instance.numeroControl = _siguiente_numero_control('05', self.sucursal)

        # Campos de contingencia por defecto como null
        instance.tipoContingencia = None
        instance.motivoContin = None

        if commit:
            instance.save()
        return instance


class SeleccionItemsForm(forms.Form):
    """
    Formulario dinámico para seleccionar items del CCF original
    CORREGIDO: Validación mejorada de checkboxes y cantidades
    """
    def __init__(self, items_originales, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        for item in items_originales:
            # Campo checkbox para seleccionar el item
            self.fields[f'seleccionar_{item.id}'] = forms.BooleanField(
                required=False,
                label='',
                widget=forms.CheckboxInput(attrs={
                    'class': 'form-check-input item-checkbox',
                    'data-item-id': item.id,
                    'data-descripcion': item.descripcion,
                    'data-cantidad': str(item.cantidad),
                    'data-precio': str(item.precioUni),
                    'data-total': str(item.ventaGravada),
                    'onchange': f'toggleCantidadInput({item.id})'  # JavaScript para habilitar/deshabilitar
                })
            )
            
            # Campo para cantidad a devolver (máximo la cantidad original)
            self.fields[f'cantidad_{item.id}'] = forms.DecimalField(
                required=False,
                initial=item.cantidad,
                max_value=item.cantidad,
                min_value=Decimal('0.01'),
                decimal_places=2,
                max_digits=10,
                widget=forms.NumberInput(attrs={
                    'class': 'form-control form-control-sm cantidad-input',
                    'step': '0.01',
                    'max': str(item.cantidad),
                    'disabled': True,  # Se habilita cuando se selecciona el checkbox
                    'data-item-id': item.id,
                    'data-precio-unitario': str(item.precioUni),
                    'data-cantidad-maxima': str(item.cantidad)
                })
            )

    def clean(self):
        cleaned_data = super().clean()
        items_seleccionados = []
        errores = []
        
        # CORRECCIÓN: Verificar que al menos un item esté seleccionado
        for field_name, value in cleaned_data.items():
            if field_name.startswith('seleccionar_') and value:
                item_id = field_name.replace('seleccionar_', '')
                cantidad_field = f'cantidad_{item_id}'
                cantidad = cleaned_data.get(cantidad_field, Decimal('0'))
                
                # Validar que la cantidad sea válida
                if not cantidad or cantidad <= 0:
                    errores.append(f'Debe especificar una cantidad válida mayor a 0 para el item seleccionado.')
                    continue
                
                # Obtener el item original para validar cantidad máxima
                try:
                    from .models import CuerpoDocumentoItem
                    item_original = CuerpoDocumentoItem.objects.get(id=item_id)
                    
                    if cantidad > item_original.cantidad:
                        errores.append(f'La cantidad ({cantidad}) no puede ser mayor a la cantidad original ({item_original.cantidad}) para el item: {item_original.descripcion}')
                        continue
                        
                except CuerpoDocumentoItem.DoesNotExist:
                    errores.append(f'Item no encontrado: {item_id}')
                    continue
                
                items_seleccionados.append({
                    'item_id': item_id,
                    'cantidad': cantidad
                })
        
        # Si hay errores específicos, mostrarlos
        if errores:
            for error in errores:
                raise forms.ValidationError(error)
        
        # Validar que hay al menos un item seleccionado
        if not items_seleccionados:
            raise forms.ValidationError('Debe seleccionar al menos un item marcando el checkbox correspondiente.')
        
        cleaned_data['items_seleccionados'] = items_seleccionados
        return cleaned_data


class NotaCreditoSimplificadaForm(forms.ModelForm):
    """
    Formulario simplificado para Nota de Crédito - basado en el patrón de crear_factura_electronica
    OPTIMIZADO: Manejo automático de campos sin asignaciones directas
    """
    class Meta:
        model = NotaCreditoDetalle
        fields = ['motivo_nota_credito', 'tipo_nota_credito']
        widgets = {
            'motivo_nota_credito': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describa el motivo de la nota de crédito...',
                'required': True
            }),
            'tipo_nota_credito': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Configuración adicional similar a otros formularios del sistema
        self.fields['motivo_nota_credito'].required = True
        self.fields['tipo_nota_credito'].required = True
    
# dte/forms.py - Agregar al final del archivo

def obtener_precio_exacto_producto(item_original):
    """
    Obtiene el precio exacto del producto usando el índice almacenado
    CORRECCIÓN MÍNIMA: Usar precioIndiceUsado y descuentoAplicado correctamente
    """
    try:
        from django.db.models import Q
        from productos.models import Producto
        from decimal import Decimal
        
        print(f"DEBUG obtener_precio_exacto: Procesando item con código {item_original.codigo}")
        print(f"DEBUG obtener_precio_exacto: Precio índice usado: {item_original.precioIndiceUsado}")
        print(f"DEBUG obtener_precio_exacto: Descuento aplicado: {item_original.descuentoAplicado}%")
        
        # PASO 1: Buscar producto por código
        producto = Producto.objects.filter(
            Q(codigo1=item_original.codigo) |
            Q(codigo2=item_original.codigo) |
            Q(codigo3=item_original.codigo) |
            Q(codigo4=item_original.codigo)
        ).first()
        
        if not producto:
            print(f"WARNING: No se encontró producto con código {item_original.codigo}")
            return None
        
        # CORRECCIÓN MÍNIMA: Obtener el precio exacto usando el índice almacenado
        precio_original_con_iva = None
        precio_usado_descripcion = ""
        
        if item_original.precioIndiceUsado == 1:
            precio_original_con_iva = producto.precio1
            precio_usado_descripcion = "Precio 1"
        elif item_original.precioIndiceUsado == 2:
            precio_original_con_iva = producto.precio2 or producto.precio1
            precio_usado_descripcion = "Precio 2"
        elif item_original.precioIndiceUsado == 3:
            precio_original_con_iva = producto.precio3 or producto.precio1
            precio_usado_descripcion = "Precio 3"
        elif item_original.precioIndiceUsado == 4:
            precio_original_con_iva = producto.precio4 or producto.precio1
            precio_usado_descripcion = "Precio 4"
        else:
            # Fallback si no hay índice válido
            precio_original_con_iva = producto.precio1
            precio_usado_descripcion = "Precio 1 (fallback)"
        
        if not precio_original_con_iva or precio_original_con_iva <= 0:
            print(f"WARNING: {precio_usado_descripcion} no disponible para {producto.nombre}")
            return None
        
        print(f"DEBUG obtener_precio_exacto: {precio_usado_descripcion} = ${precio_original_con_iva}")
        
        # CORRECCIÓN MÍNIMA: Aplicar el descuento almacenado
        descuento_aplicado = item_original.descuentoAplicado or Decimal('0.00')
        factor_descuento = Decimal('1') - (descuento_aplicado / Decimal('100'))
        precio_final_con_iva = precio_original_con_iva * factor_descuento
        
        print(f"DEBUG obtener_precio_exacto: Descuento aplicado: {descuento_aplicado}%")
        print(f"DEBUG obtener_precio_exacto: Precio final con IVA: ${precio_final_con_iva}")
        
        # PASO 4: Calcular precio sin IVA e IVA
        precio_sin_iva_exacto = precio_final_con_iva / Decimal('1.13')
        iva_unitario_exacto = precio_sin_iva_exacto * Decimal('0.13')
        
        print(f"DEBUG obtener_precio_exacto: Precio sin IVA: ${precio_sin_iva_exacto}")
        print(f"DEBUG obtener_precio_exacto: IVA unitario: ${iva_unitario_exacto}")
        
        resultado = {
            'precio_con_iva': precio_final_con_iva,
            'precio_sin_iva': precio_sin_iva_exacto,
            'iva_unitario': iva_unitario_exacto,
            'precio_usado': precio_usado_descripcion,
            'descuento_aplicado': descuento_aplicado,
            'precio_original_con_iva': precio_original_con_iva,
            'producto_nombre': producto.nombre
        }
        
        print(f"DEBUG obtener_precio_exacto: Resultado exitoso para {producto.nombre}")
        return resultado
        
    except Exception as e:
        print(f"ERROR obtener_precio_exacto: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def obtener_datos_precisos_item_nc(item_original):
    """
    Función auxiliar que encapsula la lógica completa para obtener datos precisos
    CORRECCIÓN MÍNIMA: Solo cambiar para usar obtener_precio_exacto_producto corregida
    """
    try:
        # Usar la función principal corregida
        datos_precio = obtener_precio_exacto_producto(item_original)
        
        if not datos_precio:
            # Fallback: usar datos originales del CCF (SIN CAMBIOS)
            print(f"FALLBACK: Usando datos originales del CCF para {item_original.codigo}")
            precio_sin_iva_fallback = item_original.precioUni
            iva_unitario_fallback = precio_sin_iva_fallback * Decimal('0.13')
            
            return {
                'precio_con_iva': precio_sin_iva_fallback * Decimal('1.13'),
                'precio_sin_iva': precio_sin_iva_fallback,
                'iva_unitario': iva_unitario_fallback,
                'precio_usado': 'Fallback - CCF Original',
                'diferencia_original': Decimal('0.00'),
                'producto_nombre': item_original.descripcion,
                'es_fallback': True
            }
        
        # Agregar flag de que no es fallback (SIN CAMBIOS)
        datos_precio['es_fallback'] = False
        return datos_precio
        
    except Exception as e:
        print(f"ERROR obtener_datos_precisos_item_nc: {str(e)}")
        return None
    
#Aqui comienzan los cambios de anulacion
# dte/forms.py - AGREGAR al archivo forms.py existente
# dte/forms.py - AGREGAR al archivo forms.py existente

# dte/forms.py - AGREGAR al archivo forms.py existente

from django import forms
from .models import AnulacionDocumento, FacturaElectronica, AmbienteDestino
from django.utils import timezone

class AnulacionDocumentoForm(forms.ModelForm):
    """
    Formulario para crear anulaciones de documentos fiscales
    """
    
    class Meta:
        model = AnulacionDocumento
        fields = [
            'ambiente',
            'motivo_anulacion',
            'nombre_responsable',
            'tipo_doc_responsable', 
            'num_doc_responsable',
            'nombre_solicita',
            'tipo_doc_solicita',
            'num_doc_solicita'
        ]
        widgets = {
            'ambiente': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'motivo_anulacion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describa el motivo de la anulación (mínimo 5 caracteres)',
                'maxlength': 250,
                'required': True
            }),
            'nombre_responsable': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre completo del responsable',
                'maxlength': 100,
                'required': True
            }),
            'tipo_doc_responsable': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'num_doc_responsable': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número de documento',
                'maxlength': 20,
                'required': True
            }),
            'nombre_solicita': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre completo del solicitante',
                'maxlength': 100,
                'required': True
            }),
            'tipo_doc_solicita': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'num_doc_solicita': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número de documento',
                'maxlength': 20,
                'required': True
            }),
        }
        labels = {
            'ambiente': 'Ambiente de Destino',
            'motivo_anulacion': 'Motivo de la Anulación',
            'nombre_responsable': 'Nombre del Responsable',
            'tipo_doc_responsable': 'Tipo de Documento',
            'num_doc_responsable': 'Número de Documento',
            'nombre_solicita': 'Nombre del Solicitante',
            'tipo_doc_solicita': 'Tipo de Documento',
            'num_doc_solicita': 'Número de Documento',
        }
        help_texts = {
            'motivo_anulacion': 'Describa claramente el motivo por el cual se anula el documento',
            'nombre_responsable': 'Persona responsable de autorizar la anulación',
            'nombre_solicita': 'Persona que solicita la anulación del documento',
        }
    
    def __init__(self, *args, **kwargs):
        self.documento_anular = kwargs.pop('documento_anular', None)
        self.emisor = kwargs.pop('emisor', None)
        super().__init__(*args, **kwargs)
        
        # Configurar ambiente por defecto
        if not self.instance.pk:
            try:
                ambiente_default = AmbienteDestino.objects.get(codigo="00" if settings.DTE_AMBIENTE == 'test' else "01")  # Pruebas por defecto
                self.fields['ambiente'].initial = ambiente_default.pk
            except AmbienteDestino.DoesNotExist:
                pass
        
        # Agregar validaciones en HTML5
        self.fields['motivo_anulacion'].widget.attrs['minlength'] = 5
        self.fields['nombre_responsable'].widget.attrs['minlength'] = 5
        self.fields['num_doc_responsable'].widget.attrs['minlength'] = 3
        self.fields['nombre_solicita'].widget.attrs['minlength'] = 5
        self.fields['num_doc_solicita'].widget.attrs['minlength'] = 3
    
    def clean_motivo_anulacion(self):
        motivo = self.cleaned_data.get('motivo_anulacion')
        if motivo and len(motivo.strip()) < 5:
            raise forms.ValidationError('El motivo debe tener al menos 5 caracteres.')
        return motivo.strip() if motivo else motivo
    
    def clean_nombre_responsable(self):
        nombre = self.cleaned_data.get('nombre_responsable')
        if nombre and len(nombre.strip()) < 5:
            raise forms.ValidationError('El nombre debe tener al menos 5 caracteres.')
        return nombre.strip() if nombre else nombre
    
    def clean_nombre_solicita(self):
        nombre = self.cleaned_data.get('nombre_solicita')
        if nombre and len(nombre.strip()) < 5:
            raise forms.ValidationError('El nombre debe tener al menos 5 caracteres.')
        return nombre.strip() if nombre else nombre
    
    def clean_num_doc_responsable(self):
        numero = self.cleaned_data.get('num_doc_responsable')
        if numero and len(numero.strip()) < 3:
            raise forms.ValidationError('El número de documento debe tener al menos 3 caracteres.')
        return numero.strip() if numero else numero
    
    def clean_num_doc_solicita(self):
        numero = self.cleaned_data.get('num_doc_solicita')
        if numero and len(numero.strip()) < 3:
            raise forms.ValidationError('El número de documento debe tener al menos 3 caracteres.')
        return numero.strip() if numero else numero
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Asignar documento
        if self.documento_anular:
            instance.documento_anular = self.documento_anular
        
        # Siempre usar el emisor maestro (consistente con el resto del sistema)
        try:
            from .forms import _emisor_maestro
            emisor_maestro = _emisor_maestro()
        except ImportError:
            # Si hay problema con la importación circular, obtener el emisor de otra forma
            from .models import Emisor
            emisor_maestro = Emisor.objects.first()
        
        if not emisor_maestro:
            raise ValueError("No hay emisor maestro configurado en el sistema")
        instance.emisor = emisor_maestro
        
        # Configurar tipo de anulación por defecto (tipo 2)
        instance.tipo_anulacion = 2
        
        # Configurar fechas
        instance.fecha_anulacion = timezone.now().date()
        instance.hora_anulacion = timezone.now().time()
        
        if commit:
            instance.save()
        
        return instance


class BuscarDocumentoAnularForm(forms.Form):
    """
    Formulario para buscar documentos que pueden ser anulados
    """
    
    TIPO_BUSQUEDA_CHOICES = [
        ('numero_control', 'Número de Control'),
        ('codigo_generacion', 'Código de Generación'), 
        ('receptor_nombre', 'Nombre del Receptor'),
        ('receptor_documento', 'Documento del Receptor'),
    ]
    
    tipo_busqueda = forms.ChoiceField(
        choices=TIPO_BUSQUEDA_CHOICES,
        initial='numero_control',
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'id_tipo_busqueda'
        }),
        label='Buscar por'
    )
    
    termino_busqueda = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese el término de búsqueda',
            'id': 'id_termino_busqueda'
        }),
        label='Término de búsqueda'
    )
    
    def buscar_documentos(self):
        """
        Busca documentos que pueden ser anulados
        """
        if not self.is_valid():
            return FacturaElectronica.objects.none()
        
        tipo = self.cleaned_data['tipo_busqueda']
        termino = self.cleaned_data['termino_busqueda']
        
        # Solo documentos con estados que permiten anulación
        estados_anulables = ['ACEPTADO', 'ACEPTADO CON OBSERVACIONES']
        
        queryset = FacturaElectronica.objects.filter(
            estado_hacienda__in=estados_anulables
        ).select_related(
            'identificacion', 
            'identificacion__tipoDte',
            'receptor',
            'resumen'
        )
        
        # Aplicar filtro según tipo de búsqueda
        if tipo == 'numero_control':
            queryset = queryset.filter(
                identificacion__numeroControl__icontains=termino
            )
        elif tipo == 'codigo_generacion':
            queryset = queryset.filter(
                identificacion__codigoGeneracion__icontains=termino
            )
        elif tipo == 'receptor_nombre':
            queryset = queryset.filter(
                receptor__nombre__icontains=termino
            )
        elif tipo == 'receptor_documento':
            queryset = queryset.filter(
                receptor__numDocumento__icontains=termino
            )
        
        return queryset.order_by('-identificacion__fecEmi')[:20]  # Limitar resultados
    
#Aqui terminan

class SeleccionItemsNcForm(forms.Form):
    """
    Formulario dinámico MEJORADO para seleccionar items del CCF original
    ACTUALIZADO: Valida disponibilidad real de items
    """
    def __init__(self, items_disponibles, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        for item in items_disponibles:
            cantidad_disponible = item.get_cantidad_disponible_para_nc()
            
            # Solo agregar si hay cantidad disponible
            if cantidad_disponible > 0:
                # Campo checkbox para seleccionar el item
                self.fields[f'seleccionar_{item.id}'] = forms.BooleanField(
                    required=False,
                    label='',
                    widget=forms.CheckboxInput(attrs={
                        'class': 'form-check-input item-checkbox',
                        'data-item-id': item.id,
                        'data-descripcion': item.descripcion,
                        'data-cantidad-original': str(item.cantidad),
                        'data-cantidad-disponible': str(cantidad_disponible),
                        'data-cantidad-acreditada': str(item.get_cantidad_acreditada()),
                        'data-precio': str(item.precioUni),
                        'onchange': f'toggleCantidadInput({item.id})'
                    })
                )
                
                # Campo para cantidad a devolver (máximo la cantidad disponible, no la original)
                self.fields[f'cantidad_{item.id}'] = forms.DecimalField(
                    required=False,
                    initial=cantidad_disponible,  # Cambio: usar disponible como inicial
                    max_value=cantidad_disponible,  # Cambio: límite es lo disponible
                    min_value=Decimal('0.01'),
                    decimal_places=2,
                    max_digits=10,
                    widget=forms.NumberInput(attrs={
                        'class': 'form-control form-control-sm cantidad-input',
                        'step': '0.01',
                        'max': str(cantidad_disponible),  # Cambio: límite es lo disponible
                        'disabled': True,
                        'data-item-id': item.id,
                        'data-precio-unitario': str(item.precioUni),
                        'data-cantidad-maxima': str(cantidad_disponible),  # Cambio: usar disponible
                        'data-cantidad-original': str(item.cantidad),
                        'data-cantidad-acreditada': str(item.get_cantidad_acreditada())
                    })
                )

    def clean(self):
        cleaned_data = super().clean()
        items_seleccionados = []
        errores = []
        
        # Verificar que al menos un item esté seleccionado
        for field_name, value in cleaned_data.items():
            if field_name.startswith('seleccionar_') and value:
                item_id = field_name.replace('seleccionar_', '')
                cantidad_field = f'cantidad_{item_id}'
                cantidad = cleaned_data.get(cantidad_field, Decimal('0'))
                
                if not cantidad or cantidad <= 0:
                    errores.append(f'Debe especificar una cantidad válida mayor a 0 para el item seleccionado.')
                    continue
                
                # VALIDACIÓN CRÍTICA: Verificar disponibilidad real
                try:
                    from .models import CuerpoDocumentoItem
                    item_original = CuerpoDocumentoItem.objects.get(id=item_id)
                    cantidad_disponible = item_original.get_cantidad_disponible_para_nc()
                    
                    if cantidad > cantidad_disponible:
                        errores.append(
                            f'La cantidad ({cantidad}) excede la disponible ({cantidad_disponible}) '
                            f'para el item: {item_original.descripcion}. '
                            f'Ya se han acreditado {item_original.get_cantidad_acreditada()} unidades.'
                        )
                        continue
                        
                except CuerpoDocumentoItem.DoesNotExist:
                    errores.append(f'Item no encontrado: {item_id}')
                    continue
                
                items_seleccionados.append({
                    'item_id': item_id,
                    'cantidad': cantidad
                })
        
        if errores:
            for error in errores:
                raise forms.ValidationError(error)
        
        if not items_seleccionados:
            raise forms.ValidationError('Debe seleccionar al menos un item marcando el checkbox correspondiente.')
        
        cleaned_data['items_seleccionados'] = items_seleccionados
        return cleaned_data
    

class EmisorMaestroForm(forms.ModelForm):
    """Formulario para editar datos del emisor maestro"""
    
    class Meta:
        model = Emisor
        fields = [
            'nit', 'nrc', 'nombre', 'codActividad', 'descActividad',
            'nombreComercial', 'tipoEstablecimiento', 'departamento', 
            'municipio', 'complemento', 'telefono', 'correo',
            'codEstableMH', 'codEstable', 'codPuntoVentaMH', 'codPuntoVenta'
        ]
        widgets = {
            'nit': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '14 dígitos para empresa, 9 para persona'
            }),
            'nrc': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número de Registro de Contribuyente'
            }),
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Razón social o nombre completo'
            }),
            'codActividad': forms.Select(attrs={
                'class': 'form-control tom-select-actividad',
                'placeholder': 'Buscar actividad económica...'
            }),
            'descActividad': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Descripción de la actividad económica'
            }),
            'nombreComercial': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre comercial (opcional)'
            }),
            'tipoEstablecimiento': forms.Select(attrs={
                'class': 'form-control'
            }),
            'departamento': forms.Select(attrs={
                'class': 'form-control'
            }),
            'municipio': forms.Select(attrs={
                'class': 'form-control'
            }),
            'complemento': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Dirección completa del establecimiento'
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Teléfono de contacto'
            }),
            'correo': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'correo@empresa.com'
            }),
            'codEstableMH': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Código asignado por Ministerio de Hacienda'
            }),
            'codEstable': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Código de establecimiento (ej: 0001)'
            }),
            'codPuntoVentaMH': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Código punto de venta MH'
            }),
            'codPuntoVenta': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Código punto de venta (ej: 0001)'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Hacer algunos campos opcionales
        self.fields['nombreComercial'].required = False
        self.fields['codEstableMH'].required = False
        self.fields['codPuntoVentaMH'].required = False
        
        # Configurar queryset para municipios
        self.fields['municipio'].queryset = Municipio.objects.select_related('departamento').order_by('departamento__texto', 'texto')

class SucursalForm(forms.ModelForm):
    """Formulario para gestión de sucursales"""
    
    class Meta:
        model = Sucursal
        fields = ['nombre', 'codigo', 'codEstableMH', 'codEstable', 
                 'codPuntoVentaMH', 'codPuntoVenta', 'activa']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre de la sucursal'
            }),
            'codigo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Código único de sucursal'
            }),
            'codEstableMH': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Código asignado por MH'
            }),
            'codEstable': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Código establecimiento (ej: 0001)'
            }),
            'codPuntoVentaMH': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Código punto venta MH'
            }),
            'codPuntoVenta': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Código punto venta (ej: 0001)'
            }),
            'activa': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }