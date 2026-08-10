from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fraudia_claims.agent_intents import AgentIntent, detect_intent
from fraudia_claims.agent_tools import (
    aggregate_alerts,
    executive_report,
    get_claim_detail,
    get_model_metrics,
    list_amount_outliers,
    list_document_findings,
    list_policy_edge_cases,
    list_risk_cases,
    provider_red_alert_pareto,
    repeated_claim_patterns,
    top_insured_frequency,
)
from fraudia_claims.config import DEFAULT_DB_PATH
from fraudia_claims.utils import money


LOGGER = logging.getLogger(__name__)
DISCLAIMER = "El score es una alerta de revisión humana; no es una acusación ni una decisión automática."


def build_agent_answer(
    question: str,
    db_path: Path = DEFAULT_DB_PATH,
    session_cases: list[dict[str, Any]] | None = None,
) -> str:
    text = (question or "").strip()
    if not text:
        return "Escribe una pregunta sobre riesgo, documentos, proveedores, métricas o un caso SIN. " + DISCLAIMER
    if len(text) > 1200:
        return "La pregunta es demasiado larga. Resume el pedido en una sola consulta ejecutiva. " + DISCLAIMER
    try:
        intent = detect_intent(text)
        return _with_disclaimer(_answer_intent(intent, db_path, session_cases=session_cases))
    except Exception:
        LOGGER.exception("Local agent answer failed")
        return _safe_fallback()


def _answer_intent(
    intent: AgentIntent,
    db_path: Path,
    session_cases: list[dict[str, Any]] | None = None,
) -> str:
    if intent.name == "session_case":
        return _session_case_answer(session_cases)
    if intent.name == "claim_detail" and intent.claim_id:
        return _claim_answer(intent.claim_id, db_path)
    if intent.name == "top_risk":
        return _top_risk_answer(db_path)
    if intent.name == "provider_pareto":
        return _provider_pareto_answer(db_path)
    if intent.name == "provider_alerts":
        return _provider_alerts_answer(db_path)
    if intent.name == "branch_concentration":
        return _aggregate_answer("ramo", db_path)
    if intent.name == "city_concentration":
        return _aggregate_answer("ciudad", db_path)
    if intent.name == "insured_frequency":
        return _insured_frequency_answer(db_path)
    if intent.name == "documents":
        return _documents_answer(db_path)
    if intent.name == "amount_outliers":
        return _amount_outliers_answer(db_path)
    if intent.name == "policy_edges":
        return _policy_edges_answer(db_path)
    if intent.name == "repeated_patterns":
        return _repeated_patterns_answer(db_path)
    if intent.name == "savings":
        return _savings_answer(db_path)
    if intent.name == "metrics":
        return _metrics_answer(db_path)
    if intent.name == "executive_summary":
        return _executive_summary_answer(db_path)
    return _fallback_answer(db_path)


def _top_risk_answer(db_path: Path) -> str:
    rows = list_risk_cases(limit=10, db_path=db_path)
    return (
        "### Casos prioritarios para revisión\n"
        "Recomiendo iniciar por los casos con nivel rojo y mayor exposición económica, revisando evidencia documental, proveedor y patrón narrativo.\n\n"
        + _case_bullets(rows[:10])
    )


def _provider_alerts_answer(db_path: Path) -> str:
    rows = aggregate_alerts("proveedor", db_path=db_path)
    if not rows:
        return "No hay proveedores con alertas rojas concentradas en la base actual. Mantén revisión humana por score de caso."
    lines = ["### Proveedores con mayor concentración de alertas rojas"]
    for index, row in enumerate(rows[:5], start=1):
        lines.append(
            f"{index}. **{_human(row.get('grupo'))}** ({_human(row.get('tipo'))}): "
            f"{_int(row.get('alertas_rojas'))} alertas rojas, "
            f"{_int(row.get('total_siniestros'))} siniestros y score promedio {_num(row.get('score_promedio'))}."
        )
    lines.append("\nAcción sugerida: revisar recurrencia, documentos asociados y relación con casos de mayor score.")
    return "\n".join(lines)


def _provider_pareto_answer(db_path: Path) -> str:
    rows = provider_red_alert_pareto(db_path=db_path)
    if not rows:
        return _provider_alerts_answer(db_path)
    lines = ["### Proveedores que explican la mayor parte de alertas rojas"]
    for index, row in enumerate(rows[:5], start=1):
        lines.append(
            f"{index}. **{_human(row.get('proveedor'))}**: {_int(row.get('alertas_rojas'))} alertas rojas "
            f"({_num(row.get('porcentaje_acumulado'))}% acumulado), score promedio {_num(row.get('score_promedio'))}."
        )
    lines.append("\nPrioriza estos proveedores para revisión de trazabilidad y consistencia documental.")
    return "\n".join(lines)


