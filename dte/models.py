import uuid
from decimal import Decimal, ROUND_HALF_UP

from django.db import models
from django.core.validators import (
    MinValueValidator, MaxValueValidator, RegexValidator, EmailValidator, MinLengthValidator
)
from django.core.exceptions import ValidationError
import re
from django.conf import settings

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
        help_text="Formato: DTE-01-XXXXXXXX-XXXXXXXXXXXXXXX o DTE-03-XXXXXXXX-XXXXXXXXXXXXXXX"
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

# dte/models.py - Método clean() completo corregido en la clase Identificacion

    def clean(self):
        from django.core.exceptions import ValidationError
        import re

        # Validar formato del número de control según tipo de documento
        if self.tipoDte and self.numeroControl:
            if self.tipoDte.codigo == "01":  # Factura
                pattern = r"^DTE-01-[A-Z0-9]{8}-[0-9]{15}$"
                if not re.match(pattern, self.numeroControl):
                    raise ValidationError("Para Factura, numeroControl debe tener formato DTE-01-XXXXXXXX-XXXXXXXXXXXXXXX")
            elif self.tipoDte.codigo == "03":  # CCF
                pattern = r"^DTE-03-[A-Z0-9]{8}-[0-9]{15}$"
                if not re.match(pattern, self.numeroControl):
                    raise ValidationError("Para CCF, numeroControl debe tener formato DTE-03-XXXXXXXX-XXXXXXXXXXXXXXX")
            elif self.tipoDte.codigo == "14":  # NUEVO - FSE
                pattern = r"^DTE-14-[A-Z0-9]{8}-[0-9]{15}$"
                if not re.match(pattern, self.numeroControl):
                    raise ValidationError("Para FSE, numeroControl debe tener formato DTE-14-XXXXXXXX-XXXXXXXXXXXXXXX")
        # Validar versión según tipo de documento
        if self.tipoDte:
            if self.tipoDte.codigo == "01" and self.version != 1:
                raise ValidationError("Para Factura (tipoDte=01), version debe ser 1")
            elif self.tipoDte.codigo == "03" and self.version != 3:
                raise ValidationError("Para CCF (tipoDte=03), version debe ser 3")
            elif self.tipoDte.codigo == "14" and self.version != 1:  # NUEVO - FSE
                raise ValidationError("Para FSE (tipoDte=14), version debe ser 1")

        # Si tipoOperacion = '01' (Transmisión Normal), modelo debe ser '1' y sin contingencia
        if self.tipoOperacion and self.tipoOperacion.codigo == "01":
            expected_modelo = ModeloFacturacion.objects.filter(codigo="1").first()
            if self.tipoModelo != expected_modelo:
                raise ValidationError("Para transmisión normal (tipoOperacion=01), "
                                    "tipoModelo debe ser '1'.")
            if self.tipoContingencia or self.motivoContin:
                raise ValidationError("Para transmisión normal, no debe haber "
                                    "tipoContingencia ni motivoContin.")
        
        # Si tipoOperacion = '02' (Contingencia), tipoModelo debe ser '2'
        if self.tipoOperacion and self.tipoOperacion.codigo == "02":
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
                regex=r"^[0-9]{1,8}$",
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
                regex=r"^\d{1,8}$",
                message="NRC debe tener entre 1 y 8 dígitos."
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
        
        if self.departamento and self.municipio:
            try:
                depto_code = self.departamento.codigo
                muni_code = self.municipio.codigo
                
                if depto_code in DEPARTAMENTO_MUNICIPIO_MAP:
                    allowed_municipios = DEPARTAMENTO_MUNICIPIO_MAP[depto_code]
                    if muni_code not in allowed_municipios:
                        raise ValidationError(
                            f"Municipio {muni_code} no válido para el departamento {depto_code}"
                        )
            except AttributeError:
                # Si departamento o municipio no tienen el atributo codigo
                raise ValidationError(
                    "Error en la validación de ubicación. Verifique departamento y municipio."
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

    # En models.py - Agregar este campo al modelo CuerpoDocumentoItem
    descuentoAplicado = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[
            MinValueValidator(Decimal("0.00")),
            MaxValueValidator(Decimal("100.00"))
        ],
        help_text="Descuento porcentual aplicado al calcular el precio unitario"
    )

    # En models.py - Agregar este campo al modelo CuerpoDocumentoItem
    precioIndiceUsado = models.IntegerField(
        choices=[(1, 'Precio 1'), (2, 'Precio 2'), (3, 'Precio 3'), (4, 'Precio 4')],
        default=1,
        help_text="Índice del precio utilizado del producto (1-4)"
    )

    class Meta:
        db_table = "dte_cuerpo_documento_item"
        verbose_name = "Cuerpo Documento Ítem"
        verbose_name_plural = "Cuerpo Documento Ítems"

    def get_cantidad_acreditada(self):
        """
        Obtiene la cantidad total ya acreditada en Notas de Crédito
        Solo cuenta NC con estado ACEPTADO o ACEPTADO_CON_OBSERVACIONES
        """
        from django.db.models import Sum
        
        total_acreditado = self.notas_credito_aplicadas.filter(
            nota_credito__estado_hacienda__in=['ACEPTADO', 'ACEPTADO CON OBSERVACIONES']
        ).aggregate(
            total=Sum('cantidad_acreditada')
        )['total'] or Decimal('0.00')
        
        return total_acreditado
    
    def get_cantidad_disponible_para_nc(self):
        """
        Obtiene la cantidad disponible para futuras Notas de Crédito
        """
        return self.cantidad - self.get_cantidad_acreditada()
    
    def puede_ser_acreditado(self):
        """
        Verifica si este item puede ser usado en una nueva NC
        """
        return self.get_cantidad_disponible_para_nc() > Decimal('0.00')
    
    def get_notas_credito_aplicadas(self):
        """
        Obtiene las NC que han usado este item
        """
        return self.notas_credito_aplicadas.filter(
            nota_credito__estado_hacienda__in=['ACEPTADO', 'ACEPTADO CON OBSERVACIONES']
        ).select_related('nota_credito__identificacion')
    
    

 

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
        validators=[MinValueValidator(Decimal("0.00"))],
        null=True, 
        blank=True
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
    ivaPerci1 = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        verbose_name="IVA Percibido",
        validators=[MinValueValidator(Decimal("0.00"))],
        null=True,
        blank=True
    )

    # CAMPOS ESPECÍFICOS PARA FSE (solo los que NO existen)
    total_compra = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Total de Compra (solo FSE)"
    )
    descu = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Descuento (solo FSE) - diferente de totalDescu"
    )
    observaciones_fse = models.TextField(
        max_length=3000,
        blank=True,
        null=True,
        help_text="Observaciones específicas para FSE"
    )

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
        iva_p1 = self.ivaPerci1 if self.ivaPerci1 is not None else Decimal("0.00")
        tp = self.totalPagar if self.totalPagar is not None else Decimal("0.00")

        if tg <= Decimal("0.00"):
            if iva_r1 != Decimal("0.00"):
                raise ValidationError("Si totalGravada <= 0, ivaRete1 debe ser 0.00.")
            if iva_p1 != Decimal("0.00"):
                raise ValidationError("Si totalGravada <= 0, ivaPerci1 debe ser 0.00.")
        if tp == Decimal("0.00"):
            if self.condicionOperacion.codigo != "1":
                raise ValidationError("Si totalPagar = 0, condicionOperacion debe ser 1.")


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


