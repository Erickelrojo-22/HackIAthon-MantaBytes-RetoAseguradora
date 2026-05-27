from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any

import pandas as pd

from fraudia_claims.analytics import (
    city_concentration,
    document_findings,
    executive_kpis,
    provider_pareto,
    risk_matrix,
    top_cases,
)
from fraudia_claims.config import DEFAULT_DB_PATH, SCVS_CONTEXT_URL
from fraudia_claims.demo import session_cases_frame
from fraudia_claims.utils import money


DISCLAIMER = (
    "FraudIA Claims genera alertas para revision humana. "
    "No constituye acusacion de fraude, decision legal, rechazo automatico ni recomendacion de pago."
)


def _html_table(frame: pd.DataFrame, max_rows: int = 15) -> str:
    if frame.empty:
        return "<p>No hay datos para esta seccion.</p>"
    safe = frame.head(max_rows).copy()
    return safe.to_html(index=False, escape=True, border=0, classes="data-table")


def _metric(label: str, value: str) -> str:
    return f"<div class='metric'><span>{escape(label)}</span><strong>{escape(value)}</strong></div>"


def build_executive_report_html(
    session_cases: list[dict[str, Any]] | None = None,
    db_path: Path = DEFAULT_DB_PATH,
) -> str:
    kpis = executive_kpis(db_path)
    top = top_cases(10, db_path)
    providers = provider_pareto(10, db_path)
    matrix = risk_matrix(db_path)
    cities = city_concentration(8, db_path)
    docs = document_findings(db_path)
    live_cases = session_cases_frame(session_cases)
    if not top.empty:
        top["monto_reclamado"] = top["monto_reclamado"].map(money)
    if not providers.empty:
        providers["monto_priorizado"] = providers["monto_priorizado"].map(money)

    metrics = "".join(
        [
            _metric("Siniestros analizados", f"{kpis['total_siniestros']:,}"),
            _metric("Casos priorizados", f"{kpis['casos_priorizados']:,} ({kpis['porcentaje_priorizado']}%)"),
            _metric("Casos rojos", f"{kpis['casos_rojos']:,} ({kpis['porcentaje_rojo']}%)"),
            _metric("Monto priorizado", money(kpis["monto_priorizado"])),
            _metric("Ahorro potencial simulado", money(kpis["ahorro_potencial_simulado"])),
        ]
    )
    live_section = ""
    if not live_cases.empty:
        live_section = f"""
        <section>
            <h2>Casos evaluados en vivo</h2>
            {_html_table(live_cases, 20)}
        </section>
        """

    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>Reporte Ejecutivo FraudIA Claims</title>
  <style>
    body {{ font-family: Arial, sans-serif; color: #172033; margin: 32px; line-height: 1.45; }}
    header {{ border-bottom: 3px solid #1f4e79; margin-bottom: 24px; padding-bottom: 12px; }}
    h1, h2 {{ color: #1f4e79; }}
    .warning {{ background: #fff4d6; border-left: 5px solid #d99a00; padding: 12px; margin: 16px 0; }}
    .metrics {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin: 18px 0; }}
    .metric {{ background: #f3f7fb; border: 1px solid #d9e6f2; border-radius: 8px; padding: 12px; }}
    .metric span {{ display: block; color: #5b677a; font-size: 12px; }}
    .metric strong {{ display: block; margin-top: 8px; font-size: 19px; }}
    .data-table {{ border-collapse: collapse; width: 100%; font-size: 12px; margin: 10px 0 22px; }}
    .data-table th {{ background: #1f4e79; color: white; text-align: left; padding: 7px; }}
    .data-table td {{ border-bottom: 1px solid #e5e7eb; padding: 7px; vertical-align: top; }}
    footer {{ color: #5b677a; font-size: 12px; margin-top: 36px; border-top: 1px solid #e5e7eb; padding-top: 12px; }}
  </style>
</head>
<body>
  <header>
    <h1>Reporte Ejecutivo FraudIA Claims</h1>
    <p>Detector explicable de alertas de posible fraude en siniestros para Aseguradora del Sur.</p>
  </header>
  <div class="warning"><strong>Principio etico:</strong> {escape(DISCLAIMER)}</div>
  <section>
    <h2>Indicadores clave</h2>
    <div class="metrics">{metrics}</div>
  </section>
  <section>
    <h2>Top 10 casos para revision</h2>
    {_html_table(top, 10)}
  </section>
  <section>
    <h2>Proveedores con mayor concentracion</h2>
    {_html_table(providers, 10)}
  </section>
  <section>
    <h2>Matriz ramo / nivel</h2>
    {_html_table(matrix, 20)}
  </section>
  <section>
    <h2>Ciudades observadas</h2>
    {_html_table(cities, 10)}
  </section>
  <section>
    <h2>Documentos criticos</h2>
    {_html_table(docs, 15)}
  </section>
  {live_section}
  <section>
    <h2>Metodologia</h2>
    <p>El score combina reglas de negocio, deteccion de anomalias por ramo y similitud narrativa. Las etiquetas del dataset son sinteticas y se usan solo para demo y pruebas.</p>
    <p>Fuente publica de contexto: <a href="{SCVS_CONTEXT_URL}">SCVS - Portal de informacion de seguros</a>.</p>
  </section>
  <footer>{escape(DISCLAIMER)}</footer>
</body>
</html>"""