def _aggregate_answer(group_by: str, db_path: Path) -> str:
    rows = aggregate_alerts(group_by, db_path=db_path)
    if group_by == "ramo":
        lines = ["### Ramos con mayor proporción de casos en rojo"]
        for row in rows:
            lines.append(
                f"- **{_human(row.get('grupo'))}**: {_num(row.get('porcentaje_rojo'))}% rojo, "
                f"{_int(row.get('alertas_rojas'))} alertas rojas de {_int(row.get('total_siniestros'))} siniestros."
            )
        return "\n".join(lines)
    lines = ["### Ciudades con mayor concentración de alertas de revisión"]
    for row in rows[:8]:
        lines.append(
            f"- **{_human(row.get('grupo'))}**: {_int(row.get('alertas_revision'))} casos para revisión, "
            f"score promedio {_num(row.get('score_promedio'))}."
        )
    return "\n".join(lines)


def _insured_frequency_answer(db_path: Path) -> str:
    rows = top_insured_frequency(db_path=db_path)
    if not rows:
        return "No hay asegurados con frecuencia repetida relevante en la base actual."
    lines = ["### Asegurados anónimos con mayor frecuencia de reclamos"]
    for row in rows[:6]:
        lines.append(
            f"- **{row.get('id_asegurado')}**: {_int(row.get('total_siniestros'))} siniestros, "
            f"{_int(row.get('casos_rojos'))} rojos, monto reclamado acumulado {money(row.get('monto_total_reclamado'))}."
        )
    lines.append("\nÚsalo como señal de priorización, no como imputación individual.")
    return "\n".join(lines)


def _documents_answer(db_path: Path) -> str:
    grouped = aggregate_alerts("documentos", db_path=db_path)
    findings = list_document_findings(limit=8, db_path=db_path)
    lines = ["### Revisión documental en casos críticos"]
    if grouped:
        lines.append("Tipos de documentos con observaciones en casos rojos o amarillos:")
        for row in grouped[:5]:
            lines.append(
                f"- **{_human(row.get('grupo'))}**: {_int(row.get('faltantes'))} faltantes, "
                f"{_int(row.get('ilegibles'))} ilegibles, {_int(row.get('inconsistentes'))} inconsistentes."
            )
    else:
        lines.append(
            "En la base actual no aparecen documentos marcados como faltantes, ilegibles o inconsistentes para los casos críticos."
        )
    if findings:
        lines.append("\nCasos donde conviene revisar el expediente documental:")
        for row in findings[:5]:
            lines.append(
                f"- **{row.get('id_siniestro')}** ({row.get('nivel_riesgo')}, score {_int(row.get('score_final'))}): "
                f"{_human(row.get('tipo_documento'))}. {_document_status(row)}"
            )
    else:
        lines.append("\nComo no hay hallazgos documentales explícitos, prioriza revisión documental de estos casos por score:")
        lines.append(_case_bullets(list_risk_cases(limit=5, level="Rojo", db_path=db_path)))
    return "\n".join(lines)


def _amount_outliers_answer(db_path: Path) -> str:
    rows = list_amount_outliers(db_path=db_path)
    lines = ["### Montos atípicos o cercanos a suma asegurada"]
    for row in rows[:7]:
        lines.append(
            f"- **{row.get('id_siniestro')}** ({row.get('nivel_riesgo')}, score {_int(row.get('score_final'))}): "
            f"{_human(row.get('ramo'))} / {_human(row.get('cobertura'))}, monto {money(row.get('monto_reclamado'))}, "
            f"ratio suma {_num(row.get('ratio_suma'))}."
        )
    lines.append("\nQué revisar: suma asegurada, facturas, cotizaciones comparables y coherencia con la narrativa.")
    return "\n".join(lines)


def _policy_edges_answer(db_path: Path) -> str:
    rows = list_policy_edge_cases(db_path=db_path)
    lines = ["### Siniestros cercanos al inicio o fin de vigencia"]
    for row in rows[:7]:
        lines.append(
            f"- **{row.get('id_siniestro')}** ({row.get('nivel_riesgo')}, score {_int(row.get('score_final'))}): "
            f"{_human(row.get('ramo'))}, {row.get('dias_desde_inicio_poliza')} días desde inicio y "
            f"{row.get('dias_desde_fin_poliza')} días hasta fin."
        )
    lines.append("\nQué revisar: fecha de ocurrencia, fecha de reporte, vigencia efectiva y evidencia temporal.")
    return "\n".join(lines)


