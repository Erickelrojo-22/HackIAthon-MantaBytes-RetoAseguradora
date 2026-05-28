from __future__ import annotations

from pathlib import Path
import os

import pandas as pd

from fraudia_claims.config import COMPANY_DATA_DIR, DATA_SOURCE, DEFAULT_DB_PATH, RAW_DIR, SYNTHETIC_DIR
from fraudia_claims.database import (
    active_backend,
    database_label,
    execute_statement,
    read_sql,
    table_columns,
    table_names,
    write_frame,
)
from fraudia_claims.audit import ensure_audit_table
from fraudia_claims.reviews import ensure_review_tables
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

REQUIRED_DATABASE_TABLES = [*BASE_TABLES, "scores", "alertas", "metricas_modelo"]

REQUIRED_DATABASE_COLUMNS = {
    "scores": {"score_final", "nivel_riesgo", "score_modelo", "regla_min_amarillo", "nlp_min_amarillo"},
    "siniestros": {"beneficiario", "id_conductor"},
}


def save_tables_to_csv(tables: dict[str, pd.DataFrame], directory: Path = SYNTHETIC_DIR) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for name, frame in tables.items():
        target_dir = RAW_DIR if name == "contexto_publico" else directory
        target_dir.mkdir(parents=True, exist_ok=True)
        frame.to_csv(target_dir / f"{name}.csv", index=False, encoding="utf-8")


def create_indexes(db_path: Path = DEFAULT_DB_PATH) -> None:
    statements = [
        "CREATE INDEX IF NOT EXISTS idx_scores_score ON scores(score_final DESC)",
        "CREATE INDEX IF NOT EXISTS idx_scores_level ON scores(nivel_riesgo)",
        "CREATE INDEX IF NOT EXISTS idx_alertas_siniestro ON alertas(id_siniestro)",
        "CREATE INDEX IF NOT EXISTS idx_siniestros_proveedor ON siniestros(id_proveedor)",
        "CREATE INDEX IF NOT EXISTS idx_siniestros_asegurado ON siniestros(id_asegurado)",
        "CREATE INDEX IF NOT EXISTS idx_siniestros_poliza ON siniestros(id_poliza)",
    ]
    for statement in statements:
        execute_statement(statement, db_path=db_path)


def ensure_operational_tables(db_path: Path = DEFAULT_DB_PATH) -> None:
    ensure_review_tables(db_path)
    ensure_audit_table(db_path)


def save_tables_to_database(tables: dict[str, pd.DataFrame], db_path: Path = DEFAULT_DB_PATH) -> Path:
    for name, frame in tables.items():
        write_frame(name, frame, if_exists="replace", db_path=db_path)
    create_indexes(db_path)
    return db_path


def save_tables_to_sqlite(tables: dict[str, pd.DataFrame], db_path: Path = DEFAULT_DB_PATH) -> Path:
    return save_tables_to_database(tables, db_path)


def load_tables_from_csv(directory: Path = SYNTHETIC_DIR) -> dict[str, pd.DataFrame]:
    tables: dict[str, pd.DataFrame] = {}
    for name in BASE_TABLES:
        source = RAW_DIR / f"{name}.csv" if name == "contexto_publico" else directory / f"{name}.csv"
        tables[name] = pd.read_csv(source)
    return tables


def load_table(name: str, db_path: Path = DEFAULT_DB_PATH) -> pd.DataFrame:
    return read_sql(f"SELECT * FROM {name}", db_path=db_path)


def database_status(db_path: Path = DEFAULT_DB_PATH) -> dict[str, str]:
    return {
        "backend": active_backend(db_path),
        "target": database_label(db_path),
        "data_source": os.getenv("FRAUDIA_DATA_SOURCE", DATA_SOURCE),
    }


def _load_source_tables(n_per_ramo: int) -> dict[str, pd.DataFrame]:
    source = os.getenv("FRAUDIA_DATA_SOURCE", DATA_SOURCE).strip().lower() or "demo"
    if source == "company_synthetic":
        from fraudia_claims.ingestion import load_validated_company_tables

        return load_validated_company_tables(COMPANY_DATA_DIR)
    if source != "demo":
        raise ValueError("FRAUDIA_DATA_SOURCE debe ser demo o company_synthetic.")
    return generate_all(SyntheticConfig(n_per_ramo=n_per_ramo))


def initialize_demo_data(
    force: bool = False,
    n_per_ramo: int = 1000,
    db_path: Path = DEFAULT_DB_PATH,
) -> Path:
    if not force:
        existing = table_names(db_path)
        has_tables = set(REQUIRED_DATABASE_TABLES).issubset(existing)
        has_columns = True
        if has_tables:
            for table, required_columns in REQUIRED_DATABASE_COLUMNS.items():
                columns = table_columns(table, db_path)
                has_columns = has_columns and required_columns.issubset(columns)
        if has_tables and has_columns:
            ensure_operational_tables(db_path)
            return db_path
    tables = _load_source_tables(n_per_ramo)
    scores, alerts, metrics = score_claims(tables, include_metrics=True)
    tables["scores"] = scores
    tables["alertas"] = alerts
    tables["metricas_modelo"] = metrics
    if os.getenv("FRAUDIA_DATA_SOURCE", DATA_SOURCE).strip().lower() in ("", "demo"):
        save_tables_to_csv(tables)
    path = save_tables_to_database(tables, db_path)
    ensure_operational_tables(db_path)
    return path
