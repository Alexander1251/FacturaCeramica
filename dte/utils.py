# dte/utils.py

import json
from decimal import Decimal, ROUND_DOWN
from django.core.exceptions import ObjectDoesNotExist

from .models import (
    FacturaElectronica,
    Identificacion, Emisor, Receptor,
    DocumentoRelacionado, OtrosDocumentos, VentaTercero,
    CuerpoDocumentoItem, Resumen, TributoResumen, Pago,
    Extension, ApendiceItem
)
from num2words import num2words

def numero_a_letras(monto: Decimal) -> str:
    """
    Convierte un monto Decimal (p.ej. 1130.45)
    en su representación en palabras en español en MAYÚSCULAS,
    indicando DÓLAR/DÓLARES y CENTAVO/CENTAVOS según corresponda.

    Ejemplos:
      Decimal('1130.00') → 'MIL CIENTO TREINTA DÓLARES'
      Decimal('1.01')    → 'UN DÓLAR CON UN CENTAVO'
      Decimal('0.75')    → 'CERO DÓLARES CON SETENTA Y CINCO CENTAVOS'
    """
    # Aseguramos dos decimales, descartando más allá de centavos
    monto = monto.quantize(Decimal('0.01'), rounding=ROUND_DOWN)

    entero = int(monto)                            # parte entera
    centavos = int((monto - Decimal(entero)) * 100)  # parte decimal como entero

    # Convertir a texto y pasar a mayúsculas
    texto_entero = num2words(entero, lang="es").upper()
    texto_centavos = num2words(centavos, lang="es").upper()

    # Elegir singular/plural
    dolar_text = "DÓLAR" if entero == 1 else "DÓLARES"
    centavo_text = "CENTAVO" if centavos == 1 else "CENTAVOS"

    # Construir la frase final
    if centavos:
        return f"{texto_entero} {dolar_text} CON {texto_centavos} {centavo_text}"
    else:
        return f"{texto_entero} {dolar_text}"

