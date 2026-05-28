from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

import pandas as pd
import plotly.express as px
import streamlit as st

from fraudia_claims.agent_tools import get_claim_detail, list_risk_cases, score_candidate_claim
from fraudia_claims.analytics import (
    city_concentration,
    document_findings,
    executive_kpis,
    provider_pareto,
    risk_matrix,
)
from fraudia_claims.app.components import (
    alerts_markdown,
    case_card,
    dashboard_styles,
    ethical_notice,
    hero,
    metric_row,
    risk_badge,
    section_header,
    session_case_summary,
    show_dataframe,
)
from fraudia_claims.config import DEFAULT_DB_PATH, SCVS_CONTEXT_URL
from fraudia_claims.demo import GUIDED_DEMO_STEPS, demo_questions, featured_claims, session_cases_frame
from fraudia_claims.network import build_plotly_figure, graph_payload
from fraudia_claims.offline_agent import answer_offline
from fraudia_claims.openai_agent import ask_agent
from fraudia_claims.reports import build_executive_report_html
from fraudia_claims.utils import money


TableLoader = Callable[[str], pd.DataFrame]


def _session_cases() -> list[dict[str, Any]]:
    if "session_cases" not in st.session_state:
        st.session_state["session_cases"] = []
    return st.session_state["session_cases"]


def _set_selected_claim(claim_id: str) -> None:
    st.session_state["selected_claim_id"] = claim_id


def page_demo_guiada(table: TableLoader, db_path: Path = DEFAULT_DB_PATH) -> None:
    st.title("Demo guiada")
    ethical_notice()
    highlights = featured_claims(db_path)
    metric_row(highlights["kpis"])

    st.write("## Ruta sugerida para el pitch")
    for step in GUIDED_DEMO_STEPS:
        with st.container(border=True):
            st.write(f"### {step['titulo']}")
            st.write(f"**Objetivo:** {step['objetivo']}")
            st.write(f"**Accion en vivo:** {step['accion']}")
            st.caption(step["mensaje"])

    st.write("## Casos listos para presentar")
    col1, col2, col3 = st.columns(3)
    with col1:
        case_card("Caso rojo destacado", highlights["caso_rojo"])
        if st.button("Usar caso rojo en detalle"):
            _set_selected_claim(highlights["caso_rojo"]["id_siniestro"])
    with col2:
        case_card("Caso amarillo explicable", highlights["caso_amarillo"])
        if highlights["caso_amarillo"] and st.button("Usar caso amarillo en detalle"):
            _set_selected_claim(highlights["caso_amarillo"]["id_siniestro"])
    with col3:
        provider = highlights["proveedor_recurrente"]
        with st.container(border=True):
            st.write("### Proveedor recurrente")
            st.write(f"**Proveedor:** {provider.get('proveedor', 'N/A')}")
            st.write(f"**Tipo:** {provider.get('tipo', 'N/A')}")
            st.write(f"**Alertas rojas:** {provider.get('alertas_rojas', 0)}")
            st.write(f"**Monto priorizado:** {money(provider.get('monto_priorizado', 0))}")

    st.write("## Preguntas preparadas para el agente")
    for question in demo_questions():
        st.code(question)


