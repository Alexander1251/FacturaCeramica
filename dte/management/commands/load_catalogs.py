import os
import csv

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from dte.models import (
    AmbienteDestino,       # cat001
    TipoDocumento,         # cat002
    ModeloFacturacion,     # cat003
    TipoTransmision,       # cat004
    TipoContingencia,      # cat005
    GeneracionDocumento,   # cat007
    TipoEstablecimiento,   # cat009
    TipoServicio,          # cat010
    TipoItem,              # cat011
    Departamento,          # cat012
    Municipio,             # cat013
    UnidadMedida,          # cat014
    Tributo,               # cat015
    CondicionOperacion,    # cat016
    FormaPago,             # cat017
    Plazo,                 # cat018
    ActividadEconomica,    # cat019
    Pais,                  # cat020
    OtroDocumentoAsociado, # cat021
    TipoDocReceptor,       # cat022
    DocumentoContingencia, # cat023
    TipoInvalidacion       # cat024
)


class Command(BaseCommand):
    help = (
        "Carga todos los CSV de catálogos (cat001.csv … cat024.csv) "
        "desde dte/fixtures/ a sus respectivos modelos, incluyendo "
        "un manejo especial para Municipios (tres columnas)."
    )

    def handle(self, *args, **options):
        # ----------------------------------------
        # 1) Carpeta de los CSV
        # ----------------------------------------
        base_dir = os.path.join(settings.BASE_DIR, "dte", "fixtures")
        if not os.path.isdir(base_dir):
            raise CommandError(f"No se encontró la carpeta de CSV: {base_dir}")

        # ----------------------------------------
        # 2) Mapeo nombre de archivo (sin .csv) → Modelo
        # ----------------------------------------
        file_to_model = {
            "cat001": AmbienteDestino,
            "cat002": TipoDocumento,
            "cat003": ModeloFacturacion,
            "cat004": TipoTransmision,
            "cat005": TipoContingencia,
            "cat007": GeneracionDocumento,
            "cat009": TipoEstablecimiento,
            "cat010": TipoServicio,
            "cat011": TipoItem,
            "cat012": Departamento,
            "cat013": Municipio,           # Atención: Municipios necesita 3 columnas
            "cat014": UnidadMedida,
            "cat015": Tributo,
            "cat016": CondicionOperacion,
            "cat017": FormaPago,
            "cat018": Plazo,
            "cat019": ActividadEconomica,
            "cat020": Pais,
            "cat021": OtroDocumentoAsociado,
            "cat022": TipoDocReceptor,
            "cat023": DocumentoContingencia,
            "cat024": TipoInvalidacion,
        }

        # ----------------------------------------
        # 3) Recorro archivos *.csv en la carpeta
        # ----------------------------------------
        for filename in sorted(os.listdir(base_dir)):
            name, ext = os.path.splitext(filename)
            if ext.lower() != ".csv":
                continue

            if name not in file_to_model:
                self.stdout.write(self.style.WARNING(
                    f"Ignorando “{filename}”: no está mapeado a ningún modelo."
                ))
                continue

            modelo = file_to_model[name]
            ruta_csv = os.path.join(base_dir, filename)

            self.stdout.write(f"\n→ Cargando “{filename}”  →  Modelo: {modelo.__name__}")

            total = 0
            errores = 0

            with open(ruta_csv, encoding="utf-8") as f:
                reader = csv.reader(f)

                for row_num, row in enumerate(reader, start=1):
                    # —————————————————————————————————————————————
                    # 1) Salto la fila de encabezado si “row_num == 1” contiene “codigo”
                    # —————————————————————————————————————————————
                    if row_num == 1:
                        joined = ",".join(cell.strip().lower() for cell in row)
                        if "codigo" in joined:
                            continue

                    # —————————————————————————————————————————————
                    # 2) Ignoro filas completamente vacías
                    # —————————————————————————————————————————————
                    if not row or all(cell.strip() == "" for cell in row):
                        continue

                    # —————————————————————————————————————————————
                    # 3) Proceso Municipios (cat013) → espero 3 columnas
                    # —————————————————————————————————————————————
                    if name == "cat013":
                        if len(row) < 3:
                            errores += 1
                            self.stdout.write(self.style.ERROR(
                                f"  Línea {row_num}: menos de 3 columnas en {filename}"
                            ))
                            continue

                        cod_municipio = row[0].strip()
                        txt_municipio = row[1].strip()
                        cod_departamento = row[2].strip()

                        if not (cod_municipio and txt_municipio and cod_departamento):
                            errores += 1
                            self.stdout.write(self.style.ERROR(
                                f"  Línea {row_num}: código/texto/departamento vacío en {filename}"
                            ))
                            continue

                        try:
                            depto = Departamento.objects.get(codigo=cod_departamento)
                        except Departamento.DoesNotExist:
                            errores += 1
                            self.stdout.write(self.style.ERROR(
                                f"  Línea {row_num}: no existe Departamento con código “{cod_departamento}”"
                            ))
                            continue

                        try:
                            # ← Aquí está la única línea que cambia: 
                            # usamos BOTH departamento y código como lookup:
                            obj, created = Municipio.objects.update_or_create(
                                departamento=depto,
                                codigo=cod_municipio,
                                defaults={"texto": txt_municipio}
                            )
                            total += 1
                        except Exception as e:
                            errores += 1
                            self.stdout.write(self.style.ERROR(
                                f"  Línea {row_num}: error guardando Municipio → {e}"
                            ))
                            continue

                    # —————————————————————————————————————————————
                    # 4) Proceso el resto de catXXX → espero 2 columnas
                    # —————————————————————————————————————————————
                    else:
                        if len(row) < 2:
                            errores += 1
                            self.stdout.write(self.style.ERROR(
                                f"  Línea {row_num}: menos de 2 columnas en {filename}"
                            ))
                            continue

                        codigo = row[0].strip()
                        texto = row[1].strip()

                        if not (codigo and texto):
                            errores += 1
                            self.stdout.write(self.style.ERROR(
                                f"  Línea {row_num}: algún campo vacío en {filename}"
                            ))
                            continue

                        try:
                            obj, created = modelo.objects.update_or_create(
                                codigo=codigo,
                                defaults={"texto": texto}
                            )
                            total += 1
                        except Exception as e:
                            errores += 1
                            self.stdout.write(self.style.ERROR(
                                f"  Línea {row_num}: error guardando {modelo.__name__} → {e}"
                            ))
                            continue

            # Informe final por cada CSV
            self.stdout.write(self.style.SUCCESS(
                f"  {modelo.__name__}: {total} registros procesados, {errores} errores."
            ))

        self.stdout.write(self.style.SUCCESS("\n¡Carga de catálogos finalizada!"))