class Sucursal(models.Model):
    """Modelo para manejar sucursales/puntos de venta"""
    nombre = models.CharField(max_length=100, verbose_name="Nombre de la Sucursal")
    codigo = models.CharField(max_length=10, unique=True, verbose_name="Código de Sucursal")
    codEstableMH = models.CharField(max_length=4, verbose_name="Código Establecimiento MH")
    codEstable = models.CharField(max_length=4, verbose_name="Código Establecimiento")
    codPuntoVentaMH = models.CharField(max_length=4, verbose_name="Código Punto Venta MH")
    codPuntoVenta = models.CharField(max_length=15, verbose_name="Código Punto Venta")
    activa = models.BooleanField(default=True, verbose_name="Sucursal Activa")
    
    class Meta:
        db_table = "dte_sucursal"
        verbose_name = "Sucursal"
        verbose_name_plural = "Sucursales"
    
    def __str__(self):
        return f"{self.nombre} ({self.codigo})"
    
    def clean(self):
        from django.core.exceptions import ValidationError
        # Validar que los códigos estén completos
        if not self.codEstableMH or not self.codEstable:
            raise ValidationError("Los códigos de establecimiento son obligatorios")
        if not self.codPuntoVentaMH or not self.codPuntoVenta:
            raise ValidationError("Los códigos de punto de venta son obligatorios")

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

    documento_firmado = models.TextField(
        null=True, 
        blank=True,
        help_text="Documento DTE firmado en formato JWS"
    )
    
    sello_recepcion = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Sello de recepción otorgado por Hacienda"
    )
    
    fecha_procesamiento = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Fecha y hora de procesamiento en Hacienda"
    )

    # En models.py, cambiar solo las choices del estado_hacienda:

    estado_hacienda = models.CharField(
        max_length=30,  # Aumentar tamaño para "ACEPTADO_CON_OBSERVACIONES"
        choices=[
            ('ACEPTADO', 'Aceptado'),
            ('ACEPTADO_CON_OBSERVACIONES', 'Aceptado con Observaciones'),
            ('RECHAZADO', 'Rechazado'),
            ('NO_ENVIADO', 'No Enviado'),
        ],
        default='NO_ENVIADO',  # Cambiar default
        help_text="Estado del documento en Hacienda"
    )
    
    observaciones_hacienda = models.TextField(
        null=True,
        blank=True,
        help_text="Observaciones o errores reportados por Hacienda"
    )
    
    fecha_envio_hacienda = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Fecha y hora de envío a Hacienda"
    )
    
    intentos_envio = models.IntegerField(
        default=0,
        help_text="Número de intentos de envío realizados"
    )
    
    enviado_por_correo = models.BooleanField(
        default=False,
        help_text="Indica si fue enviado por correo al receptor"
    )
    
    fecha_envio_correo = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Fecha y hora de envío por correo"
    )

    # AGREGAR ESTE CAMPO A LA CLASE FacturaElectronica
    sucursal = models.ForeignKey(
        Sucursal,
        on_delete=models.PROTECT,
        verbose_name="Sucursal",
        help_text="Sucursal que emite la factura",
      
    )

    class Meta:
        db_table = "dte_factura_electronica"
        verbose_name = "Factura Electrónica"
        verbose_name_plural = "Facturas Electrónicas"

    def __str__(self):
        return self.identificacion.numeroControl
    
    def clean(self):
        super().clean()
        
        if not hasattr(self, 'identificacion') or not self.identificacion:
            return
            
        if not hasattr(self.identificacion, 'tipoDte') or not self.identificacion.tipoDte:
            return
            
        tipo_dte = self.identificacion.tipoDte.codigo
        
        # Validaciones específicas para CCF
        if tipo_dte == "03":
            if not all([
                self.receptor.tipoDocumento,
                self.receptor.numDocumento,
                self.receptor.nrc,
                self.receptor.nombre,
                self.receptor.codActividad,
                self.receptor.descActividad,
                self.receptor.departamento,
                self.receptor.municipio,
                self.receptor.complemento,
                self.receptor.telefono,
                self.receptor.correo
            ]):
                raise ValidationError("Para CCF, todos los campos del receptor son obligatorios")
            
            import re
            if not re.match(r"^(\d{9}|\d{14})$", self.receptor.numDocumento):
                raise ValidationError("Para CCF, numDocumento debe ser un NIT válido (9 o 14 dígitos)")
        
        # Validaciones específicas para FSE
        elif tipo_dte == "14":
            # Para FSE, validar campos mínimos del sujetoExcluido (receptor)
            if not all([
                self.receptor.tipoDocumento,
                self.receptor.numDocumento,
                self.receptor.nombre
            ]):
                raise ValidationError("Para FSE, son obligatorios: tipoDocumento, numDocumento y nombre del sujeto excluido")
            
            # Validar que se usen los campos FSE específicos si existe resumen
            if hasattr(self, 'resumen') and self.resumen:
                if not self.resumen.total_compra:
                    raise ValidationError("Para FSE, el campo total_compra del resumen es obligatorio")
        
        # Validar monto total vs receptor para FC
        elif tipo_dte == "01" and hasattr(self, 'resumen'):
            if self.resumen.montoTotalOperacion >= Decimal("1095.00"):
                if not all([
                    self.receptor.tipoDocumento,
                    self.receptor.numDocumento,
                    self.receptor.nombre
                ]):
                    raise ValidationError(
                        "Para FC con monto >= $1095.00, receptor debe tener "
                        "tipoDocumento, numDocumento y nombre"
                    )
    
    def get_estado_display(self):
        """Obtiene el estado formateado con color para el admin"""
        colores = {
            'ACEPTADO': '#28a745',                    # Verde
            'ACEPTADO_CON_OBSERVACIONES': '#28a745',  # Verde (mismo que aceptado)  
            'RECHAZADO': '#dc3545',                   # Rojo
            'NO_ENVIADO': '#6c757d',                  # Gris
        }
        
        estado = self.estado_hacienda or 'NO_ENVIADO'
        color = colores.get(estado, '#000000')
        
        # Texto simplificado para mostrar
        texto_estado = {
            'ACEPTADO': 'Aceptado',
            'ACEPTADO_CON_OBSERVACIONES': 'Aceptado c/Obs',
            'RECHAZADO': 'Rechazado',
            'NO_ENVIADO': 'No Enviado',
        }.get(estado, estado)
        
        return f'<span style="color: {color}; font-weight: bold;">{texto_estado}</span>'
    
    def get_items_disponibles_para_nc(self):
        """
        Obtiene los items de este CCF que aún pueden ser acreditados
        Solo para CCF (tipo 03) con estado ACEPTADO
        """
        if self.identificacion.tipoDte.codigo != '03':
            return self.cuerpo_documento.none()
        
        if self.estado_hacienda not in ['ACEPTADO', 'ACEPTADO_CON_OBSERVACIONES']:
            return self.cuerpo_documento.none()
        
        # Filtrar items que tengan cantidad disponible
        items_disponibles = []
        for item in self.cuerpo_documento.all():
            if item.puede_ser_acreditado():
                items_disponibles.append(item)
        
        return items_disponibles
    
    def tiene_items_disponibles_para_nc(self):
        """
        Verifica si este CCF tiene items disponibles para NC
        """
        return len(self.get_items_disponibles_para_nc()) > 0
    
    def get_porcentaje_acreditado(self):
        """
        Obtiene el porcentaje total ya acreditado de este CCF
        CORREGIDO: Cálculo preciso del porcentaje
        """
        if self.identificacion.tipoDte.codigo != '03':
            return Decimal('0.00')
        
        total_original = Decimal('0.00')
        total_acreditado = Decimal('0.00')
        
        for item in self.cuerpo_documento.all():
            cantidad_original = item.cantidad
            cantidad_ya_acreditada = item.get_cantidad_acreditada()
            
            total_original += cantidad_original
            total_acreditado += cantidad_ya_acreditada
        
        if total_original == Decimal('0.00'):
            return Decimal('0.00')
        
        porcentaje = (total_acreditado / total_original) * Decimal('100.00')
        return porcentaje.quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)

    get_estado_display.allow_tags = True
    get_estado_display.short_description = 'Estado'

    def to_json(self, incluir_firma_y_sello: bool = False):
        """
        Construye un dict válido para serializar a JSON que cumpla con el esquema.
        Utiliza build_dte_json de utils.py
        """
        # Importar aquí para evitar imports circulares
        from .utils import build_dte_json
        
        return build_dte_json(self, incluir_firma_y_sello)

