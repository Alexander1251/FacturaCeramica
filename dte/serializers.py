# dte/serializers.py

from rest_framework import serializers
from decimal import Decimal
from .models import (
    FacturaElectronica,
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
    # Catálogos
    TipoDocumento,
    GeneracionDocumento,
    TipoItem,
    UnidadMedida,
    Tributo,
    CondicionOperacion,
    FormaPago,
    Plazo,
    ActividadEconomica,
    TipoDocReceptor,
    Departamento,
    Municipio,
    TipoEstablecimiento,
    OtroDocumentoAsociado,
    TipoServicio
)


class IdentificacionSerializer(serializers.ModelSerializer):
    """Serializer para la identificación del DTE"""
    
    tipoDte = serializers.SlugRelatedField(
        slug_field="codigo",
        queryset=TipoDocumento.objects.all()
    )
    
    class Meta:
        model = Identificacion
        fields = [
            'version', 'ambiente', 'tipoDte', 'numeroControl',
            'codigoGeneracion', 'tipoModelo', 'tipoOperacion',
            'tipoContingencia', 'motivoContin', 'fecEmi',
            'horEmi', 'tipoMoneda'
        ]


class DocumentoRelacionadoSerializer(serializers.ModelSerializer):
    """Serializer para documentos relacionados"""
    
    tipoDocumento = serializers.SlugRelatedField(
        slug_field="codigo",
        queryset=TipoDocumento.objects.all()
    )
    tipoGeneracion = serializers.SlugRelatedField(
        slug_field="codigo",
        queryset=GeneracionDocumento.objects.all()
    )

    class Meta:
        model = DocumentoRelacionado
        fields = [
            'tipoDocumento', 'tipoGeneracion',
            'numeroDocumento', 'fechaEmision'
        ]


class EmisorSerializer(serializers.ModelSerializer):
    """Serializer para el emisor"""
    
    codActividad = serializers.SlugRelatedField(
        slug_field="codigo",
        queryset=ActividadEconomica.objects.all()
    )
    tipoEstablecimiento = serializers.SlugRelatedField(
        slug_field="codigo",
        queryset=TipoEstablecimiento.objects.all()
    )
    departamento = serializers.SlugRelatedField(
        slug_field="codigo",
        queryset=Departamento.objects.all()
    )
    municipio = serializers.SlugRelatedField(
        slug_field="codigo",
        queryset=Municipio.objects.all()
    )
    
    class Meta:
        model = Emisor
        fields = [
            'nit', 'nrc', 'nombre', 'codActividad', 'descActividad',
            'nombreComercial', 'tipoEstablecimiento', 'departamento',
            'municipio', 'complemento', 'telefono', 'correo',
            'codEstableMH', 'codEstable', 'codPuntoVentaMH', 'codPuntoVenta'
        ]


class ReceptorSerializer(serializers.ModelSerializer):
    """Serializer para el receptor - Adaptado para FC y CCF"""
    
    tipoDocumento = serializers.SlugRelatedField(
        slug_field="codigo",
        queryset=TipoDocReceptor.objects.all(),
        required=False,
        allow_null=True
    )
    codActividad = serializers.SlugRelatedField(
        slug_field="codigo",
        queryset=ActividadEconomica.objects.all(),
        required=False,
        allow_null=True
    )
    departamento = serializers.SlugRelatedField(
        slug_field="codigo",
        queryset=Departamento.objects.all(),
        required=False,
        allow_null=True
    )
    municipio = serializers.SlugRelatedField(
        slug_field="codigo",
        queryset=Municipio.objects.all(),
        required=False,
        allow_null=True
    )
    
    class Meta:
        model = Receptor
        fields = [
            'tipoDocumento', 'numDocumento', 'nrc', 'nombre',
            'codActividad', 'descActividad', 'departamento',
            'municipio', 'complemento', 'telefono', 'correo'
        ]


class OtrosDocumentosSerializer(serializers.ModelSerializer):
    """Serializer para otros documentos asociados"""
    
    codDocAsociado = serializers.SlugRelatedField(
        slug_field="codigo",
        queryset=OtroDocumentoAsociado.objects.all()
    )
    medico_tipoServicio = serializers.SlugRelatedField(
        slug_field="codigo",
        queryset=TipoServicio.objects.all(),
        required=False,
        allow_null=True
    )
    
    class Meta:
        model = OtrosDocumentos
        fields = [
            'codDocAsociado', 'descDocumento', 'detalleDocumento',
            'medico_nombre', 'medico_nit', 'medico_docIdentificacion',
            'medico_tipoServicio'
        ]


