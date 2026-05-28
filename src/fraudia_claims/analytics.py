from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from fraudia_claims.config import DEFAULT_DB_PATH
from fraudia_claims.database import read_sql


REVIEW_LEVELS = ("Rojo", "Amarillo")
SAVINGS_RATE = 0.12


def _read_sql(query: str, db_path: Path = DEFAULT_DB_PATH, params: dict[str, Any] | None = None) -> pd.DataFrame:
    return read_sql(query, params=params or {}, db_path=db_path)


def executive_kpis(db_path: Path = DEFAULT_DB_PATH) -> dict[str, Any]:
    query = """
        SELECT
            COUNT(*) AS total_siniestros,
            SUM(CASE WHEN sc.nivel_riesgo = 'Rojo' THEN 1 ELSE 0 END) AS casos_rojos,
            SUM(CASE WHEN sc.nivel_riesgo = 'Amarillo' THEN 1 ELSE 0 END) AS casos_amarillos,
            SUM(CASE WHEN sc.nivel_riesgo IN ('Rojo', 'Amarillo') THEN 1 ELSE 0 END) AS casos_priorizados,
            SUM(si.monto_reclamado) AS monto_expuesto,
            SUM(CASE WHEN sc.nivel_riesgo IN ('Rojo', 'Amarillo') THEN si.monto_reclamado ELSE 0 END) AS monto_priorizado,
            AVG(sc.score_final) AS score_promedio
        FROM scores sc
        JOIN siniestros si ON si.id_siniestro = sc.id_siniestro
    """
    frame = _read_sql(query, db_path)
    row = frame.iloc[0].to_dict()
    total = int(row["total_siniestros"] or 0)
    prioritized = int(row["casos_priorizados"] or 0)
    red = int(row["casos_rojos"] or 0)
    yellow = int(row["casos_amarillos"] or 0)
    exposed = float(row["monto_expuesto"] or 0)
    prioritized_amount = float(row["monto_priorizado"] or 0)
    return {
        "total_siniestros": total,
        "casos_rojos": red,
        "casos_amarillos": yellow,
        "casos_priorizados": prioritized,
        "porcentaje_priorizado": round(100 * prioritized / total, 2) if total else 0,
        "porcentaje_rojo": round(100 * red / total, 2) if total else 0,
        "monto_expuesto": round(exposed, 2),
        "monto_priorizado": round(prioritized_amount, 2),
        "ahorro_potencial_simulado": round(prioritized_amount * SAVINGS_RATE, 2),
        "score_promedio": round(float(row["score_promedio"] or 0), 2),
    }


def top_cases(limit: int = 10, db_path: Path = DEFAULT_DB_PATH) -> pd.DataFrame:
    return _read_sql(
        """
        SELECT
            sc.id_siniestro,
            sc.score_final,
            sc.nivel_riesgo,
            si.ramo,
            si.cobertura,
            si.sucursal AS ciudad,
            si.monto_reclamado,
            pr.nombre AS proveedor,
            sc.explicacion_resumen
        FROM scores sc
        JOIN siniestros si ON si.id_siniestro = sc.id_siniestro
        LEFT JOIN proveedores pr ON pr.id_proveedor = si.id_proveedor
        ORDER BY sc.score_final DESC, si.monto_reclamado DESC
        LIMIT :limit
        """,
        db_path,
        {"limit": int(limit)},
    )


