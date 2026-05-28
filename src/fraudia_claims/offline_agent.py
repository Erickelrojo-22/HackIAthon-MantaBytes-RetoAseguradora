from __future__ import annotations

import re
from pathlib import Path

from fraudia_claims.agent_tools import (
    aggregate_alerts,
    executive_report,
    get_claim_detail,
    get_model_metrics,
    list_amount_outliers,
    list_policy_edge_cases,
    list_risk_cases,
    provider_red_alert_pareto,
    repeated_claim_patterns,
    top_insured_frequency,
)
from fraudia_claims.config import DEFAULT_DB_PATH
from fraudia_claims.utils import money, normalize_text


def _table(rows: list[dict], columns: list[str]) -> str:
    if not rows:
        return "No encontre resultados para esa consulta."
    header = "| " + " | ".join(columns) + " |"
    sep = "| " + " | ".join(["---"] * len(columns)) + " |"
    body = []
    for row in rows:
        body.append("| " + " | ".join(str(row.get(col, "")) for col in columns) + " |")
    return "\n".join([header, sep, *body])


def _format_cases(rows: list[dict]) -> str:
    formatted = []
    for row in rows:
        formatted.append(
            {
                "id": row["id_siniestro"],
                "score": row["score_final"],
                "nivel": row["nivel_riesgo"],
                "ramo": row["ramo"],
                "ciudad": row["ciudad"],
                "monto": money(row["monto_reclamado"]),
                "proveedor": row["proveedor"],
            }
        )
    return _table(formatted, ["id", "score", "nivel", "ramo", "ciudad", "monto", "proveedor"])


def _claim_answer(claim_id: str, db_path: Path) -> str:
    detail = get_claim_detail(claim_id, db_path)
    if "error" in detail:
        return detail["error"]
    alerts = "\n".join(
        f"- {a['codigo']}: {a['descripcion']} ({a['puntos']} pts). Evidencia: {a['evidencia']}"
        for a in detail["alertas"][:8]
    )
    return (
        f"### {claim_id}\n"
        f"- Nivel: **{detail['nivel_riesgo']}**\n"
        f"- Score: **{detail['score_final']}** "
        f"(reglas {detail['score_reglas']}, anomalia {detail['score_anomalia']}, NLP {detail['score_nlp']})\n"
        f"- Ramo/cobertura: {detail['ramo']} / {detail['cobertura']}\n"
        f"- Proveedor: {detail.get('proveedor_nombre', '')}\n"
        f"- Accion sugerida: {detail['accion_sugerida']}\n\n"
        f"Alertas principales:\n{alerts if alerts else '- Sin alertas materiales.'}"
    )


def _session_case_answer(session_cases: list[dict] | None) -> str:
    if not session_cases:
        return (
            "Todavia no hay casos evaluados en vivo en esta sesion. "
            "Para la prueba del jurado, carga un caso en 'Evaluar caso nuevo' y luego vuelve a preguntarme."
        )
    case = session_cases[-1]
    alerts = "\n".join(
        f"- {alert.get('codigo')}: {alert.get('descripcion')} ({alert.get('puntos')} pts). Evidencia: {alert.get('evidencia')}"
        for alert in case.get("alertas", [])[:8]
    )
    return (
        "### Ultimo caso evaluado en vivo\n"
        f"- ID temporal: **{case.get('id_temporal', 'TMP')}**\n"
        f"- Nivel: **{case.get('nivel_riesgo', '')}**\n"
        f"- Score: **{case.get('score_final', 0)}** "
        f"(reglas {case.get('score_reglas', 0)}, anomalia {case.get('score_anomalia', 0)}, NLP {case.get('score_nlp', 0)})\n"
        f"- Ramo/cobertura: {case.get('ramo', '')} / {case.get('cobertura', '')}\n"
        f"- Monto reclamado: {money(case.get('monto_reclamado', 0))}\n"
        f"- Accion sugerida: {case.get('accion_sugerida', 'Revision humana')}\n\n"
        "Este resultado es una alerta temporal de revision humana y no modifica la base historica.\n\n"
        f"Alertas principales:\n{alerts if alerts else '- Sin alertas materiales.'}"
    )


