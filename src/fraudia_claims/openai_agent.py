from __future__ import annotations

import json
import logging
import os
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from fraudia_claims.agent_tools import (
    aggregate_alerts,
    executive_report,
    get_claim_detail,
    get_relationship_network,
    get_model_metrics,
    list_amount_outliers,
    list_policy_edge_cases,
    list_risk_cases,
    provider_red_alert_pareto,
    repeated_claim_patterns,
    score_candidate_claim,
    top_insured_frequency,
)
from fraudia_claims.agent_intents import is_fast_local_question
from fraudia_claims.config import DEFAULT_DB_PATH
from fraudia_claims.offline_agent import answer_offline
from fraudia_claims.utils import money, normalize_text


FAST_LOCAL_QUESTIONS = {
    "cuales son los 10 siniestros con mayor riesgo",
    "cuales son los 10 siniestros con mayor riesgo de posible fraude",
    "que proveedores concentran mas alertas",
    "que proveedores concentran mas alertas rojas",
    "que proveedores concentran el 80 de las alertas rojas",
    "que ramos tienen mayor porcentaje de casos sospechosos",
    "que ciudades presentan mayor concentracion de alertas",
    "que asegurados tienen mayor frecuencia de reclamos",
    "que documentos faltan en los casos criticos",
    "que casos tienen montos atipicos",
    "que siniestros ocurrieron cerca del inicio de la poliza",
    "que patrones se repiten en los reclamos sospechosos",
    "genera un resumen ejecutivo de los casos criticos",
    "recomienda que casos deberia revisar primero el analista",
    "cual es el ahorro potencial simulado",
    "que metricas tiene el modelo supervisado",
}

LOGGER = logging.getLogger(__name__)