# Agregar esta nueva clase al archivo models.py existente

class NotaCreditoDetalle(models.Model):
    """
    Modelo específico para almacenar detalles adicionales de Notas de Crédito
    """
    factura = models.OneToOneField(
        'FacturaElectronica',
        on_delete=models.CASCADE,
        related_name='nota_credito_detalle'
    )
    motivo_nota_credito = models.TextField(
        max_length=500,
        verbose_name="Motivo de la Nota de Crédito",
        help_text="Descripción del motivo por el cual se emite la nota de crédito"
    )
    documento_origen_uuid = models.CharField(
        max_length=36,
        verbose_name="UUID del Documento Original",
        help_text="Código de generación del CCF o NC original que se está acreditando"
    )
    tipo_nota_credito = models.CharField(
        max_length=20,
        choices=[
            ('TOTAL', 'Nota de Crédito Total'),
            ('PARCIAL', 'Nota de Crédito Parcial'),
            ('CORRECCION', 'Corrección de Datos'),
            ('DEVOLUCION', 'Devolución de Mercadería'),
            ('DESCUENTO', 'Descuento Posterior')
        ],
        default='PARCIAL',
        verbose_name="Tipo de Nota de Crédito"
    )
    
    class Meta:
        db_table = "dte_nota_credito_detalle"
        verbose_name = "Detalle de Nota de Crédito"
        verbose_name_plural = "Detalles de Notas de Crédito"
    
    def __str__(self):
        return f"NC {self.factura.identificacion.numeroControl} - {self.tipo_nota_credito}"
    