def _repeated_patterns_answer(db_path: Path) -> str:
    rows = repeated_claim_patterns(limit=20, db_path=db_path)
    if not rows:
        return "No se detectaron narrativas repetidas materiales en la base actual."
    rows = sorted(rows, key=lambda row: (_risk_rank(row.get("nivel_riesgo")), -int(row.get("score_final") or 0)))[:6]
    lines = [
        "### Patrones narrativos repetidos",
        "La similitud alta indica textos o descripciones muy parecidas; es una señal para comparar expedientes, no una acusación.",
    ]
    for row in rows:
        lines.append(
            f"- **{row.get('id_siniestro')}** ({row.get('nivel_riesgo')}, score {_int(row.get('score_final'))}) "
            f"se parece a **{row.get('siniestro_similar') or 'otro caso'}** con similitud {_num(row.get('similitud_narrativa'))}. "
            f"Ramo: {_human(row.get('ramo'))}. Revisar narrativa, proveedor y documentos."
        )
    return "\n".join(lines)


def _savings_answer(db_path: Path) -> str:
    report = executive_report(db_path=db_path)
    savings = report["ahorro_potencial_simulado"]
    return (
        "### Ahorro potencial simulado\n"
        f"- Base de revisión rojo/amarillo: **{money(savings['base_revision_rojo_amarillo'])}**\n"
        f"- Tasa evitable estimada: **{savings['tasa_evitable_demo']:.0%}**\n"
        f"- Monto estimado: **{money(savings['monto_estimado'])}**\n\n"
        "Este valor sirve para priorizar revisión humana y explicar impacto potencial; no representa ahorro contable real."
    )


def _metrics_answer(db_path: Path) -> str:
    rows = get_model_metrics(db_path=db_path)
    if not rows:
        return "No hay métricas supervisadas disponibles en esta base. El sistema mantiene reglas explicables y trazabilidad."
    lines = ["### Métricas del modelo supervisado"]
    near_perfect = False
    for row in rows:
        metric_name = str(row.get("metrica"))
        try:
            value = float(row.get("valor"))
        except (TypeError, ValueError):
            value = None
        if metric_name in {"accuracy", "precision", "recall", "f1", "auc_roc"} and value is not None and value >= 0.98:
            near_perfect = True
        lines.append(f"- **{_human(metric_name)}**: {_num(row.get('valor'))}. {_human(row.get('detalle'))}")
    lines.append("\nSon métricas sobre etiqueta sintética reproducible; no equivalen a validación legal.")
    if near_perfect:
        lines.append(
            "\n**Nota de interpretación:** en el generador sintético, la etiqueta de fraude determina también otras "
            "variables (monto, demora de reporte, etc.) que el modelo usa como entrada. Un valor cercano a 1.0 "
            "confirma que el pipeline reproduce la etiqueta simulada, no que detecte fraude real; úsalo como prueba "
            "de integración del modelo, no como evidencia de desempeño."
        )
    return "\n".join(lines)


def _executive_summary_answer(db_path: Path) -> str:
    report = executive_report(db_path=db_path)
    summary = report["resumen"]
    savings = report["ahorro_potencial_simulado"]
    return (
        "### Resumen ejecutivo\n"
        "FraudIA Claims prioriza siniestros para revisión humana combinando reglas, anomalías, similitud narrativa y un modelo supervisado.\n\n"
        f"- Total de siniestros: **{_int(summary.get('total_siniestros'))}**\n"
        f"- Casos rojos: **{_int(summary.get('rojos'))}**\n"
        f"- Casos amarillos: **{_int(summary.get('amarillos'))}**\n"
        f"- Ahorro potencial simulado: **{money(savings['monto_estimado'])}**\n\n"
        "Casos más urgentes:\n"
        + _case_bullets(report["top_casos"][:5])
    )


def _claim_answer(claim_id: str, db_path: Path) -> str:
    detail = get_claim_detail(claim_id, db_path)
    if "error" in detail:
        return f"No encontré el siniestro **{claim_id}** en la base actual. Revisa el identificador y vuelve a preguntar."
    alerts = detail.get("alertas", [])[:6]
    documents = detail.get("documentos", [])[:5]
    lines = [
        f"### Expediente {claim_id}",
        f"- Nivel: **{detail.get('nivel_riesgo')}**, score **{_int(detail.get('score_final'))}**.",
        f"- Ramo/cobertura: {_human(detail.get('ramo'))} / {_human(detail.get('cobertura'))}.",
        f"- Proveedor: {_human(detail.get('proveedor_nombre'))}.",
        f"- Acción sugerida: {_human(detail.get('accion_sugerida'))}.",
    ]
    if alerts:
        lines.append("\nAlertas principales:")
        for alert in alerts:
            lines.append(f"- **{alert.get('codigo')}**: {_human(alert.get('descripcion'))} ({_int(alert.get('puntos'))} pts).")
    if documents:
        observed = [doc for doc in documents if _document_status(doc) != "Sin observación material registrada."]
        if observed:
            lines.append("\nDocumentos observados:")
            for doc in observed[:4]:
                lines.append(f"- {_human(doc.get('tipo_documento'))}: {_document_status(doc)}")
    return "\n".join(lines)


