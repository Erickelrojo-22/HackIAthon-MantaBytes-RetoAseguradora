from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from fraudia_claims.analytics import impact_summary
from fraudia_claims.config import DEFAULT_DB_PATH
from fraudia_claims.scoring import level_from_score


def _connect(db_path: Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _rows(cursor: sqlite3.Cursor) -> list[dict[str, Any]]:
    return [dict(row) for row in cursor.fetchall()]


def list_risk_cases(limit: int = 10, level: str | None = None, db_path: Path = DEFAULT_DB_PATH) -> list[dict[str, Any]]:
    level_clause = ""
    params: list[Any] = []
    if level:
        level_clause = "WHERE sc.nivel_riesgo = ?"
        params.append(level)
    params.append(int(limit))
    query = f"""
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
        {level_clause}
        ORDER BY sc.score_final DESC, si.monto_reclamado DESC
        LIMIT ?
    """
    with _connect(db_path) as conn:
        return _rows(conn.execute(query, params))


def get_claim_detail(id_siniestro: str, db_path: Path = DEFAULT_DB_PATH) -> dict[str, Any]:
    query = """
        SELECT
            si.*,
            sc.score_final,
            sc.score_reglas,
            sc.score_anomalia,
            sc.score_nlp,
            sc.nivel_riesgo,
            sc.accion_sugerida,
            sc.similitud_narrativa,
            sc.siniestro_similar,
            sc.explicacion_resumen,
            pr.nombre AS proveedor_nombre,
            pr.tipo AS proveedor_tipo,
            pr.lista_restrictiva AS proveedor_lista_restrictiva
        FROM siniestros si
        JOIN scores sc ON sc.id_siniestro = si.id_siniestro
        LEFT JOIN proveedores pr ON pr.id_proveedor = si.id_proveedor
        WHERE si.id_siniestro = ?
    """
    with _connect(db_path) as conn:
        row = conn.execute(query, [id_siniestro]).fetchone()
        if row is None:
            return {"error": f"No existe el siniestro {id_siniestro}."}
        detail = dict(row)
        detail["alertas"] = _rows(
            conn.execute(
                """
                SELECT codigo, categoria, severidad, puntos, descripcion, evidencia, es_critica
                FROM alertas
                WHERE id_siniestro = ?
                ORDER BY puntos DESC, codigo
                """,
                [id_siniestro],
            )
        )
        detail["documentos"] = _rows(
            conn.execute(
                """
                SELECT tipo_documento, entregado, legible, inconsistencia_detectada, adulteracion_confirmada, observacion
                FROM documentos
                WHERE id_siniestro = ?
                ORDER BY tipo_documento
                """,
                [id_siniestro],
            )
        )
        return detail


def aggregate_alerts(group_by: str = "proveedor", db_path: Path = DEFAULT_DB_PATH) -> list[dict[str, Any]]:
    if group_by == "proveedor":
        query = """
            SELECT
                pr.nombre AS grupo,
                pr.tipo,
                COUNT(*) AS total_siniestros,
                SUM(CASE WHEN sc.nivel_riesgo = 'Rojo' THEN 1 ELSE 0 END) AS alertas_rojas,
                ROUND(AVG(sc.score_final), 2) AS score_promedio
            FROM siniestros si
            JOIN scores sc ON sc.id_siniestro = si.id_siniestro
            LEFT JOIN proveedores pr ON pr.id_proveedor = si.id_proveedor
            GROUP BY pr.nombre, pr.tipo
            HAVING alertas_rojas > 0
            ORDER BY alertas_rojas DESC, score_promedio DESC
            LIMIT 15
        """
    elif group_by == "ramo":
        query = """
            SELECT
                si.ramo AS grupo,
                COUNT(*) AS total_siniestros,
                SUM(CASE WHEN sc.nivel_riesgo = 'Rojo' THEN 1 ELSE 0 END) AS alertas_rojas,
                ROUND(100.0 * SUM(CASE WHEN sc.nivel_riesgo = 'Rojo' THEN 1 ELSE 0 END) / COUNT(*), 2) AS porcentaje_rojo,
                ROUND(AVG(sc.score_final), 2) AS score_promedio
            FROM siniestros si
            JOIN scores sc ON sc.id_siniestro = si.id_siniestro
            GROUP BY si.ramo
            ORDER BY porcentaje_rojo DESC, score_promedio DESC
        """
    elif group_by == "ciudad":
        query = """
            SELECT
                si.sucursal AS grupo,
                COUNT(*) AS total_siniestros,
                SUM(CASE WHEN sc.nivel_riesgo IN ('Rojo', 'Amarillo') THEN 1 ELSE 0 END) AS alertas_revision,
                ROUND(AVG(sc.score_final), 2) AS score_promedio
            FROM siniestros si
            JOIN scores sc ON sc.id_siniestro = si.id_siniestro
            GROUP BY si.sucursal
            ORDER BY alertas_revision DESC, score_promedio DESC
            LIMIT 12
        """
    elif group_by == "documentos":
        query = """
            SELECT
                d.tipo_documento AS grupo,
                COUNT(*) AS total_documentos_observados,
                SUM(CASE WHEN d.entregado = 0 THEN 1 ELSE 0 END) AS faltantes,
                SUM(CASE WHEN d.legible = 0 THEN 1 ELSE 0 END) AS ilegibles,
                SUM(CASE WHEN d.inconsistencia_detectada = 1 THEN 1 ELSE 0 END) AS inconsistentes
            FROM documentos d
            JOIN scores sc ON sc.id_siniestro = d.id_siniestro
            WHERE sc.nivel_riesgo = 'Rojo'
              AND (d.entregado = 0 OR d.legible = 0 OR d.inconsistencia_detectada = 1)
            GROUP BY d.tipo_documento
            ORDER BY total_documentos_observados DESC
        """
    else:
        raise ValueError(f"Agrupacion no soportada: {group_by}")
    with _connect(db_path) as conn:
        return _rows(conn.execute(query))


def get_relationship_network(limit: int = 60, db_path: Path = DEFAULT_DB_PATH) -> dict[str, list[dict[str, Any]]]:
    query = """
        SELECT
            si.id_siniestro,
            si.id_asegurado,
            si.id_proveedor,
            pr.nombre AS proveedor,
            si.ramo,
            sc.score_final,
            sc.nivel_riesgo
        FROM siniestros si
        JOIN scores sc ON sc.id_siniestro = si.id_siniestro
        LEFT JOIN proveedores pr ON pr.id_proveedor = si.id_proveedor
        ORDER BY sc.score_final DESC
        LIMIT ?
    """
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []
    with _connect(db_path) as conn:
        for row in conn.execute(query, [int(limit)]):
            claim = f"claim:{row['id_siniestro']}"
            insured = f"insured:{row['id_asegurado']}"
            provider = f"provider:{row['id_proveedor']}"
            nodes[claim] = {
                "id": claim,
                "label": row["id_siniestro"],
                "tipo": "Siniestro",
                "score": row["score_final"],
                "nivel": row["nivel_riesgo"],
                "ramo": row["ramo"],
            }
            nodes.setdefault(
                insured,
                {
                    "id": insured,
                    "label": row["id_asegurado"],
                    "tipo": "Asegurado",
                    "score": row["score_final"],
                    "nivel": row["nivel_riesgo"],
                    "ramo": row["ramo"],
                },
            )
            nodes.setdefault(
                provider,
                {
                    "id": provider,
                    "label": row["proveedor"],
                    "tipo": "Proveedor",
                    "score": row["score_final"],
                    "nivel": row["nivel_riesgo"],
                    "ramo": row["ramo"],
                },
            )
            edges.append({"source": insured, "target": claim, "relacion": "reporta"})
            edges.append({"source": provider, "target": claim, "relacion": "atiende"})
    return {"nodes": list(nodes.values()), "edges": edges}


def get_impact_summary(db_path: Path = DEFAULT_DB_PATH) -> dict[str, Any]:
    return impact_summary(db_path)


def score_candidate_claim(data: dict[str, Any]) -> dict[str, Any]:
    alerts: list[dict[str, Any]] = []
    points = 0
    critical = False

    def add(code: str, description: str, pts: int, evidence: str, is_critical: bool = False) -> None:
        nonlocal points, critical
        points += int(pts)
        critical = critical or is_critical
        alerts.append({"codigo": code, "descripcion": description, "puntos": pts, "evidencia": evidence, "es_critica": is_critical})

    days_start = int(data.get("dias_desde_inicio_poliza", 999))
    days_end = int(data.get("dias_desde_fin_poliza", 999))
    border = min(days_start, days_end)
    if border <= 10:
        add("RF-05", "Siniestro muy cercano al borde de vigencia.", 8, f"{border} dias al borde.")
    elif border <= 30:
        add("RF-05", "Siniestro cercano al borde de vigencia.", 4, f"{border} dias al borde.")

    delay = int(data.get("dias_entre_ocurrencia_reporte", 0))
    if delay > 7:
        add("RF-12", "Reporte tardio.", 5, f"{delay} dias de demora.")
    elif delay >= 4:
        add("RF-12", "Reporte con demora moderada.", 3, f"{delay} dias de demora.")

    amount = float(data.get("monto_reclamado", 0) or 0)
    insured_sum = max(float(data.get("suma_asegurada", 1) or 1), 1)
    ratio = amount / insured_sum
    if ratio >= 0.95:
        add("RF-14", "Monto cercano a la suma asegurada.", 5, f"Ratio {ratio:.2f}.")

    if bool(data.get("proveedor_lista_restrictiva", False)):
        add("RF-03", "Proveedor en lista restrictiva simulada.", 10, "Coincidencia exacta.", True)
    if bool(data.get("documentos_inconsistentes", False)):
        add("RF-11", "Documentos inconsistentes.", 10, "Marcado en formulario.")
    if bool(data.get("adulteracion_documental", False)):
        add("RF-02", "Adulteracion documental simulada.", 10, "Marcado en formulario.", True)
    if not bool(data.get("documentos_completos", True)):
        add("RF-10", "Documentos incompletos o ilegibles.", 4, "Marcado en formulario.")

    ramo = str(data.get("ramo", "Vehiculos"))
    cobertura = str(data.get("cobertura", ""))
    if ramo == "Vehiculos":
        if cobertura == "Perdida Total por Robo":
            add("RF-01", "Perdida total por robo requiere revision especializada.", 20, "Cobertura PTxRB.", True)
        if "Robo" in cobertura and int(data.get("denuncia_horas", delay * 24)) > 48:
            add("RF-06", "Demora atipica en denuncia de robo.", 8, f"{int(data.get('denuncia_horas', delay * 24))} horas.")
        if bool(data.get("dinamica_imposible", False)):
            add("RF-04", "Dinamica fisicamente imposible.", 20, "Marcado en formulario.", True)
        if not bool(data.get("tercero_identificado", True)) and ratio > 0.35:
            add("RF-20", "Danio relevante sin tercero identificado.", 5, "Sin tercero identificado.")
    elif ramo == "Salud" and bool(data.get("factura_duplicada", False)):
        add("RS-01", "Factura repetida en reclamo de salud.", 8, "Marcado en formulario.")
    elif ramo == "Hogar" and bool(data.get("factura_duplicada", False)):
        add("RH-01", "Factura repetida en reclamo de hogar.", 8, "Marcado en formulario.")

    score = min(100, min(points, 60))
    if critical and score < 76:
        score = 76
    level = level_from_score(score)
    explanation = " | ".join(f"{alert['descripcion']} ({alert['puntos']} pts)" for alert in alerts[:3])
    return {
        "score_final": int(score),
        "nivel_riesgo": level,
        "score_reglas": int(points),
        "score_anomalia": 0,
        "score_nlp": 0,
        "accion_sugerida": {
            "Verde": "Continuar flujo normal.",
            "Amarillo": "Escalar a revision documental.",
            "Rojo": "Escalar a revision especializada de campo.",
        }[level],
        "alertas": alerts,
        "explicacion_resumen": explanation or "Sin alertas materiales; mantener flujo normal con controles habituales.",
    }
