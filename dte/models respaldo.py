import uuid
from decimal import Decimal

from django.db import models
from django.core.validators import (
    MinValueValidator, MaxValueValidator, RegexValidator, EmailValidator, MinLengthValidator
)
from django.core.exceptions import ValidationError

# ——— CATÁLOGOS EXISTENTES ———
class CatalogoBase(models.Model):
    codigo = models.CharField(max_length=4, primary_key=True)
    texto = models.CharField(max_length=150)

    class Meta:
        abstract = True
        ordering = ["codigo"]

    def __str__(self):
        return f"{self.codigo} – {self.texto}"


class AmbienteDestino(CatalogoBase):       # CAT-001
    class Meta:
        db_table = "cat_ambiente_destino"
        verbose_name = "Ambiente de Destino"
        verbose_name_plural = "Ambientes de Destino"


class TipoDocumento(CatalogoBase):         # CAT-002
    class Meta:
        db_table = "cat_tipo_documento"
        verbose_name = "Tipo de Documento"
        verbose_name_plural = "Tipos de Documento"


class ModeloFacturacion(CatalogoBase):     # CAT-003
    class Meta:
        db_table = "cat_modelo_facturacion"
        verbose_name = "Modelo de Facturación"
        verbose_name_plural = "Modelos de Facturación"


class TipoTransmision(CatalogoBase):       # CAT-004
    class Meta:
        db_table = "cat_tipo_transmision"
        verbose_name = "Tipo de Transmisión"
        verbose_name_plural = "Tipos de Transmisión"


class TipoContingencia(CatalogoBase):      # CAT-005
    class Meta:
        db_table = "cat_tipo_contingencia"
        verbose_name = "Tipo de Contingencia"
        verbose_name_plural = "Tipos de Contingencia"


class GeneracionDocumento(CatalogoBase):   # CAT-007
    class Meta:
        db_table = "cat_generacion_documento"
        verbose_name = "Generación de Documento"
        verbose_name_plural = "Generaciones de Documento"


class TipoEstablecimiento(CatalogoBase):   # CAT-009
    class Meta:
        db_table = "cat_tipo_establecimiento"
        verbose_name = "Tipo de Establecimiento"
        verbose_name_plural = "Tipos de Establecimiento"


class TipoServicio(CatalogoBase):          # CAT-010
    class Meta:
        db_table = "cat_tipo_servicio"
        verbose_name = "Tipo de Servicio"
        verbose_name_plural = "Tipos de Servicio"


class TipoItem(CatalogoBase):              # CAT-011
    class Meta:
        db_table = "cat_tipo_item"
        verbose_name = "Tipo de Ítem"
        verbose_name_plural = "Tipos de Ítem"


class Departamento(CatalogoBase):          # CAT-012
    class Meta:
        db_table = "cat_departamento"
        verbose_name = "Departamento"
        verbose_name_plural = "Departamentos"


class Municipio(models.Model):
    departamento = models.ForeignKey(
        Departamento,
        on_delete=models.CASCADE,
        related_name="municipios"
    )
    codigo = models.CharField(max_length=4)
    texto  = models.CharField(max_length=150)

    class Meta:
        unique_together = ("departamento", "codigo")
        ordering = ["departamento__codigo", "codigo"]
        db_table = "cat_municipio"
        verbose_name = "Municipio"
        verbose_name_plural = "Municipios"

    def __str__(self):
        return f"{self.departamento.codigo}-{self.codigo} – {self.texto}"


class UnidadMedida(CatalogoBase):          # CAT-014
    class Meta:
        db_table = "cat_unidad_medida"
        verbose_name = "Unidad de Medida"
        verbose_name_plural = "Unidades de Medida"


class Tributo(models.Model):               # CAT-015 (no abstracto)
    codigo = models.CharField(max_length=2, primary_key=True)
    texto = models.CharField(max_length=150)

    class Meta:
        ordering = ["codigo"]
        db_table = "cat_tributo"
        verbose_name = "Tributo"
        verbose_name_plural = "Tributos"

    def __str__(self):
        return f"{self.codigo} – {self.texto}"


class CondicionOperacion(CatalogoBase):     # CAT-016
    class Meta:
        db_table = "cat_condicion_operacion"
        verbose_name = "Condición de Operación"
        verbose_name_plural = "Condiciones de Operación"


class FormaPago(CatalogoBase):              # CAT-017
    class Meta:
        db_table = "cat_forma_pago"
        verbose_name = "Forma de Pago"
        verbose_name_plural = "Formas de Pago"


class Plazo(CatalogoBase):                  # CAT-018
    class Meta:
        db_table = "cat_plazo"
        verbose_name = "Plazo"
        verbose_name_plural = "Plazos"


