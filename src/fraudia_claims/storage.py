from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from fraudia_claims.config import DEFAULT_DB_PATH, RAW_DIR, SYNTHETIC_DIR
from fraudia_claims.scoring import score_claims
from fraudia_claims.synthetic_data import SyntheticConfig, generate_all


BASE_TABLES = [
    "contexto_publico",
    "asegurados",
    "polizas",
    "proveedores",
    "vehiculos",
    "siniestros",
    "documentos",
]


def save_tables_to_csv(tables: dict[str, pd.DataFrame], directory: Path = SYNTHETIC_DIR) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for name, frame in tables.items():
        target_dir = RAW_DIR if name == "contexto_publico" else directory
        target_dir.mkdir(parents=True, exist_ok=True)
        frame.to_csv(target_dir / f"{name}.csv", index=False, encoding="utf-8")


def save_tables_to_sqlite(tables: dict[str, pd.DataFrame], db_path: Path = DEFAULT_DB_PATH) -> Path:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        for name, frame in tables.items():
            frame.to_sql(name, conn, index=False, if_exists="replace")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_scores_score ON scores(score_final DESC)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_scores_level ON scores(nivel_riesgo)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_alertas_siniestro ON alertas(id_siniestro)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_siniestros_proveedor ON siniestros(id_proveedor)")
    return db_path


def load_tables_from_csv(directory: Path = SYNTHETIC_DIR) -> dict[str, pd.DataFrame]:
    tables: dict[str, pd.DataFrame] = {}
    for name in BASE_TABLES:
        source = RAW_DIR / f"{name}.csv" if name == "contexto_publico" else directory / f"{name}.csv"
        tables[name] = pd.read_csv(source)
    return tables


def load_table(name: str, db_path: Path = DEFAULT_DB_PATH) -> pd.DataFrame:
    with sqlite3.connect(db_path) as conn:
        return pd.read_sql_query(f"SELECT * FROM {name}", conn)


def initialize_demo_data(
    force: bool = False,
    n_per_ramo: int = 1000,
    db_path: Path = DEFAULT_DB_PATH,
) -> Path:
    if db_path.exists() and not force:
        return db_path
    tables = generate_all(SyntheticConfig(n_per_ramo=n_per_ramo))
    scores, alerts = score_claims(tables)
    tables["scores"] = scores
    tables["alertas"] = alerts
    save_tables_to_csv(tables)
    return save_tables_to_sqlite(tables, db_path)
