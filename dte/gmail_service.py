import os
import json
import base64
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Dict, Any
from django.conf import settings

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    GMAIL_AVAILABLE = True
except ImportError:
    GMAIL_AVAILABLE = False

logger = logging.getLogger(__name__)


class GmailService:
    """Servicio para envío de correos usando Gmail API"""
    
    def __init__(self):
        self.service = None
        self.enabled = getattr(settings, 'GMAIL_API_ENABLED', False) and GMAIL_AVAILABLE
        
        if self.enabled:
            try:
                self.service = self._authenticate()
            except Exception as e:
                logger.error(f"Error inicializando Gmail API: {str(e)}")
                self.enabled = False
    
    def _authenticate(self):
        """Autentica con Gmail API"""
        creds = None
        token_file = getattr(settings, 'GMAIL_TOKEN_FILE', None)
        credentials_file = getattr(settings, 'GMAIL_CREDENTIALS_FILE', None)
        scopes = getattr(settings, 'GMAIL_SCOPES', ['https://www.googleapis.com/auth/gmail.send'])
        
        if not credentials_file or not os.path.exists(credentials_file):
            raise Exception("Archivo de credenciales de Gmail no encontrado")
        
        # Cargar token existente
        if token_file and os.path.exists(token_file):
            creds = Credentials.from_authorized_user_file(token_file, scopes)
        
        # Si no hay credenciales válidas, autenticar
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(credentials_file, scopes)
                creds = flow.run_local_server(port=0)
            
            # Guardar credenciales para la próxima ejecución
            if token_file:
                with open(token_file, 'w') as token:
                    token.write(creds.to_json())
        
        return build('gmail', 'v1', credentials=creds)
    
    def enviar_correo(self, destinatario: str, asunto: str, cuerpo: str, 
                      archivos_adjuntos: List[Dict[str, Any]] = None,
                      copia_oculta: List[str] = None) -> bool:
        """
        Envía un correo usando Gmail API
        
        Args:
            destinatario: Email del destinatario
            asunto: Asunto del correo
            cuerpo: Cuerpo del correo en HTML o texto plano
            archivos_adjuntos: Lista de archivos [{filename, content, mimetype}]
            copia_oculta: Lista de emails para copia oculta
        
        Returns:
            bool: True si el envío fue exitoso
        """
        if not self.enabled or not self.service:
            logger.warning("Gmail API no está habilitado, usando fallback")
            return self._fallback_email(destinatario, asunto, cuerpo, archivos_adjuntos, copia_oculta)
        
        try:
            # Crear mensaje
            mensaje = self._crear_mensaje(destinatario, asunto, cuerpo, archivos_adjuntos, copia_oculta)
            
            # Enviar mensaje
            result = self.service.users().messages().send(userId='me', body=mensaje).execute()
            
            logger.info(f"Correo enviado exitosamente a {destinatario}. Message ID: {result.get('id')}")
            return True
            
        except Exception as e:
            logger.error(f"Error enviando correo con Gmail API: {str(e)}")
            # Intentar fallback
            return self._fallback_email(destinatario, asunto, cuerpo, archivos_adjuntos, copia_oculta)
    
    def _crear_mensaje(self, destinatario: str, asunto: str, cuerpo: str,
                       archivos_adjuntos: List[Dict[str, Any]] = None,
                       copia_oculta: List[str] = None) -> dict:
        """Crea el mensaje en formato RFC2822"""
        
        mensaje = MIMEMultipart()
        mensaje['to'] = destinatario
        mensaje['subject'] = asunto
        
        # Agregar remitente desde settings
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com')
        mensaje['from'] = from_email
        
        # Copia oculta
        if copia_oculta:
            mensaje['bcc'] = ', '.join(copia_oculta)
        
        # Cuerpo del mensaje
        mensaje.attach(MIMEText(cuerpo, 'html' if '<html>' in cuerpo.lower() else 'plain'))
        
        # Archivos adjuntos
        if archivos_adjuntos:
            for archivo in archivos_adjuntos:
                adjunto = MIMEBase('application', 'octet-stream')
                
                # Manejar contenido como bytes o string
                content = archivo['content']
                if isinstance(content, str):
                    content = content.encode('utf-8')
                
                adjunto.set_payload(content)
                encoders.encode_base64(adjunto)
                
                adjunto.add_header(
                    'Content-Disposition',
                    f'attachment; filename="{archivo["filename"]}"'
                )
                mensaje.attach(adjunto)
        
        # Codificar mensaje
        raw_message = base64.urlsafe_b64encode(mensaje.as_bytes()).decode('utf-8')
        
        return {'raw': raw_message}
    
    def _fallback_email(self, destinatario: str, asunto: str, cuerpo: str,
                        archivos_adjuntos: List[Dict[str, Any]] = None,
                        copia_oculta: List[str] = None) -> bool:
        """Fallback usando el sistema de correo de Django"""
        try:
            from django.core.mail import EmailMessage
            
            email = EmailMessage(
                subject=asunto,
                body=cuerpo,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com'),
                to=[destinatario],
                bcc=copia_oculta or []
            )
            
            # Detectar si es HTML
            if '<html>' in cuerpo.lower() or '<p>' in cuerpo.lower():
                email.content_subtype = 'html'
            
            # Adjuntar archivos
            if archivos_adjuntos:
                for archivo in archivos_adjuntos:
                    content = archivo['content']
                    if isinstance(content, str):
                        content = content.encode('utf-8')
                    
                    email.attach(
                        archivo['filename'],
                        content,
                        archivo['mimetype']
                    )
            
            email.send(fail_silently=False)
            logger.info(f"Correo enviado usando Django fallback a {destinatario}")
            return True
            
        except Exception as e:
            logger.error(f"Error en fallback email: {str(e)}")
            return False
    
    def verificar_configuracion(self) -> Dict[str, Any]:
        """Verifica la configuración de Gmail API"""
        status = {
            'gmail_api_disponible': GMAIL_AVAILABLE,
            'gmail_habilitado': self.enabled,
            'servicio_inicializado': self.service is not None,
            'archivos_configuracion': {}
        }
        
        # Verificar archivos de configuración
        credentials_file = getattr(settings, 'GMAIL_CREDENTIALS_FILE', None)
        token_file = getattr(settings, 'GMAIL_TOKEN_FILE', None)
        
        if credentials_file:
            status['archivos_configuracion']['credentials'] = {
                'ruta': credentials_file,
                'existe': os.path.exists(credentials_file)
            }
        
        if token_file:
            status['archivos_configuracion']['token'] = {
                'ruta': token_file,
                'existe': os.path.exists(token_file)
            }
        
        return status