class ActividadEconomica(models.Model):     # CAT-019 (no abstracto)
    codigo = models.CharField(max_length=6, primary_key=True)
    texto = models.CharField(max_length=150)

    class Meta:
        ordering = ["codigo"]
        db_table = "cat_actividad_economica"
        verbose_name = "Actividad Económica"
        verbose_name_plural = "Actividades Económicas"

    def __str__(self):
        return f"{self.codigo} – {self.texto}"


class Pais(CatalogoBase):                   # CAT-020
    class Meta:
        db_table = "cat_pais"
        verbose_name = "País"
        verbose_name_plural = "Paises"


class OtroDocumentoAsociado(CatalogoBase):  # CAT-021
    class Meta:
        db_table = "cat_otro_documento_asociado"
        verbose_name = "Otro Documento Asociado"
        verbose_name_plural = "Otros Documentos Asociados"


class TipoDocReceptor(CatalogoBase):        # CAT-022
    class Meta:
        db_table = "cat_tipo_doc_receptor"
        verbose_name = "Tipo de Documento Receptor"
        verbose_name_plural = "Tipos de Documento Receptor"


class DocumentoContingencia(CatalogoBase):  # CAT-023
    class Meta:
        db_table = "cat_documento_contingencia"
        verbose_name = "Documento de Contingencia"
        verbose_name_plural = "Documentos de Contingencia"


class TipoInvalidacion(CatalogoBase):       # CAT-024
    class Meta:
        db_table = "cat_tipo_invalidacion"
        verbose_name = "Tipo de Invalidación"
        verbose_name_plural = "Tipos de Invalidación"


# --------------- MODELOS PRINCIPALES ---------------

class Identificacion(models.Model):
    version = models.IntegerField(default=1)
    ambiente = models.ForeignKey(
        AmbienteDestino,
        on_delete=models.PROTECT,
        verbose_name="Ambiente de Destino"
    )
    tipoDte = models.ForeignKey(
        TipoDocumento,
        on_delete=models.PROTECT,
        verbose_name="Tipo de Documento"
    )
    numeroControl = models.CharField(
        max_length=31,
        unique=True,
        help_text="Formato: DTE-01-XXXXXXXX-XXXXXXXXXXXXXXX",
        validators=[
            RegexValidator(
                regex=r"^DTE-01-[A-Z0-9]{8}-[0-9]{15}$",
                message="Debe tener formato DTE-01-XXXXXXXX-XXXXXXXXXXXXXXX"
            )
        ]
    )
    codigoGeneracion = models.CharField(
        max_length=36,
        help_text="UUID: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX",
        validators=[
            RegexValidator(
                regex=r"^[A-F0-9]{8}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{12}$",
                message="Debe ser un UUID en mayúsculas "
                        "(ej. 1234ABCD-1234-1234-1234-1234567890AB)"
            )
        ]
    )
    tipoModelo = models.ForeignKey(
        ModeloFacturacion,
        on_delete=models.PROTECT,
        verbose_name="Modelo de Facturación"
    )
    tipoOperacion = models.ForeignKey(
        TipoTransmision,
        on_delete=models.PROTECT,
        verbose_name="Tipo de Transmisión"
    )
    tipoContingencia = models.ForeignKey(
        TipoContingencia,
        on_delete=models.PROTECT,
        verbose_name="Tipo de Contingencia",
        null=True,
        blank=True
    )
    motivoContin = models.CharField(
        max_length=150,
        null=True,
        blank=True,
        help_text="Motivo de Contingencia",
        validators=[MinLengthValidator(5)] 
    )
    fecEmi = models.DateField(verbose_name="Fecha de Emisión")
    horEmi = models.TimeField(
        verbose_name="Hora de Emisión",
        validators=[
            RegexValidator(
                regex=r"^(0[0-9]|1[0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]$",
                message="Debe tener formato HH:MM:SS (24 horas)."
            )
        ]
    )
    tipoMoneda = models.CharField(
        max_length=3,
        default="USD",
        help_text="Tipo de Moneda"
    )

    class Meta:
        db_table = "dte_identificacion"
        verbose_name = "Identificación"
        verbose_name_plural = "Identificaciones"

    def __str__(self):
        return self.numeroControl

    def clean(self):
        from django.core.exceptions import ValidationError

        # Si tipoOperacion = '01' (Transmisión Normal), modelo debe ser '1' y sin contingencia
        if self.tipoOperacion.codigo == "01":
            expected_modelo = ModeloFacturacion.objects.filter(codigo="1").first()
            if self.tipoModelo != expected_modelo:
                raise ValidationError("Para transmisión normal (tipoOperacion=01), "
                                      "tipoModelo debe ser '1'.")
            if self.tipoContingencia or self.motivoContin:
                raise ValidationError("Para transmisión normal, no debe haber "
                                      "tipoContingencia ni motivoContin.")
        # Si tipoOperacion = '02' (Contingencia), tipoModelo debe ser '2'
        if self.tipoOperacion.codigo == "02":
            expected_modelo = ModeloFacturacion.objects.filter(codigo="2").first()
            if self.tipoModelo != expected_modelo:
                raise ValidationError("Para transmisión por contingencia "
                                      "(tipoOperacion=02), tipoModelo debe ser '2'.")


