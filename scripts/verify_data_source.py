from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fraudia_claims.database import execute_one
from fraudia_claims.storage import database_status


TABLES = [
    "asegurados",
    "polizas",
    "proveedores",
    "vehiculos",
    "siniestros",
    "documentos",
    "scores",
    "alertas",
    "metricas_modelo",
]


def main() -> int:
    status = database_status()
    print("FraudIA data source verification")
    print(f"backend: {status['backend']}")
    print(f"target: {status['target']}")
    print(f"data_source: {status['data_source']}")
    print()
    for table in TABLES:
        row = execute_one(f"SELECT COUNT(*) AS rows FROM {table}")
        print(f"{table}: {row['rows'] if row else 0}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
