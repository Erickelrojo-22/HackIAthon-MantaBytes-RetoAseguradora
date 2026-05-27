from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
SYNTHETIC_DIR = DATA_DIR / "synthetic"
PROCESSED_DIR = DATA_DIR / "processed"
DEFAULT_DB_PATH = Path(os.getenv("FRAUDIA_DB_PATH", PROCESSED_DIR / "fraudia_claims.db"))

SEED = 2026
RAMOS = ("Vehiculos", "Salud", "Hogar")
LEVELS = {
    "Verde": {"min": 0, "max": 40, "accion": "Continuar flujo normal."},
    "Amarillo": {
        "min": 41,
        "max": 75,
        "accion": "Escalar a Unidad Antifraude para revision documental.",
    },
    "Rojo": {
        "min": 76,
        "max": 100,
        "accion": "Escalar a Unidad Antifraude para revision especializada de campo.",
    },
}

SCVS_CONTEXT_URL = "https://appscvsmovil.supercias.gob.ec/PortalInformacion/seguros.html"

CIUDADES = (
    "Guayaquil",
    "Quito",
    "Cuenca",
    "Manta",
    "Portoviejo",
    "Ambato",
    "Loja",
    "Santo Domingo",
)