#Aqui comienzan los cambios de anulacion
# dte/models.py - AGREGAR al archivo models.py existente
from django.db import models
from django.utils import timezone  # NUEVO - Para los campos de fecha/hora
import uuid  # NUEVO - Para generar códigos de generación
from decimal import Decimal
from django.core.validators import MinValueValidator, MaxValueValidator
class AnulacionDocumento(models.Model):
    """
    Modelo para gestionar la anulación de documentos fiscales
    Basado en el esquema anulacion-schema-v2.json
    """
    # Campos de identificación
    codigo_generacion = models.CharField(
        max_length=36,
        unique=True,
        verbose_name="Código de Generación",
        help_text="UUID para identificar esta anulación"
    )
    
    ambiente = models.ForeignKey(
        'AmbienteDestino',
        on_delete=models.CASCADE,
        verbose_name="Ambiente"
    )
    
    fecha_anulacion = models.DateField(
        verbose_name="Fecha de Anulación",
        default=timezone.now
    )
    
    hora_anulacion = models.TimeField(
        verbose_name="Hora de Anulación", 
        default=timezone.now
    )
    
    # Datos del emisor
    emisor = models.ForeignKey(
        'Emisor',
        on_delete=models.CASCADE,
        verbose_name="Emisor"
    )
    
    # Documento a anular
    documento_anular = models.ForeignKey(
        'FacturaElectronica',
        on_delete=models.CASCADE,
        related_name='anulaciones',
        verbose_name="Documento a Anular"
    )
    
    # Motivo de anulación (tipo 2 = anulación sin documento de reemplazo)
    TIPO_ANULACION_CHOICES = [
        (1, 'Anulación con documento de reemplazo'),
        (2, 'Anulación sin documento de reemplazo'),
        (3, 'Corrección de datos'),
    ]
    
    tipo_anulacion = models.IntegerField(
        choices=TIPO_ANULACION_CHOICES,
        default=2,
        verbose_name="Tipo de Anulación"
    )
    
    motivo_anulacion = models.TextField(
        max_length=250,
        verbose_name="Motivo de Anulación",
        help_text="Descripción del motivo de la anulación"
    )
    
    # Datos del responsable
    nombre_responsable = models.CharField(
        max_length=100,
        verbose_name="Nombre del Responsable"
    )
    
    TIPO_DOC_CHOICES = [
        ('36', 'NIT'),
        ('13', 'DUI'),
        ('02', 'Carnet de Residente'),
        ('03', 'Pasaporte'),
        ('37', 'Otro'),
    ]
    
    tipo_doc_responsable = models.CharField(
        max_length=2,
        choices=TIPO_DOC_CHOICES,
        verbose_name="Tipo Documento Responsable"
    )
    
    num_doc_responsable = models.CharField(
        max_length=20,
        verbose_name="Número Documento Responsable"
    )
    
    # Datos del solicitante
    nombre_solicita = models.CharField(
        max_length=100,
        verbose_name="Nombre quien Solicita"
    )
    
    tipo_doc_solicita = models.CharField(
        max_length=2,
        choices=TIPO_DOC_CHOICES,
        verbose_name="Tipo Documento Solicitante"
    )
    
    num_doc_solicita = models.CharField(
        max_length=20,
        verbose_name="Número Documento Solicitante"
    )
    
    # Estados de procesamiento
    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente de Envío'),
        ('ENVIADO', 'Enviado a Hacienda'),
        ('ACEPTADO', 'Aceptado por Hacienda'),
        ('RECHAZADO', 'Rechazado por Hacienda'),
        ('ERROR', 'Error en Procesamiento'),
    ]
    
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='PENDIENTE',
        verbose_name="Estado"
    )
    
    # Respuesta de Hacienda
    sello_recepcion = models.CharField(
        max_length=40,
        blank=True,
        null=True,
        verbose_name="Sello de Recepción"
    )
    
    fecha_procesamiento = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Fecha de Procesamiento"
    )
    
    observaciones = models.TextField(
        blank=True,
        null=True,
        verbose_name="Observaciones"
    )
    
    respuesta_hacienda = models.JSONField(
        blank=True,
        null=True,
        verbose_name="Respuesta Completa de Hacienda"
    )
    
    # Campos de auditoría
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    creado_por = models.CharField(max_length=100, blank=True, null=True)
    
    class Meta:
        db_table = "dte_anulacion_documento"
        verbose_name = "Anulación de Documento"
        verbose_name_plural = "Anulaciones de Documentos"
        ordering = ['-creado_en']
    
    def __str__(self):
        return f"Anulación {self.codigo_generacion} - {self.documento_anular.identificacion.numeroControl}"
    
    def save(self, *args, **kwargs):
        # Generar código de generación si no existe
        if not self.codigo_generacion:
            self.codigo_generacion = str(uuid.uuid4()).upper()
        super().save(*args, **kwargs)
    
    @property
    def puede_anularse(self):
        """
        Verifica si el documento puede ser anulado
        Solo se pueden anular documentos ACEPTADO o ACEPTADO_CON_OBSERVACIONES
        """
        estados_validos = ['ACEPTADO', 'ACEPTADO CON OBSERVACIONES']
        return self.documento_anular.estado_hacienda in estados_validos
    
    # dte/models.py - REEMPLAZAR el método generar_json_anulacion con esta versión simplificada
