from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd

from fraudia_claims.config import COMPANY_DATA_DIR
from fraudia_claims.synthetic_data import generate_public_context


COMPANY_TABLES = ["asegurados", "polizas", "proveedores", "vehiculos", "siniestros", "documentos"]

REQUIRED_COLUMNS: dict[str, set[str]] = {
    "asegurados": {
        "id_asegurado",
        "segmento",
        "antiguedad",
        "ciudad",
        "numero_polizas",
        "reclamos_ultimos_12_meses",
        "mora_actual",
        "score_cliente_simulado",
        "lista_restrictiva",
    },
    "polizas": {
        "id_poliza",
        "id_asegurado",
        "ramo",
        "fecha_inicio",
        "fecha_fin",
        "prima",
        "suma_asegurada",
        "deducible",
        "canal_venta",
        "ciudad",
        "estado_poliza",
    },
    "proveedores": {
        "id_proveedor",
        "tipo",
        "ciudad",
        "reclamos_asociados",
        "monto_promedio_reclamado",
        "porcentaje_casos_observados",
        "antiguedad",
        "nombre",
        "ramo",
        "lista_restrictiva",
    },
    "vehiculos": {
        "id_vehiculo",
        "id_poliza",
    },
    "siniestros": {
        "id_siniestro",
        "id_poliza",
        "id_asegurado",
        "ramo",
        "cobertura",
        "fecha_ocurrencia",
        "fecha_reporte",
        "monto_reclamado",
        "monto_estimado",
        "monto_pagado",
        "estado",
        "sucursal",
        "descripcion",
        "documentos_completos",
        "id_proveedor",
        "beneficiario",
        "dias_desde_inicio_poliza",
        "dias_desde_fin_poliza",
        "dias_entre_ocurrencia_reporte",
        "historial_siniestros_asegurado",
        "etiqueta_fraude_simulada",
        "id_vehiculo",
        "id_conductor",
        "solo_rc",
        "tercero_identificado",
        "accidente_madrugada",
        "dinamica_imposible",
        "relato_ilogico",
        "denuncia_horas",
        "procedimiento_codigo",
        "factura_numero",
    },
    "documentos": {
        "id_documento",
        "id_siniestro",
        "tipo_documento",
        "entregado",
        "legible",
        "fecha_emision",
        "inconsistencia_detectada",
        "adulteracion_confirmada",
        "observacion",
    },
}


@dataclass(frozen=True)
class DataQualityIssue:
    table: str
    severity: str
    message: str


def _missing_columns(table: str, columns: Iterable[str]) -> set[str]:
    return REQUIRED_COLUMNS.get(table, set()) - set(columns)


def read_company_tables(directory: Path = COMPANY_DATA_DIR) -> dict[str, pd.DataFrame]:
    tables: dict[str, pd.DataFrame] = {}
    for table in COMPANY_TABLES:
        path = directory / f"{table}.csv"
        if not path.exists():
            raise FileNotFoundError(f"Falta {path}. Esperado dentro del paquete sintetico empresarial.")
        tables[table] = pd.read_csv(path)

    context_path = directory / "contexto_publico.csv"
    tables["contexto_publico"] = pd.read_csv(context_path) if context_path.exists() else generate_public_context()
    return tables


def validate_company_tables(tables: dict[str, pd.DataFrame]) -> list[DataQualityIssue]:
    issues: list[DataQualityIssue] = []
    for table in COMPANY_TABLES:
        frame = tables.get(table)
        if frame is None:
            issues.append(DataQualityIssue(table, "error", "Tabla requerida ausente."))
            continue
        missing = _missing_columns(table, frame.columns)
        if missing:
            issues.append(DataQualityIssue(table, "error", f"Columnas faltantes: {', '.join(sorted(missing))}."))
        if frame.empty:
            issues.append(DataQualityIssue(table, "warning", "Tabla vacia."))
        if table == "siniestros" and "id_siniestro" in frame.columns and frame["id_siniestro"].duplicated().any():
            issues.append(DataQualityIssue(table, "error", "Existen id_siniestro duplicados."))
        if "id_poliza" in frame.columns and table == "polizas" and frame["id_poliza"].duplicated().any():
            issues.append(DataQualityIssue(table, "error", "Existen id_poliza duplicados."))
    return issues


def data_quality_report(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    issues = validate_company_tables(tables)
    issue_counts: dict[str, int] = {}
    for issue in issues:
        if issue.severity == "error":
            issue_counts[issue.table] = issue_counts.get(issue.table, 0) + 1
    for table in COMPANY_TABLES:
        frame = tables.get(table, pd.DataFrame())
        rows.append(
            {
                "tabla": table,
                "filas": int(len(frame)),
                "columnas": int(len(frame.columns)),
                "errores": issue_counts.get(table, 0),
                "estado": "ok" if issue_counts.get(table, 0) == 0 else "revisar",
            }
        )
    return pd.DataFrame(rows)


def load_validated_company_tables(directory: Path = COMPANY_DATA_DIR) -> dict[str, pd.DataFrame]:
    tables = read_company_tables(directory)
    errors = [issue for issue in validate_company_tables(tables) if issue.severity == "error"]
    if errors:
        detail = " ".join(f"{issue.table}: {issue.message}" for issue in errors)
        raise ValueError(f"Dataset empresarial sintetico invalido. {detail}")
    return tables
