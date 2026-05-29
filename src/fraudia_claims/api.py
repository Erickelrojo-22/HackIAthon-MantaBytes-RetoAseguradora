from __future__ import annotations

from typing import Any

import json
import tempfile
from pathlib import Path
from threading import Lock

import pandas as pd
from fastapi import BackgroundTasks, Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from fraudia_claims.agent_tools import (
    aggregate_alerts,
    claim_exists,
    executive_report,
    get_claim_detail,
    get_relationship_network,
    get_model_metrics,
    list_risk_cases,
    provider_red_alert_pareto,
    score_candidate_claim,
)
from fraudia_claims.analytics import city_concentration, executive_kpis, provider_pareto, risk_matrix
from fraudia_claims.audit import list_audit_events, log_event
from fraudia_claims.auth import DemoUser, authenticate_demo_user, current_user, optional_user, require_roles, user_to_dict
from fraudia_claims.config import DEFAULT_DB_PATH
from fraudia_claims.ingestion import REQUIRED_COLUMNS, data_quality_report, validate_company_tables
from fraudia_claims.openai_agent import ask_agent_with_status
from fraudia_claims.reviews import REVIEW_STATUSES, create_review_decision, list_review_history
from fraudia_claims.storage import database_status, ensure_operational_tables, initialize_demo_data


_APP_READY = False
_APP_READY_LOCK = Lock()


def ensure_app_ready() -> None:
    global _APP_READY
    if _APP_READY:
        return
    with _APP_READY_LOCK:
        if _APP_READY:
            return
        initialize_demo_data(force=False)
        ensure_operational_tables(DEFAULT_DB_PATH)
        _APP_READY = True