def provider_pareto(limit: int = 15, db_path: Path = DEFAULT_DB_PATH) -> pd.DataFrame:
    return _read_sql(
        """
        SELECT
            pr.nombre AS proveedor,
            pr.tipo,
            COUNT(*) AS total_siniestros,
            SUM(CASE WHEN sc.nivel_riesgo = 'Rojo' THEN 1 ELSE 0 END) AS alertas_rojas,
            SUM(CASE WHEN sc.nivel_riesgo IN ('Rojo', 'Amarillo') THEN si.monto_reclamado ELSE 0 END) AS monto_priorizado,
            ROUND(AVG(sc.score_final), 2) AS score_promedio
        FROM siniestros si
        JOIN scores sc ON sc.id_siniestro = si.id_siniestro
        LEFT JOIN proveedores pr ON pr.id_proveedor = si.id_proveedor
        GROUP BY pr.nombre, pr.tipo
        HAVING SUM(CASE WHEN sc.nivel_riesgo = 'Rojo' THEN 1 ELSE 0 END) > 0
        ORDER BY alertas_rojas DESC, monto_priorizado DESC
        LIMIT :limit
        """,
        db_path,
        {"limit": int(limit)},
    )


def risk_matrix(db_path: Path = DEFAULT_DB_PATH) -> pd.DataFrame:
    return _read_sql(
        """
        SELECT
            si.ramo,
            sc.nivel_riesgo,
            COUNT(*) AS total,
            ROUND(SUM(si.monto_reclamado), 2) AS monto_reclamado
        FROM scores sc
        JOIN siniestros si ON si.id_siniestro = sc.id_siniestro
        GROUP BY si.ramo, sc.nivel_riesgo
        ORDER BY si.ramo, sc.nivel_riesgo
        """,
        db_path,
    )


def city_concentration(limit: int = 10, db_path: Path = DEFAULT_DB_PATH) -> pd.DataFrame:
    return _read_sql(
        """
        SELECT
            si.sucursal AS ciudad,
            COUNT(*) AS total_siniestros,
            SUM(CASE WHEN sc.nivel_riesgo IN ('Rojo', 'Amarillo') THEN 1 ELSE 0 END) AS casos_revision,
            ROUND(100.0 * SUM(CASE WHEN sc.nivel_riesgo IN ('Rojo', 'Amarillo') THEN 1 ELSE 0 END) / COUNT(*), 2) AS porcentaje_revision,
            ROUND(AVG(sc.score_final), 2) AS score_promedio
        FROM siniestros si
        JOIN scores sc ON sc.id_siniestro = si.id_siniestro
        GROUP BY si.sucursal
        ORDER BY casos_revision DESC, score_promedio DESC
        LIMIT :limit
        """,
        db_path,
        {"limit": int(limit)},
    )


def document_findings(db_path: Path = DEFAULT_DB_PATH) -> pd.DataFrame:
    return _read_sql(
        """
        SELECT
            d.tipo_documento,
            COUNT(*) AS observaciones,
            SUM(CASE WHEN d.entregado = 0 THEN 1 ELSE 0 END) AS faltantes,
            SUM(CASE WHEN d.legible = 0 THEN 1 ELSE 0 END) AS ilegibles,
            SUM(CASE WHEN d.inconsistencia_detectada = 1 THEN 1 ELSE 0 END) AS inconsistentes,
            SUM(CASE WHEN d.adulteracion_confirmada = 1 THEN 1 ELSE 0 END) AS adulteraciones
        FROM documentos d
        JOIN scores sc ON sc.id_siniestro = d.id_siniestro
        WHERE sc.nivel_riesgo = 'Rojo'
          AND (d.entregado = 0 OR d.legible = 0 OR d.inconsistencia_detectada = 1 OR d.adulteracion_confirmada = 1)
        GROUP BY d.tipo_documento
        ORDER BY observaciones DESC
        """,
        db_path,
    )


def impact_summary(db_path: Path = DEFAULT_DB_PATH) -> dict[str, Any]:
    kpis = executive_kpis(db_path)
    providers = provider_pareto(3, db_path)
    top_provider = providers.iloc[0].to_dict() if not providers.empty else {}
    return {
        **kpis,
        "tasa_ahorro_simulada": SAVINGS_RATE,
        "proveedor_mas_observado": top_provider.get("proveedor", "N/A"),
        "alertas_rojas_proveedor_top": int(top_provider.get("alertas_rojas", 0) or 0),
    }