class CuerpoDocumentoItemSerializer(serializers.ModelSerializer):
    """Serializer para ítems del cuerpo del documento"""
    
    tipoItem = serializers.SlugRelatedField(
        slug_field="codigo",
        queryset=TipoItem.objects.all()
    )
    uniMedida = serializers.SlugRelatedField(
        slug_field="codigo",
        queryset=UnidadMedida.objects.all()
    )
    codTributo = serializers.SlugRelatedField(
        slug_field="codigo",
        queryset=Tributo.objects.all(),
        required=False,
        allow_null=True
    )
    tributos = serializers.SlugRelatedField(
        many=True,
        slug_field="codigo",
        queryset=Tributo.objects.all(),
        required=False
    )

    class Meta:
        model = CuerpoDocumentoItem
        fields = [
            'numItem', 'tipoItem', 'numeroDocumento', 'cantidad',
            'codigo', 'codTributo', 'uniMedida', 'descripcion',
            'precioUni', 'montoDescu', 'ventaNoSuj', 'ventaExenta',
            'ventaGravada', 'tributos', 'psv', 'noGravado', 'ivaItem'
        ]


class TributoResumenSerializer(serializers.ModelSerializer):
    """Serializer para tributos del resumen"""
    
    codigo = serializers.SlugRelatedField(
        slug_field="codigo",
        queryset=Tributo.objects.all()
    )
    
    class Meta:
        model = TributoResumen
        fields = ['codigo', 'descripcion', 'valor']


class PagoSerializer(serializers.ModelSerializer):
    """Serializer para formas de pago"""
    
    codigo = serializers.SlugRelatedField(
        slug_field="codigo",
        queryset=FormaPago.objects.all()
    )
    plazo = serializers.SlugRelatedField(
        slug_field="codigo",
        queryset=Plazo.objects.all(),
        required=False,
        allow_null=True
    )
    
    class Meta:
        model = Pago
        fields = ['codigo', 'montoPago', 'referencia', 'plazo', 'periodo']


class ResumenSerializer(serializers.ModelSerializer):
    """Serializer para el resumen del DTE"""
    
    condicionOperacion = serializers.SlugRelatedField(
        slug_field="codigo",
        queryset=CondicionOperacion.objects.all()
    )
    tributos = TributoResumenSerializer(many=True, required=False)
    pagos = PagoSerializer(many=True, required=False)

    class Meta:
        model = Resumen
        fields = [
            'totalNoSuj', 'totalExenta', 'totalGravada', 'subTotalVentas',
            'descuNoSuj', 'descuExenta', 'descuGravada', 'porcentajeDescuento',
            'totalDescu', 'tributos', 'subTotal', 'ivaRete1', 'reteRenta',
            'montoTotalOperacion', 'totalNoGravado', 'totalPagar',
            'totalLetras', 'totalIva', 'saldoFavor', 'condicionOperacion',
            'pagos', 'numPagoElectronico', 'ivaPerci1'
        ]


class ExtensionSerializer(serializers.ModelSerializer):
    """Serializer para la extensión del DTE"""
    
    class Meta:
        model = Extension
        fields = [
            'nombEntrega', 'docuEntrega', 'nombRecibe',
            'docuRecibe', 'observaciones', 'placaVehiculo'
        ]


class ApendiceItemSerializer(serializers.ModelSerializer):
    """Serializer para ítems del apéndice"""
    
    class Meta:
        model = ApendiceItem
        fields = ['campo', 'etiqueta', 'valor']


class VentaTerceroSerializer(serializers.ModelSerializer):
    """Serializer para ventas por cuenta de terceros"""
    
    class Meta:
        model = VentaTercero
        fields = ['nit', 'nombre']


