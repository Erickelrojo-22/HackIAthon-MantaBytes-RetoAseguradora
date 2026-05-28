from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

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
            sc.score_modelo,
            sc.probabilidad_modelo,
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


def get_model_metrics(db_path: Path = DEFAULT_DB_PATH) -> list[dict[str, Any]]:
    query = """
        SELECT modelo, metrica, valor, detalle, fecha_generacion
        FROM metricas_modelo
        ORDER BY
            CASE metrica
                WHEN 'status' THEN 0
                WHEN 'precision' THEN 1
                WHEN 'recall' THEN 2
                WHEN 'f1' THEN 3
                WHEN 'auc_roc' THEN 4
                ELSE 5
            END,
            metrica
    """
    with _connect(db_path) as conn:
        try:
            return _rows(conn.execute(query))
        except sqlite3.OperationalError:
            return []


def provider_red_alert_pareto(db_path: Path = DEFAULT_DB_PATH) -> list[dict[str, Any]]:
    query = """
        WITH provider_red AS (
            SELECT
                pr.nombre AS proveedor,
                pr.tipo,
                COUNT(*) AS alertas_rojas,
                ROUND(AVG(sc.score_final), 2) AS score_promedio
            FROM siniestros si
            JOIN scores sc ON sc.id_siniestro = si.id_siniestro
            LEFT JOIN proveedores pr ON pr.id_proveedor = si.id_proveedor
            WHERE sc.nivel_riesgo = 'Rojo'
            GROUP BY pr.nombre, pr.tipo
        ),
        ranked AS (
            SELECT
                proveedor,
                tipo,
                alertas_rojas,
                score_promedio,
                SUM(alertas_rojas) OVER () AS total_rojas,
                SUM(alertas_rojas) OVER (ORDER BY alertas_rojas DESC, score_promedio DESC) AS acumulado
            FROM provider_red
        )
        SELECT
            proveedor,
            tipo,
            alertas_rojas,
            score_promedio,
            ROUND(100.0 * alertas_rojas / NULLIF(total_rojas, 0), 2) AS porcentaje_rojas,
            ROUND(100.0 * acumulado / NULLIF(total_rojas, 0), 2) AS porcentaje_acumulado
        FROM ranked
        WHERE 100.0 * (acumulado - alertas_rojas) / NULLIF(total_rojas, 0) < 80
        ORDER BY alertas_rojas DESC, score_promedio DESC
    """
    with _connect(db_path) as conn:
        return _rows(conn.execute(query))


def top_insured_frequency(limit: int = 10, db_path: Path = DEFAULT_DB_PATH) -> list[dict[str, Any]]:
    query = """
        SELECT
            si.id_asegurado,
            COUNT(*) AS total_siniestros,
            SUM(CASE WHEN sc.nivel_riesgo = 'Rojo' THEN 1 ELSE 0 END) AS casos_rojos,
            ROUND(AVG(sc.score_final), 2) AS score_promedio,
            ROUND(SUM(si.monto_reclamado), 2) AS monto_total_reclamado
        FROM siniestros si
        JOIN scores sc ON sc.id_siniestro = si.id_siniestro
        GROUP BY si.id_asegurado
        HAVING total_siniestros > 1
        ORDER BY total_siniestros DESC, casos_rojos DESC, score_promedio DESC
        LIMIT ?
    """
    with _connect(db_path) as conn:
        return _rows(conn.execute(query, [int(limit)]))


def list_amount_outliers(limit: int = 10, db_path: Path = DEFAULT_DB_PATH) -> list[dict[str, Any]]:
    query = """
        SELECT
            sc.id_siniestro,
            sc.score_final,
            sc.nivel_riesgo,
            si.ramo,
            si.cobertura,
            si.monto_reclamado,
            ROUND(sc.monto_reclamado / NULLIF(po.suma_asegurada, 0), 3) AS ratio_suma,
            sc.explicacion_resumen
        FROM scores sc
        JOIN siniestros si ON si.id_siniestro = sc.id_siniestro
        JOIN polizas po ON po.id_poliza = si.id_poliza
        WHERE sc.score_final >= 41
           OR sc.monto_reclamado / NULLIF(po.suma_asegurada, 0) >= 0.80
        ORDER BY ratio_suma DESC, sc.score_final DESC
        LIMIT ?
    """
    with _connect(db_path) as conn:
        return _rows(conn.execute(query, [int(limit)]))


def list_policy_edge_cases(limit: int = 10, db_path: Path = DEFAULT_DB_PATH) -> list[dict[str, Any]]:
    query = """
        SELECT
            sc.id_siniestro,
            sc.score_final,
            sc.nivel_riesgo,
            si.ramo,
            si.cobertura,
            si.fecha_ocurrencia,
            si.dias_desde_inicio_poliza,
            si.dias_desde_fin_poliza,
            sc.explicacion_resumen
        FROM scores sc
        JOIN siniestros si ON si.id_siniestro = sc.id_siniestro
        WHERE si.dias_desde_inicio_poliza <= 30
           OR si.dias_desde_fin_poliza <= 30
        ORDER BY
            CASE WHEN si.dias_desde_inicio_poliza <= si.dias_desde_fin_poliza
                THEN si.dias_desde_inicio_poliza
                ELSE si.dias_desde_fin_poliza
            END ASC,
            sc.score_final DESC
        LIMIT ?
    """
    with _connect(db_path) as conn:
        return _rows(conn.execute(query, [int(limit)]))