class DocumentoRelacionado(models.Model):
    factura = models.ForeignKey(
        'FacturaElectronica',
        on_delete=models.CASCADE,
        related_name='documentos_relacionados'
    )
    tipoDocumento = models.ForeignKey(
        TipoDocumento,
        on_delete=models.PROTECT,
        verbose_name="Tipo de Documento Relacionado"
    )
    tipoGeneracion = models.ForeignKey(
        GeneracionDocumento,
        on_delete=models.PROTECT,
        verbose_name="Tipo de Generación"
    )
    numeroDocumento = models.CharField(
        max_length=36,
        help_text="Si tipoGeneracion=2 debe ser UUID; "
                  "si tipoGeneracion=1, 1–20 caracteres"
    )
    fechaEmision = models.DateField(verbose_name="Fecha de Emisión Relacionada")

    class Meta:
        db_table = "dte_documento_relacionado"
        verbose_name = "Documento Relacionado"
        verbose_name_plural = "Documentos Relacionados"

    def __str__(self):
        return f"{self.factura.identificacion.numeroControl} – {self.tipoDocumento.codigo} – {self.numeroDocumento}"

    def clean(self):
        from django.core.exceptions import ValidationError
        import re

        if self.tipoGeneracion.codigo == "2":
            pattern = re.compile(
                r"^[A-F0-9]{8}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{12}$"
            )
            if not pattern.match(self.numeroDocumento):
                raise ValidationError(
                    "numeroDocumento debe ser UUID cuando tipoGeneracion=2."
                )
        if self.tipoGeneracion.codigo == "1":
            if not (1 <= len(self.numeroDocumento) <= 20):
                raise ValidationError(
                    "numeroDocumento debe tener entre 1 y 20 "
                    "caracteres cuando tipoGeneracion=1."
                )


class Emisor(models.Model):
    nit = models.CharField(
        max_length=14,
        validators=[
            RegexValidator(
                regex=r"^(\d{9}|\d{14})$",
                message="NIT debe tener 9 o 14 dígitos."
            )
        ]
    )
    nrc = models.CharField(
        max_length=8,
        validators=[
            RegexValidator(
                regex=r"^\d{2,8}$",
                message="NRC debe tener entre 2 y 8 dígitos."
            )
        ]
    )
    nombre = models.CharField(max_length=250)
    codActividad = models.ForeignKey(
        ActividadEconomica,
        on_delete=models.PROTECT,
        verbose_name="Código de Actividad Económica"
    )
    descActividad = models.CharField(
        max_length=150,
        validators=[MinLengthValidator(5)]  
    )
    nombreComercial = models.CharField(
        max_length=150, 
        null=True, 
        blank=True,
        validators=[MinLengthValidator(5)] 
    )
    tipoEstablecimiento = models.ForeignKey(
        TipoEstablecimiento,
        on_delete=models.PROTECT
    )

    departamento = models.ForeignKey(
        Departamento,
        on_delete=models.PROTECT
    )
    municipio = models.ForeignKey(
        Municipio,
        on_delete=models.PROTECT
    )
    complemento = models.CharField(max_length=200)

    telefono = models.CharField(
        max_length=30,
        validators=[
            RegexValidator(
                regex=r"^\+?[\d\s\-]{8,30}$",
                message="Teléfono inválido."
            )
        ]
    )
    correo = models.EmailField(
        max_length=100,
        validators=[EmailValidator(message="Correo inválido.")]
    )
    codEstableMH = models.CharField(max_length=4, null=True, blank=True)
    codEstable = models.CharField(max_length=4, null=True, blank=True)
    codPuntoVentaMH = models.CharField(max_length=4, null=True, blank=True)
    codPuntoVenta = models.CharField(max_length=15, null=True, blank=True)

    class Meta:
        db_table = "dte_emisor"
        verbose_name = "Emisor"
        verbose_name_plural = "Emisores"

    def __str__(self):
        return self.nombre
    
    def clean(self):
        from django.core.exceptions import ValidationError
        
        # Validación de relación departamento-municipio
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
        
        depto_code = self.departamento.codigo
        muni_code = self.municipio.codigo
        
        if depto_code in DEPARTAMENTO_MUNICIPIO_MAP:
            allowed_municipios = DEPARTAMENTO_MUNICIPIO_MAP[depto_code]
            if muni_code not in allowed_municipios:
                raise ValidationError(
                    f"Municipio {muni_code} no válido para el departamento {depto_code}"
                )
    



