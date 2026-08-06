from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
SYNTHETIC_DIR = DATA_DIR / "synthetic"
PROCESSED_DIR = DATA_DIR / "processed"
DEFAULT_DB_PATH = Path(os.getenv("FRAUDIA_DB_PATH", PROCESSED_DIR / "fraudia_claims.db"))
DB_BACKEND = os.getenv("FRAUDIA_DB_BACKEND", "sqlite")
DATABASE_URL = os.getenv("FRAUDIA_DATABASE_URL", "")
DATA_SOURCE = os.getenv("FRAUDIA_DATA_SOURCE", "demo")
COMPANY_DATA_DIR = Path(os.getenv("FRAUDIA_COMPANY_DATA_DIR", DATA_DIR / "company_synthetic"))

# Comma-separated origins. Empty => localhost defaults for local demo.
_CORS_RAW = os.getenv("FRAUDIA_CORS_ORIGINS", "").strip()
CORS_ORIGINS = [origin.strip() for origin in _CORS_RAW.split(",") if origin.strip()] or [
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "http://127.0.0.1:4173",
    "http://localhost:4173",
]

MAX_CSV_UPLOAD_BYTES = int(os.getenv("FRAUDIA_MAX_CSV_BYTES", str(2 * 1024 * 1024)))
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("FRAUDIA_RATE_LIMIT_WINDOW", "60"))
RATE_LIMIT_MAX_REQUESTS = int(os.getenv("FRAUDIA_RATE_LIMIT_MAX", "60"))

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
