# dte/services.py

import json
import requests
from datetime import datetime, timedelta
from django.core.mail import EmailMessage
from django.conf import settings
from typing import Dict, Any, List, Optional
import logging
from django.utils import timezone
from .utils import build_dte_json
from .gmail_service import GmailService

logger = logging.getLogger(__name__)


class DTEService:
    """
    Servicio para gestionar la firma electrónica y comunicación con Hacienda
    para Documentos Tributarios Electrónicos (DTE)
    Soporta tanto Facturas (FC) como Crédito Fiscal (CCF)
    """
    
    def __init__(self, emisor, ambiente='test', firmador_url=None, dte_urls=None, 
                 dte_user=None, dte_password=None):
        self.emisor = emisor
        self.ambiente = ambiente
        self.firmador_url = firmador_url or getattr(settings, 'FIRMADOR_URL', 'http://localhost:8113/firmardocumento/')
        self.dte_urls = dte_urls or getattr(settings, 'DTE_URLS', {}).get(ambiente, {})
        self.dte_user = dte_user or getattr(settings, 'DTE_USER', '')
        self.dte_password = dte_password or getattr(settings, 'DTE_PASSWORD', '')
        self._token = None
        self._token_expiry = None
        
    def enviar_correo_factura_simplificado(self, factura, archivos_adjuntos: List[Dict[str, Any]]):
        """
        Envía la factura por correo electrónico al receptor (versión simplificada)
        ACTUALIZADO: Usa Gmail API si está disponible
        """
        try:
            gmail_service = GmailService()
            
            asunto = f"Factura {factura.identificacion.numeroControl} (Imprimible)"
            
            mensaje = f"""
    <html>
    <body>
    <p>Estimado/a {factura.receptor.nombre},</p>

    <p>Le enviamos el imprimible de su factura con los siguientes datos:</p>

    <ul>
    <li><strong>Número de Control:</strong> {factura.identificacion.numeroControl}</li>
    <li><strong>Fecha de Emisión:</strong> {factura.identificacion.fecEmi}</li>
    <li><strong>Total:</strong> ${factura.resumen.totalPagar:.2f}</li>
    </ul>

    <p><strong>IMPORTANTE:</strong> Este documento NO tiene validez fiscal oficial ya que no fue enviado a Hacienda para su procesamiento.</p>

    <p>Adjuntamos:</p>
    <ul>
    <li>Factura en formato PDF (versión imprimible)</li>
    </ul>

    <p>Saludos cordiales,<br>
    {factura.emisor.nombre}<br>
    NIT: {factura.emisor.nit}</p>
    </body>
    </html>
            """
            
            # Intentar Gmail API primero
            success = gmail_service.enviar_correo(
                destinatario=factura.receptor.correo,
                asunto=asunto,
                cuerpo=mensaje,
                archivos_adjuntos=archivos_adjuntos,
                copia_oculta=[factura.emisor.correo] if factura.emisor.correo else None
            )
            
            if success:
                # Actualizar registro de envío
                factura.enviado_por_correo = True
                factura.fecha_envio_correo = timezone.localtime()
                factura.save(update_fields=['enviado_por_correo', 'fecha_envio_correo'])
                
                logger.info(f"Factura simplificada enviada por correo a {factura.receptor.correo}")
            else:
                raise Exception("No se pudo enviar el correo con Gmail API ni con el sistema por defecto")
                
        except Exception as e:
            logger.error(f"Error al enviar correo simplificado: {str(e)}")
            raise
    
    def firmar_documento(self, dte_json: Dict[str, Any]) -> str:
        """
        Firma electrónicamente el documento DTE (FC o CCF)
        
        Args:
            dte_json: Diccionario con el DTE a firmar
            
        Returns:
            str: Documento firmado en formato JWS
            
        Raises:
            Exception: Si hay error en el proceso de firma
        """
        try:
            # Convertir el diccionario a JSON string
            dte_json_str = dte_json
            
            # Preparar datos para el firmador según documentación oficial
            payload = {
                'nit': str(self.emisor.nit),
                'activo': True,
                'passwordPri': str(getattr(settings, 'DTE_CERTIFICADO_PASSWORD', '')),
                'dteJson': dte_json_str
            }
            
            headers = {
                'Content-Type': 'application/json'
            }
            
            tipo_doc = dte_json.get('identificacion', {}).get('tipoDte', 'XX')
            doc_name = "CCF" if tipo_doc == "03" else "Factura"
            
            logger.info(f"Enviando {doc_name} a firmar: {dte_json['identificacion']['codigoGeneracion']}")
            logger.debug(f"Payload del firmador: {json.dumps(payload, indent=2)}")
            
            # Enviar solicitud al firmador
            response = requests.post(
                self.firmador_url,
                json=payload,
                headers=headers,
                timeout=30
            )
            
            logger.debug(f"Respuesta del firmador - Status: {response.status_code}")
            logger.debug(f"Respuesta del firmador - Body: {response.text}")
            
            if response.status_code == 200:
                try:
                    resultado = response.json()
                    if resultado.get('status') == 'OK':
                        logger.info(f"{doc_name} firmado exitosamente")
                        return resultado['body']
                    else:
                        # Manejar diferentes tipos de respuesta de error
                        if isinstance(resultado.get('body'), dict):
                            error_msg = resultado['body'].get('mensaje', 'Error desconocido en la firma')
                        else:
                            error_msg = str(resultado.get('body', 'Error desconocido en la firma'))
                        raise Exception(f"Error al firmar {doc_name}: {error_msg}")
                except json.JSONDecodeError:
                    raise Exception(f"Respuesta inválida del servicio de firma: {response.text}")
            else:
                raise Exception(f"Error HTTP {response.status_code} al firmar {doc_name}: {response.text}")
                
        except requests.exceptions.Timeout:
            raise Exception("Timeout al conectar con el servicio de firma")
        except requests.exceptions.ConnectionError:
            raise Exception("No se pudo conectar con el servicio de firma. Verifique que esté ejecutándose.")
        except Exception as e:
            # Log detallado para debugging
            logger.error(f"Error detallado en firmar_documento: {str(e)}")
            if 'dte_json' in locals():
                logger.error(f"JSON que causó el error: {json.dumps(dte_json, indent=2, default=str)}")
            raise

    def verificar_servicio_firma(self) -> bool:
        """
        Verifica que el servicio de firma esté disponible
        
        Returns:
            bool: True si el servicio está disponible
        """
        try:
            # Hacer una petición de prueba al servicio
            response = requests.get(
                self.firmador_url.replace('/firmardocumento/', '/'),
                timeout=5
            )
            return True
        except:
            return False
                
    def autenticar(self) -> str:
        """
        Autentica con el servicio de Hacienda y obtiene un token
        
        Returns:
            str: Token de autenticación
            
        Raises:
            Exception: Si hay error en la autenticación
        """
        # Verificar si tenemos un token válido en caché
        if self._token and self._token_expiry and datetime.now() < self._token_expiry:
            return self._token
            
        try:
            auth_url = self.dte_urls.get('auth')
            if not auth_url:
                raise Exception(f"URL de autenticación no configurada para ambiente {self.ambiente}")
            
            logger.info(f"Autenticando con Hacienda en: {auth_url}")
            
            # CORRECCIÓN PRINCIPAL: Usar application/x-www-form-urlencoded
            # Preparar datos de autenticación como form data
            data = {
                'user': self.dte_user,
                'pwd': self.dte_password
            }
            
            # Headers corregidos para form data
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'User-Agent': 'DTE-Django-App'
            }
            
            logger.debug(f"Datos de autenticación: user={self.dte_user}, pwd=[OCULTO]")
            
            response = requests.post(
                auth_url,
                data=data,  # Usar 'data' no 'json' para form-urlencoded
                headers=headers,
                timeout=30
            )
            
            logger.debug(f"Respuesta autenticación - Status: {response.status_code}")
            logger.debug(f"Respuesta autenticación - Headers: {dict(response.headers)}")
            logger.debug(f"Respuesta autenticación - Body: {response.text}")
            
            if response.status_code == 200:
                try:
                    resultado = response.json()
                    logger.debug(f"JSON respuesta: {json.dumps(resultado, indent=2)}")
                    
                    if resultado.get('status') == 'OK':
                        self._token = resultado['body']['token']
                        # Token válido por 24 horas en producción, 48 en pruebas
                        hours = 48 if self.ambiente == 'test' else 24
                        self._token_expiry = datetime.now() + timedelta(hours=hours)
                        logger.info("Autenticación exitosa con Hacienda")
                        return self._token
                    else:
                        error_msg = resultado.get('descripcionMsg', resultado.get('message', 'Error desconocido'))
                        raise Exception(f"Error de autenticación: {error_msg}")
                except json.JSONDecodeError as e:
                    logger.error(f"Error decodificando JSON: {e}")
                    logger.error(f"Respuesta cruda: {response.text}")
                    raise Exception(f"Respuesta no válida del servidor: {response.text}")
            else:
                error_msg = f"Error HTTP {response.status_code}"
                try:
                    error_json = response.json()
                    error_msg += f": {error_json.get('descripcionMsg', error_json.get('message', 'Error desconocido'))}"
                except:
                    error_msg += f": {response.text}"
                raise Exception(error_msg)
                
        except requests.exceptions.Timeout:
            raise Exception("Timeout al conectar con el servicio de autenticación de Hacienda")
        except requests.exceptions.ConnectionError:
            raise Exception(f"No se pudo conectar con Hacienda. Verifique la URL: {auth_url}")
        except Exception as e:
            logger.error(f"Error al autenticar con Hacienda: {str(e)}")
            raise
            
    # dte/services.py - Función enviar_dte CORREGIDA (solo la parte del nombre del documento)

    def enviar_dte(self, documento_firmado: str, token: str, codigo_generacion: str, 
                tipo_dte: str) -> Dict[str, Any]:
        """
        Envía el DTE firmado a Hacienda para su recepción
        Soporta FC (01), CCF (03) y NC (05)
        
        Args:
            documento_firmado: Documento firmado en formato JWS
            token: Token de autenticación
            codigo_generacion: Código de generación del DTE
            tipo_dte: Tipo de documento (01=FC, 03=CCF, 05=NC)
            
        Returns:
            Dict con la respuesta de Hacienda
            
        Raises:
            Exception: Si hay error en el envío
        """
        try:
            recepcion_url = self.dte_urls.get('recepcion')
            if not recepcion_url:
                raise Exception(f"URL de recepción no configurada para ambiente {self.ambiente}")
            
            # Preparar datos para envío
            ambiente_codigo = "00" if self.ambiente == 'test' else "01"
            
            # Determinar versión según tipo de documento
            version = 3 if tipo_dte == "03" or tipo_dte == "05" else 1
            
            data = {
                'ambiente': ambiente_codigo,
                'idEnvio': 1,  # Correlativo
                'version': version,
                'tipoDte': tipo_dte,
                'documento': documento_firmado,
                'codigoGeneracion': codigo_generacion
            }

            # CORRECCIÓN: Mapeo completo de nombres de documentos
            if tipo_dte == "03":
                doc_name = "CCF"
            elif tipo_dte == "05":  # NUEVO: Soporte para Nota de Crédito
                doc_name = "Nota de Crédito"
            elif tipo_dte == "14":
                doc_name = "FSE"
            else:  # tipo_dte == "01" o cualquier otro
                doc_name = "Factura"
                
            logger.debug(f"Datos de envío {doc_name}: {json.dumps(data, indent=2)}")
            
            headers = {
                'Authorization': token,
                'User-Agent': 'DTE-Django-App',
                'Content-Type': 'application/json'
            }
            
            logger.info(f"Enviando {doc_name} a Hacienda: {codigo_generacion}")
            
            response = requests.post(
                recepcion_url,
                json=data,
                headers=headers,
                timeout=30
            )
            
            logger.debug(f"Respuesta envío - Status: {response.status_code}")
            logger.debug(f"Respuesta envío - Body: {response.text}")
            
            if response.status_code == 200:
                resultado = response.json()
                logger.info(f"Respuesta de Hacienda para {doc_name}: {resultado.get('estado')} - {resultado.get('descripcionMsg')}")
                if resultado.get('observaciones'):
                    logger.info(f"Observaciones: {resultado.get('observaciones')}")
                return resultado
            else:
                try:
                    error_data = response.json()
                    error_msg = error_data.get('descripcionMsg', error_data.get('message', 'Error desconocido'))
                except:
                    error_msg = response.text
                raise Exception(f"Error HTTP {response.status_code}: {error_msg}")
                
        except requests.exceptions.Timeout:
            # Implementar política de reintentos según manual
            logger.warning(f"Timeout al enviar {doc_name}, consultando estado...")
            return self._consultar_estado_dte(token, codigo_generacion, tipo_dte)
        except Exception as e:
            logger.error(f"Error al enviar {doc_name}: {str(e)}")
            raise
            
    def _consultar_estado_dte(self, token: str, codigo_generacion: str, 
                              tipo_dte: str, reintentos: int = 2) -> Dict[str, Any]:
        """
        Consulta el estado de un DTE en Hacienda
        
        Implementa la política de reintentos según el manual técnico
        """
        consulta_url = self.dte_urls.get('consulta')
        doc_name = "CCF" if tipo_dte == "03" else "Factura"
        
        if not consulta_url:
            raise Exception(f"URL de consulta no configurada para ambiente {self.ambiente}")
        
        for intento in range(reintentos + 1):
            try:
                data = {
                    'nitEmisor': self.emisor.nit,
                    'tdte': tipo_dte,
                    'codigoGeneracion': codigo_generacion
                }
                
                headers = {
                    'Authorization': token,
                    'User-Agent': 'DTE-Django-App',
                    'Content-Type': 'application/json'
                }
                
                response = requests.post(
                    consulta_url,
                    json=data,
                    headers=headers,
                    timeout=8  # 8 segundos según manual
                )
                
                if response.status_code == 200:
                    return response.json()
                    
            except Exception as e:
                logger.warning(f"Intento {intento + 1} de consulta {doc_name} falló: {str(e)}")
                if intento < reintentos:
                    continue
                    
        # Si no se pudo verificar después de reintentos, considerar contingencia
        raise Exception(f"No se pudo verificar el estado del {doc_name}. Considere modo contingencia.")

    def enviar_a_hacienda(self, token: str, codigo_generacion: str, tipo_dte: str, dte_json: dict) -> Dict[str, Any]:
        """
        Método unificado para enviar DTE a Hacienda
        """
        try:
            # Primero firmar el documento
            documento_firmado = self.firmar_documento(dte_json)
            
            # Luego enviarlo a Hacienda
            respuesta = self.enviar_dte(documento_firmado, token, codigo_generacion, tipo_dte)
            
            # Procesar respuesta y extraer información relevante
            resultado = {
                'estado': respuesta.get('estado', 'ERROR'),
                'descripcion': respuesta.get('descripcionMsg', ''),
                'sello': respuesta.get('selloRecibido', ''),
                'observaciones': respuesta.get('observaciones', []),
                'fecha_procesamiento': respuesta.get('fhProcesamiento', ''),
                'respuesta_completa': respuesta
            }
            
            return resultado
            
        except Exception as e:
            logger.error(f"Error en enviar_a_hacienda: {str(e)}")
            return {
                'estado': 'ERROR',
                'descripcion': str(e),
                'sello': '',
                'observaciones': [str(e)],
                'fecha_procesamiento': '',
                'respuesta_completa': {}
            }
            
        # dte/services.py - Función enviar_correo_factura CORREGIDA

    # dte/services.py - Función enviar_correo_factura CORREGIDA para evitar JSON duplicado

    def enviar_correo_factura(self, factura, archivos_adjuntos: List[Dict[str, Any]]):
        """
        Envía la factura por correo electrónico al receptor
        Soporta FC, CCF y NC (Nota de Crédito)
        ACTUALIZADO: Usa Gmail API con fallback a Django Email
        """
        try:
            # Importar GmailService
            from .gmail_service import GmailService
            gmail_service = GmailService()
            
            tipo_doc = factura.identificacion.tipoDte.codigo
            
            # Mapeo completo de tipos de documento
            if tipo_doc == "03":
                doc_name = "Crédito Fiscal"
            elif tipo_doc == "05":
                doc_name = "Nota de Crédito Electrónica"
            elif tipo_doc == "14":
                doc_name = "Factura de Sujeto Excluido"
            else:
                doc_name = "Factura Electrónica"
            
            asunto = f"{doc_name} {factura.identificacion.numeroControl}"
            
            # Mensaje personalizado según tipo de documento (CONVERTIDO A HTML)
            if tipo_doc == "05":  # Nota de Crédito
                # Obtener información del documento relacionado
                doc_relacionado = factura.documentos_relacionados.first()
                doc_original_info = ""
                if doc_relacionado:
                    doc_original_info = f"""
    <li><strong>Documento Original:</strong> {doc_relacionado.tipoDocumento.texto}</li>
    <li><strong>Número Original:</strong> {doc_relacionado.numeroDocumento}</li>
    <li><strong>Fecha Original:</strong> {doc_relacionado.fechaEmision.strftime('%d/%m/%Y')}</li>
                    """
                
                # Obtener motivo si existe
                motivo_info = ""
                if hasattr(factura, 'nota_credito_detalle') and factura.nota_credito_detalle:
                    motivo_info = f"<p><strong>Motivo:</strong> {factura.nota_credito_detalle.motivo_nota_credito}</p>"
                
                mensaje = f"""
    <html>
    <body>
    <p>Estimado/a {factura.receptor.nombre},</p>

    <p>Le enviamos su {doc_name.lower()} con los siguientes datos:</p>

    <ul>
    <li><strong>Número de Control:</strong> {factura.identificacion.numeroControl}</li>
    <li><strong>Código de Generación:</strong> {factura.identificacion.codigoGeneracion}</li>
    <li><strong>Fecha de Emisión:</strong> {factura.identificacion.fecEmi}</li>
    <li><strong>Monto del Crédito:</strong> ${factura.resumen.totalPagar:.2f}</li>
    <li><strong>Estado:</strong> {factura.get_estado_hacienda_display()}</li>
    {doc_original_info}
    </ul>

    {motivo_info}

    <p>Esta nota de crédito debe aplicarse según corresponda a su contabilidad.</p>

    <p><strong>Adjuntamos:</strong></p>
    <ul>
    <li>{doc_name} en formato PDF (versión legible)</li>
    <li>Documento JSON con firma electrónica y sello de recepción</li>
    </ul>

    <p>Puede verificar la autenticidad de este documento en:<br>
    <a href="https://admin.factura.gob.sv/consultaPublica">https://admin.factura.gob.sv/consultaPublica</a></p>

    <p><strong>Código de Generación para verificación:</strong> {factura.identificacion.codigoGeneracion}</p>
    {"<p><strong>Sello de Recepción:</strong> " + factura.sello_recepcion + "</p>" if factura.sello_recepcion else ""}

    <p>Saludos cordiales,<br>
    {factura.emisor.nombre}<br>
    NIT: {factura.emisor.nit}</p>
    </body>
    </html>
                """
            else:
                # Mensaje para FC, CCF y FSE (CONVERTIDO A HTML)
                mensaje = f"""
    <html>
    <body>
    <p>Estimado/a {factura.receptor.nombre},</p>

    <p>Le enviamos su {doc_name.lower()} con los siguientes datos:</p>

    <ul>
    <li><strong>Número de Control:</strong> {factura.identificacion.numeroControl}</li>
    <li><strong>Código de Generación:</strong> {factura.identificacion.codigoGeneracion}</li>
    <li><strong>Fecha de Emisión:</strong> {factura.identificacion.fecEmi}</li>
    <li><strong>Total:</strong> ${factura.resumen.totalPagar:.2f}</li>
    <li><strong>Estado:</strong> {factura.get_estado_hacienda_display()}</li>
    </ul>

    <p><strong>Adjuntamos:</strong></p>
    <ul>
    <li>{doc_name} en formato PDF (versión legible)</li>
    <li>Documento JSON con firma electrónica y sello de recepción</li>
    </ul>

    <p>Puede verificar la autenticidad de este documento en:<br>
    <a href="https://admin.factura.gob.sv/consultaPublica">https://admin.factura.gob.sv/consultaPublica</a></p>

    <p><strong>Código de Generación para verificación:</strong> {factura.identificacion.codigoGeneracion}</p>
    {"<p><strong>Sello de Recepción:</strong> " + factura.sello_recepcion + "</p>" if factura.sello_recepcion else ""}

    <p>Saludos cordiales,<br>
    {factura.emisor.nombre}<br>
    NIT: {factura.emisor.nit}</p>
    </body>
    </html>
                """
            
            # NUEVO: Intentar Gmail API primero, luego fallback a Django Email
            success = gmail_service.enviar_correo(
                destinatario=factura.receptor.correo,
                asunto=asunto,
                cuerpo=mensaje,
                archivos_adjuntos=archivos_adjuntos,
                copia_oculta=[factura.emisor.correo] if factura.emisor.correo else None
            )
            
            if success:
                # Actualizar registro de envío
                factura.enviado_por_correo = True
                factura.fecha_envio_correo = timezone.localtime()
                factura.save(update_fields=['enviado_por_correo', 'fecha_envio_correo'])
                
                logger.info(f"{doc_name} enviado por correo a {factura.receptor.correo} usando Gmail API")
            else:
                # Si Gmail API falla, usar método original como último recurso
                logger.warning(f"Gmail API falló, intentando método original para {doc_name}")
                self._enviar_correo_django_fallback(factura, archivos_adjuntos, asunto, mensaje, doc_name)
                
        except Exception as e:
            logger.error(f"Error al enviar correo: {str(e)}")
            # Intentar método original como último recurso
            try:
                # Convertir HTML a texto plano para Django Email
                import re
                mensaje_texto = re.sub('<[^<]+?>', '', mensaje)  # Remover tags HTML básico
                mensaje_texto = mensaje_texto.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
                
                self._enviar_correo_django_fallback(factura, archivos_adjuntos, asunto, mensaje_texto, doc_name)
            except Exception as fallback_error:
                logger.error(f"Error en fallback de Django Email: {str(fallback_error)}")
                # No lanzar excepción para no interrumpir el proceso principal

    def _enviar_correo_django_fallback(self, factura, archivos_adjuntos, asunto, mensaje, doc_name):
        """Método de fallback usando Django Email (NUEVO MÉTODO AUXILIAR)"""
        try:
            from django.core.mail import EmailMessage
            
            email = EmailMessage(
                subject=asunto,
                body=mensaje,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[factura.receptor.correo],
                cc=[factura.emisor.correo] if factura.emisor.correo else []
            )
            
            # Adjuntar archivos
            for archivo in archivos_adjuntos:
                email.attach(
                    archivo['filename'],
                    archivo['content'],
                    archivo['mimetype']
                )
            
            email.send(fail_silently=False)
            
            # Actualizar registro de envío
            factura.enviado_por_correo = True
            factura.fecha_envio_correo = timezone.localtime()
            factura.save(update_fields=['enviado_por_correo', 'fecha_envio_correo'])
            
            logger.info(f"{doc_name} enviado por correo a {factura.receptor.correo} usando Django Email (fallback)")
            
        except Exception as e:
            logger.error(f"Error en Django Email fallback: {str(e)}")
            raise
            # No lanzar excepción para no interrumpir el proceso principal


    #Aqui comienzan los cambios de anulacion 
    # dte/services.py - AGREGAR al DTEService existente