def queue_log_event(
    background_tasks: BackgroundTasks,
    actor_email: str,
    actor_role: str,
    action: str,
    resource_type: str,
    resource_id: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    background_tasks.add_task(
        log_event,
        actor_email,
        actor_role,
        action,
        resource_type,
        resource_id,
        metadata,
        DEFAULT_DB_PATH,
    )


app = FastAPI(
    title="FraudIA Claims API",
    version="0.2.0",
    description="API minima para integrar el scoring explicable de siniestros.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class LoginPayload(BaseModel):
    email: str
    password: str


class ReviewDecisionPayload(BaseModel):
    status: str = Field(pattern="^(En revision|Descartado|Escalado|Confirmado para investigacion)$")
    comentario: str = ""


class AgentQuestionPayload(BaseModel):
    question: str
    id_siniestro: str | None = None
    scope: str = "general"


@app.on_event("startup")
def startup() -> None:
    ensure_app_ready()


@app.post("/auth/login")
def login(payload: LoginPayload) -> dict[str, Any]:
    token, user = authenticate_demo_user(payload.email, payload.password)
    return {"access_token": token, "user": user_to_dict(user)}


@app.get("/health")
def health() -> dict[str, Any]:
    ensure_app_ready()
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
    ensure_app_ready()
    return list_risk_cases(limit=limit, level=level, db_path=DEFAULT_DB_PATH)


@app.get("/claims/{id_siniestro}")
def claim_detail(
    id_siniestro: str,
    background_tasks: BackgroundTasks,
    user: DemoUser | None = Depends(optional_user),
) -> dict[str, Any]:
    ensure_app_ready()
    detail = get_claim_detail(id_siniestro.upper(), db_path=DEFAULT_DB_PATH)
    if user is not None and "error" not in detail:
        queue_log_event(background_tasks, user.email, user.role, "claim.detail.viewed", "claim", id_siniestro.upper())
    return detail


@app.get("/dashboard/kpis")
def dashboard_kpis(
    background_tasks: BackgroundTasks,
    user: DemoUser = Depends(require_roles("Analista", "Jefatura", "Auditoria")),
) -> dict[str, Any]:
    ensure_app_ready()
    kpis = executive_kpis(DEFAULT_DB_PATH)
    providers = provider_pareto(5, DEFAULT_DB_PATH).to_dict(orient="records")
    cities = city_concentration(5, DEFAULT_DB_PATH).to_dict(orient="records")
    matrix = risk_matrix(DEFAULT_DB_PATH).to_dict(orient="records")
    queue_log_event(background_tasks, user.email, user.role, "dashboard.kpis.viewed", "dashboard", "kpis")
    return {"kpis": kpis, "proveedores_criticos": providers, "ciudades_criticas": cities, "matriz_riesgo": matrix}


@app.post("/claims/{id_siniestro}/review-decision")
def review_decision(
    id_siniestro: str,
    payload: ReviewDecisionPayload,
    user: DemoUser = Depends(require_roles("Analista", "Jefatura")),
) -> dict[str, Any]:
    ensure_app_ready()
    detail = get_claim_detail(id_siniestro.upper(), db_path=DEFAULT_DB_PATH)
    if "error" in detail:
        raise HTTPException(status_code=404, detail=detail["error"])
    return create_review_decision(
        id_siniestro.upper(),
        payload.status,
        payload.comentario,
        user.email,
        user.role,
        db_path=DEFAULT_DB_PATH,
    )


@app.get("/claims/{id_siniestro}/review-history")
def review_history(
    id_siniestro: str,
    background_tasks: BackgroundTasks,
    user: DemoUser = Depends(require_roles("Analista", "Jefatura", "Auditoria")),
) -> list[dict[str, Any]]:
    ensure_app_ready()
    queue_log_event(background_tasks, user.email, user.role, "review_history.viewed", "claim", id_siniestro.upper())
    return list_review_history(id_siniestro.upper(), db_path=DEFAULT_DB_PATH)


@app.get("/audit-log")
def audit_log(
    background_tasks: BackgroundTasks,
    actor_email: str | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    user: DemoUser = Depends(require_roles("Jefatura", "Auditoria")),
) -> list[dict[str, Any]]:
    ensure_app_ready()
    queue_log_event(background_tasks, user.email, user.role, "audit_log.viewed", "audit", "audit_log")
    return list_audit_events(
        actor_email=actor_email,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        db_path=DEFAULT_DB_PATH,
    )


@app.post("/agent/question")
def agent_question(
    payload: AgentQuestionPayload,
    background_tasks: BackgroundTasks,
    user: DemoUser = Depends(current_user),
) -> dict[str, Any]:
    ensure_app_ready()
    question = payload.question
    if payload.id_siniestro and payload.id_siniestro.upper() not in question.upper():
        question = f"{question}\n\nSiniestro relacionado: {payload.id_siniestro.upper()}"
    answer, source = ask_agent_with_status(question, DEFAULT_DB_PATH)
    queue_log_event(
        background_tasks,
        user.email,
        user.role,
        "agent.question.asked",
        payload.scope or "agent",
        payload.id_siniestro.upper() if payload.id_siniestro else "general",
        {"question": payload.question, "source": source},
    )
    return {
        "answer": answer,
        "source": source,
        "disclaimer": "Alerta de revision humana; no acusacion ni decision automatica.",
    }


@app.get("/agent/suggested-questions/{id_siniestro}")
def suggested_questions(
    id_siniestro: str,
    background_tasks: BackgroundTasks,
    user: DemoUser = Depends(require_roles("Analista", "Jefatura", "Auditoria")),
) -> dict[str, Any]:
    ensure_app_ready()
    if not claim_exists(id_siniestro.upper(), db_path=DEFAULT_DB_PATH):
        raise HTTPException(status_code=404, detail=f"No existe el siniestro {id_siniestro.upper()}.")
    questions = [
        f"Explica por que el siniestro {id_siniestro.upper()} fue priorizado.",
        f"Que documentos observados tiene el siniestro {id_siniestro.upper()}?",
        f"Que proveedor atiende el siniestro {id_siniestro.upper()} y que alertas concentra?",
        f"Que accion humana recomiendas para {id_siniestro.upper()} sin acusar fraude?",
    ]
    queue_log_event(background_tasks, user.email, user.role, "agent.suggested_questions.generated", "claim", id_siniestro.upper())
    return {"id_siniestro": id_siniestro.upper(), "questions": questions}


@app.get("/agent/executive-summary")
def agent_executive_summary(
    background_tasks: BackgroundTasks,
    group_by: str = Query(pattern="^(proveedor|ciudad)$"),
    value: str = "",
    user: DemoUser = Depends(require_roles("Jefatura", "Auditoria")),
) -> dict[str, Any]:
    ensure_app_ready()
    if group_by == "proveedor":
        data = provider_pareto(15, DEFAULT_DB_PATH).to_dict(orient="records")
    else:
        data = city_concentration(15, DEFAULT_DB_PATH).to_dict(orient="records")
    filtered = [row for row in data if not value or value.lower() in json.dumps(row, ensure_ascii=False).lower()]
    queue_log_event(background_tasks, user.email, user.role, "agent.executive_summary.generated", group_by, value or "all")
    return {
        "group_by": group_by,
        "value": value,
        "summary": "Resumen ejecutivo para priorizacion humana; no constituye acusacion ni decision automatica.",
        "rows": filtered,
    }


@app.post("/claims/upload-csv")
async def upload_claims_csv(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user: DemoUser = Depends(require_roles("Analista", "Jefatura")),
) -> dict[str, Any]:
    ensure_app_ready()
    content = await file.read()
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
            tmp.write(content)
            temp_path = Path(tmp.name)
        frame = pd.read_csv(temp_path)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"CSV invalido: {exc}") from exc
    finally:
        try:
            temp_path.unlink(missing_ok=True)  # type: ignore[name-defined]
        except Exception:
            pass

    stem = Path(file.filename or "").stem
    required = REQUIRED_COLUMNS.get(stem, set())
    missing = sorted(required - set(frame.columns)) if required else []
    status_value = "revisar" if missing else "ok"
    queue_log_event(
        background_tasks,
        user.email,
        user.role,
        "claims.upload_csv.validated",
        "csv",
        file.filename or "upload.csv",
        {"rows": len(frame), "columns": list(frame.columns), "status": status_value, "missing": missing},
    )
    return {
        "filename": file.filename,
        "table_detected": stem or None,
        "rows": int(len(frame)),
        "columns": list(frame.columns),
        "status": status_value,
        "missing_columns": missing,
        "message": "CSV validado. En v1 no reemplaza tablas persistidas desde este endpoint.",
    }


@app.get("/alerts/aggregate")
def alerts_aggregate(
    group_by: str = Query(default="proveedor", pattern="^(proveedor|ramo|ciudad|documentos)$"),
) -> list[dict[str, Any]]:
    ensure_app_ready()
    return aggregate_alerts(group_by=group_by, db_path=DEFAULT_DB_PATH)


@app.get("/alerts/provider-pareto")
def alerts_provider_pareto() -> list[dict[str, Any]]:
    ensure_app_ready()
    return provider_red_alert_pareto(db_path=DEFAULT_DB_PATH)


@app.get("/relationships")
def relationships(limit: int = Query(default=60, ge=10, le=120)) -> dict[str, list[dict[str, Any]]]:
    ensure_app_ready()
    return get_relationship_network(limit=limit, db_path=DEFAULT_DB_PATH)


@app.get("/report/summary")
def report_summary() -> dict[str, Any]:
    ensure_app_ready()
    return executive_report(db_path=DEFAULT_DB_PATH)


@app.post("/score-candidate")
def score_candidate(payload: dict[str, Any]) -> dict[str, Any]:
    return score_candidate_claim(payload)


@app.get("/metrics")
def metrics() -> list[dict[str, Any]]:
    ensure_app_ready()
    return get_model_metrics(db_path=DEFAULT_DB_PATH)