class FacturaElectronicaSerializer(serializers.ModelSerializer):
    """
    Serializer principal para Factura Electrónica
    Soporta tanto FC (01) como CCF (03)
    """
    
    identificacion = IdentificacionSerializer()
    documentos_relacionados = DocumentoRelacionadoSerializer(many=True, required=False)
    emisor = EmisorSerializer(read_only=True)
    receptor = ReceptorSerializer()
    otros_documentos = OtrosDocumentosSerializer(many=True, required=False)
    venta_tercero = VentaTerceroSerializer(required=False, allow_null=True)
    cuerpo_documento = CuerpoDocumentoItemSerializer(many=True)
    resumen = ResumenSerializer()
    extension = ExtensionSerializer(required=False, allow_null=True)
    apendice = ApendiceItemSerializer(many=True, required=False)
    
    class Meta:
        model = FacturaElectronica
        fields = [
            'identificacion', 'documentos_relacionados', 'emisor',
            'receptor', 'otros_documentos', 'venta_tercero',
            'cuerpo_documento', 'resumen', 'extension', 'apendice',
            'documento_firmado', 'sello_recepcion', 'fecha_procesamiento',
            'estado_hacienda', 'observaciones_hacienda'
        ]
        read_only_fields = [
            'documento_firmado', 'sello_recepcion', 'fecha_procesamiento',
            'estado_hacienda', 'observaciones_hacienda'
        ]

    def create(self, validated_data):
        """
        Crea una nueva factura electrónica con todos sus elementos relacionados
        """
        # Extraer datos anidados
        identificacion_data = validated_data.pop('identificacion')
        documentos_relacionados_data = validated_data.pop('documentos_relacionados', [])
        receptor_data = validated_data.pop('receptor')
        otros_documentos_data = validated_data.pop('otros_documentos', [])
        venta_tercero_data = validated_data.pop('venta_tercero', None)
        cuerpo_documento_data = validated_data.pop('cuerpo_documento')
        resumen_data = validated_data.pop('resumen')
        extension_data = validated_data.pop('extension', None)
        apendice_data = validated_data.pop('apendice', [])
        
        # Crear identificación
        identificacion = Identificacion.objects.create(**identificacion_data)
        
        # Crear o obtener receptor
        receptor, _ = Receptor.objects.get_or_create(**receptor_data)
        
        # Crear factura principal
        factura = FacturaElectronica.objects.create(
            identificacion=identificacion,
            receptor=receptor,
            **validated_data
        )
        
        # Crear documentos relacionados
        for doc_rel_data in documentos_relacionados_data:
            DocumentoRelacionado.objects.create(factura=factura, **doc_rel_data)
        
        # Crear otros documentos
        for otro_doc_data in otros_documentos_data:
            OtrosDocumentos.objects.create(factura=factura, **otro_doc_data)
        
        # Crear venta a tercero si existe
        if venta_tercero_data:
            VentaTercero.objects.create(factura=factura, **venta_tercero_data)
        
        # Crear ítems del cuerpo
        for item_data in cuerpo_documento_data:
            tributos_data = item_data.pop('tributos', [])
            item = CuerpoDocumentoItem.objects.create(factura=factura, **item_data)
            if tributos_data:
                item.tributos.set(tributos_data)
        
        # Extraer datos del resumen
        tributos_resumen_data = resumen_data.pop('tributos', [])
        pagos_data = resumen_data.pop('pagos', [])
        
        # Crear resumen
        resumen = Resumen.objects.create(factura=factura, **resumen_data)
        
        # Crear tributos del resumen
        for tributo_data in tributos_resumen_data:
            TributoResumen.objects.create(resumen=resumen, **tributo_data)
        
        # Crear pagos
        for pago_data in pagos_data:
            Pago.objects.create(resumen=resumen, **pago_data)
        
        # Crear extensión si existe
        if extension_data:
            Extension.objects.create(factura=factura, **extension_data)
        
        # Crear apéndice
        for apendice_item_data in apendice_data:
            ApendiceItem.objects.create(factura=factura, **apendice_item_data)
        
        return factura

    def update(self, instance, validated_data):
        """
        Actualiza una factura electrónica existente
        Solo permite actualizar ciertos campos después de la creación
        """
        # Campos que se pueden actualizar
        updatable_fields = [
            'estado_hacienda', 'observaciones_hacienda',
            'documento_firmado', 'sello_recepcion',
            'fecha_procesamiento'
        ]
        
        for field in updatable_fields:
            if field in validated_data:
                setattr(instance, field, validated_data[field])
        
        instance.save()
        return instance

    def validate(self, data):
        """
        Validaciones adicionales según el tipo de documento
        """
        identificacion_data = data.get('identificacion', {})
        receptor_data = data.get('receptor', {})
        cuerpo_data = data.get('cuerpo_documento', [])
        resumen_data = data.get('resumen', {})
        
        tipo_dte = identificacion_data.get('tipoDte')
        
        if not tipo_dte:
            raise serializers.ValidationError("Tipo de DTE es requerido")
        
        tipo_codigo = tipo_dte.codigo if hasattr(tipo_dte, 'codigo') else str(tipo_dte)
        
        # Validaciones específicas para CCF
        if tipo_codigo == "03":
            # Receptor debe tener todos los campos obligatorios
            campos_obligatorios = [
                'numDocumento', 'nrc', 'nombre', 'codActividad',
                'descActividad', 'departamento', 'municipio',
                'complemento', 'telefono', 'correo'
            ]
            
            for campo in campos_obligatorios:
                if not receptor_data.get(campo):
                    raise serializers.ValidationError(
                        f"Para CCF, el campo '{campo}' del receptor es obligatorio"
                    )
            
            # El tipo de documento debe ser NIT (36)
            tipo_doc = receptor_data.get('tipoDocumento')
            if hasattr(tipo_doc, 'codigo'):
                tipo_doc_codigo = tipo_doc.codigo
            else:
                tipo_doc_codigo = str(tipo_doc)
                
            if tipo_doc_codigo != "36":
                raise serializers.ValidationError(
                    "Para CCF, el receptor debe tener tipo documento NIT (36)"
                )
        
        # Validaciones para Factura
        elif tipo_codigo == "01":
            # Verificar monto total vs datos del receptor
            monto_total = resumen_data.get('montoTotalOperacion', Decimal('0'))
            if monto_total >= Decimal('1095.00'):
                campos_minimos = ['tipoDocumento', 'numDocumento', 'nombre']
                for campo in campos_minimos:
                    if not receptor_data.get(campo):
                        raise serializers.ValidationError(
                            f"Para FC con monto >= $1095.00, el campo '{campo}' del receptor es obligatorio"
                        )
        
        # Validar que haya al menos un ítem
        if not cuerpo_data:
            raise serializers.ValidationError("Debe incluir al menos un ítem en el cuerpo del documento")
        
        return data


