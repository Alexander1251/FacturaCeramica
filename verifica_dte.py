#!/usr/bin/env python
import os
import sys
import json

# 1) Asegurarnos de que el directorio base del proyecto esté en PYTHONPATH
sys.path.append(os.getcwd())

# 2) Configurar Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "inventario.settings")
import django

django.setup()

from jsonschema import validate, ValidationError
from dte.utils import build_dte_json
from dte.schema import FE_SCHEMA
from dte.models import FacturaElectronica


def main():
    if len(sys.argv) != 2:
        print("Uso: python verifica_dte.py <ID_FACTURA>")
        sys.exit(1)

    # 3) Leer y validar el argumento
    try:
        factura_id = int(sys.argv[1])
    except ValueError:
        print("ERROR: <ID_FACTURA> debe ser un número entero.")
        sys.exit(1)

    # 4) Obtener la factura de la base de datos
    try:
        factura = FacturaElectronica.objects.get(pk=factura_id)
    except FacturaElectronica.DoesNotExist:
        print(f"ERROR: No existe ninguna FacturaElectronica con ID = {factura_id}.")
        sys.exit(1)

    # 5) Generar el JSON usando build_dte_json
    try:
        resultado = build_dte_json(factura)
    except Exception as e:
        print("❌ Falló al construir el JSON de la factura:")
        print(f"   {e}")
        sys.exit(1)

    # 6) Mostrar el JSON generado (formateado)
    print("\n=== JSON generado ===")
    print(json.dumps(resultado, indent=2, ensure_ascii=False))
    print("======================\n")

    # 7) Validar contra el schema FE_SCHEMA
    try:
        validate(instance=resultado, schema=FE_SCHEMA)
        print("✅ El JSON generado es válido según FE_SCHEMA.")
    except ValidationError as e:
        print("❌ El JSON generado NO cumple con FE_SCHEMA:")
        print(f"   Mensaje de error: {e.message}")
        # e.path es una deque que indica la ruta hasta el valor inválido dentro del JSON
        loc = list(e.path)
        print(f"   Ubicación en JSON: {loc if loc else 'raíz'}")
        # e.schema_path indica la ruta dentro del esquema donde ocurre la violación
        ruta = list(e.schema_path)
        print(f"   Ruta en esquema: {ruta}\n")


if __name__ == "__main__":
    main()
