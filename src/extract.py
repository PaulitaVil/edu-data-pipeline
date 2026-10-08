"""Extracción de indicadores educativos del Banco Mundial (capa RAW).

Descarga los datos tal cual los entrega la API y los guarda en data/raw/
sin modificarlos. La limpieza y la carga en la base de datos se hacen en
pasos posteriores del pipeline.

Uso (desde la raíz del repositorio):
    python src/extract.py
"""

import json
import time
from pathlib import Path

import requests

BASE_URL = "https://api.worldbank.org/v2"
RAW_DIR = Path("data/raw")
DATE_RANGE = "2000:2024"

# Código del indicador -> descripción legible
INDICATORS = {
    # Inversión y contexto económico
    "SE.XPD.TOTL.GD.ZS": "Gasto público en educación (% del PIB)",
    "NY.GDP.PCAP.CD": "PIB per cápita (US$ actuales)",
    # Resultados y acceso
    "SE.PRM.CMPT.ZS": "Finalización de primaria (% del grupo de edad)",
    "SE.ADT.LITR.ZS": "Alfabetización de adultos (%)",
    "SE.PRM.ENRL.TC.ZS": "Alumnos por docente, primaria",
    "HD.HCI.OVRL": "Índice de Capital Humano",
    # Dimensión de género
    "SE.PRM.ENRR.FE": "Matrícula primaria, niñas (% bruto)",
    "SE.PRM.ENRR.MA": "Matrícula primaria, niños (% bruto)",
    "SE.SEC.ENRR.FE": "Matrícula secundaria, niñas (% bruto)",
    "SE.SEC.ENRR.MA": "Matrícula secundaria, niños (% bruto)",
    "SE.ADT.LITR.FE.ZS": "Alfabetización adultos, mujeres (%)",
    "SE.ADT.LITR.MA.ZS": "Alfabetización adultos, hombres (%)",
    "SE.ENR.PRSC.FM.ZS": "Índice de paridad de género, primaria y secundaria",
}


def fetch_all_pages(url: str, params: dict) -> list:
    """Recorre todas las páginas de un endpoint y devuelve todos los registros."""
    records = []
    page = 1
    while True:
        response = requests.get(url, params={**params, "page": page}, timeout=30)
        response.raise_for_status()
        payload = response.json()

        # Si la API rechaza la consulta, devuelve solo un mensaje de error
        if len(payload) < 2:
            raise ValueError(f"Respuesta inesperada de la API: {payload}")

        meta, data = payload
        if data is None:  # el indicador existe pero no tiene datos
            break

        records.extend(data)
        if page >= meta["pages"]:
            break
        page += 1
        time.sleep(0.2)  # cortesía con el servidor
    return records


def save_json(data: list, path: Path) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    # 1) Metadatos de países (región, nivel de ingreso...). Nos permite
    #    distinguir países reales de agregados como "Mundo" y filtrar Latinoamérica.
    countries = fetch_all_pages(f"{BASE_URL}/country", {"format": "json", "per_page": 500})
    save_json(countries, RAW_DIR / "countries.json")
    print(f"countries: {len(countries)} registros")

    # 2) Un archivo JSON por indicador
    failed = []
    for code, name in INDICATORS.items():
        try:
            records = fetch_all_pages(
                f"{BASE_URL}/country/all/indicator/{code}",
                {"format": "json", "per_page": 20000, "date": DATE_RANGE},
            )
            save_json(records, RAW_DIR / f"{code}.json")
            print(f"{code}: {len(records)} registros - {name}")
        except (requests.RequestException, ValueError) as error:
            failed.append(code)
            print(f"ERROR en {code}: {error}")

    if failed:
        print(f"\nIndicadores con problemas: {failed}")
    else:
        print("\nExtracción completada sin errores.")


if __name__ == "__main__":
    main()