def repeated_claim_patterns(limit: int = 10, db_path: Path = DEFAULT_DB_PATH) -> list[dict[str, Any]]:
    query = """
        SELECT
            sc.id_siniestro,
            sc.score_final,
            sc.nivel_riesgo,
            si.ramo,
            si.cobertura,
            ROUND(sc.similitud_narrativa, 4) AS similitud_narrativa,
            sc.siniestro_similar,
            si.descripcion
        FROM scores sc
        JOIN siniestros si ON si.id_siniestro = sc.id_siniestro
        WHERE sc.similitud_narrativa >= 0.70
           OR sc.siniestro_similar <> ''
        ORDER BY sc.similitud_narrativa DESC, sc.score_final DESC
        LIMIT ?
    """
    with _connect(db_path) as conn:
        return _rows(conn.execute(query, [int(limit)]))


def executive_report(db_path: Path = DEFAULT_DB_PATH) -> dict[str, Any]:
    with _connect(db_path) as conn:
        summary = dict(
            conn.execute(
                """
                SELECT
                    COUNT(*) AS total_siniestros,
                    SUM(CASE WHEN nivel_riesgo = 'Rojo' THEN 1 ELSE 0 END) AS rojos,
                    SUM(CASE WHEN nivel_riesgo = 'Amarillo' THEN 1 ELSE 0 END) AS amarillos,
                    SUM(CASE WHEN nivel_riesgo = 'Verde' THEN 1 ELSE 0 END) AS verdes,
                    ROUND(AVG(score_final), 2) AS score_promedio
                FROM scores
                """
            ).fetchone()
        )
        amounts = dict(
            conn.execute(
                """
                SELECT
                    ROUND(SUM(CASE WHEN sc.nivel_riesgo = 'Rojo' THEN si.monto_reclamado ELSE 0 END), 2) AS monto_rojo,
                    ROUND(SUM(CASE WHEN sc.nivel_riesgo IN ('Rojo', 'Amarillo') THEN si.monto_reclamado ELSE 0 END), 2) AS monto_revision
                FROM scores sc
                JOIN siniestros si ON si.id_siniestro = sc.id_siniestro
                """
            ).fetchone()
        )
    monto_revision = float(amounts.get("monto_revision") or 0)
    return {
        "resumen": summary,
        "exposicion": amounts,
        "ahorro_potencial_simulado": {
            "base_revision_rojo_amarillo": round(monto_revision, 2),
            "tasa_evitable_demo": 0.12,
            "monto_estimado": round(monto_revision * 0.12, 2),
            "nota": "Simulacion ejecutiva para priorizacion; no representa ahorro contable real.",
        },
        "top_casos": list_risk_cases(limit=10, db_path=db_path),
        "proveedores_80_20": provider_red_alert_pareto(db_path=db_path),
        "metricas_modelo": get_model_metrics(db_path=db_path),
    }


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


def score_candidate_claim(data: dict[str, Any]) -> dict[str, Any]:
    alerts: list[dict[str, Any]] = []
    points = 0
    critical = False
    min_yellow = False

    def add(
        code: str,
        description: str,
        pts: int,
        evidence: str,
        is_critical: bool = False,
        force_yellow: bool = False,
    ) -> None:
        nonlocal points, critical, min_yellow
        points += int(pts)
        critical = critical or is_critical
        min_yellow = min_yellow or force_yellow
        alerts.append({"codigo": code, "descripcion": description, "puntos": pts, "evidencia": evidence, "es_critica": is_critical})

    days_start = int(data.get("dias_desde_inicio_poliza", 999))
    days_end = int(data.get("dias_desde_fin_poliza", 999))
    border = min(days_start, days_end)
    if border <= 10:
        add("RF-05", "Siniestro muy cercano al borde de vigencia.", 8, f"{border} dias al borde.", force_yellow=border <= 1)
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
            hours = int(data.get("denuncia_horas", delay * 24))
            add("RF-06", "Demora atipica en denuncia de robo.", 8, f"{hours} horas.", force_yellow=hours > 96)
        if bool(data.get("dinamica_imposible", False)):
            add("RF-04", "Dinamica fisicamente imposible.", 20, "Marcado en formulario.", True)
        if not bool(data.get("tercero_identificado", True)) and ratio > 0.35:
            add("RF-20", "Danio relevante sin tercero identificado.", 5, "Sin tercero identificado.")
    elif ramo == "Salud" and bool(data.get("factura_duplicada", False)):
        add("RS-01", "Factura repetida en reclamo de salud.", 8, "Marcado en formulario.")
    elif ramo == "Hogar" and bool(data.get("factura_duplicada", False)):
        add("RH-01", "Factura repetida en reclamo de hogar.", 8, "Marcado en formulario.")

    if bool(data.get("narrativa_clonada", False)):
        add("RF-07", "Narrativa identica o clonada.", 8, "Marcado en formulario.", force_yellow=True)

    score = min(100, min(points, 60))
    if min_yellow and score < 41:
        score = 41
    if critical and score < 76:
        score = 76
    level = level_from_score(score)
    explanation = " | ".join(
        f"{alert['descripcion']} ({alert['puntos']} pts)" for alert in alerts[:3]
    ) or "Sin alertas materiales; mantener flujo normal con controles habituales."
    return {
        "score_final": int(score),
        "nivel_riesgo": level,
        "score_reglas": int(points),
        "score_anomalia": 0,
        "score_nlp": 0,
        "probabilidad_modelo": 0.0,
        "score_modelo": 0,
        "accion_sugerida": {
            "Verde": "Continuar flujo normal.",
            "Amarillo": "Escalar a revision documental.",
            "Rojo": "Escalar a revision especializada de campo.",
        }[level],
        "explicacion_resumen": explanation,
        "alertas": alerts,
    }
