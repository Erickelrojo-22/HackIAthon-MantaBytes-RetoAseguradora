from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from fraudia_claims.analytics import executive_kpis, provider_pareto, top_cases
from fraudia_claims.config import DEFAULT_DB_PATH
from fraudia_claims.agent_tools import get_claim_detail


GUIDED_DEMO_STEPS = [
    {
        "titulo": "1. Problema",
        "objetivo": "Mostrar que el analista necesita priorizar casos entre miles de siniestros.",
        "accion": "Abrir Resumen y explicar KPIs generales.",
        "mensaje": "FraudIA no acusa fraude: ordena senales para revision humana.",
    },
    {
        "titulo": "2. Priorizacion",
        "objetivo": "Evidenciar semaforo y bandeja de revision.",
        "accion": "Abrir Bandeja de revision filtrada por Rojo y Amarillo.",
        "mensaje": "El score combina reglas trazables, anomalias y similitud narrativa.",
    },
    {
        "titulo": "3. Explicabilidad",
        "objetivo": "Demostrar por que un caso fue marcado en rojo.",
        "accion": "Abrir Detalle del siniestro destacado.",
        "mensaje": "Cada alerta conserva puntos, evidencia y accion sugerida.",
    },
    {
        "titulo": "4. Relaciones",
        "objetivo": "Mostrar proveedores, asegurados y siniestros conectados.",
        "accion": "Abrir Red de relaciones.",
        "mensaje": "La red ayuda a detectar concentraciones, no culpabilidad.",
    },
    {
        "titulo": "5. Agente IA",
        "objetivo": "Responder preguntas del jurado en lenguaje natural.",
        "accion": "Preguntar por proveedores con mas alertas rojas.",
        "mensaje": "El agente usa herramientas locales y funciona sin API.",
    },
    {
        "titulo": "6. Prueba de fuego",
        "objetivo": "Evaluar un caso nuevo ocurrido cerca del inicio de vigencia.",
        "accion": "Abrir Evaluar caso nuevo y calcular score temporal.",
        "mensaje": "El caso queda en sesion para la demo, sin alterar la base historica.",
    },
    {
        "titulo": "7. Cierre ejecutivo",
        "objetivo": "Entregar evidencia descargable para gerencia/auditoria.",
        "accion": "Descargar reporte HTML.",
        "mensaje": "El reporte documenta hallazgos y limitaciones eticas.",
    },
]


def featured_claims(db_path: Path = DEFAULT_DB_PATH) -> dict[str, Any]:
    top = top_cases(25, db_path)
    red = top[top["nivel_riesgo"] == "Rojo"]
    yellow_case = _level_demo_case("Amarillo", db_path)
    green = _level_demo_case("Verde", db_path)
    red_case = red.iloc[0].to_dict() if not red.empty else top.iloc[0].to_dict()
    providers = provider_pareto(5, db_path)
    provider = providers.iloc[0].to_dict() if not providers.empty else {}
    return {
        "caso_rojo": red_case,
        "detalle_rojo": get_claim_detail(str(red_case["id_siniestro"]), db_path) if red_case else {},
        "caso_amarillo": yellow_case,
        "caso_verde": green,
        "prueba_fuego": {
            "ramo": "Vehiculos",
            "cobertura": "Perdida Total por Robo",
            "monto_reclamado": 29500,
            "suma_asegurada": 30000,
            "dias_desde_inicio_poliza": 1,
            "dias_desde_fin_poliza": 364,
            "dias_entre_ocurrencia_reporte": 5,
            "denuncia_horas": 72,
            "documentos_completos": False,
            "documentos_inconsistentes": True,
            "tercero_identificado": False,
        },
        "proveedor_recurrente": provider,
        "kpis": executive_kpis(db_path),
    }


def _green_demo_case(db_path: Path = DEFAULT_DB_PATH) -> dict[str, Any]:
    return _level_demo_case("Verde", db_path)


def _level_demo_case(level: str, db_path: Path = DEFAULT_DB_PATH) -> dict[str, Any]:
    import sqlite3

    order = "sc.score_final ASC, si.monto_reclamado ASC" if level == "Verde" else "sc.score_final DESC, si.monto_reclamado DESC"
    query = """
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
        WHERE sc.nivel_riesgo = ?
        ORDER BY """ + order + """
        LIMIT 1
    """
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(query, [level]).fetchone()
    return dict(row) if row else {}


def demo_questions() -> list[str]:
    return [
        "Cuales son los 10 siniestros con mayor riesgo?",
        "Por que este siniestro fue marcado como alto riesgo?",
        "Que proveedores concentran mas alertas rojas?",
        "Que ramos tienen mayor porcentaje de casos rojos?",
        "Que ciudades presentan mayor concentracion de alertas?",
        "Que documentos faltan en los casos criticos?",
        "Genera un resumen ejecutivo de los casos criticos.",
        "Cual es el ahorro potencial simulado?",
        "Explica el ultimo caso evaluado en vivo.",
    ]


def session_cases_frame(session_cases: list[dict[str, Any]] | None) -> pd.DataFrame:
    rows = []
    for idx, case in enumerate(session_cases or [], start=1):
        rows.append(
            {
                "id_temporal": case.get("id_temporal", f"TMP{idx:03d}"),
                "ramo": case.get("ramo", ""),
                "cobertura": case.get("cobertura", ""),
                "score_final": case.get("score_final", 0),
                "nivel_riesgo": case.get("nivel_riesgo", ""),
                "monto_reclamado": case.get("monto_reclamado", 0),
                "alertas": len(case.get("alertas", [])),
                "explicacion": case.get("explicacion_resumen", ""),
            }
        )
    return pd.DataFrame(rows)