def _session_case_answer(session_cases: list[dict[str, Any]] | None) -> str:
    if not session_cases:
        return "Todavía no hay casos evaluados en vivo en esta sesión. Ejecuta un caso temporal y vuelve a preguntarme."
    case = session_cases[-1]
    alerts = case.get("alertas", [])[:6]
    lines = [
        "### Último caso evaluado en vivo",
        f"- ID temporal: **{case.get('id_temporal', 'TMP')}**",
        f"- Nivel: **{case.get('nivel_riesgo', '')}**, score **{_int(case.get('score_final'))}**.",
        f"- Ramo/cobertura: {_human(case.get('ramo'))} / {_human(case.get('cobertura'))}.",
        f"- Monto reclamado: {money(case.get('monto_reclamado', 0))}.",
        f"- Acción sugerida: {_human(case.get('accion_sugerida', 'Revisión humana'))}.",
    ]
    if alerts:
        lines.append("\nAlertas principales:")
        for alert in alerts:
            lines.append(f"- **{alert.get('codigo')}**: {_human(alert.get('descripcion'))} ({_int(alert.get('puntos'))} pts).")
    return "\n".join(lines)


def _fallback_answer(db_path: Path) -> str:
    rows = list_risk_cases(limit=5, db_path=db_path)
    return (
        "Puedo responder sobre casos de mayor riesgo, proveedores, ramos, ciudades, documentos, montos atípicos, vigencia, patrones narrativos, métricas o el detalle de un SIN.\n\n"
        "Como punto de partida, estos son los casos prioritarios:\n"
        + _case_bullets(rows)
    )


def _case_bullets(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "- No hay casos disponibles con esos filtros."
    lines = []
    for index, row in enumerate(rows, start=1):
        lines.append(
            f"{index}. **{row.get('id_siniestro')}**: {row.get('nivel_riesgo')} / score {_int(row.get('score_final'))}. "
            f"{_human(row.get('ramo'))} en {_human(row.get('ciudad'))}, monto {money(row.get('monto_reclamado'))}. "
            f"Proveedor: {_human(row.get('proveedor'))}. Motivo: {_human(row.get('explicacion_resumen'))}"
        )
    return "\n".join(lines)


def _document_status(row: dict[str, Any]) -> str:
    notes = []
    if not bool(row.get("entregado", True)):
        notes.append("documento faltante")
    if not bool(row.get("legible", True)):
        notes.append("documento ilegible")
    if bool(row.get("inconsistencia_detectada", False)):
        notes.append("inconsistencia detectada")
    if bool(row.get("adulteracion_confirmada", False)):
        notes.append("posible adulteración marcada")
    observation = str(row.get("observacion") or "").strip()
    if observation:
        notes.append(_human(observation))
    return "; ".join(notes) if notes else "Sin observación material registrada."


def _with_disclaimer(answer: str) -> str:
    if "revisión humana" in answer.lower() and "decisión automática" in answer.lower():
        return answer
    return answer.rstrip() + "\n\n" + DISCLAIMER


def _safe_fallback() -> str:
    return (
        "No pude completar la consulta con las herramientas locales en este momento. "
        "Puedes preguntar por casos de mayor riesgo, proveedores críticos, documentos, métricas o un SIN específico. "
        + DISCLAIMER
    )


def _human(value: Any) -> str:
    text = "" if value is None else str(value)
    replacements = {
        "Vehiculos": "Vehículos",
        "Perdida": "Pérdida",
        "Danio": "Daño",
        "dano": "daño",
        "revision": "revisión",
        "decision": "decisión",
        "automatica": "automática",
        "poliza": "póliza",
        "atipico": "atípico",
        "anomalia": "anomalía",
        "numerico": "numérico",
        "historica": "histórica",
        "multiples": "múltiples",
        "Facturacion": "Facturación",
        "Mecanica": "Mecánica",
        "Anonimo": "Anónimo",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    return text


def _int(value: Any) -> int:
    try:
        return int(float(value or 0))
    except Exception:
        return 0


def _num(value: Any) -> str:
    try:
        return f"{float(value or 0):.2f}"
    except Exception:
        return "0.00"


def _risk_rank(value: Any) -> int:
    return {"Rojo": 0, "Amarillo": 1, "Verde": 2}.get(str(value), 3)