def page_resumen(table: TableLoader, db_path: Path = DEFAULT_DB_PATH) -> None:
    dashboard_styles()
    scores = table("scores")
    claims = table("siniestros")
    context = table("contexto_publico")
    kpis = executive_kpis(db_path)
    merged = scores.merge(
        claims[["id_siniestro", "fecha_ocurrencia", "ramo", "sucursal", "monto_reclamado"]],
        on=["id_siniestro", "ramo"],
        how="left",
    )

    hero(
        "FraudIA Claims",
        "Dashboard ejecutivo para priorizar alertas de posible fraude en siniestros. "
        "El foco es acelerar la revision humana con evidencia trazable.",
    )
    ethical_notice()
    section_header("Indicadores ejecutivos", "Resumen de exposicion, prioridad y ahorro potencial simulado.")
    metric_row(kpis)

    level_order = ["Verde", "Amarillo", "Rojo"]
    level_colors = {"Verde": "#12B76A", "Amarillo": "#F79009", "Rojo": "#D92D20"}
    by_level = (
        scores["nivel_riesgo"]
        .value_counts()
        .reindex(level_order)
        .fillna(0)
        .reset_index()
    )
    by_level.columns = ["nivel_riesgo", "total"]
    by_ramo = (
        merged.groupby(["ramo", "nivel_riesgo"], as_index=False)
        .agg(total=("id_siniestro", "count"), monto=("monto_reclamado", "sum"))
    )
    providers = provider_pareto(10, db_path)
    cities = city_concentration(10, db_path)

    section_header("Mapa de riesgo", "Distribucion del semaforo y concentracion por ramo.")
    left, right = st.columns([0.9, 1.1])
    with left:
        fig = px.pie(
            by_level,
            names="nivel_riesgo",
            values="total",
            hole=0.48,
            color="nivel_riesgo",
            color_discrete_map=level_colors,
        )
        fig.update_traces(textposition="inside", textinfo="percent+label")
        fig.update_layout(height=360, margin=dict(l=10, r=10, t=20, b=10), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    with right:
        fig = px.bar(
            by_ramo,
            x="ramo",
            y="total",
            color="nivel_riesgo",
            color_discrete_map=level_colors,
            category_orders={"nivel_riesgo": level_order},
            labels={"ramo": "Ramo", "total": "Siniestros", "nivel_riesgo": "Nivel"},
        )
        fig.update_layout(height=360, barmode="stack", margin=dict(l=10, r=10, t=20, b=10), legend_title_text="Nivel")
        st.plotly_chart(fig, use_container_width=True)

    section_header("Concentracion operativa", "Proveedores y ciudades con mayor carga de revision.")
    c1, c2 = st.columns(2)
    with c1:
        if providers.empty:
            show_dataframe(providers)
        else:
            fig = px.bar(
                providers.sort_values("alertas_rojas"),
                x="alertas_rojas",
                y="proveedor",
                orientation="h",
                color="score_promedio",
                color_continuous_scale=["#D1E9FF", "#1F4E79"],
                labels={"alertas_rojas": "Alertas rojas", "proveedor": "Proveedor", "score_promedio": "Score promedio"},
            )
            fig.update_layout(height=420, margin=dict(l=10, r=10, t=20, b=10), coloraxis_showscale=False)
            st.plotly_chart(fig, use_container_width=True)
    with c2:
        if cities.empty:
            show_dataframe(cities)
        else:
            fig = px.bar(
                cities,
                x="ciudad",
                y="casos_revision",
                color="porcentaje_revision",
                color_continuous_scale=["#ECFDF3", "#067647"],
                labels={"ciudad": "Ciudad", "casos_revision": "Casos revision", "porcentaje_revision": "% revision"},
            )
            fig.update_layout(height=420, margin=dict(l=10, r=10, t=20, b=10), coloraxis_showscale=False)
            st.plotly_chart(fig, use_container_width=True)

    section_header("Tablero para analistas", "Casos prioritarios y tablas de soporte para auditoria.")
    t1, t2 = st.columns([1.2, 1])
    with t1:
        st.write("#### Top 10 para revision")
        top = pd.DataFrame(list_risk_cases(limit=10, db_path=db_path))
        show_dataframe(top)
    with t2:
        st.write("#### Pareto de proveedores")
        show_dataframe(providers)

    st.write("#### Fuente publica de contexto")
    st.dataframe(context, hide_index=True, use_container_width=True)
    st.markdown(f"Portal de referencia: [SCVS - informacion de seguros]({SCVS_CONTEXT_URL})")


def page_bandeja(table: TableLoader) -> None:
    scores = table("scores")
    claims = table("siniestros")
    providers = table("proveedores")[["id_proveedor", "nombre"]]
    data = scores.merge(
        claims[["id_siniestro", "fecha_ocurrencia", "ramo", "cobertura", "sucursal", "descripcion"]],
        on=["id_siniestro", "ramo", "cobertura", "sucursal"],
        how="left",
    ).merge(providers, on="id_proveedor", how="left")

    st.title("Bandeja de revision")
    st.caption("Filtra, ordena y descarga los casos priorizados por score.")
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
    show_dataframe(filtered[show_cols])


def page_detalle(table: TableLoader, db_path: Path = DEFAULT_DB_PATH) -> None:
    scores = table("scores")
    st.title("Detalle del siniestro")
    ordered = scores.sort_values("score_final", ascending=False)["id_siniestro"].tolist()
    selected = st.session_state.get("selected_claim_id")
    index = ordered.index(selected) if selected in ordered else 0
    claim_id = st.selectbox("Selecciona un siniestro", ordered, index=index)
    _set_selected_claim(claim_id)
    detail = get_claim_detail(claim_id, db_path)
    if "error" in detail:
        st.error(detail["error"])
        return

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Score", detail["score_final"])
    c2.metric("Nivel", risk_badge(detail["nivel_riesgo"]))
    c3.metric("Reglas", detail["score_reglas"])
    c4.metric("IA/NLP", detail["score_anomalia"] + detail["score_nlp"])

    st.write("### Resumen")
    st.write(detail["explicacion_resumen"])
    st.write("**Accion sugerida:**", detail["accion_sugerida"])
    st.write(
        f"**Ramo/cobertura:** {detail['ramo']} / {detail['cobertura']} | "
        f"**Monto:** {money(detail['monto_reclamado'])} | **Proveedor:** {detail.get('proveedor_nombre', '')}"
    )
    if detail.get("siniestro_similar"):
        st.write(
            f"**Narrativa similar:** {detail['siniestro_similar']} "
            f"({float(detail.get('similitud_narrativa') or 0):.1%})"
        )

    st.write("### Alertas principales")
    st.markdown(alerts_markdown(detail["alertas"], limit=8))
    st.dataframe(pd.DataFrame(detail["alertas"]), hide_index=True, use_container_width=True)
    st.write("### Documentos")
    st.dataframe(pd.DataFrame(detail["documentos"]), hide_index=True, use_container_width=True)
    with st.expander("Descripcion del reclamo"):
        st.write(detail["descripcion"])


def page_case_form() -> None:
    st.title("Evaluar caso nuevo")
    st.caption("Calcula un score temporal sin modificar SQLite. Ideal para la prueba de fuego del jurado.")
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
        cases = _session_cases()
        result.update(
            {
                "id_temporal": f"TMP{len(cases) + 1:03d}",
                "ramo": ramo,
                "cobertura": cobertura,
                "monto_reclamado": monto,
                "suma_asegurada": suma,
            }
        )
        cases.append(result)
        st.success(f"Nivel {risk_badge(result['nivel_riesgo'])} | Score {result['score_final']}")
        st.write("**Accion sugerida:**", result["accion_sugerida"])
        st.markdown(alerts_markdown(result["alertas"]))

    live = _session_cases()
    st.write("### Casos evaluados en vivo")
    frame = pd.DataFrame([session_case_summary(case, idx) for idx, case in enumerate(live, start=1)])
    show_dataframe(frame, "Todavia no hay casos evaluados en vivo.")


def page_network(db_path: Path = DEFAULT_DB_PATH) -> None:
    st.title("Red de relaciones")
    limit = st.slider("Numero de siniestros de mayor riesgo en la red", 20, 120, 60, step=10)
    payload = graph_payload(limit=limit, db_path=db_path)
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


def page_agent(db_path: Path = DEFAULT_DB_PATH) -> None:
    st.title("Agente IA")
    st.caption("Funciona offline. Si configuras OPENAI_API_KEY y OPENAI_MODEL, redacta con OpenAI usando herramientas locales.")
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []

    examples = demo_questions()
    selected = st.selectbox("Pregunta sugerida", examples)
    custom = st.text_area("O escribe tu pregunta", value=selected, height=100)
    use_openai = st.toggle("Usar OpenAI si hay credenciales", value=True)
    if st.button("Preguntar"):
        with st.spinner("Consultando agente..."):
            if use_openai:
                answer = ask_agent(custom, db_path, session_cases=_session_cases())
                source = "OpenAI opcional con fallback offline"
            else:
                answer = answer_offline(custom, db_path, session_cases=_session_cases())
                source = "Offline"
        st.session_state["chat_history"].append({"question": custom, "answer": answer, "source": source})

    for item in reversed(st.session_state["chat_history"][-6:]):
        with st.chat_message("user"):
            st.write(item["question"])
        with st.chat_message("assistant"):
            st.caption(f"Fuente: {item['source']}")
            st.markdown(item["answer"])


def page_report(db_path: Path = DEFAULT_DB_PATH) -> None:
    st.title("Reporte ejecutivo")
    ethical_notice()
    kpis = executive_kpis(db_path)
    metric_row(kpis)

    html = build_executive_report_html(_session_cases(), db_path)
    st.download_button(
        "Descargar reporte HTML",
        html.encode("utf-8"),
        "reporte_ejecutivo_fraudia.html",
        "text/html",
    )

    c1, c2 = st.columns(2)
    with c1:
        st.write("### Matriz ramo / nivel")
        show_dataframe(risk_matrix(db_path))
        st.write("### Documentos criticos")
        show_dataframe(document_findings(db_path))
    with c2:
        st.write("### Pareto de proveedores")
        show_dataframe(provider_pareto(10, db_path))
        st.write("### Casos evaluados en vivo")
        show_dataframe(session_cases_frame(_session_cases()), "No hay casos temporales en sesion.")


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
`score_final = min(100, min(puntos_reglas, 60) + puntos_anomalia + puntos_nlp)`.
Las reglas criticas elevan el caso a rojo como minimo, para forzar revision especializada.

### Uso de IA
El LLM opcional solo redacta y consulta herramientas locales. El score base se calcula fuera del LLM y queda trazado en tablas.
        """
    )