class DTECreateSerializer(serializers.Serializer):
    """
    Serializer simplificado para crear DTEs via API
    """
    tipo_dte = serializers.ChoiceField(choices=[('01', 'Factura'), ('03', 'CCF')])
    receptor = ReceptorSerializer()
    items = CuerpoDocumentoItemSerializer(many=True)
    observaciones = serializers.CharField(required=False, allow_blank=True)
    
    def create(self, validated_data):
        """
        Crea un DTE completo a partir de datos simplificados
        """
        from .forms import _emisor_maestro
        from .utils import numero_a_letras
        from decimal import Decimal, ROUND_HALF_UP
        import uuid
        from django.utils import timezone
        
        tipo_dte = validated_data['tipo_dte']
        receptor_data = validated_data['receptor']
        items_data = validated_data['items']
        observaciones = validated_data.get('observaciones', '')
        
        # Crear identificación
        emisor = _emisor_maestro()
        now = timezone.localtime()
        
        # Generar número de control
        prefijo = f"DTE-{tipo_dte}-{emisor.codEstable.zfill(4)}{emisor.codPuntoVenta.zfill(4)}-"
        ultimo = (
            Identificacion.objects.filter(numeroControl__startswith=prefijo)
            .order_by("-numeroControl")
            .first()
        )
        correlativo = 1 if not ultimo else int(ultimo.numeroControl[-15:]) + 1
        numero_control = f"{prefijo}{correlativo:015d}"
        
        identificacion = Identificacion.objects.create(
            version=3 if tipo_dte == "03" else 1,
            ambiente_id="00",  # Test
            tipoDte_id=tipo_dte,
            numeroControl=numero_control,
            codigoGeneracion=str(uuid.uuid4()).upper(),
            tipoModelo_id="1",
            tipoOperacion_id="1",
            fecEmi=now.date(),
            horEmi=now.time(),
            tipoMoneda="USD"
        )
        
        # Crear receptor
        receptor, _ = Receptor.objects.get_or_create(**receptor_data)
        
        # Crear factura
        factura = FacturaElectronica.objects.create(
            identificacion=identificacion,
            emisor=emisor,
            receptor=receptor
        )
        
        # Crear ítems y calcular totales
        total_gravada = Decimal('0')
        total_iva = Decimal('0')
        
        for idx, item_data in enumerate(items_data, 1):
            item_data['numItem'] = idx
            item = CuerpoDocumentoItem.objects.create(factura=factura, **item_data)
            
            total_gravada += item.ventaGravada
            total_iva += item.ivaItem
        
        # Crear resumen
        total_pagar = total_gravada + total_iva
        total_letras = numero_a_letras(total_pagar)
        
        resumen_data = {
            'totalNoSuj': Decimal('0.00'),
            'totalExenta': Decimal('0.00'),
            'totalGravada': total_gravada,
            'subTotal': total_gravada,
            'subTotalVentas': total_gravada,
            'descuNoSuj': Decimal('0.00'),
            'descuExenta': Decimal('0.00'),
            'descuGravada': Decimal('0.00'),
            'porcentajeDescuento': Decimal('0.00'),
            'totalDescu': Decimal('0.00'),
            'ivaRete1': Decimal('0.00'),
            'reteRenta': Decimal('0.00'),
            'montoTotalOperacion': total_gravada,
            'totalNoGravado': Decimal('0.00'),
            'totalPagar': total_pagar,
            'saldoFavor': Decimal('0.00'),
            'condicionOperacion_id': "1",
            'numPagoElectronico': "",
            'totalLetras': total_letras
        }
        
        # Campos específicos según tipo
        if tipo_dte == "03":
            resumen_data['ivaPerci1'] = Decimal('0.00')
        else:
            resumen_data['totalIva'] = total_iva
        
        resumen = Resumen.objects.create(factura=factura, **resumen_data)
        
        # Crear extensión con observaciones si las hay
        if observaciones:
            Extension.objects.create(
                factura=factura,
                observaciones=observaciones
            )
        
        return factura