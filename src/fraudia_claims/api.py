from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Query

from fraudia_claims.agent_tools import (
    aggregate_alerts,
    get_claim_detail,
    get_model_metrics,
    list_risk_cases,
    score_candidate_claim,
)
from fraudia_claims.config import DEFAULT_DB_PATH
from fraudia_claims.storage import initialize_demo_data


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
    return {
        "status": "ok",
        "db_path": str(DEFAULT_DB_PATH),
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


@app.post("/score-candidate")
def score_candidate(payload: dict[str, Any]) -> dict[str, Any]:
    return score_candidate_claim(payload)


@app.get("/metrics")
def metrics() -> list[dict[str, Any]]:
    initialize_demo_data(force=False)
    return get_model_metrics(db_path=DEFAULT_DB_PATH)