def build_dte_json(factura: FacturaElectronica, incluir_firma_y_sello: bool = False) -> dict:
    """
    Construye y devuelve el JSON (como dict) de un DTE completo,
    tomando como entrada un objeto FacturaElectronica.
    VERSIÓN EXPANDIDA: Maneja FC, CCF, FSE y NC (Nota de Crédito)
    """

    def rd(x):
        return round(float(x), 2)
    
    # Verificaciones robustas
    if not hasattr(factura, 'identificacion') or not factura.identificacion:
        raise ValueError("La factura no tiene identificación")
    
    if not hasattr(factura.identificacion, 'tipoDte') or not factura.identificacion.tipoDte:
        raise ValueError("La identificación no tiene tipoDte asignado")
    
    tipo_dte = factura.identificacion.tipoDte.codigo

    # 1) Identificación - IGUAL para todos
    identificacion = {
        "version": factura.identificacion.version,
        "ambiente": factura.identificacion.ambiente.codigo,
        "tipoDte": tipo_dte,
        "numeroControl": factura.identificacion.numeroControl,
        "codigoGeneracion": factura.identificacion.codigoGeneracion,
        "tipoModelo": int(factura.identificacion.tipoModelo.codigo),
        "tipoOperacion": int(factura.identificacion.tipoOperacion.codigo),
        "tipoContingencia": (
            int(factura.identificacion.tipoContingencia.codigo)
            if factura.identificacion.tipoContingencia else None
        ),
        "motivoContin": factura.identificacion.motivoContin,
        "fecEmi": factura.identificacion.fecEmi.isoformat(),
        "horEmi": factura.identificacion.horEmi.strftime("%H:%M:%S"),
        "tipoMoneda": factura.identificacion.tipoMoneda,
    }

    # 2) Documentos Relacionados - IGUAL para todos
    docs_rel = []
    for dr in factura.documentos_relacionados.all():
        docs_rel.append({
            "tipoDocumento": dr.tipoDocumento.codigo,
            "tipoGeneracion": int(dr.tipoGeneracion.codigo),
            "numeroDocumento": dr.numeroDocumento,
            "fechaEmision": dr.fechaEmision.isoformat(),
        })

    # 3) Emisor - DIFERENCIADO por tipo
    em = factura.emisor
    sucursal = factura.sucursal
    if not em:
        raise ValueError("La factura no tiene emisor")
    
    if not sucursal:
        raise ValueError("La factura debe tener una sucursal asignada")

    
    if tipo_dte == "14":  # FSE - Estructura simplificada
        emisor = {
            "nit": em.nit,
            "nrc": em.nrc,
            "nombre": em.nombre,
            "codActividad": em.codActividad.codigo,
            "descActividad": em.descActividad,
            "direccion": {
                "departamento": em.departamento.codigo,
                "municipio": em.municipio.codigo,
                "complemento": em.complemento,
            },
            "telefono": em.telefono,
            "codEstableMH": sucursal.codEstableMH,
            "codEstable": sucursal.codEstable,
            "codPuntoVentaMH": sucursal.codPuntoVentaMH,
            "codPuntoVenta": sucursal.codPuntoVenta,
            "correo": em.correo,
        }
    else:  # FC, CCF y NC - Estructura completa
        emisor = {
            "nit": em.nit,
            "nrc": em.nrc,
            "nombre": em.nombre,
            "codActividad": em.codActividad.codigo,
            "descActividad": em.descActividad,
            "nombreComercial": em.nombreComercial,  # Solo para FC/CCF/NC
            "tipoEstablecimiento": em.tipoEstablecimiento.codigo,  # Solo para FC/CCF/NC
            "direccion": {
                "departamento": em.departamento.codigo,
                "municipio": em.municipio.codigo,
                "complemento": em.complemento,
            },
            "telefono": em.telefono,
            "correo": em.correo,
        }
        
        # NUEVO: Para NC no incluir códigos de establecimiento
        if tipo_dte != "05":  # Para todos excepto NC
            emisor.update({
                "codEstableMH": sucursal.codEstableMH,
                "codEstable": sucursal.codEstable,
                "codPuntoVentaMH": sucursal.codPuntoVentaMH,
                "codPuntoVenta": sucursal.codPuntoVenta,
            })

    # 4) Receptor/SujetoExcluido - DIFERENCIADO por tipo
    rc = factura.receptor
    if not rc:
        raise ValueError("La factura no tiene receptor")
    
    # Función auxiliar para normalizar número de documento
    def normalizar_num_documento(num_doc, tipo_doc_codigo):
        """
        Normaliza el número de documento según el tipo:
        - Para DUI (13): Remueve guión para envío al MH
        - Para otros tipos: Mantiene formato original
        """
        if not num_doc:
            return num_doc
            
        if tipo_doc_codigo == "13":  # DUI
            # Remover guión solo para transmisión
            return num_doc.replace("-", "")
        
        return num_doc
        
    if tipo_dte == "14":  # FSE - Sujeto Excluido
        receptor_key = "sujetoExcluido"
        
        # Normalizar número de documento para transmisión
        num_documento_normalizado = normalizar_num_documento(
            rc.numDocumento, 
            rc.tipoDocumento.codigo if rc.tipoDocumento else None
        )
        
        receptor = {
            "tipoDocumento": (rc.tipoDocumento.codigo if rc.tipoDocumento else None),
            "numDocumento": num_documento_normalizado,  # Usar versión normalizada
            "nombre": rc.nombre,
            # Campos opcionales que se envían como null si no existen
            "codActividad": (rc.codActividad.codigo if rc.codActividad else None),
            "descActividad": rc.descActividad,
            "direccion": ({
                "departamento": rc.departamento.codigo,
                "municipio": rc.municipio.codigo,
                "complemento": rc.complemento,
            } if any([rc.departamento, rc.municipio, rc.complemento]) else None),
            "telefono": rc.telefono,
            "correo": rc.correo,
        }
    elif tipo_dte in ["03", "05"]:  # CCF y NC - numDocumento va en "nit"
        receptor_key = "receptor"
        receptor = {
            "nit": rc.numDocumento,  # Para CCF y NC, numDocumento va en campo "nit"
            "nrc": rc.nrc,
            "nombre": rc.nombre,
            "codActividad": rc.codActividad.codigo,
            "descActividad": rc.descActividad,
            "nombreComercial": getattr(rc, 'nombreComercial', None),
            "direccion": {
                "departamento": rc.departamento.codigo,
                "municipio": rc.municipio.codigo,
                "complemento": rc.complemento,
            },
            "telefono": rc.telefono,
            "correo": rc.correo,
        }
    else:  # FC (01)
        receptor_key = "receptor"
        receptor = {
            "tipoDocumento": (rc.tipoDocumento.codigo if rc.tipoDocumento else None),
            "numDocumento": rc.numDocumento,  # Para FC mantiene en numDocumento
            "nrc": rc.nrc,
            "nombre": rc.nombre,
            "codActividad": (rc.codActividad.codigo if rc.codActividad else None),
            "descActividad": rc.descActividad,
            "direccion": {
                "departamento": rc.departamento.codigo if rc.departamento else None,
                "municipio": rc.municipio.codigo if rc.municipio else None,
                "complemento": rc.complemento,
            } if any([rc.departamento, rc.municipio, rc.complemento]) else None,
            "telefono": rc.telefono,
            "correo": rc.correo,
        }

    # 5) Otros Documentos - IGUAL para todos (EXCEPTO NC que no lo usa)
    otros_docs = []
    if tipo_dte != "05":  # NC no incluye otrosDocumentos según esquema
        for od in factura.otros_documentos.all():
            otros_docs.append({
                "codDocAsociado": int(od.codDocAsociado.codigo),
                "descDocumento": od.descDocumento,
                "detalleDocumento": od.detalleDocumento,
                "medico": (
                    {
                        "nombre": od.medico.nombre,
                        "nit": od.medico.nit,
                        "docIdentificacion": od.medico.docIdentificacion,
                        "tipoServicio": int(od.medico.tipoServicio.codigo),
                    }
                    if od.medico
                    else None
                ),
            })

    # 6) Venta Tercero - IGUAL para todos
    vt_data = None
    if hasattr(factura, 'venta_tercero') and factura.venta_tercero:
        vt = factura.venta_tercero
        vt_data = {
            "nit": vt.nit,
            "nombre": vt.nombre,
        }

    # 7) Cuerpo Documento - DIFERENCIADO por tipo
    cuerpo = []
    for item in factura.cuerpo_documento.all():
        if tipo_dte == "14":  # FSE
            item_dict = {
                "numItem": item.numItem,
                "tipoItem": int(item.tipoItem.codigo),
                "cantidad": rd(item.cantidad),
                "codigo": item.codigo,
                "uniMedida": int(item.uniMedida.codigo),
                "descripcion": item.descripcion,
                "precioUni": rd(item.precioUni),
                "montoDescu": rd(item.montoDescu),
                "compra": rd(getattr(item, 'compra', item.ventaGravada)),  # FSE usa 'compra'
            }
        else:  # FC, CCF y NC
            tributos_it = [t.codigo for t in item.tributos.all()] if item.tributos.exists() else None

            # Estructura existente para FC, CCF y NC
            item_dict = {
                "numItem": item.numItem,
                "tipoItem": int(item.tipoItem.codigo),
                "numeroDocumento": item.numeroDocumento,
                "cantidad": rd(item.cantidad),
                "codigo": item.codigo,
                "codTributo": (item.codTributo.codigo if item.codTributo else None),
                "uniMedida": int(item.uniMedida.codigo),
                "descripcion": item.descripcion,
                "precioUni": rd(item.precioUni),
                "montoDescu": rd(item.montoDescu),
                "ventaNoSuj": rd(item.ventaNoSuj),
                "ventaExenta": rd(item.ventaExenta),
                "ventaGravada": rd(item.ventaGravada),
                "tributos": tributos_it,
            }
            
            # NUEVO: Para NC, algunos campos no se incluyen según esquema
            if tipo_dte != "05":  # Solo para FC y CCF
                item_dict.update({
                    "psv": rd(item.psv),
                    "noGravado": rd(item.noGravado),
                })
                
                # ivaItem solo para FC
                if tipo_dte == "01":  
                    item_dict["ivaItem"] = rd(item.ivaItem)
        
        cuerpo.append(item_dict)

    # 8) Resumen - DIFERENCIADO por tipo
    rs = factura.resumen
    if not rs:
        raise ValueError("La factura no tiene resumen")

    if tipo_dte == "14":  # FSE
        # Construir pagos - debe ser null si está vacío, no array vacío
        pagos_list = []
        for p in rs.pagos.all():
            pagos_list.append({
                "codigo": p.codigo.codigo,
                "montoPago": rd(p.montoPago),
                "referencia": p.referencia,
                "plazo": p.plazo,
                "periodo": (int(p.periodo.codigo) if p.periodo else None),
            })
        
        resumen = {
            "totalCompra": rd(rs.total_compra) if rs.total_compra else 0.00,
            "descu": rd(rs.descu) if rs.descu else 0.00,
            "totalDescu": rd(rs.totalDescu) if rs.totalDescu else 0.00,  # Campo obligatorio
            "subTotal": rd(rs.subTotal) if rs.subTotal else 0.00,        # Campo obligatorio  
            "ivaRete1": rd(rs.ivaRete1) if rs.ivaRete1 else 0.00,       # Campo obligatorio
            "reteRenta": rd(rs.reteRenta) if rs.reteRenta else 0.00,     # Campo obligatorio
            "totalPagar": rd(rs.totalPagar),
            "totalLetras": rs.totalLetras,
            "condicionOperacion": int(rs.condicionOperacion.codigo),
            # CLAVE: pagos debe ser null si está vacío, no []
            "pagos": pagos_list if pagos_list else None,
            # Observaciones específicas de FSE - obligatorio según esquema
            "observaciones": rs.observaciones_fse if hasattr(rs, 'observaciones_fse') and rs.observaciones_fse else "",
        }
    elif tipo_dte == "05":  # NC - Estructura específica según esquema fe-nc-v3.json
        resumen = {
            # Campos obligatorios para NC según esquema
            "totalNoSuj": rd(rs.totalNoSuj),
            "totalExenta": rd(rs.totalExenta), 
            "totalGravada": rd(rs.totalGravada),
            "subTotalVentas": rd(rs.subTotalVentas),
            "descuNoSuj": rd(rs.descuNoSuj),
            "descuExenta": rd(rs.descuExenta),
            "descuGravada": rd(rs.descuGravada),
            "totalDescu": rd(rs.totalDescu),
            "tributos": (
                [
                    {
                        "codigo": t.codigo.codigo if hasattr(t.codigo, 'codigo') else str(t.codigo),
                        "descripcion": t.descripcion,
                        "valor": rd(t.valor),
                    }
                    for t in rs.tributos.all()
                ]
                if rs.tributos.exists()
                else None
            ),
            "subTotal": rd(rs.subTotal),
            "ivaPerci1": rd(rs.ivaPerci1) if rs.ivaPerci1 else rd(Decimal('0')),  # Obligatorio para NC
            "ivaRete1": rd(rs.ivaRete1),
            "reteRenta": rd(rs.reteRenta),
            "montoTotalOperacion": rd(rs.montoTotalOperacion),
            "totalLetras": rs.totalLetras,
            "condicionOperacion": int(rs.condicionOperacion.codigo),
        }
    else:  # FC, CCF - estructura existente
        # Construir pagos - APLICAR LA MISMA LÓGICA: null si está vacío
        pagos_list = []
        for p in rs.pagos.all():
            pagos_list.append({
                "codigo": p.codigo.codigo,
                "montoPago": rd(p.montoPago),
                "referencia": p.referencia,
                "plazo": p.plazo,
                "periodo": (int(p.periodo.codigo) if p.periodo else None),
            })
        
        resumen = {
            "totalNoSuj": rd(rs.totalNoSuj),
            "totalExenta": rd(rs.totalExenta), 
            "totalGravada": rd(rs.totalGravada),
            "subTotalVentas": rd(rs.subTotalVentas),
            "descuNoSuj": rd(rs.descuNoSuj),
            "descuExenta": rd(rs.descuExenta),
            "descuGravada": rd(rs.descuGravada),
            "porcentajeDescuento": rd(rs.porcentajeDescuento),
            "totalDescu": rd(rs.totalDescu),
            "tributos": (
                [
                    {
                        "codigo": t.codigo.codigo if hasattr(t.codigo, 'codigo') else str(t.codigo),
                        "descripcion": t.descripcion,
                        "valor": rd(t.valor),
                    }
                    for t in rs.tributos.all()
                ]
                if rs.tributos.exists()
                else None
            ),
            "subTotal": rd(rs.subTotal),
            "ivaRete1": rd(rs.ivaRete1),
            "reteRenta": rd(rs.reteRenta),
            "montoTotalOperacion": rd(rs.montoTotalOperacion),
            "totalNoGravado": rd(rs.totalNoGravado),
            "totalPagar": rd(rs.totalPagar),
            "totalLetras": rs.totalLetras,
            "saldoFavor": rd(rs.saldoFavor),
            "condicionOperacion": int(rs.condicionOperacion.codigo),
            # CLAVE: pagos debe ser null si está vacío, no [] - PARA TODOS LOS TIPOS
            "pagos": pagos_list if pagos_list else None,
            "numPagoElectronico": rs.numPagoElectronico,
        }
        
        # Campos específicos por tipo de documento
        if tipo_dte == "03":  # CCF
            resumen["ivaPerci1"] = rd(rs.ivaPerci1) if rs.ivaPerci1 else rd(Decimal('0'))
        elif tipo_dte == "01":  # FC
            resumen["totalIva"] = rd(rs.totalIva) if rs.totalIva else rd(Decimal('0'))

    # 9) Extension - IGUAL para todos
    ext_data = None
    if hasattr(factura, 'extension') and factura.extension:
        ext = factura.extension
        ext_data = {
            "nombEntrega": ext.nombEntrega,
            "docuEntrega": ext.docuEntrega,
            "nombRecibe": ext.nombRecibe,
            "docuRecibe": ext.docuRecibe,
            "observaciones": ext.observaciones,
        }
        
        # NUEVO: placaVehiculo solo para tipos que no sean NC
        if tipo_dte != "05":
            ext_data["placaVehiculo"] = ext.placaVehiculo

    # 10) Apéndice - IGUAL para todos (campos nulos se manejan aquí)
    apendice = []
    for ap in factura.apendice.all():
        apendice.append({
            "campo": ap.campo,
            "etiqueta": ap.etiqueta,
            "valor": ap.valor,
        })

    # 11) Construcción final del JSON - DIFERENCIADO por tipo de DTE
    if incluir_firma_y_sello:
        if tipo_dte == "14":  # FSE - Estructura simplificada
            dte_dict = {
                "identificacion": identificacion,
                "emisor": emisor,
                receptor_key: receptor,  # "sujetoExcluido" para FSE
                "cuerpoDocumento": cuerpo,
                "resumen": resumen,
                "apendice": apendice if apendice else None,
                "firma": factura.documento_firmado,
                "selloRecibido": factura.sello_recepcion
            }
        elif tipo_dte == "05":  # NC - Estructura específica para Nota de Crédito
            dte_dict = {
                "identificacion": identificacion,
                "documentoRelacionado": docs_rel,  # OBLIGATORIO para NC
                "emisor": emisor,
                receptor_key: receptor,  # "receptor" para NC
                "ventaTercero": vt_data,  # OBLIGATORIO según esquema NC (puede ser null)
                "cuerpoDocumento": cuerpo,
                "resumen": resumen,
                "extension": ext_data,  # OBLIGATORIO según esquema NC (puede ser null)
                "apendice": apendice if apendice else None,  # OBLIGATORIO según esquema NC (puede ser null)
                "firma": factura.documento_firmado,
                "selloRecibido": factura.sello_recepcion
            }
            # Para NC: otrosDocumentos NO está en el esquema, por eso se omite
        else:  # FC y CCF - Estructura completa
            dte_dict = {
                "identificacion": identificacion,
                "documentoRelacionado": docs_rel,
                "emisor": emisor,
                receptor_key: receptor,  # "receptor" para FC y CCF
                "otrosDocumentos": otros_docs,
                "ventaTercero": vt_data,
                "cuerpoDocumento": cuerpo,
                "resumen": resumen,
                "extension": ext_data,
                "apendice": apendice if apendice else None,
                "firma": factura.documento_firmado,
                "selloRecibido": factura.sello_recepcion
            }
            
            # Limpiar campos vacíos para FC y CCF
            if not dte_dict["documentoRelacionado"]:
                dte_dict["documentoRelacionado"] = None
            if not dte_dict["otrosDocumentos"]:
                dte_dict["otrosDocumentos"] = None
            if not dte_dict["cuerpoDocumento"]:
                dte_dict["cuerpoDocumento"] = None
            if not dte_dict["apendice"]:
                dte_dict["apendice"] = None
    else:
        # Sin firma y sello
        if tipo_dte == "14":  # FSE - Estructura simplificada sin firma
            dte_dict = {
                "identificacion": identificacion,
                "emisor": emisor,
                receptor_key: receptor,  # "sujetoExcluido" para FSE
                "cuerpoDocumento": cuerpo,
                "resumen": resumen,
                "apendice": apendice if apendice else None,
            }
        elif tipo_dte == "05":  # NC - Estructura específica para Nota de Crédito sin firma
            dte_dict = {
                "identificacion": identificacion,
                "documentoRelacionado": docs_rel,  # OBLIGATORIO para NC
                "emisor": emisor,
                receptor_key: receptor,  # "receptor" para NC
                "ventaTercero": vt_data,  # OBLIGATORIO según esquema NC (puede ser null)
                "cuerpoDocumento": cuerpo,
                "resumen": resumen,
                "extension": ext_data,  # OBLIGATORIO según esquema NC (puede ser null)
                "apendice": apendice if apendice else None,  # OBLIGATORIO según esquema NC (puede ser null)
            }
            # Para NC: otrosDocumentos NO está en el esquema, por eso se omite
        else:  # FC y CCF - Estructura completa sin firma
            dte_dict = {
                "identificacion": identificacion,
                "documentoRelacionado": docs_rel,
                "emisor": emisor,
                receptor_key: receptor,  # "receptor" para FC y CCF
                "otrosDocumentos": otros_docs,
                "ventaTercero": vt_data,
                "cuerpoDocumento": cuerpo,
                "resumen": resumen,
                "extension": ext_data,
                "apendice": apendice if apendice else None,
            }
            
            # Limpiar campos vacíos para FC y CCF
            if not dte_dict["documentoRelacionado"]:
                dte_dict["documentoRelacionado"] = None
            if not dte_dict["otrosDocumentos"]:
                dte_dict["otrosDocumentos"] = None
            if not dte_dict["cuerpoDocumento"]:
                dte_dict["cuerpoDocumento"] = None
            if not dte_dict["apendice"]:
                dte_dict["apendice"] = None

    # Validación extra para montos altos - RESTAURADA
    if rs.montoTotalOperacion and rs.montoTotalOperacion >= Decimal("1095.00"):
        if not (rc.tipoDocumento and rc.numDocumento and rc.nombre):
            raise ValueError(
                "Para montoTotalOperacion >= 1095.00, el receptor debe "
                "tener tipoDocumento, numDocumento y nombre."
            )

    return dte_dict