# dte/models.py - CORREGIR el formato de fecha y hora en generar_json_anulacion

    def generar_json_anulacion(self):
        """
        Genera el JSON de anulación según el esquema anulacion-schema-v2.json
        """
        from django.utils import timezone
        
        # Obtener datos del documento original
        doc_original = self.documento_anular
        
        # Obtener el emisor del documento original
        emisor = doc_original.emisor
        
        # Determinar ambiente
        ambiente_codigo = "00" if settings.DTE_AMBIENTE == 'test' else "01"
        
        # IMPORTANTE: Usar fecha y hora actuales para la anulación
        # Hacienda requiere que la anulación sea en tiempo real
        ahora = timezone.localtime()
        fecha_anulacion = ahora.date()
        hora_anulacion = ahora.time()
        
        # Función auxiliar para obtener valores seguros
        def get_safe_value(obj, attr, default=""):
            try:
                value = getattr(obj, attr, default)
                if hasattr(value, 'codigo'):  # Para ForeignKeys
                    return value.codigo
                return value if value is not None else default
            except:
                return default
        
        # Preparar datos del emisor de forma segura
        emisor_data = {
            "nit": get_safe_value(emisor, 'nit'),
            "nombre": get_safe_value(emisor, 'nombre'),
            "tipoEstablecimiento": get_safe_value(emisor, 'tipoEstablecimiento', '01'),
            "nomEstablecimiento": (
                get_safe_value(emisor, 'nombreComercial') or 
                get_safe_value(emisor, 'nombre', 'Establecimiento Principal')
            ),
            "codEstableMH": get_safe_value(emisor, 'codEstableMH'),
            "codEstable": get_safe_value(emisor, 'codEstable', '0001'),
            "codPuntoVentaMH": get_safe_value(emisor, 'codPuntoVentaMH'),
            "codPuntoVenta": get_safe_value(emisor, 'codPuntoVenta', '0001'),
            "telefono": get_safe_value(emisor, 'telefono'),
            "correo": get_safe_value(emisor, 'correo')
        }
        
        # Validar campos obligatorios
        if not emisor_data["nit"]:
            raise ValueError("El emisor debe tener NIT")
        if not emisor_data["correo"]:
            raise ValueError("El emisor debe tener correo electrónico")
        
        # Calcular monto IVA de forma segura
        monto_iva = 0
        try:
            resumen = doc_original.resumen
            if hasattr(resumen, 'totalIva') and resumen.totalIva:
                monto_iva = float(resumen.totalIva)
            elif hasattr(resumen, 'ivaPerci1') and resumen.ivaPerci1:
                monto_iva = float(resumen.ivaPerci1)
        except:
            monto_iva = 0

        import re

        telefono_raw = get_safe_value(doc_original.receptor, 'telefono') or ''
        solo_digitos = re.sub(r'\D', '', telefono_raw)

        if len(solo_digitos) >= 8:
            telefono_json = solo_digitos
        else:
            telefono_json = None

        
        # Construir JSON según esquema con formato correcto de fecha/hora
        anulacion_json = {
            "identificacion": {
                "version": 2,
                "ambiente": ambiente_codigo,
                "codigoGeneracion": self.codigo_generacion,
                "fecAnula": fecha_anulacion.strftime("%Y-%m-%d"),  # Formato: YYYY-MM-DD
                "horAnula": hora_anulacion.strftime("%H:%M:%S")     # Formato: HH:MM:SS
            },
            "emisor": emisor_data,
            "documento": {
                "tipoDte": doc_original.identificacion.tipoDte.codigo,
                "codigoGeneracion": doc_original.identificacion.codigoGeneracion,
                "selloRecibido": doc_original.sello_recepcion or "",
                "numeroControl": doc_original.identificacion.numeroControl,
                "fecEmi": doc_original.identificacion.fecEmi.strftime("%Y-%m-%d"),
                "montoIva": monto_iva,
                "codigoGeneracionR": None,  # Para tipo 2 siempre es null
                "tipoDocumento": doc_original.receptor.tipoDocumento.codigo,
                "numDocumento": doc_original.receptor.numDocumento,
                "nombre": doc_original.receptor.nombre,
                "telefono": telefono_json,
                "correo": get_safe_value(doc_original.receptor, 'correo')
            },
            "motivo": {
                "tipoAnulacion": self.tipo_anulacion,
                "motivoAnulacion": self.motivo_anulacion,
                "nombreResponsable": self.nombre_responsable,
                "tipDocResponsable": self.tipo_doc_responsable,
                "numDocResponsable": self.num_doc_responsable,
                "nombreSolicita": self.nombre_solicita,
                "tipDocSolicita": self.tipo_doc_solicita,
                "numDocSolicita": self.num_doc_solicita
            }
        }
        
        print(f"DEBUG: Fecha anulación: {fecha_anulacion.strftime('%Y-%m-%d')}")
        print(f"DEBUG: Hora anulación: {hora_anulacion.strftime('%H:%M:%S')}")
        print(f"DEBUG: JSON de anulación generado para documento {doc_original.identificacion.numeroControl}")
        
        return anulacion_json

    # Y también simplificar el método save:

    def save(self, *args, **kwargs):
        # Generar código de generación si no existe
        if not self.codigo_generacion:
            self.codigo_generacion = str(uuid.uuid4()).upper()
            
        # Usar el emisor del documento si no se especifica otro
        if not self.emisor and self.documento_anular:
            self.emisor = self.documento_anular.emisor
            
        super().save(*args, **kwargs)
    