class Receptor(models.Model):
    tipoDocumento = models.ForeignKey(
        TipoDocReceptor,
        on_delete=models.PROTECT,
        verbose_name="Tipo de Documento Receptor",
        null=True,
        blank=True
    )
    numDocumento = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text="Si tipoDocumento=36 debe tener 9 o 14 dígitos; "
                  "si tipoDocumento=13, patrón XXXXXXXX-X"
    )
    nrc = models.CharField(
        max_length=8,
        null=True,
        blank=True,
        validators=[
            RegexValidator(
                regex=r"^\d{2,8}$",
                message="NRC debe tener entre 2 y 8 dígitos."
            )
        ]
    )
    nombre = models.CharField(max_length=250, null=True, blank=True)
    codActividad = models.ForeignKey(
        ActividadEconomica,
        on_delete=models.PROTECT,
        verbose_name="Código de Actividad Económica Receptor",
        null=True,
        blank=True
    )
    descActividad = models.CharField(max_length=150, null=True, blank=True)

    departamento = models.ForeignKey(
        Departamento,
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )
    municipio = models.ForeignKey(
        Municipio,
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )
    complemento = models.CharField(max_length=200, null=True, blank=True)

    telefono = models.CharField(
        max_length=30,
        null=True,
        blank=True,
        validators=[
            RegexValidator(
                regex=r"^\+?[\d\s\-]{8,30}$",
                message="Teléfono inválido."
            )
        ]
    )
    correo = models.EmailField(
        max_length=100,
        null=True,
        blank=True,
        validators=[EmailValidator(message="Correo inválido.")]
    )

    class Meta:
        db_table = "dte_receptor"
        verbose_name = "Receptor"
        verbose_name_plural = "Receptores"

    def __str__(self):
        return self.nombre or f"{self.numDocumento or ''}".strip() or "Receptor sin nombre"

    def clean(self):
        from django.core.exceptions import ValidationError
        import re

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
        
        depto_code = self.departamento.codigo
        muni_code = self.municipio.codigo
        
        if depto_code in DEPARTAMENTO_MUNICIPIO_MAP:
            allowed_municipios = DEPARTAMENTO_MUNICIPIO_MAP[depto_code]
            if muni_code not in allowed_municipios:
                raise ValidationError(
                    f"Municipio {muni_code} no válido para el departamento {depto_code}"
                )

        if self.tipoDocumento and self.tipoDocumento.codigo == "36":
            num = (self.numDocumento or "").strip()
            if not re.match(r"^(\d{9}|\d{14})$", num):
                raise ValidationError(
            "Para tipoDocumento=36, numDocumento debe tener 9 o 14 dígitos."
                 )

        if self.tipoDocumento and self.tipoDocumento.codigo == "13":
             num = (self.numDocumento or "").strip()
             if not re.match(r"^[0-9]{8}-[0-9]$", num):
                raise ValidationError(
                "Para tipoDocumento=13, numDocumento debe seguir el patrón XXXXXXXX-X."
             )
        if self.tipoDocumento and self.tipoDocumento.codigo != "36" and self.nrc:
            raise ValidationError("Si tipoDocumento no es 36, nrc debe ser null.")
        
        if any([self.departamento, self.municipio, self.complemento]):
            if not all([self.departamento, self.municipio, self.complemento]):
                raise ValidationError(
                    "La dirección debe estar completa si se proporciona"
                )


class OtrosDocumentos(models.Model):
    factura = models.ForeignKey(
        'FacturaElectronica',
        on_delete=models.CASCADE,
        related_name='otros_documentos'
    )
    codDocAsociado = models.ForeignKey(
        OtroDocumentoAsociado,
        on_delete=models.PROTECT
    )
    descDocumento = models.CharField(max_length=100, null=True, blank=True)
    detalleDocumento = models.CharField(max_length=300, null=True, blank=True)

    medico_nombre = models.CharField(max_length=100, null=True, blank=True)
    medico_nit = models.CharField(
        max_length=14,
        null=True,
        blank=True,
        validators=[
            RegexValidator(
                regex=r"^(\d{9}|\d{14})$",
                message="NIT debe tener 9 o 14 dígitos."
            )
        ]
    )
    medico_docIdentificacion = models.CharField(max_length=25, null=True, blank=True)
    medico_tipoServicio = models.ForeignKey(
        TipoServicio,
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )

    class Meta:
        db_table = "dte_otros_documentos"
        verbose_name = "Otros Documentos"
        verbose_name_plural = "Otros Documentos"

    def __str__(self):
        return f"{self.factura.identificacion.numeroControl} – {self.codDocAsociado.codigo}"

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.codDocAsociado.codigo == "3":
            if not all([
                self.medico_nombre,
                (self.medico_nit or self.medico_docIdentificacion),
                self.medico_tipoServicio
            ]):
                raise ValidationError(
                    "Para codDocAsociado=3, debe completar todos los campos de médico."
                )
            if self.descDocumento or self.detalleDocumento:
                raise ValidationError(
                    "Para codDocAsociado=3, descDocumento y detalleDocumento deben ser null."
                )
        else:
            if not (self.descDocumento and self.detalleDocumento):
                raise ValidationError(
                    "Para codDocAsociado distinto de 3, descDocumento y detalleDocumento son obligatorios."
                )
            if any([
                self.medico_nombre, self.medico_nit,
                self.medico_docIdentificacion, self.medico_tipoServicio
            ]):
                raise ValidationError(
                    "Para codDocAsociado distinto de 3, todos los campos de médico deben ser null."
                )


