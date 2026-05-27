from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from fraudia_claims.agent_tools import (
    aggregate_alerts,
    get_claim_detail,
    get_relationship_network,
    list_risk_cases,
    score_candidate_claim,
)
from fraudia_claims.config import DEFAULT_DB_PATH
from fraudia_claims.offline_agent import answer_offline


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
    if name == "score_candidate_claim":
        return score_candidate_claim(arguments)
    raise ValueError(f"Herramienta no soportada: {name}")


def ask_with_openai(question: str, db_path: Path = DEFAULT_DB_PATH) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL")
    if not api_key or not model:
        return answer_offline(question, db_path)

    try:
        from openai import OpenAI
    except Exception:
        return answer_offline(question, db_path)

    client = OpenAI(api_key=api_key)
    instructions = (
        "Eres FraudIA Claims, un agente para una aseguradora. Responde en espanol, con tono ejecutivo y claro. "
        "Tu salida siempre debe decir que el score es una alerta de revision humana, no una acusacion ni decision automatica. "
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
                        "output": json.dumps(result, ensure_ascii=False),
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
        return text.strip() if text else answer_offline(question, db_path)
    except Exception:
        return answer_offline(question, db_path)


def ask_agent(question: str, db_path: Path = DEFAULT_DB_PATH) -> str:
    return ask_with_openai(question, db_path)
