# dte/schema.py - ACTUALIZAR para incluir esquema de anulación

from pathlib import Path
import json

BASE_DIR = Path(__file__).resolve().parent
SCHEMA_FC_PATH = BASE_DIR / "schemas" / "fe-fc-v1.json"
SCHEMA_CCF_PATH = BASE_DIR / "schemas" / "fe-ccf-v3.json"
SCHEMA_FSE_PATH = BASE_DIR / "schemas" / "fe-fse-v1.json"
SCHEMA_NC_PATH = BASE_DIR / "schemas" / "fe-nc-v3.json"
# NUEVO: Esquema de anulación
SCHEMA_ANULACION_PATH = BASE_DIR / "schemas" / "anulacion-schema-v2.json"

# Cargar esquemas JSON existentes
with SCHEMA_FC_PATH.open(encoding="utf-8") as f:
    FE_SCHEMA = json.load(f)

with SCHEMA_CCF_PATH.open(encoding="utf-8") as f:
    CCF_SCHEMA = json.load(f)

with SCHEMA_FSE_PATH.open(encoding="utf-8") as f:
    FSE_SCHEMA = json.load(f)

with SCHEMA_NC_PATH.open(encoding="utf-8") as f:
    NC_SCHEMA = json.load(f)

# NUEVO: Cargar esquema de anulación
try:
    with SCHEMA_ANULACION_PATH.open(encoding="utf-8") as f:
        ANULACION_SCHEMA = json.load(f)
except FileNotFoundError:
    # Si no existe el archivo, usar esquema básico
    ANULACION_SCHEMA = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "Invalidacion de Documento Tributario Electronico",
        "type": "object",
        "required": ["identificacion", "emisor", "documento", "motivo"]
    }

# Función existente actualizada
def get_schema_for_tipo_dte(tipo_dte: str):
    """
    Retorna el esquema JSON apropiado según el tipo de DTE
    
    Args:
        tipo_dte: Código del tipo de documento ('01', '03', '14', '05', 'ANULACION')
        
    Returns:
        dict: Esquema JSON correspondiente
    """
    if tipo_dte == "03":
        return CCF_SCHEMA
    elif tipo_dte == "14":
        return FSE_SCHEMA
    elif tipo_dte == "05":
        return NC_SCHEMA
    elif tipo_dte == "ANULACION":  # NUEVO
        return ANULACION_SCHEMA
    else:  # Por defecto Factura ('01')
        return FE_SCHEMA

# NUEVA función específica para anulación
def get_anulacion_schema():
    """
    Retorna el esquema específico para anulaciones
    """
    return ANULACION_SCHEMA

# Mantener compatibilidad hacia atrás
DTE_SCHEMA = FE_SCHEMA