class VentaTercero(models.Model):
    factura = models.OneToOneField(
        'FacturaElectronica',
        on_delete=models.CASCADE,
        related_name='venta_tercero'
    )
    nit = models.CharField(
        max_length=14,
        validators=[
            RegexValidator(
                regex=r"^(\d{9}|\d{14})$",
                message="NIT de tercero debe tener 9 o 14 dígitos."
            )
        ]
    )
    nombre = models.CharField(max_length=250)

    class Meta:
        db_table = "dte_venta_tercero"
        verbose_name = "Venta Tercero"
        verbose_name_plural = "Ventas Terceros"

    def __str__(self):
        return f"{self.nombre} ({self.nit})"


class CuerpoDocumentoItem(models.Model):
    factura = models.ForeignKey(
        'FacturaElectronica',
        on_delete=models.CASCADE,
        related_name='cuerpo_documento'
    )
    numItem = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(2000)]
    )
    tipoItem = models.ForeignKey(
        TipoItem,
        on_delete=models.PROTECT,
        verbose_name="Tipo de Ítem"
    )
    numeroDocumento = models.CharField(max_length=36, null=True, blank=True)
    cantidad = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.00")),
            MaxValueValidator(Decimal("99999999999.99"))
        ]
    )
    codigo = models.CharField(max_length=25, null=True, blank=True)
    codTributo = models.ForeignKey(
        Tributo,
        on_delete=models.PROTECT,
        verbose_name="Código de Tributo",
        null=True,
        blank=True
    )
    uniMedida = models.ForeignKey(
        UnidadMedida,
        on_delete=models.PROTECT,
        verbose_name="Unidad de Medida"
    )
    descripcion = models.CharField(max_length=1000)
    precioUni = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.00")),
            MaxValueValidator(Decimal("99999999999.99"))
        ]
    )
    montoDescu = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.00")),
            MaxValueValidator(Decimal("99999999999.99"))
        ]
    )
    ventaNoSuj = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.00")),
            MaxValueValidator(Decimal("99999999999.99"))
        ]
    )
    ventaExenta = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.00")),
            MaxValueValidator(Decimal("99999999999.99"))
        ]
    )
    ventaGravada = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.00")),
            MaxValueValidator(Decimal("99999999999.99"))
        ]
    )
    tributos = models.ManyToManyField(
        Tributo,
        blank=True,
        related_name="items_cuerpo"
    )
    psv = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.00")),
            MaxValueValidator(Decimal("99999999999.99"))
        ]
    )
    noGravado = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("-99999999999.99")),
            MaxValueValidator(Decimal("99999999999.99"))
        ]
    )
    ivaItem = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.00")),
            MaxValueValidator(Decimal("99999999999.99"))
        ]
    )

    class Meta:
        db_table = "dte_cuerpo_documento_item"
        verbose_name = "Cuerpo Documento Ítem"
        verbose_name_plural = "Cuerpo Documento Ítems"

 

    def clean(self):
        # 0) Si aún no hay factura asignada, saltar todas las validaciones
        if self.factura_id is None:
            return

        # 1) Validaciones generales
        if self.ventaGravada <= Decimal("0.00"):
            if self.tributos.exists():
                raise ValidationError("Si ventaGravada ≤ 0, tributos debe estar vacío.")
            if self.ivaItem != Decimal("0.00"):
                raise ValidationError("Si ventaGravada ≤ 0, ivaItem debe ser 0.00.")

        # 2) Validaciones según tipoItem
        if self.tipoItem.codigo == "4":
            # 2.1) uniMedida debe ser "99"
            if self.uniMedida.codigo != "99":
                raise ValidationError("Para tipoItem=4, uniMedida debe ser '99'.")
            # 2.2) tributos vacío
            if self.tributos.exists():
                raise ValidationError("Para tipoItem=4, tributos debe estar vacío.")
            # 2.3) codTributo no puede ser null
            if self.codTributo is None:
                raise ValidationError("Para tipoItem=4, codTributo debe estar presente.")
        else:
            # tipoItem ≠ 4
            # 2.4) codTributo debe ser null
            if self.codTributo is not None:
                raise ValidationError("Para tipoItem≠4, codTributo debe quedar vacío.")
            # 2.5) al menos un tributo
            if not self.tributos.exists():
                raise ValidationError("Para tipoItem≠4, debe especificar al menos un tributo.")
            # 2.6) códigos permitidos
            ALLOWED_TRIBUTO_CODES = [
                "20","C3","59","71","D1","C8","D5","D4","C5","C6","C7",
                "19","28","31","32","33","34","35","36","37","38","39",
                "42","43","44","50","51","52","53","54","55","58","77",
                "78","79","85","86","91","92","A1","A5","A7","A9"
            ]
            invalid = self.tributos.exclude(codigo__in=ALLOWED_TRIBUTO_CODES)
            if invalid.exists():
                codes = ", ".join(invalid.values_list('codigo', flat=True))
                raise ValidationError(f"Códigos de tributo no permitidos: {codes}")

    def __str__(self):
        # Mostrar número de control sólo si ya existe factura
        if self.factura_id:
            control = self.factura.identificacion.numeroControl
        else:
            control = "(sin factura)"
        return f"{control} – Ítem {self.numItem}"


