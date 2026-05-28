from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from fraudia_claims.utils import money


RISK_LABELS = {
    "Rojo": "ALTO / Rojo",
    "Amarillo": "MEDIO / Amarillo",
    "Verde": "BAJO / Verde",
}

RISK_COLORS = {
    "Rojo": "#B42318",
    "Amarillo": "#B54708",
    "Verde": "#067647",
}

APP_ASSETS = Path(__file__).resolve().parent / "assets"
TEAM_LOGO = APP_ASSETS / "manta_bytes_logo.svg"


def risk_badge(level: str) -> str:
    return RISK_LABELS.get(str(level), str(level))


def ethical_notice() -> None:
    st.info(
        "FraudIA genera alertas para revision humana. No acusa fraude, no rechaza reclamos y no decide pagos."
    )


def dashboard_styles() -> None:
    st.markdown(
        """
        <style>
        .fraudia-hero {
            padding: 1.25rem 1.4rem;
            border-radius: 18px;
            background: linear-gradient(135deg, #0f2742 0%, #1f4e79 55%, #2f80ed 100%);
            color: white;
            margin-bottom: 1rem;
            box-shadow: 0 14px 34px rgba(15, 39, 66, 0.18);
        }
        .fraudia-hero-inner {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1.2rem;
        }
        .fraudia-hero-copy {
            flex: 1;
            min-width: 0;
        }
        .fraudia-hero-logo {
            width: 148px;
            max-width: 28%;
            padding: .45rem .65rem;
            border-radius: 14px;
            background: rgba(255, 255, 255, .95);
            box-shadow: 0 10px 24px rgba(15, 39, 66, 0.18);
        }
        .fraudia-hero h1 {
            margin: 0 0 .35rem 0;
            color: white;
        }
        .fraudia-hero p {
            margin: 0;
            max-width: 900px;
            color: #eaf2ff;
        }
        .fraudia-card {
            padding: 1rem;
            border-radius: 16px;
            border: 1px solid #d9e6f2;
            background: #ffffff;
            box-shadow: 0 8px 22px rgba(15, 39, 66, 0.08);
            min-height: 120px;
        }
        .fraudia-card span {
            display: block;
            color: #667085;
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: .05em;
        }
        .fraudia-card strong {
            display: block;
            color: #101828;
            font-size: 1.45rem;
            margin-top: .35rem;
        }
        .fraudia-card small {
            display: block;
            color: #667085;
            margin-top: .35rem;
        }
        .risk-pill {
            display: inline-block;
            padding: .18rem .55rem;
            border-radius: 999px;
            color: white;
            font-size: .78rem;
            font-weight: 700;
        }
        .fraudia-team-caption {
            text-align: center;
            color: #475467;
            font-size: .78rem;
            margin-top: -.35rem;
            margin-bottom: .65rem;
        }
        @media (max-width: 780px) {
            .fraudia-hero-inner {
                align-items: flex-start;
                flex-direction: column;
            }
            .fraudia-hero-logo {
                max-width: 190px;
                width: 44%;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _logo_data_uri() -> str:
    if not TEAM_LOGO.exists():
        return ""
    encoded = base64.b64encode(TEAM_LOGO.read_bytes()).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


def team_brand_sidebar() -> None:
    if TEAM_LOGO.exists():
        st.sidebar.image(str(TEAM_LOGO), width=210)
        st.sidebar.markdown(
            "<div class='fraudia-team-caption'>Manta Bytes | HackIAthon 2026</div>",
            unsafe_allow_html=True,
        )


def hero(title: str, subtitle: str) -> None:
    logo = _logo_data_uri()
    logo_markup = f'<img class="fraudia-hero-logo" src="{logo}" alt="Manta Bytes">' if logo else ""
    st.markdown(
        f"""
        <div class="fraudia-hero">
            <div class="fraudia-hero-inner">
                <div class="fraudia-hero-copy">
                    <h1>{title}</h1>
                    <p>{subtitle}</p>
                </div>
                {logo_markup}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_header(title: str, subtitle: str | None = None) -> None:
    st.markdown(f"### {title}")
    if subtitle:
        st.caption(subtitle)


def metric_cards(cards: list[dict[str, str]]) -> None:
    cols = st.columns(len(cards))
    for col, card in zip(cols, cards):
        with col:
            st.markdown(
                f"""
                <div class="fraudia-card">
                    <span>{card['label']}</span>
                    <strong>{card['value']}</strong>
                    <small>{card.get('help', '')}</small>
                </div>
                """,
                unsafe_allow_html=True,
            )


def metric_row(kpis: dict[str, Any]) -> None:
    metric_cards(
        [
            {
                "label": "Siniestros",
                "value": f"{int(kpis['total_siniestros']):,}",
                "help": "Dataset sintetico multirramo",
            },
            {
                "label": "Casos priorizados",
                "value": f"{int(kpis['casos_priorizados']):,}",
                "help": f"{kpis['porcentaje_priorizado']}% requiere revision",
            },
            {
                "label": "Casos rojos",
                "value": f"{int(kpis['casos_rojos']):,}",
                "help": f"{kpis['porcentaje_rojo']}% del total",
            },
            {
                "label": "Monto priorizado",
                "value": money(kpis["monto_priorizado"]),
                "help": "Exposicion para revision",
            },
            {
                "label": "Ahorro simulado",
                "value": money(kpis["ahorro_potencial_simulado"]),
                "help": "Supuesto operativo de demo",
            },
        ]
    )


def risk_pill(level: str) -> str:
    color = RISK_COLORS.get(str(level), "#475467")
    label = risk_badge(level)
    return f"<span class='risk-pill' style='background:{color}'>{label}</span>"


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
        st.write(f"**Nivel:** {risk_badge(case.get('nivel_riesgo', ''))} | **Score:** {case.get('score_final', 'N/A')}")
        st.write(f"**Ramo:** {case.get('ramo', 'N/A')} | **Cobertura:** {case.get('cobertura', 'N/A')}")
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
