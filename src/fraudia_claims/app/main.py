from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import pandas as pd
import streamlit as st

from fraudia_claims.agent_tools import (
    aggregate_alerts,
    get_claim_detail,
    list_risk_cases,
    score_candidate_claim,
)
from fraudia_claims.config import DEFAULT_DB_PATH, SCVS_CONTEXT_URL
from fraudia_claims.network import build_plotly_figure, graph_payload
from fraudia_claims.offline_agent import answer_offline
from fraudia_claims.openai_agent import ask_agent
from fraudia_claims.storage import initialize_demo_data, load_table
from fraudia_claims.utils import money


st.set_page_config(
    page_title="FraudIA Claims",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_resource(show_spinner=False)
def ensure_db() -> Path:
    return initialize_demo_data(force=False)


@st.cache_data(show_spinner=False)
def table(name: str) -> pd.DataFrame:
    ensure_db()
    return load_table(name)


def risk_badge(level: str) -> str:
    return {"Rojo": "🔴 Rojo", "Amarillo": "🟡 Amarillo", "Verde": "🟢 Verde"}.get(level, level)


def sidebar() -> str:
    st.sidebar.title("FraudIA Claims")
    st.sidebar.caption("Agente explicable para alertas de posible fraude en siniestros.")
    page = st.sidebar.radio(
        "Navegacion",
        [
            "Resumen",
            "Bandeja de revision",
            "Detalle del siniestro",
            "Evaluar caso nuevo",
            "Red de relaciones",
            "Agente IA",
            "Metodologia y limitaciones",
        ],
    )
    st.sidebar.divider()
    if st.sidebar.button("Regenerar dataset demo"):
        initialize_demo_data(force=True)
        st.cache_data.clear()
        st.cache_resource.clear()
        st.rerun()
    st.sidebar.caption("Los scores son alertas de revision humana, no acusaciones.")
    return page


def page_resumen() -> None:
    scores = table("scores")
    claims = table("siniestros")
    providers = table("proveedores")
    context = table("contexto_publico")
    metrics = table("metricas_modelo")
    merged = scores.merge(claims[["id_siniestro", "fecha_ocurrencia", "ramo", "sucursal"]], on=["id_siniestro", "ramo"], how="left")

    st.title("FraudIA Claims")
    st.subheader("Priorizacion explicable de siniestros para revision humana")
    st.info(
        "Este prototipo no acusa fraude ni decide pagos. Genera alertas trazables para que un analista priorice la revision."
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Siniestros", f"{len(claims):,}")
    c2.metric("Casos rojos", f"{int((scores['nivel_riesgo'] == 'Rojo').sum()):,}")
    c3.metric("Proveedores", f"{len(providers):,}")
    c4.metric("Score promedio", f"{scores['score_final'].mean():.1f}")

    by_level = scores["nivel_riesgo"].value_counts().reindex(["Verde", "Amarillo", "Rojo"]).fillna(0)
    by_ramo = merged.groupby(["ramo", "nivel_riesgo"]).size().unstack(fill_value=0)
    left, right = st.columns([1, 1])
    with left:
        st.write("### Distribucion por nivel")
        st.bar_chart(by_level)
    with right:
        st.write("### Alertas por ramo")
        st.bar_chart(by_ramo)

    st.write("### Fuente publica de contexto")
    st.dataframe(context, hide_index=True, use_container_width=True)
    st.markdown(f"Portal de referencia: [SCVS - informacion de seguros]({SCVS_CONTEXT_URL})")

    st.write("### Top 10 para revision")
    st.dataframe(pd.DataFrame(list_risk_cases(limit=10, db_path=DEFAULT_DB_PATH)), hide_index=True, use_container_width=True)

    st.write("### Metricas del modelo supervisado")
    st.caption("Calculadas sobre etiqueta sintetica; sirven para reproducibilidad, no para afirmar desempeno productivo.")
    metric_view = metrics[metrics["metrica"].isin(["precision", "recall", "f1", "auc_roc", "matriz_confusion_tp", "matriz_confusion_fp"])]
    st.dataframe(metric_view, hide_index=True, use_container_width=True)


def page_bandeja() -> None:
    scores = table("scores")
    claims = table("siniestros")
    providers = table("proveedores")[["id_proveedor", "nombre"]]
    data = scores.merge(
        claims[["id_siniestro", "fecha_ocurrencia", "ramo", "cobertura", "sucursal", "descripcion"]],
        on=["id_siniestro", "ramo", "cobertura", "sucursal"],
        how="left",
    ).merge(providers, on="id_proveedor", how="left")

    st.title("Bandeja de revision")
    st.caption("Filtra y descarga los casos priorizados por score.")
    f1, f2, f3, f4 = st.columns(4)
    level = f1.multiselect("Nivel", ["Rojo", "Amarillo", "Verde"], default=["Rojo", "Amarillo"])
    ramo = f2.multiselect("Ramo", sorted(data["ramo"].unique()), default=list(sorted(data["ramo"].unique())))
    ciudad = f3.multiselect("Ciudad", sorted(data["sucursal"].unique()), default=list(sorted(data["sucursal"].unique())))
    min_score = f4.slider("Score minimo", 0, 100, 41)
    filtered = data[
        data["nivel_riesgo"].isin(level)
        & data["ramo"].isin(ramo)
        & data["sucursal"].isin(ciudad)
        & (data["score_final"] >= min_score)
    ].sort_values("score_final", ascending=False)

    st.download_button(
        "Descargar bandeja CSV",
        filtered.to_csv(index=False).encode("utf-8"),
        "bandeja_revision_fraudia.csv",
        "text/csv",
    )
    show_cols = [
        "id_siniestro",
        "score_final",
        "nivel_riesgo",
        "ramo",
        "cobertura",
        "sucursal",
        "monto_reclamado",
        "nombre",
        "explicacion_resumen",
    ]
    st.dataframe(filtered[show_cols], hide_index=True, use_container_width=True)


def page_detalle() -> None:
    scores = table("scores")
    st.title("Detalle del siniestro")
    default_index = int(scores["score_final"].idxmax())
    claim_id = st.selectbox(
        "Selecciona un siniestro",
        scores.sort_values("score_final", ascending=False)["id_siniestro"].tolist(),
        index=0 if default_index >= 0 else None,
    )
    detail = get_claim_detail(claim_id, DEFAULT_DB_PATH)
    if "error" in detail:
        st.error(detail["error"])
        return

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Score", detail["score_final"])
    c2.metric("Nivel", risk_badge(detail["nivel_riesgo"]))
    c3.metric("Reglas", detail["score_reglas"])
    c4.metric("IA/NLP/Modelo", detail["score_anomalia"] + detail["score_nlp"] + detail.get("score_modelo", 0))

    st.write("### Resumen")
    st.write(detail["explicacion_resumen"])
    st.write("**Accion sugerida:**", detail["accion_sugerida"])
    st.write(
        f"**Ramo/cobertura:** {detail['ramo']} / {detail['cobertura']} · "
        f"**Monto:** {money(detail['monto_reclamado'])} · **Proveedor:** {detail.get('proveedor_nombre', '')}"
    )
    if detail.get("siniestro_similar"):
        st.write(
            f"**Narrativa similar:** {detail['siniestro_similar']} "
            f"({float(detail.get('similitud_narrativa') or 0):.1%})"
        )
    st.write(
        f"**Modelo supervisado demo:** {float(detail.get('probabilidad_modelo') or 0):.1%} "
        f"({int(detail.get('score_modelo') or 0)} pts)"
    )

    st.write("### Alertas")
    st.dataframe(pd.DataFrame(detail["alertas"]), hide_index=True, use_container_width=True)
    st.write("### Documentos")
    st.dataframe(pd.DataFrame(detail["documentos"]), hide_index=True, use_container_width=True)
    with st.expander("Descripcion del reclamo"):
        st.write(detail["descripcion"])


def page_case_form() -> None:
    st.title("Evaluar caso nuevo")
    st.caption("Calcula un score temporal sin modificar la base. Sirve para la prueba de fuego del jurado.")
    with st.form("candidate"):
        c1, c2, c3 = st.columns(3)
        ramo = c1.selectbox("Ramo", ["Vehiculos", "Salud", "Hogar"])
        coverage_options = {
            "Vehiculos": ["Choque", "Robo", "Responsabilidad Civil", "Perdida Total por Robo"],
            "Salud": ["Consulta Especializada", "Cirugia Ambulatoria", "Hospitalizacion", "Medicamentos"],
            "Hogar": ["Incendio", "Danio Agua", "Robo Hogar", "Responsabilidad Civil"],
        }
        cobertura = c2.selectbox("Cobertura", coverage_options[ramo])
        monto = c3.number_input("Monto reclamado", min_value=0.0, value=28000.0, step=500.0)
        c4, c5, c6 = st.columns(3)
        suma = c4.number_input("Suma asegurada", min_value=1.0, value=30000.0, step=500.0)
        dias_inicio = c5.number_input("Dias desde inicio de poliza", min_value=0, value=1, step=1)
        dias_fin = c6.number_input("Dias hasta fin de poliza", min_value=0, value=364, step=1)
        c7, c8, c9 = st.columns(3)
        dias_reporte = c7.number_input("Dias entre ocurrencia y reporte", min_value=0, value=5, step=1)
        denuncia_horas = c8.number_input("Horas hasta denuncia", min_value=0, value=72, step=1)
        proveedor_lista = c9.checkbox("Proveedor en lista restrictiva simulada")
        d1, d2, d3, d4 = st.columns(4)
        docs_ok = d1.checkbox("Documentos completos", value=False)
        docs_bad = d2.checkbox("Documentos inconsistentes", value=True)
        altered = d3.checkbox("Adulteracion documental")
        no_third = d4.checkbox("Sin tercero identificado", value=True)
        impossible = st.checkbox("Dinamica fisicamente imposible")
        duplicated = st.checkbox("Factura duplicada")
        submitted = st.form_submit_button("Calcular score")

    if submitted:
        result = score_candidate_claim(
            {
                "ramo": ramo,
                "cobertura": cobertura,
                "monto_reclamado": monto,
                "suma_asegurada": suma,
                "dias_desde_inicio_poliza": dias_inicio,
                "dias_desde_fin_poliza": dias_fin,
                "dias_entre_ocurrencia_reporte": dias_reporte,
                "denuncia_horas": denuncia_horas,
                "proveedor_lista_restrictiva": proveedor_lista,
                "documentos_completos": docs_ok,
                "documentos_inconsistentes": docs_bad,
                "adulteracion_documental": altered,
                "tercero_identificado": not no_third,
                "dinamica_imposible": impossible,
                "factura_duplicada": duplicated,
            }
        )
        st.session_state["ultimo_caso_evaluado"] = result
        st.success(f"Nivel {risk_badge(result['nivel_riesgo'])} · Score {result['score_final']}")
        st.write("**Accion sugerida:**", result["accion_sugerida"])
        st.dataframe(pd.DataFrame(result["alertas"]), hide_index=True, use_container_width=True)

    if "ultimo_caso_evaluado" in st.session_state:
        st.info("El caso queda visible en esta sesion como evaluacion temporal; no altera los scores historicos.")


def page_network() -> None:
    st.title("Red de relaciones")
    limit = st.slider("Numero de siniestros de mayor riesgo en la red", 20, 120, 60, step=10)
    payload = graph_payload(limit=limit, db_path=DEFAULT_DB_PATH)
    fig = build_plotly_figure(payload)
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Plotly no esta instalado. Mostrando datos de nodos y aristas.")
    left, right = st.columns(2)
    left.write("### Nodos")
    left.dataframe(pd.DataFrame(payload["nodes"]), hide_index=True, use_container_width=True)
    right.write("### Relaciones")
    right.dataframe(pd.DataFrame(payload["edges"]), hide_index=True, use_container_width=True)


def page_agent() -> None:
    st.title("Agente IA")
    st.caption("Funciona offline. Si configuras OPENAI_API_KEY y OPENAI_MODEL, redacta con OpenAI usando herramientas locales de solo lectura.")
    examples = [
        "Cuales son los 10 siniestros con mayor riesgo?",
        "Que proveedores concentran mas alertas rojas?",
        "Que ramos tienen mayor porcentaje de casos rojos?",
        "Que documentos faltan en los casos criticos?",
        "Que asegurados tienen mayor frecuencia de reclamos?",
        "Que casos tienen montos atipicos?",
        "Que proveedores concentran el 80% de las alertas rojas?",
        "Que metricas tiene el modelo supervisado?",
        "Genera un resumen ejecutivo de los casos criticos.",
    ]
    prompt = st.selectbox("Pregunta sugerida", examples)
    custom = st.text_area("O escribe tu pregunta", value=prompt, height=100)
    use_openai = st.toggle("Usar OpenAI si hay credenciales", value=True)
    if st.button("Preguntar"):
        with st.spinner("Consultando agente..."):
            answer = ask_agent(custom, DEFAULT_DB_PATH) if use_openai else answer_offline(custom, DEFAULT_DB_PATH)
        st.markdown(answer)


def page_methodology() -> None:
    st.title("Metodologia y limitaciones")
    st.markdown(
        """
### Que hace el prototipo
- Prioriza casos para revision humana con reglas explicables, anomalias numericas y similitud narrativa.
- Trabaja con datos sinteticos y contexto publico agregado; no usa datos personales reales.
- Mantiene trazabilidad por regla, puntos y evidencia visible para el analista.

### Que no hace
- No acusa formalmente fraude.
- No rechaza siniestros automaticamente.
- No decide pagos ni reemplaza al analista.
- No afirma desempeno real con etiquetas sinteticas.

### Score
`score_final = min(100, min(puntos_reglas, 60) + puntos_anomalia + puntos_nlp + puntos_modelo)`.
Las reglas criticas elevan el caso a rojo como minimo, para forzar revision especializada.

### Uso de IA
El LLM opcional solo redacta y consulta herramientas locales. El score base se calcula fuera del LLM y queda trazado en tablas. El modelo supervisado usa etiqueta sintetica para demo y deja metricas reproducibles.
        """
    )


def main() -> None:
    ensure_db()
    page = sidebar()
    if page == "Resumen":
        page_resumen()
    elif page == "Bandeja de revision":
        page_bandeja()
    elif page == "Detalle del siniestro":
        page_detalle()
    elif page == "Evaluar caso nuevo":
        page_case_form()
    elif page == "Red de relaciones":
        page_network()
    elif page == "Agente IA":
        page_agent()
    elif page == "Metodologia y limitaciones":
        page_methodology()


if __name__ == "__main__":
    main()