class Resumen(models.Model):
    factura = models.OneToOneField(
        'FacturaElectronica',
        on_delete=models.CASCADE,
        related_name='resumen'
    )
    totalNoSuj = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))]
    )
    totalExenta = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))]
    )
    totalGravada = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))]
    )
    subTotalVentas = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))]
    )
    descuNoSuj = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))]
    )
    descuExenta = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))]
    )
    descuGravada = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))]
    )
    porcentajeDescuento = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.00")),
            MaxValueValidator(Decimal("100.00"))
        ]
    )
    totalDescu = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))]
    )
    subTotal = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))]
    )
    ivaRete1 = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))]
    )
    reteRenta = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))]
    )
    montoTotalOperacion = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))]
    )
    totalNoGravado = models.DecimalField(
        max_digits=20,
        decimal_places=2
    )
    totalPagar = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))]
    )
    totalLetras = models.CharField(max_length=200)
    totalIva = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))]
    )
    saldoFavor = models.DecimalField(
        max_digits=20,
        decimal_places=2
    )
    condicionOperacion = models.ForeignKey(
        CondicionOperacion,
        on_delete=models.PROTECT
    )
    numPagoElectronico = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        db_table = "dte_resumen"
        verbose_name = "Resumen"
        verbose_name_plural = "Resúmenes"

    def __str__(self):
        return f"{self.factura.identificacion.numeroControl} – Resumen"

    # … definición de campos …

    def clean(self):
        # Interpretar None como 0.00 para evitar TypeError
        tg = self.totalGravada if self.totalGravada is not None else Decimal("0.00")
        iva_r1 = self.ivaRete1 if self.ivaRete1 is not None else Decimal("0.00")

        if tg <= Decimal("0.00") and iva_r1 != Decimal("0.00"):
            raise ValidationError("Si totalGravada <= 0, ivaRete1 debe ser 0.00.")


class TributoResumen(models.Model):
    resumen = models.ForeignKey(
        Resumen,
        on_delete=models.CASCADE,
        related_name='tributos'
    )
    codigo = models.ForeignKey(
        Tributo,
        on_delete=models.PROTECT
    )
    descripcion = models.CharField(max_length=150,  blank=True)
    valor = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))]
    )

    class Meta:
        db_table = "dte_tributo_resumen"
        verbose_name = "Tributo Resumen"
        verbose_name_plural = "Tributos Resumen"

    def __str__(self):
        return f"{self.resumen.factura.identificacion.numeroControl} – {self.codigo.codigo}"

    def save(self, *args, **kwargs):
        if self.codigo and not self.descripcion:
            self.descripcion = self.codigo.texto
        super().save(*args, **kwargs)


class Pago(models.Model):
    resumen = models.ForeignKey(
        Resumen,
        on_delete=models.CASCADE,
        related_name='pagos'
    )
    codigo = models.ForeignKey(
        FormaPago,
        on_delete=models.PROTECT
    )
    montoPago = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))]
    )
    referencia = models.CharField(max_length=50, null=True, blank=True)
    plazo = models.ForeignKey(
        Plazo,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        validators=[RegexValidator(  # Añadido validador de formato
            regex=r"^0[1-3]$",
            message="Plazo debe tener formato 01, 02 o 03"
        )]
    )
    periodo = models.SmallIntegerField(null=True, blank=True)

    class Meta:
        db_table = "dte_pago"
        verbose_name = "Pago"
        verbose_name_plural = "Pagos"

    def __str__(self):
        return f"{self.resumen.factura.identificacion.numeroControl} – Pago {self.montoPago}"