def answer_offline(
    question: str,
    db_path: Path = DEFAULT_DB_PATH,
    session_cases: list[dict] | None = None,
) -> str:
    text = normalize_text(question)
    if (
        "ultimo caso" in text
        or "caso evaluado" in text
        or "evaluado en vivo" in text
        or "caso nuevo" in text and "explica" in text
    ):
        return _session_case_answer(session_cases)

    claim_match = re.search(r"sin\d{5}", text)
    if claim_match and ("por que" in text or "explica" in text or "detalle" in text):
        return _claim_answer(claim_match.group(0).upper(), db_path)

    if "top" in text or "mayor riesgo" in text or "revisar primero" in text or "10 siniestros" in text:
        rows = list_risk_cases(limit=10, db_path=db_path)
        return "Estos son los siniestros que conviene priorizar para revision humana:\n\n" + _format_cases(rows)

    if "proveedor" in text and ("roja" in text or "alerta" in text or "concentran" in text or "80" in text):
        if "80" in text or "ochenta" in text:
            rows = provider_red_alert_pareto(db_path=db_path)
            return "Proveedores que explican aproximadamente el 80% acumulado de alertas rojas:\n\n" + _table(
                rows,
                ["proveedor", "tipo", "alertas_rojas", "porcentaje_rojas", "porcentaje_acumulado", "score_promedio"],
            )
        rows = aggregate_alerts("proveedor", db_path=db_path)
        return "Proveedores con mayor concentracion de alertas rojas para revision humana:\n\n" + _table(
            rows,
            ["grupo", "tipo", "total_siniestros", "alertas_rojas", "score_promedio"],
        )

    if "ramo" in text or "ramos" in text:
        rows = aggregate_alerts("ramo", db_path=db_path)
        return "Ramos con mayor proporcion de casos en rojo para revision humana:\n\n" + _table(
            rows,
            ["grupo", "total_siniestros", "alertas_rojas", "porcentaje_rojo", "score_promedio"],
        )

    if "ciudad" in text or "ciudades" in text:
        rows = aggregate_alerts("ciudad", db_path=db_path)
        return "Ciudades con mayor concentracion de casos para revision:\n\n" + _table(
            rows,
            ["grupo", "total_siniestros", "alertas_revision", "score_promedio"],
        )

    if "documento" in text or "faltan" in text or "faltantes" in text:
        rows = aggregate_alerts("documentos", db_path=db_path)
        return "Documentos con mas observaciones en casos rojos para revision documental:\n\n" + _table(
            rows,
            ["grupo", "total_documentos_observados", "faltantes", "ilegibles", "inconsistentes"],
        )

    if "ahorro" in text:
        report = executive_report(db_path=db_path)
        savings = report["ahorro_potencial_simulado"]
        return (
            "El ahorro potencial simulado sirve para priorizar revision humana, no para decidir pagos automaticamente.\n\n"
            f"- Base de revision rojo/amarillo: {money(savings['base_revision_rojo_amarillo'])}\n"
            f"- Tasa evitable demo: {savings['tasa_evitable_demo']:.0%}\n"
            f"- Monto estimado: {money(savings['monto_estimado'])}\n"
            f"- Nota: {savings['nota']}"
        )

    if "asegurado" in text and ("frecuencia" in text or "reclamo" in text or "siniestro" in text):
        rows = top_insured_frequency(db_path=db_path)
        return "Asegurados anonimos con mayor frecuencia de reclamos para priorizar revision humana:\n\n" + _table(
            rows,
            ["id_asegurado", "total_siniestros", "casos_rojos", "score_promedio", "monto_total_reclamado"],
        )

    if "monto" in text and ("atipico" in text or "alto" in text or "suma asegurada" in text):
        rows = list_amount_outliers(db_path=db_path)
        return "Siniestros con montos atipicos o cercanos a la suma asegurada para revision humana:\n\n" + _table(
            rows,
            ["id_siniestro", "score_final", "nivel_riesgo", "ramo", "cobertura", "monto_reclamado", "ratio_suma"],
        )

    if ("inicio" in text or "fin" in text or "vigencia" in text or "poliza" in text) and ("cerca" in text or "ocurrieron" in text):
        rows = list_policy_edge_cases(db_path=db_path)
        return "Siniestros ocurridos cerca del inicio o fin de vigencia para revision humana:\n\n" + _table(
            rows,
            [
                "id_siniestro",
                "score_final",
                "nivel_riesgo",
                "ramo",
                "dias_desde_inicio_poliza",
                "dias_desde_fin_poliza",
            ],
        )

    if ("patron" in text or "repiten" in text or "repetidos" in text or "narrativa" in text) and "resumen" not in text:
        rows = repeated_claim_patterns(db_path=db_path)
        return "Patrones repetidos encontrados en narrativas de reclamos para revision humana:\n\n" + _table(
            rows,
            ["id_siniestro", "score_final", "nivel_riesgo", "ramo", "similitud_narrativa", "siniestro_similar"],
        )

    if "metrica" in text or "precision" in text or "recall" in text or "auc" in text or "modelo" in text:
        rows = get_model_metrics(db_path=db_path)
        return (
            "Metricas del modelo supervisado sobre etiqueta sintetica. Son evidencia de reproducibilidad, no validacion legal:\n\n"
            + _table(rows, ["modelo", "metrica", "valor", "detalle"])
        )

    if "resumen ejecutivo" in text or "resumen" in text or "patrones" in text:
        report = executive_report(db_path=db_path)
        top = list_risk_cases(limit=5, db_path=db_path)
        providers = aggregate_alerts("proveedor", db_path=db_path)[:5]
        ramo = aggregate_alerts("ramo", db_path=db_path)
        savings = report["ahorro_potencial_simulado"]
        return (
            "### Resumen ejecutivo\n"
            "El prototipo prioriza casos para revision humana mediante reglas trazables, anomalias numericas y similitud narrativa. "
            "Los scores no constituyen acusaciones ni decisiones automaticas.\n\n"
            f"Ahorro potencial simulado por priorizacion: {money(savings['monto_estimado'])} "
            f"sobre una base de revision de {money(savings['base_revision_rojo_amarillo'])}.\n\n"
            "Casos mas urgentes:\n\n"
            f"{_format_cases(top)}\n\n"
            "Concentracion por ramo:\n\n"
            f"{_table(ramo, ['grupo', 'total_siniestros', 'alertas_rojas', 'porcentaje_rojo', 'score_promedio'])}\n\n"
            "Proveedores destacados:\n\n"
            f"{_table(providers, ['grupo', 'tipo', 'alertas_rojas', 'score_promedio'])}"
        )

    rows = list_risk_cases(limit=10, db_path=db_path)
    return (
        "Puedo responder preguntas sobre top de riesgo, proveedores, ramos, ciudades, asegurados frecuentes, documentos faltantes, montos atipicos, vigencia, patrones, metricas y el detalle de un SINxxxxx. "
        "Como punto de partida, estos son los casos prioritarios:\n\n"
        + _format_cases(rows)
    )

