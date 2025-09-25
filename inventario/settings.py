
# ===== SETTINGS.PY CORREGIDO =====
"""
Django settings for inventario project.
"""

from pathlib import Path
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-k)b#a!mksaj(ua18bdeui@p&*kf@%=+#nguwo-l*wiph(-%y&^'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['165.227.126.13', 'localhost', '127.0.0.1']

# Application definition
INSTALLED_APPS = [
    # Tu app personalizada primero
    'crispy_forms',
    "crispy_bootstrap5",
    'widget_tweaks',
    'productos',
    'dte',

    # Apps de autenticación y sesiones de Django
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',

    # Admin al final
    'django.contrib.admin',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'productos.middleware.AdminRequiredMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'inventario.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],  # CORREGIDO: Eliminé la duplicación
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'inventario.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'es'
TIME_ZONE = 'America/El_Salvador'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
# CORREGIDO: Configuración de archivos estáticos unificada
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'  # Para producción

# CORREGIDO: Configuración de archivos media unificada y corregida
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'  # Usar Path en lugar de os.path.join

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Configuración de usuario personalizado
AUTH_USER_MODEL = 'productos.Usuario'
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = 'login'

# Ambiente DTE (test/prod)
DTE_AMBIENTE = 'test'  # Cambiar a 'prod' en producción

# URLs del servicio DTE según el ambiente
DTE_URLS = {
    'test': {
        'auth': 'https://apitest.dtes.mh.gob.sv/seguridad/auth',
        'recepcion': 'https://apitest.dtes.mh.gob.sv/fesv/recepciondte',
        'consulta': 'https://apitest.dtes.mh.gob.sv/fesv/recepcion/consultadte/',
        'anulacion': 'https://apitest.dtes.mh.gob.sv/fesv/anulardte',
        'contingencia': 'https://apitest.dtes.mh.gob.sv/fesv/contingencia',  # NUEVO
    },
    'prod': {
        'auth': 'https://api.dtes.mh.gob.sv/seguridad/auth',
        'recepcion': 'https://api.dtes.mh.gob.sv/fesv/recepciondte', 
        'consulta': 'https://api.dtes.mh.gob.sv/fesv/recepcion/consultadte/',
        'anulacion': 'https://api.dtes.mh.gob.sv/fesv/anulardte',
        'contingencia': 'https://apitest.dtes.mh.gob.sv/fesv/contingencia',  # NUEVO
    }
}

CONTINGENCIA_CONFIG = {
    'MAX_DOCUMENTOS_PRUEBA': 10,
    'TIMEOUT_CONTINGENCIA': 60,
    'TIPOS_DOCUMENTO_SOPORTADOS': ['01', '03', '05', '14'],
    'TIPOS_CONTINGENCIA': {
        1: 'Interrupción del suministro eléctrico',
        2: 'Interrupción del servicio de Internet', 
        3: 'Falla en el sistema informático del contribuyente',
        4: 'Falla en el sistema del Ministerio de Hacienda',
        5: 'Otras contingencias'
    }
}

# Credenciales para autenticación con Hacienda
DTE_USER = '06032509661015'  # Tu NIT de emisor registrado
DTE_PASSWORD = 'Gmda250966$'  # Tu contraseña del sistema de Hacienda
ANULACION_SCHEMA_PATH = BASE_DIR / "dte" / "schemas" / "anulacion-schema-v2.json"
# Configuración del firmador electrónico
FIRMADOR_URL = 'http://localhost:8113/firmardocumento/'
DTE_CERTIFICADO_PASSWORD = 'maam26082025$'  # Contraseña del certificado digital
ANULACION_CONFIG = {
    'TIPOS_DOCUMENTO_PERSONA': [
        ('36', 'NIT'),
        ('13', 'DUI'),
        ('02', 'Carnet de Residente'),
        ('03', 'Pasaporte'),
        ('37', 'Otro'),
    ],
    'MOTIVO_MIN_LENGTH': 5,
    'MOTIVO_MAX_LENGTH': 250,
    'NOMBRE_MIN_LENGTH': 5,
    'NOMBRE_MAX_LENGTH': 100,
    'NUM_DOC_MIN_LENGTH': 3,
    'NUM_DOC_MAX_LENGTH': 20,
}
# Configuración de certificados (para firma electrónica)
DTE_PRIVATE_KEY = BASE_DIR / "certs" / "clave_privada.pem"
DTE_PRIVATE_PASS = DTE_CERTIFICADO_PASSWORD  # Usar la misma contraseña

# Configuración de timeouts y reintentos
DTE_REQUEST_TIMEOUT = 30
DTE_MAX_REINTENTOS = 2
DTE_CONTINGENCIA_ACTIVA = False

# Directorio temporal para archivos DTE
DTE_TEMP_DIR = BASE_DIR / 'temp' / 'dte'
DTE_TEMP_DIR.mkdir(parents=True, exist_ok=True)


# Crear directorio DTE si no existe
DTE_TEMP_DIR.mkdir(parents=True, exist_ok=True)

# Configuración de Crispy Forms
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# Configuración de Email
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_HOST_USER = 'inventario221@gmail.com'
EMAIL_HOST_PASSWORD = 'iotyvsbjcfdoicjr'
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = "Mi Empresa <inventario221@gmail.com>"

# Agregar a settings.py para ver los logs detallados

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': 'debug.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'dte.services': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'dte.views': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

ANULACION_VALIDATIONS = {
    'ESTADOS_ANULABLES': ['ACEPTADO', 'ACEPTADO CON OBSERVACIONES'],
    'TIPOS_DTE_ANULABLES': ['01', '03', '05', '14'],  # FC, CCF, NC, FSE
    'REQUIERE_MOTIVO': True,
    'REQUIERE_RESPONSABLE': True,
    'REQUIERE_SOLICITANTE': True,
}

# settings.py

# … otras configuraciones …

# Documentos Tributarios Electrónicos (DTE)
# settings.py - Sección DTE corregida




# Gmail API Configuration
GMAIL_API_ENABLED = True  # Set to False to use Django's default email
GMAIL_CREDENTIALS_FILE = os.path.join(BASE_DIR, 'gmail_credentials.json')  # Path to your credentials
GMAIL_TOKEN_FILE = os.path.join(BASE_DIR, 'gmail_token.json')  # Path to store token
GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.send']