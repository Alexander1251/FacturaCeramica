from django.core.management.base import BaseCommand
import csv, pathlib

from dte.models import (
    AmbienteDestino,        # CAT-001
    TipoDocumento,          # CAT-002
    ModeloFacturacion,      # CAT-003
    TipoTransmision,        # CAT-004
    TipoContingencia,       # CAT-005
    GeneracionDocumento,    # CAT-007
    TipoEstablecimiento,    # CAT-009
    TipoServicio,           # CAT-010
    TipoItem,               # CAT-011
    Departamento,           # CAT-012
    Municipio,              # CAT-013
    UnidadMedida,           # CAT-014
    Tributo,                # CAT-015
    CondicionOperacion,     # CAT-016
    FormaPago,              # CAT-017
    Plazo,                  # CAT-018
    ActividadEconomica,     # CAT-019
    Pais,
    OtroDocumentoAsociado,  # CAT-021
    TipoDocReceptor,        # CAT-022
    DocumentoContingencia,  # CAT-023
    TipoInvalidacion,       # CAT-024
)

class Command(BaseCommand):
    help = "Carga en BD los catálogos 001–019 (sin 006/008) y 021–024 para FE"

    def add_arguments(self, parser):
        parser.add_argument('archivos', nargs='+',
                            help='Rutas a CSV de catálogos (p.ej. cat001.csv)')

    def handle(self, *args, **opts):
        tabla = {
            'cat001': AmbienteDestino,
            'cat002': TipoDocumento,
            'cat003': ModeloFacturacion,
            'cat004': TipoTransmision,
            'cat005': TipoContingencia,
            'cat007': GeneracionDocumento,
            'cat009': TipoEstablecimiento,
            'cat010': TipoServicio,
            'cat011': TipoItem,
            'cat012': Departamento,
            'cat013': Municipio,
            'cat014': UnidadMedida,
            'cat015': Tributo,
            'cat016': CondicionOperacion,
            'cat017': FormaPago,
            'cat018': Plazo,
            'cat019': ActividadEconomica,
            'cat020': Pais,
            'cat021': OtroDocumentoAsociado,
            'cat022': TipoDocReceptor,
            'cat023': DocumentoContingencia,
            'cat024': TipoInvalidacion,
        }

        for ruta in opts['archivos']:
            key = pathlib.Path(ruta).stem.lower()
            Model = tabla.get(key)
            if not Model:
                self.stdout.write(self.style.WARNING(f"Ignorando {ruta}: sin modelo para '{key}'"))
                continue

            with open(ruta, newline='', encoding='utf-8') as f:
                for row in csv.DictReader(f):
                    Model.objects.update_or_create(
                        codigo=row['codigo'],
                        defaults={'texto': row['texto']}
                    )
            self.stdout.write(self.style.SUCCESS(f"Cargado catálogo {key}"))

        self.stdout.write(self.style.SUCCESS("¡Todos los catálogos requeridos para FE han sido importados!"))
