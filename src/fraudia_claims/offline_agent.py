from __future__ import annotations

import re
from pathlib import Path

from fraudia_claims.agent_tools import aggregate_alerts, get_claim_detail, list_risk_cases
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


def answer_offline(question: str, db_path: Path = DEFAULT_DB_PATH) -> str:
    text = normalize_text(question)
    claim_match = re.search(r"sin\d{5}", text)
    if claim_match and ("por que" in text or "explica" in text or "detalle" in text):
        return _claim_answer(claim_match.group(0).upper(), db_path)

    if "top" in text or "mayor riesgo" in text or "revisar primero" in text or "10 siniestros" in text:
        rows = list_risk_cases(limit=10, db_path=db_path)
        return "Estos son los siniestros que conviene revisar primero:\n\n" + _format_cases(rows)

    if "proveedor" in text and ("roja" in text or "alerta" in text or "concentran" in text or "80" in text):
        rows = aggregate_alerts("proveedor", db_path=db_path)
        return "Proveedores con mayor concentracion de alertas rojas:\n\n" + _table(
            rows,
            ["grupo", "tipo", "total_siniestros", "alertas_rojas", "score_promedio"],
        )

    if "ramo" in text or "ramos" in text:
        rows = aggregate_alerts("ramo", db_path=db_path)
        return "Ramos con mayor proporcion de casos en rojo:\n\n" + _table(
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
        return "Documentos con mas observaciones en casos rojos:\n\n" + _table(
            rows,
            ["grupo", "total_documentos_observados", "faltantes", "ilegibles", "inconsistentes"],
        )

    if "resumen ejecutivo" in text or "resumen" in text or "patrones" in text:
        top = list_risk_cases(limit=5, db_path=db_path)
        providers = aggregate_alerts("proveedor", db_path=db_path)[:5]
        ramo = aggregate_alerts("ramo", db_path=db_path)
        return (
            "### Resumen ejecutivo\n"
            "El prototipo prioriza casos para revision humana mediante reglas trazables, anomalias numericas y similitud narrativa. "
            "Los scores no constituyen acusaciones ni decisiones automaticas.\n\n"
            "Casos mas urgentes:\n\n"
            f"{_format_cases(top)}\n\n"
            "Concentracion por ramo:\n\n"
            f"{_table(ramo, ['grupo', 'total_siniestros', 'alertas_rojas', 'porcentaje_rojo', 'score_promedio'])}\n\n"
            "Proveedores destacados:\n\n"
            f"{_table(providers, ['grupo', 'tipo', 'alertas_rojas', 'score_promedio'])}"
        )

    rows = list_risk_cases(limit=10, db_path=db_path)
    return (
        "Puedo responder preguntas sobre top de riesgo, proveedores, ramos, ciudades, documentos faltantes, patrones y el detalle de un SINxxxxx. "
        "Como punto de partida, estos son los casos prioritarios:\n\n"
        + _format_cases(rows)
    )
