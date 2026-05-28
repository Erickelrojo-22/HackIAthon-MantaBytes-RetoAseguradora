from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Query

from fraudia_claims.agent_tools import (
    aggregate_alerts,
    executive_report,
    get_claim_detail,
    get_relationship_network,
    get_model_metrics,
    list_risk_cases,
    provider_red_alert_pareto,
    score_candidate_claim,
)
from fraudia_claims.config import DEFAULT_DB_PATH
from fraudia_claims.storage import database_status, initialize_demo_data


app = FastAPI(
    title="FraudIA Claims API",
    version="0.2.0",
    description="API minima para integrar el scoring explicable de siniestros.",
)


@app.on_event("startup")
def startup() -> None:
    initialize_demo_data(force=False)


@app.get("/health")
def health() -> dict[str, Any]:
    initialize_demo_data(force=False)
    status = database_status(DEFAULT_DB_PATH)
    return {
        "status": "ok",
        "database": status,
        "principio": "Alertas de revision humana; no acusaciones ni decisiones automaticas.",
    }


@app.get("/claims/risk")
def claims_risk(
    limit: int = Query(default=10, ge=1, le=100),
    level: str | None = Query(default=None, pattern="^(Verde|Amarillo|Rojo)$"),
) -> list[dict[str, Any]]:
    initialize_demo_data(force=False)
    return list_risk_cases(limit=limit, level=level, db_path=DEFAULT_DB_PATH)


@app.get("/claims/{id_siniestro}")
def claim_detail(id_siniestro: str) -> dict[str, Any]:
    initialize_demo_data(force=False)
    return get_claim_detail(id_siniestro.upper(), db_path=DEFAULT_DB_PATH)


@app.get("/alerts/aggregate")
def alerts_aggregate(
    group_by: str = Query(default="proveedor", pattern="^(proveedor|ramo|ciudad|documentos)$"),
) -> list[dict[str, Any]]:
    initialize_demo_data(force=False)
    return aggregate_alerts(group_by=group_by, db_path=DEFAULT_DB_PATH)


@app.get("/alerts/provider-pareto")
def alerts_provider_pareto() -> list[dict[str, Any]]:
    initialize_demo_data(force=False)
    return provider_red_alert_pareto(db_path=DEFAULT_DB_PATH)


@app.get("/relationships")
def relationships(limit: int = Query(default=60, ge=10, le=120)) -> dict[str, list[dict[str, Any]]]:
    initialize_demo_data(force=False)
    return get_relationship_network(limit=limit, db_path=DEFAULT_DB_PATH)


@app.get("/report/summary")
def report_summary() -> dict[str, Any]:
    initialize_demo_data(force=False)
    return executive_report(db_path=DEFAULT_DB_PATH)


@app.post("/score-candidate")
def score_candidate(payload: dict[str, Any]) -> dict[str, Any]:
    return score_candidate_claim(payload)


@app.get("/metrics")
def metrics() -> list[dict[str, Any]]:
    initialize_demo_data(force=False)
    return get_model_metrics(db_path=DEFAULT_DB_PATH)