# Agregar estos métodos a la clase DTEService existente
# dte/services.py - AGREGAR al DTEService existente

# Agregar estos métodos a la clase DTEService existente

    def anular_documento(self, anulacion_obj, token: str = None) -> Dict[str, Any]:
        """
        Procesa la anulación de un documento fiscal
        
        Args:
            anulacion_obj: Instancia de AnulacionDocumento
            token: Token de autenticación (opcional, se obtendrá si no se proporciona)
            
        Returns:
            Dict con el resultado del procesamiento
        """
        try:
            # Validar que el documento se puede anular
            if not anulacion_obj.puede_anularse:
                return {
                    'estado': 'ERROR',
                    'descripcion': 'El documento no puede ser anulado. Solo se pueden anular documentos ACEPTADOS.',
                    'sello': '',
                    'observaciones': ['Estado del documento no permite anulación'],
                    'fecha_procesamiento': '',
                    'respuesta_completa': {}
                }
            
            # Obtener token si no se proporciona
            if not token:
                token = self.autenticar()
            
            # Generar JSON de anulación
            anulacion_json = anulacion_obj.generar_json_anulacion()
            
            # Validar JSON contra esquema (opcional)
            # self._validar_esquema_anulacion(anulacion_json)
            print(anulacion_json)
            # Firmar documento de anulación
            documento_firmado = self.firmar_documento(anulacion_json)
            
            # Enviar anulación a Hacienda
            respuesta = self.enviar_anulacion_dte(
                documento_firmado=documento_firmado,
                token=token,
                codigo_generacion=anulacion_obj.codigo_generacion
            )
            
            # Procesar respuesta
            resultado = {
                'estado': respuesta.get('estado', 'ERROR'),
                'descripcion': respuesta.get('descripcionMsg', respuesta.get('mensaje', '')),
                'sello': respuesta.get('selloRecibido', ''),
                'observaciones': respuesta.get('observaciones', []),
                'fecha_procesamiento': respuesta.get('fhProcesamiento', respuesta.get('fechaHora', '')),
                'respuesta_completa': respuesta
            }
            
            # CORREGIDO: Actualizar objeto de anulación según el estado real de Hacienda
            estado_hacienda = resultado['estado']
            
            if estado_hacienda in ['RECIBIDO', 'ACEPTADO', 'PROCESADO']:  # ← AGREGAR 'PROCESADO'
                anulacion_obj.estado = 'ACEPTADO'  # Nuestro estado interno
                anulacion_obj.sello_recepcion = resultado['sello']
                anulacion_obj.fecha_procesamiento = timezone.now()
                anulacion_obj.observaciones = '; '.join(resultado['observaciones']) if resultado['observaciones'] else None
                anulacion_obj.respuesta_hacienda = resultado['respuesta_completa']
                
                # Actualizar estado del documento original
                anulacion_obj.documento_anular.estado_hacienda = 'ANULADO'
                anulacion_obj.documento_anular.save(update_fields=['estado_hacienda'])
                
                logger.info(f"Anulación {anulacion_obj.codigo_generacion} procesada exitosamente")
                
            else:
                anulacion_obj.estado = 'RECHAZADO'
                anulacion_obj.observaciones = '; '.join(resultado['observaciones']) if resultado['observaciones'] else resultado['descripcion']
                anulacion_obj.respuesta_hacienda = resultado['respuesta_completa']
                
                logger.warning(f"Anulación {anulacion_obj.codigo_generacion} rechazada: {resultado['descripcion']}")
            
            anulacion_obj.save()
            
            return resultado
            
        except Exception as e:
            logger.error(f"Error al anular documento: {str(e)}")
            
            # Actualizar estado de error
            anulacion_obj.estado = 'ERROR'
            anulacion_obj.observaciones = str(e)
            anulacion_obj.save()
            
            return {
                'estado': 'ERROR',
                'descripcion': str(e),
                'sello': '',
                'observaciones': [str(e)],
                'fecha_procesamiento': '',
                'respuesta_completa': {}
            }

    def enviar_anulacion_dte(self, documento_firmado: str, token: str, codigo_generacion: str) -> Dict[str, Any]:
        """
        Envía la anulación de DTE firmada a Hacienda
        
        Args:
            documento_firmado: Documento de anulación firmado en formato JWS
            token: Token de autenticación
            codigo_generacion: Código de generación de la anulación
            
        Returns:
            Dict con la respuesta de Hacienda
            
        Raises:
            Exception: Si hay error en el envío
        """
        try:
            # URL específica para anulaciones
            anulacion_url = self.dte_urls.get('anulacion')
            if not anulacion_url:
                # URL por defecto según documentación
                if self.ambiente == 'test':
                    anulacion_url = 'https://apitest.dtes.mh.gob.sv/fesv/anulardte'
                else:
                    anulacion_url = 'https://api.dtes.mh.gob.sv/fesv/anulardte'
            
            headers = {
                'Content-Type': 'application/json',
                'Authorization': token,
                'User-Agent': 'SistemaFacturacion/1.0'
            }
            
            # Preparar datos para envío (formato específico para anulaciones)
            data = {
                'ambiente': "00" if self.ambiente == 'test' else "01",
                'idEnvio': 1,
                'version': 2,  # Versión 2 para anulaciones
                'documento': documento_firmado,
                'codigoGeneracion': codigo_generacion
            }
            
            logger.info(f"Enviando anulación a: {anulacion_url}")
            logger.info(f"Código generación: {codigo_generacion}")
            
            response = requests.post(
                anulacion_url,
                headers=headers,
                json=data,
                timeout=30
            )
            
            logger.info(f"Status code: {response.status_code}")
            logger.info(f"Response: {response.text}")
            
            if response.status_code == 200:
                return response.json()
            else:
                error_msg = f"Error HTTP {response.status_code}: {response.text}"
                raise Exception(error_msg)
                
        except requests.exceptions.Timeout:
            raise Exception("Timeout al enviar anulación a Hacienda")
        except requests.exceptions.ConnectionError:
            raise Exception("Error de conexión con el servicio de Hacienda")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Error en la petición: {str(e)}")
        except Exception as e:
            logger.error(f"Error al enviar anulación: {str(e)}")
            raise

    def _validar_esquema_anulacion(self, anulacion_json: dict):
        """
        Valida el JSON de anulación contra el esquema anulacion-schema-v2.json
        """
        try:
            # Cargar esquema de anulación
            schema_path = getattr(settings, 'ANULACION_SCHEMA_PATH', None)
            if not schema_path:
                # Buscar en la carpeta schemas
                from pathlib import Path
                schema_path = Path(settings.BASE_DIR) / "dte" / "schemas" / "anulacion-schema-v2.json"
            
            if schema_path.exists():
                with open(schema_path, 'r', encoding='utf-8') as f:
                    schema = json.load(f)
                
                # Validar usando jsonschema
                from jsonschema import validate
                validate(instance=anulacion_json, schema=schema)
                logger.info("JSON de anulación válido según esquema")
            else:
                logger.warning("Esquema de anulación no encontrado, saltando validación")
                
        except Exception as e:
            logger.error(f"Error al validar esquema de anulación: {str(e)}")
            raise Exception(f"JSON de anulación inválido: {str(e)}")

    def consultar_estado_anulacion(self, codigo_generacion: str, token: str = None) -> Dict[str, Any]:
        """
        Consulta el estado de una anulación en Hacienda
        """
        try:
            if not token:
                token = self.autenticar()
            
            consulta_url = self.dte_urls.get('consulta', '')
            if not consulta_url:
                if self.ambiente == 'test':
                    consulta_url = 'https://apitest.dtes.mh.gob.sv/fesv/consultadte'
                else:
                    consulta_url = 'https://api.dtes.mh.gob.sv/fesv/consultadte'
            
            headers = {
                'Authorization': token,
                'User-Agent': 'SistemaFacturacion/1.0'
            }
            
            params = {
                'ambiente': "00" if self.ambiente == 'test' else "01",
                'codigoGeneracion': codigo_generacion
            }
            
            response = requests.get(
                consulta_url,
                headers=headers,
                params=params,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"Error al consultar estado: HTTP {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error al consultar estado de anulación: {str(e)}")
            return {
                'estado': 'ERROR',
                'descripcion': str(e)
            }