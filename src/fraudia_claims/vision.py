from __future__ import annotations

import base64
import json
import os
from typing import Any


MAX_IMAGE_BYTES = 8 * 1024 * 1024
SUPPORTED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}


def image_analysis_available() -> bool:
    return bool(os.getenv("OPENAI_API_KEY") and os.getenv("OPENAI_MODEL"))


def _data_url(image_bytes: bytes, mime_type: str) -> str:
    encoded = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:{mime_type};base64,{encoded}"


def _offline_result(reason: str) -> dict[str, Any]:
    return {
        "status": "offline",
        "modelo_openai": os.getenv("OPENAI_MODEL", ""),
        "severidad_visual": "No evaluada",
        "confianza": 0.0,
        "observaciones": [reason],
        "anomalias_potenciales": [],
        "accion_sugerida": "Continuar con revision documental y peritaje humano.",
        "disclaimer": "Analisis visual no disponible; no modifica score ni reemplaza peritaje.",
    }


def analyze_claim_image(
    image_bytes: bytes,
    mime_type: str,
    claim_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if mime_type not in SUPPORTED_MIME_TYPES:
        return _offline_result(f"Tipo de archivo no soportado para demo: {mime_type}.")
    if len(image_bytes) > MAX_IMAGE_BYTES:
        return _offline_result("Imagen demasiado grande para la demo; reduce el tamano antes de analizar.")
    if not image_analysis_available():
        return _offline_result("Faltan OPENAI_API_KEY u OPENAI_MODEL; Vision opera en modo offline.")

    try:
        from openai import OpenAI
    except Exception:
        return _offline_result("El paquete openai no esta instalado en el entorno.")

    context = claim_context or {}
    prompt = {
        "objetivo": "Analizar una foto de siniestro solo para priorizar revision humana.",
        "contexto_siniestro": context,
        "instrucciones": [
            "No acuses fraude ni afirmes dolo.",
            "Describe hallazgos visuales observables y posibles inconsistencias.",
            "Indica severidad_visual como Baja, Media o Alta.",
            "Devuelve JSON valido con observaciones, anomalias_potenciales, severidad_visual, confianza y accion_sugerida.",
        ],
    }

    try:
        client = OpenAI()
        response = client.responses.create(
            model=os.environ["OPENAI_MODEL"],
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": json.dumps(prompt, ensure_ascii=False)},
                        {"type": "input_image", "image_url": _data_url(image_bytes, mime_type), "detail": "auto"},
                    ],
                }
            ],
        )
        raw_text = getattr(response, "output_text", "") or "{}"
        parsed = json.loads(raw_text)
    except Exception as exc:
        return _offline_result(f"No fue posible completar el analisis visual: {exc}")

    return {
        "status": "ok",
        "modelo_openai": os.environ["OPENAI_MODEL"],
        "severidad_visual": str(parsed.get("severidad_visual", "Media")),
        "confianza": float(parsed.get("confianza", 0) or 0),
        "observaciones": list(parsed.get("observaciones", [])),
        "anomalias_potenciales": list(parsed.get("anomalias_potenciales", [])),
        "accion_sugerida": str(parsed.get("accion_sugerida", "Escalar a revision humana si corresponde.")),
        "disclaimer": "Analisis visual auxiliar; no modifica score ni reemplaza peritaje.",
    }
