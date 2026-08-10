from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Literal

from fraudia_claims.utils import normalize_text


IntentName = Literal[
    "amount_outliers",
    "branch_concentration",
    "city_concentration",
    "claim_detail",
    "documents",
    "executive_summary",
    "fallback",
    "insured_frequency",
    "metrics",
    "policy_edges",
    "provider_alerts",
    "provider_pareto",
    "repeated_patterns",
    "savings",
    "session_case",
    "top_risk",
]


@dataclass(frozen=True)
class AgentIntent:
    name: IntentName
    normalized_question: str
    claim_id: str | None = None


CANONICAL_QUESTIONS: dict[IntentName, tuple[str, ...]] = {
    "top_risk": (
        "cuales son los 10 siniestros con mayor riesgo",
        "cuales son los 10 siniestros con mayor riesgo de posible fraude",
        "recomienda que casos deberia revisar primero el analista",
        "que casos deberia revisar primero el analista",
    ),
    "provider_alerts": (
        "que proveedores concentran mas alertas",
        "que proveedores concentran mas alertas rojas",
    ),
    "provider_pareto": (
        "que proveedores concentran el 80 de las alertas rojas",
        "que proveedores explican el 80 de las alertas rojas",
    ),
    "branch_concentration": ("que ramos tienen mayor porcentaje de casos sospechosos",),
    "city_concentration": ("que ciudades presentan mayor concentracion de alertas",),
    "insured_frequency": ("que asegurados tienen mayor frecuencia de reclamos",),
    "documents": (
        "que documentos faltan en los casos criticos",
        "que documentos estan observados en los casos criticos",
    ),
    "amount_outliers": (
        "que casos tienen montos atipicos",
        "que siniestros tienen montos cercanos a la suma asegurada",
    ),
    "policy_edges": ("que siniestros ocurrieron cerca del inicio de la poliza",),
    "repeated_patterns": (
        "que patrones se repiten en los reclamos sospechosos",
        "que narrativas se repiten en los reclamos sospechosos",
    ),
    "savings": ("cual es el ahorro potencial simulado",),
    "metrics": ("que metricas tiene el modelo supervisado",),
    "executive_summary": ("genera un resumen ejecutivo de los casos criticos",),
}


def extract_claim_id(question: str) -> str | None:
    match = re.search(r"\bSIN[-\s]?(\d{4,5})\b", question, flags=re.IGNORECASE)
    if not match:
        return None
    digits = match.group(1)
    if "-" in match.group(0):
        return f"SIN-{digits}"
    if len(digits) == 4:
        return f"SIN-{digits}"
    return f"SIN{digits}"


def detect_intent(question: str) -> AgentIntent:
    normalized = normalize_text(question)
    claim_id = extract_claim_id(question)
    if _mentions_session_case(normalized):
        return AgentIntent("session_case", normalized, claim_id=claim_id)
    if claim_id:
        # Un SIN valido en la pregunta ya es suficiente para pedir el detalle
        # del expediente: antes se exigia ademas una palabra clave como
        # "explica" o "detalle", asi que "cuentame sobre SIN-1023" nunca
        # disparaba este intent y caia en una respuesta generica.
        return AgentIntent("claim_detail", normalized, claim_id=claim_id)

    fuzzy = _best_fuzzy_intent(normalized)
    if fuzzy:
        return AgentIntent(fuzzy, normalized, claim_id=claim_id)

    # Antes de aqui habia heuristicas de una sola palabra clave ('ramo' in
    # normalized, 'modelo' in normalized, etc.) que interceptaban preguntas
    # libres ("como funciona tu modelo?") y las respondian con una plantilla
    # generica, incluso con OPENAI_API_KEY configurada. Cualquier pregunta
    # que no calce con una de las canonicas de la demo (fuzzy match arriba)
    # ni sea un SIN especifico se deja como "fallback": is_fast_local_question
    # la excluye de las respuestas locales rapidas, asi que ask_agent_with_status
    # la envia al modelo cuando hay API key, y solo usa la plantilla generica
    # como ultimo recurso si OpenAI no esta disponible.
    return AgentIntent("fallback", normalized, claim_id=claim_id)


def is_fast_local_question(question: str) -> bool:
    return detect_intent(question).name not in {"claim_detail", "fallback", "session_case"}


def _best_fuzzy_intent(normalized: str) -> IntentName | None:
    best_intent: IntentName | None = None
    best_ratio = 0.0
    for intent, examples in CANONICAL_QUESTIONS.items():
        for example in examples:
            ratio = SequenceMatcher(None, normalized, example).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_intent = intent
    return best_intent if best_ratio >= 0.86 else None


def _mentions_session_case(normalized: str) -> bool:
    return "ultimo caso" in normalized or "caso evaluado" in normalized or "evaluado en vivo" in normalized