class Extension(models.Model):
    factura = models.OneToOneField(
        'FacturaElectronica',
        on_delete=models.CASCADE,
        related_name='extension'
    )
    nombEntrega = models.CharField(max_length=100, null=True, blank=True)
    docuEntrega = models.CharField(max_length=25, null=True, blank=True)
    nombRecibe = models.CharField(max_length=100, null=True, blank=True)
    docuRecibe = models.CharField(max_length=25, null=True, blank=True)
    observaciones = models.TextField(null=True, blank=True, max_length=3000)
    placaVehiculo = models.CharField(max_length=10, null=True, blank=True)

    class Meta:
        db_table = "dte_extension"
        verbose_name = "Extensión"
        verbose_name_plural = "Extensiones"

    def __str__(self):
        return f"{self.factura.identificacion.numeroControl} – Extensión"


class ApendiceItem(models.Model):
    factura = models.ForeignKey(
        'FacturaElectronica',
        on_delete=models.CASCADE,
        related_name='apendice'
    )
    campo = models.CharField(max_length=25)
    etiqueta = models.CharField(max_length=50)
    valor = models.CharField(max_length=150)

    class Meta:
        db_table = "dte_apendice_item"
        verbose_name = "Apéndice Ítem"
        verbose_name_plural = "Apéndice Ítems"

    def __str__(self):
        return f"{self.factura.identificacion.numeroControl} – {self.campo}"


