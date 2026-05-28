from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fraudia_claims.app.pages import (
    page_agent,
    page_bandeja,
    page_case_form,
    page_demo_guiada,
    page_detalle,
    page_image_analysis,
    page_jury_test,
    page_methodology,
    page_network,
    page_audit,
    page_report,
    page_resumen,
)
from fraudia_claims.app.components import dashboard_styles, team_brand_sidebar
from fraudia_claims.storage import initialize_demo_data, load_table


st.set_page_config(
    page_title="FraudIA Claims",
    page_icon="FI",
    layout="wide",
    initial_sidebar_state="expanded",
)


PAGES = [
    "Demo guiada",
    "Resumen",
    "Bandeja de revision",
    "Detalle del siniestro",
    "Prueba del jurado",
    "Evaluar caso nuevo",
    "Analisis de imagenes",
    "Red de relaciones",
    "Agente IA",
    "Reporte ejecutivo",
    "Auditoria",
    "Metodologia y limitaciones",
]


@st.cache_resource(show_spinner=False)
def ensure_db() -> Path:
    return initialize_demo_data(force=False)


@st.cache_data(show_spinner=False)
def table(name: str) -> pd.DataFrame:
    ensure_db()
    return load_table(name)


def sidebar() -> str:
    dashboard_styles()
    team_brand_sidebar()
    st.sidebar.title("FraudIA Claims")
    st.sidebar.caption("Agente explicable para alertas de posible fraude en siniestros.")
    st.sidebar.write("### Login demo")
    role = st.sidebar.selectbox("Rol", ["Analista", "Jefatura", "Auditoria"])
    email_by_role = {
        "Analista": "analista@fraudia.demo",
        "Jefatura": "jefatura@fraudia.demo",
        "Auditoria": "auditoria@fraudia.demo",
    }
    st.session_state["demo_user"] = {
        "email": email_by_role[role],
        "name": f"{role} Demo",
        "role": role,
    }
    st.sidebar.caption(f"Sesion activa: {st.session_state['demo_user']['email']}")
    page = st.sidebar.radio("Navegacion", PAGES)
    st.sidebar.divider()
    if st.sidebar.button("Regenerar dataset demo"):
        initialize_demo_data(force=True)
        st.cache_data.clear()
        st.cache_resource.clear()
        st.rerun()
    st.sidebar.caption("Los scores son alertas de revision humana, no acusaciones.")
    return page


def main() -> None:
    db_path = ensure_db()
    page = sidebar()
    if page == "Demo guiada":
        page_demo_guiada(table, db_path)
    elif page == "Resumen":
        page_resumen(table, db_path)
    elif page == "Bandeja de revision":
        page_bandeja(table)
    elif page == "Detalle del siniestro":
        page_detalle(table, db_path)
    elif page == "Prueba del jurado":
        page_jury_test()
    elif page == "Evaluar caso nuevo":
        page_case_form()
    elif page == "Analisis de imagenes":
        page_image_analysis(table)
    elif page == "Red de relaciones":
        page_network(db_path)
    elif page == "Agente IA":
        page_agent(db_path)
    elif page == "Reporte ejecutivo":
        page_report(db_path)
    elif page == "Auditoria":
        page_audit(db_path)
    elif page == "Metodologia y limitaciones":
        page_methodology()


if __name__ == "__main__":
    main()