TOOLS = [
    {
        "type": "function",
        "name": "list_risk_cases",
        "description": "Lista siniestros priorizados por score de riesgo.",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "minimum": 1, "maximum": 20},
                "level": {"type": "string", "enum": ["Verde", "Amarillo", "Rojo"]},
            },
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "get_claim_detail",
        "description": "Obtiene detalle y alertas explicables de un siniestro.",
        "parameters": {
            "type": "object",
            "properties": {"id_siniestro": {"type": "string"}},
            "required": ["id_siniestro"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "aggregate_alerts",
        "description": "Agrupa alertas por proveedor, ramo, ciudad o documentos.",
        "parameters": {
            "type": "object",
            "properties": {"group_by": {"type": "string", "enum": ["proveedor", "ramo", "ciudad", "documentos"]}},
            "required": ["group_by"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "get_relationship_network",
        "description": "Devuelve nodos y relaciones entre siniestros, asegurados y proveedores.",
        "parameters": {
            "type": "object",
            "properties": {"limit": {"type": "integer", "minimum": 10, "maximum": 120}},
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "get_model_metrics",
        "description": "Devuelve metricas reproducibles del modelo supervisado entrenado con etiqueta sintetica.",
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "type": "function",
        "name": "provider_red_alert_pareto",
        "description": "Lista proveedores que explican aproximadamente el 80 por ciento acumulado de alertas rojas.",
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "type": "function",
        "name": "top_insured_frequency",
        "description": "Lista asegurados anonimos con mayor frecuencia de siniestros.",
        "parameters": {
            "type": "object",
            "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 20}},
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "list_amount_outliers",
        "description": "Lista siniestros con montos atipicos o cercanos a suma asegurada.",
        "parameters": {
            "type": "object",
            "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 20}},
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "list_policy_edge_cases",
        "description": "Lista siniestros ocurridos cerca del inicio o fin de vigencia de la poliza.",
        "parameters": {
            "type": "object",
            "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 20}},
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "repeated_claim_patterns",
        "description": "Lista reclamos con narrativas similares o patrones textuales repetidos.",
        "parameters": {
            "type": "object",
            "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 20}},
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "executive_report",
        "description": "Devuelve resumen ejecutivo, exposicion y ahorro potencial simulado.",
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "type": "function",
        "name": "score_candidate_claim",
        "description": "Calcula un score temporal para un siniestro nuevo sin persistirlo.",
        "parameters": {"type": "object", "properties": {}, "additionalProperties": True},
    },
]


def _dispatch(name: str, arguments: dict[str, Any], db_path: Path) -> Any:
    if name == "list_risk_cases":
        return list_risk_cases(limit=int(arguments.get("limit", 10)), level=arguments.get("level"), db_path=db_path)
    if name == "get_claim_detail":
        return get_claim_detail(str(arguments["id_siniestro"]).upper(), db_path=db_path)
    if name == "aggregate_alerts":
        return aggregate_alerts(str(arguments["group_by"]), db_path=db_path)
    if name == "get_relationship_network":
        return get_relationship_network(limit=int(arguments.get("limit", 60)), db_path=db_path)
    if name == "get_model_metrics":
        return get_model_metrics(db_path=db_path)
    if name == "provider_red_alert_pareto":
        return provider_red_alert_pareto(db_path=db_path)
    if name == "top_insured_frequency":
        return top_insured_frequency(limit=int(arguments.get("limit", 10)), db_path=db_path)
    if name == "list_amount_outliers":
        return list_amount_outliers(limit=int(arguments.get("limit", 10)), db_path=db_path)
    if name == "list_policy_edge_cases":
        return list_policy_edge_cases(limit=int(arguments.get("limit", 10)), db_path=db_path)
    if name == "repeated_claim_patterns":
        return repeated_claim_patterns(limit=int(arguments.get("limit", 10)), db_path=db_path)
    if name == "executive_report":
        return executive_report(db_path=db_path)
    if name == "score_candidate_claim":
        return score_candidate_claim(arguments)
    raise ValueError(f"Herramienta no soportada: {name}")


def _json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if hasattr(value, "item") and callable(value.item):
        try:
            return _json_safe(value.item())
        except Exception:
            return str(value)
    return value


def _should_answer_from_session(question: str) -> bool:
    text = question.lower()
    return "ultimo caso" in text or "caso evaluado" in text or "evaluado en vivo" in text


def _is_fast_local_question(question: str) -> bool:
    return is_fast_local_question(question)


def _format_local_table(rows: list[dict[str, Any]], columns: list[str]) -> str:
    if not rows:
        return "No encontre resultados para esa consulta."
    header = "| " + " | ".join(columns) + " |"
    sep = "| " + " | ".join(["---"] * len(columns)) + " |"
    body = ["| " + " | ".join(str(row.get(col, "")) for col in columns) + " |" for row in rows]
    return "\n".join([header, sep, *body])


def _format_local_cases(rows: list[dict[str, Any]]) -> str:
    formatted = [
        {
            "id": row.get("id_siniestro"),
            "score": row.get("score_final"),
            "nivel": row.get("nivel_riesgo"),
            "ramo": row.get("ramo"),
            "ciudad": row.get("ciudad"),
            "monto": money(row.get("monto_reclamado")),
            "proveedor": row.get("proveedor"),
        }
        for row in rows
    ]
    return _format_local_table(formatted, ["id", "score", "nivel", "ramo", "ciudad", "monto", "proveedor"])


def _fast_local_answer(question: str, db_path: Path, session_cases: list[dict[str, Any]] | None = None) -> str:
    return _safe_offline_answer(question, db_path, session_cases=session_cases)


def _safe_offline_answer(
    question: str,
    db_path: Path,
    session_cases: list[dict[str, Any]] | None = None,
) -> str:
    try:
        return answer_offline(question, db_path, session_cases=session_cases)
    except Exception:
        LOGGER.exception("Offline agent fallback failed")
        return (
            "No pude completar la consulta con las herramientas locales en este momento. "
            "Puedes preguntar por casos de mayor riesgo, proveedores críticos, documentos, métricas o un SIN específico. "
            "El score es una alerta de revisión humana; no es una acusación ni una decisión automática."
        )


def ask_with_openai(
    question: str,
    db_path: Path = DEFAULT_DB_PATH,
    session_cases: list[dict[str, Any]] | None = None,
) -> str:
    answer, _source = ask_with_openai_status(question, db_path, session_cases=session_cases)
    return answer


def _with_disclaimer(answer: str) -> str:
    required = "alerta de revision humana"
    normalized = normalize_text(answer)
    if required in normalized or "revision humana" in normalized:
        return answer
    return (
        answer.rstrip()
        + "\n\nNota: este score es una alerta de revisión humana; no es una acusación ni una decisión automática."
    )


def ask_with_openai_status(
    question: str,
    db_path: Path = DEFAULT_DB_PATH,
    session_cases: list[dict[str, Any]] | None = None,
) -> tuple[str, str]:
    question = (question or "").strip()
    if not question:
        return _safe_offline_answer(question, db_path, session_cases=session_cases), "Validación local"
    if len(question) > 1200:
        return _safe_offline_answer(question, db_path, session_cases=session_cases), "Validación local"

    if _should_answer_from_session(question):
        return _safe_offline_answer(question, db_path, session_cases=session_cases), "Sesion local"

    if _is_fast_local_question(question):
        return _fast_local_answer(question, db_path, session_cases=session_cases), "Herramientas locales rapidas"

    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL")
    if not api_key or not model:
        return _safe_offline_answer(question, db_path, session_cases=session_cases), "Offline"

    try:
        from openai import OpenAI
    except Exception:
        return _safe_offline_answer(question, db_path, session_cases=session_cases), "Offline"

    client = OpenAI(api_key=api_key)
    instructions = (
        "Eres FraudIA Claims, un agente para una aseguradora. Responde siempre en español, con tono ejecutivo y claro. "
        "Usa tildes y caracteres propios del español, como ñ, cuando correspondan. "
        "Tu salida siempre debe decir que el score es una alerta de revisión humana, no una acusación ni decisión automática. "
        "Usa solo las herramientas locales; no inventes datos."
    )
    try:
        response = client.responses.create(
            model=model,
            instructions=instructions,
            input=question,
            tools=TOOLS,
            tool_choice="auto",
        )
        pending_outputs = []
        for item in getattr(response, "output", []) or []:
            if getattr(item, "type", None) == "function_call":
                args = json.loads(getattr(item, "arguments", "{}") or "{}")
                result = _dispatch(getattr(item, "name"), args, db_path)
                pending_outputs.append(
                    {
                        "type": "function_call_output",
                        "call_id": getattr(item, "call_id"),
                        "output": json.dumps(_json_safe(result), ensure_ascii=False),
                    }
                )
        if pending_outputs:
            response = client.responses.create(
                model=model,
                instructions=instructions,
                previous_response_id=response.id,
                input=pending_outputs,
                tools=TOOLS,
            )
        text = getattr(response, "output_text", None)
        if text:
            return _with_disclaimer(text.strip()), f"OpenAI activo ({model})"
        return _safe_offline_answer(question, db_path, session_cases=session_cases), "Offline"
    except Exception:
        LOGGER.exception("OpenAI agent fallback activated")
        return _safe_offline_answer(question, db_path, session_cases=session_cases), "Offline"


def ask_agent(
    question: str,
    db_path: Path = DEFAULT_DB_PATH,
    session_cases: list[dict[str, Any]] | None = None,
) -> str:
    return ask_with_openai(question, db_path, session_cases=session_cases)


def ask_agent_with_status(
    question: str,
    db_path: Path = DEFAULT_DB_PATH,
    session_cases: list[dict[str, Any]] | None = None,
) -> tuple[str, str]:
    return ask_with_openai_status(question, db_path, session_cases=session_cases)