class FacturaElectronica(models.Model):
    identificacion = models.OneToOneField(
        Identificacion,
        on_delete=models.CASCADE,
        related_name='+'
    )
    emisor = models.ForeignKey(
        Emisor,
        on_delete=models.CASCADE,
        related_name='facturas' 
    )
    receptor = models.ForeignKey(
        Receptor,
        on_delete=models.CASCADE,
        related_name='facturas'
    )

    class Meta:
        db_table = "dte_factura_electronica"
        verbose_name = "Factura Electrónica"
        verbose_name_plural = "Facturas Electrónicas"

    def __str__(self):
        return self.identificacion.numeroControl

    def to_json(self):
        """
        Construye un dict válido para serializar a JSON que cumpla con el esquema.
        Redondea todos los valores numéricos a dos decimales.
        """
        def rd(x):
            return round(float(x), 2)

        data = {
            "identificacion": {
                "version": self.identificacion.version,
                "ambiente": self.identificacion.ambiente.codigo,
                "tipoDte": self.identificacion.tipoDte.codigo,
                "numeroControl": self.identificacion.numeroControl,
                "codigoGeneracion": self.identificacion.codigoGeneracion,
                "tipoModelo": int(self.identificacion.tipoModelo.codigo),
                "tipoOperacion": int(self.identificacion.tipoOperacion.codigo),
                "tipoContingencia": int(self.identificacion.tipoContingencia.codigo)
                                   if self.identificacion.tipoContingencia else None,
                "motivoContin": self.identificacion.motivoContin,
                "fecEmi": self.identificacion.fecEmi.isoformat(),
                "horEmi": self.identificacion.horEmi.strftime("%H:%M:%S"),
                "tipoMoneda": self.identificacion.tipoMoneda,
            },
            "documentoRelacionado": [
                {
                    "tipoDocumento": dr.tipoDocumento.codigo,
                    "tipoGeneracion": int(dr.tipoGeneracion.codigo),
                    "numeroDocumento": dr.numeroDocumento,
                    "fechaEmision": dr.fechaEmision.isoformat(),
                }
                for dr in self.documentos_relacionados.all()
            ],
            "emisor": {
                "nit": self.emisor.nit,
                "nrc": self.emisor.nrc,
                "nombre": self.emisor.nombre,
                "codActividad": self.emisor.codActividad.codigo,
                "descActividad": self.emisor.descActividad,
                "nombreComercial": self.emisor.nombreComercial,
                "tipoEstablecimiento": self.emisor.tipoEstablecimiento.codigo,
                "direccion": {
                    "departamento": self.emisor.departamento.codigo,
                    "municipio": self.emisor.municipio.codigo,
                    "complemento": self.emisor.complemento,
                },
                "telefono": self.emisor.telefono,
                "correo": self.emisor.correo,
                "codEstableMH": self.emisor.codEstableMH,
                "codEstable": self.emisor.codEstable,
                "codPuntoVentaMH": self.emisor.codPuntoVentaMH,
                "codPuntoVenta": self.emisor.codPuntoVenta,
            },
            "receptor": {
                "tipoDocumento": self.receptor.tipoDocumento.codigo
                                 if self.receptor.tipoDocumento else None,
                "numDocumento": self.receptor.numDocumento,
                "nrc": self.receptor.nrc,
                "nombre": self.receptor.nombre,
                "codActividad": self.receptor.codActividad.codigo
                                if self.receptor.codActividad else None,
                "descActividad": self.receptor.descActividad,
                "direccion": {
                    "departamento": self.receptor.departamento.codigo
                                   if self.receptor.departamento else None,
                    "municipio": self.receptor.municipio.codigo
                                 if self.receptor.municipio else None,
                    "complemento": self.receptor.complemento,
                },
                "telefono": self.receptor.telefono,
                "correo": self.receptor.correo,
            },
            "otrosDocumentos": [
                {
                    "codDocAsociado": od.codDocAsociado.codigo,
                    "descDocumento": od.descDocumento,
                    "detalleDocumento": od.detalleDocumento,
                    "medico": {
                        "nombre": od.medico_nombre,
                        "nit": od.medico_nit,
                        "docIdentificacion": od.medico_docIdentificacion,
                        "tipoServicio": int(od.medico_tipoServicio.codigo)
                                        if od.medico_tipoServicio else None,
                    } if od.codDocAsociado.codigo == "3" else None,
                }
                for od in self.otros_documentos.all()
            ],
            "ventaTercero": {
                "nit": self.venta_tercero.nit,
                "nombre": self.venta_tercero.nombre
            } if hasattr(self, 'venta_tercero') and self.venta_tercero else None,
            "cuerpoDocumento": [
                {
                    "numItem": it.numItem,
                    "tipoItem": int(it.tipoItem.codigo),
                    "numeroDocumento": it.numeroDocumento,
                    "cantidad": rd(it.cantidad),
                    "codigo": it.codigo,
                    "codTributo": it.codTributo.codigo if it.codTributo else None,
                    "uniMedida": int(it.uniMedida.codigo),
                    "descripcion": it.descripcion,
                    "precioUni": rd(it.precioUni),
                    "montoDescu": rd(it.montoDescu),
                    "ventaNoSuj": rd(it.ventaNoSuj),
                    "ventaExenta": rd(it.ventaExenta),
                    "ventaGravada": rd(it.ventaGravada),
                    "tributos": [t.codigo for t in it.tributos.all()]
                                if it.tributos.exists() else None,
                    "psv": rd(it.psv),
                    "noGravado": rd(it.noGravado),
                    "ivaItem": rd(it.ivaItem),
                }
                for it in self.cuerpo_documento.all()
            ],
            "resumen": {
                "totalNoSuj": rd(self.resumen.totalNoSuj),
                "totalExenta": rd(self.resumen.totalExenta),
                "totalGravada": rd(self.resumen.totalGravada),
                "subTotalVentas": rd(self.resumen.subTotalVentas),
                "descuNoSuj": rd(self.resumen.descuNoSuj),
                "descuExenta": rd(self.resumen.descuExenta),
                "descuGravada": rd(self.resumen.descuGravada),
                "porcentajeDescuento": rd(self.resumen.porcentajeDescuento),
                "totalDescu": rd(self.resumen.totalDescu),
                "tributos": [
                    {
                        "codigo": tr.codigo.codigo,
                        "descripcion": tr.descripcion,
                        "valor": rd(tr.valor)
                    } for tr in self.resumen.tributos.all()
                ] or None,
                "subTotal": rd(self.resumen.subTotal),
                "ivaRete1": rd(self.resumen.ivaRete1),
                "reteRenta": rd(self.resumen.reteRenta),
                "montoTotalOperacion": rd(self.resumen.montoTotalOperacion),
                "totalNoGravado": rd(self.resumen.totalNoGravado),
                "totalPagar": rd(self.resumen.totalPagar),
                "totalLetras": self.resumen.totalLetras,
                "totalIva": rd(self.resumen.totalIva),
                "saldoFavor": rd(self.resumen.saldoFavor),
                "condicionOperacion": int(self.resumen.condicionOperacion.codigo),
                "pagos": [
                    {
                        "codigo": pg.codigo.codigo,
                        "montoPago": rd(pg.montoPago),
                        "referencia": pg.referencia,
                        "plazo": pg.plazo.codigo if pg.plazo else None,
                        "periodo": pg.periodo,
                    } for pg in self.resumen.pagos.all()
                ] if self.resumen.pagos.exists() else None,
                "numPagoElectronico": self.resumen.numPagoElectronico,
            },
            "extension": {
                "nombEntrega": self.extension.nombEntrega,
                "docuEntrega": self.extension.docuEntrega,
                "nombRecibe": self.extension.nombRecibe,
                "docuRecibe": self.extension.docuRecibe,
                "observaciones": self.extension.observaciones,
                "placaVehiculo": self.extension.placaVehiculo,
            } if hasattr(self, 'extension') else None,
            "apendice": [
                {
                    "campo": ap.campo,
                    "etiqueta": ap.etiqueta,
                    "valor": ap.valor,
                }
                for ap in self.apendice.all()
            ],
        }

        if self.resumen.montoTotalOperacion >= Decimal("1095.00"):
            if not (self.receptor.tipoDocumento and
                    self.receptor.numDocumento and
                    self.receptor.nombre):
                raise ValueError(
                    "Para montoTotalOperacion >= 1095.00, el receptor debe "
                    "tener tipoDocumento, numDocumento y nombre."
                )

        return data