#Aqui terminan

class ItemNotaCredito(models.Model):
    """
    Modelo para controlar qué items de CCF han sido utilizados en Notas de Crédito
    Evita duplicación de acreditaciones
    """
    # Referencia al item original del CCF
    item_original = models.ForeignKey(
        'CuerpoDocumentoItem',
        on_delete=models.CASCADE,
        related_name='notas_credito_aplicadas',
        help_text="Item del CCF original al que se aplica esta NC"
    )
    
    # Referencia al item de la nota de crédito
    item_nota_credito = models.ForeignKey(
        'CuerpoDocumentoItem',
        on_delete=models.CASCADE,
        related_name='referencia_item_original',
        help_text="Item de la NC que referencia al original" 
    )
    
    # Referencia a la factura de nota de crédito
    nota_credito = models.ForeignKey(
        'FacturaElectronica',
        on_delete=models.CASCADE,
        related_name='items_referenciados',
        help_text="NC que contiene este item"
    )
    
    # Cantidad del item original que se acredita
    cantidad_acreditada = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        help_text="Cantidad del item original que se acredita en esta NC"
    )
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'dte_item_nota_credito'
        verbose_name = 'Item de Nota de Crédito'
        verbose_name_plural = 'Items de Notas de Crédito'
        
        # Evitar duplicados
        constraints = [
            models.UniqueConstraint(
                fields=['item_original', 'item_nota_credito'],
                name='unique_item_original_nc'
            )
        ]
        
        indexes = [
            models.Index(fields=['item_original']),
            models.Index(fields=['nota_credito']),
        ]
    
    def __str__(self):
        return f"NC {self.nota_credito.identificacion.numeroControl} - Item {self.item_original.descripcion}"
    
    def clean(self):
        """Validaciones de negocio"""
        # Validar que el item original sea de un CCF
        if self.item_original.factura.identificacion.tipoDte.codigo != '03':
            raise ValidationError("Solo se pueden acreditar items de Crédito Fiscal (CCF)")
        
        # Validar que la NC sea tipo 05
        if self.nota_credito.identificacion.tipoDte.codigo != '05':
            raise ValidationError("Solo se puede referenciar desde Notas de Crédito (tipo 05)")
        
        # Validar que no se exceda la cantidad disponible
        cantidad_ya_acreditada = self.item_original.get_cantidad_acreditada()
        cantidad_disponible = self.item_original.cantidad - cantidad_ya_acreditada
        
        if self.cantidad_acreditada > cantidad_disponible:
            raise ValidationError(
                f"Cantidad excede disponible. "
                f"Original: {self.item_original.cantidad}, "
                f"Ya acreditada: {cantidad_ya_acreditada}, "
                f"Disponible: {cantidad_disponible}"
            )
