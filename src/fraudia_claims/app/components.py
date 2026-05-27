from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from fraudia_claims.utils import money


RISK_LABELS = {
    "Rojo": "[ROJO] Rojo",
    "Amarillo": "[AMARILLO] Amarillo",
    "Verde": "[VERDE] Verde",
}


def risk_badge(level: str) -> str:
    return RISK_LABELS.get(str(level), str(level))


def ethical_notice() -> None:
    st.info(
        "FraudIA genera alertas para revision humana. No acusa fraude, no rechaza reclamos y no decide pagos."
    )


def metric_row(kpis: dict[str, Any]) -> None:
    cols = st.columns(5)
    cols[0].metric("Siniestros", f"{int(kpis['total_siniestros']):,}")
    cols[1].metric("Prioridad", f"{int(kpis['casos_priorizados']):,}", f"{kpis['porcentaje_priorizado']}%")
    cols[2].metric("Rojos", f"{int(kpis['casos_rojos']):,}", f"{kpis['porcentaje_rojo']}%")
    cols[3].metric("Monto priorizado", money(kpis["monto_priorizado"]))
    cols[4].metric("Ahorro simulado", money(kpis["ahorro_potencial_simulado"]))


def show_dataframe(frame: pd.DataFrame, empty_message: str = "No hay datos para mostrar.") -> None:
    if frame.empty:
        st.warning(empty_message)
    else:
        st.dataframe(frame, hide_index=True, use_container_width=True)


def case_card(title: str, case: dict[str, Any]) -> None:
    if not case:
        st.warning(f"No hay datos para {title}.")
        return
    with st.container(border=True):
        st.write(f"### {title}")
        st.write(f"**Siniestro:** {case.get('id_siniestro', 'N/A')}")
        st.write(f"**Nivel:** {risk_badge(case.get('nivel_riesgo', ''))} · **Score:** {case.get('score_final', 'N/A')}")
        st.write(f"**Ramo:** {case.get('ramo', 'N/A')} · **Cobertura:** {case.get('cobertura', 'N/A')}")
        if "monto_reclamado" in case:
            st.write(f"**Monto reclamado:** {money(case.get('monto_reclamado'))}")
        if case.get("proveedor"):
            st.write(f"**Proveedor:** {case['proveedor']}")
        if case.get("explicacion_resumen"):
            st.caption(case["explicacion_resumen"])


def alerts_markdown(alerts: list[dict[str, Any]], limit: int = 6) -> str:
    if not alerts:
        return "- Sin alertas materiales."
    return "\n".join(
        f"- `{alert.get('codigo')}` {alert.get('descripcion')} ({alert.get('puntos')} pts). {alert.get('evidencia')}"
        for alert in alerts[:limit]
    )


def session_case_summary(case: dict[str, Any], index: int) -> dict[str, Any]:
    return {
        "id_temporal": case.get("id_temporal", f"TMP{index:03d}"),
        "ramo": case.get("ramo", ""),
        "cobertura": case.get("cobertura", ""),
        "score_final": case.get("score_final", 0),
        "nivel_riesgo": case.get("nivel_riesgo", ""),
        "monto_reclamado": case.get("monto_reclamado", 0),
        "alertas": len(case.get("alertas", [])),
        "explicacion": case.get("explicacion_resumen", ""),
    }
