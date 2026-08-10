from __future__ import annotations

from typing import Any, Literal

import json
import re
import tempfile
from pathlib import Path
from threading import Lock

import pandas as pd
from fastapi import BackgroundTasks, Depends, FastAPI, File, HTTPException, Query, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from fraudia_claims.agent_tools import (
    aggregate_alerts,
    claim_exists,
    count_risk_cases,
    executive_report,
    get_claim_detail,
    get_relationship_network,
    get_model_metrics,
    list_risk_case_options,
    list_risk_cases,
    provider_red_alert_pareto,
    score_candidate_claim,
)
from fraudia_claims.analytics import city_concentration, executive_kpis, provider_pareto, risk_matrix
from fraudia_claims.audit import list_audit_events, log_event
from fraudia_claims.auth import DemoUser, authenticate_demo_user, current_user, require_roles, user_to_dict
from fraudia_claims.config import CORS_ORIGINS, DEFAULT_DB_PATH, MAX_CSV_UPLOAD_BYTES
from fraudia_claims.ingestion import REQUIRED_COLUMNS, missing_required_columns
from fraudia_claims.openai_agent import ask_agent_with_status
from fraudia_claims.rate_limit import enforce_rate_limit
from fraudia_claims.reviews import REVIEW_STATUSES, create_review_decision, list_review_history
from fraudia_claims.storage import database_status, ensure_operational_tables, initialize_demo_data
from fraudia_claims.vision import MAX_IMAGE_BYTES, analyze_claim_image, image_analysis_available


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
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
    expose_headers=["X-Total-Count"],
)


class LoginPayload(BaseModel):
    email: str
    password: str


_REVIEW_STATUS_PATTERN = "^(" + "|".join(re.escape(status) for status in REVIEW_STATUSES) + ")$"


class ReviewDecisionPayload(BaseModel):
    status: str = Field(pattern=_REVIEW_STATUS_PATTERN)
    comentario: str = ""


class AgentQuestionPayload(BaseModel):
    question: str
    id_siniestro: str | None = None
    scope: str = "general"


class CandidateScorePayload(BaseModel):
    ramo: Literal["Vehiculos", "Salud", "Hogar"]
    cobertura: str = Field(min_length=3, max_length=80)
    monto_reclamado: float = Field(ge=100, le=100000)
    suma_asegurada: float = Field(ge=500, le=200000)
    dias_desde_inicio_poliza: int = Field(ge=0, le=365)
    dias_desde_fin_poliza: int = Field(ge=0, le=365)
    dias_entre_ocurrencia_reporte: int = Field(ge=0, le=365)
    denuncia_horas: int = Field(ge=0, le=720)
    documentos_completos: bool = True
    documentos_inconsistentes: bool = False
    tercero_identificado: bool = True
    proveedor_lista_restrictiva: bool = False
    adulteracion_documental: bool = False
    dinamica_imposible: bool = False
    factura_duplicada: bool = False
    narrativa_clonada: bool = False


ALLOWED_CANDIDATE_COVERAGES: dict[str, set[str]] = {
    "Vehiculos": {
        "Perdida Total por Robo",
        "Robo",
        "Robo de Accesorios",
        "Choque",
        "Cristales",
        "Responsabilidad Civil",
    },
    "Salud": {
        "Consulta Especializada",
        "Emergencia",
        "Hospitalizacion",
        "Procedimiento Ambulatorio",
    },
    "Hogar": {
        "Danio Agua",
        "Incendio",
        "Robo",
        "Cristales",
        "Responsabilidad Civil",
    },
}


def candidate_payload_data(payload: CandidateScorePayload) -> dict[str, Any]:
    if hasattr(payload, "model_dump"):
        return payload.model_dump()
    return payload.dict()


def validate_candidate_payload(data: dict[str, Any]) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    ramo = str(data["ramo"])
    cobertura = str(data["cobertura"])
    if cobertura not in ALLOWED_CANDIDATE_COVERAGES.get(ramo, set()):
        errors.append(
            {
                "field": "cobertura",
                "message": f"La cobertura no corresponde al ramo {ramo}.",
            }
        )
    if float(data["monto_reclamado"]) > float(data["suma_asegurada"]):
        errors.append(
            {
                "field": "monto_reclamado",
                "message": "El monto reclamado no debe superar la suma asegurada en esta prueba.",
            }
        )
    if int(data["dias_desde_inicio_poliza"]) + int(data["dias_desde_fin_poliza"]) > 366:
        errors.append(
            {
                "field": "dias_desde_inicio_poliza",
                "message": "La vigencia simulada no debe superar 366 dias.",
            }
        )
    return errors


@app.on_event("startup")
def startup() -> None:
    ensure_app_ready()


@app.post("/auth/login")
def login(payload: LoginPayload, request: Request) -> dict[str, Any]:
    enforce_rate_limit(request, "login")
    token, user = authenticate_demo_user(payload.email, payload.password)
    return {"access_token": token, "user": user_to_dict(user)}


@app.get("/health")
def health() -> dict[str, Any]:
    ensure_app_ready()
    status = database_status(DEFAULT_DB_PATH)
    return {
        "status": "ok",
        "database": status,
        "vision_available": image_analysis_available(),
        "principio": "Alertas de revision humana; no acusaciones ni decisiones automaticas.",
    }


@app.get("/claims/risk")
def claims_risk(
    response: Response,
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    level: str | None = Query(default=None, pattern="^(Verde|Amarillo|Rojo)$"),
    ramo: str | None = Query(default=None, max_length=40),
    ciudad: str | None = Query(default=None, max_length=80),
    min_score: int | None = Query(default=None, ge=0, le=100),
    user: DemoUser = Depends(require_roles("Analista", "Jefatura", "Auditoria")),
) -> list[dict[str, Any]]:
    ensure_app_ready()
    rows = list_risk_cases(
        limit=limit,
        offset=offset,
        level=level,
        ramo=ramo,
        ciudad=ciudad,
        min_score=min_score,
        db_path=DEFAULT_DB_PATH,
    )
    total = count_risk_cases(level=level, ramo=ramo, ciudad=ciudad, min_score=min_score, db_path=DEFAULT_DB_PATH)
    response.headers["X-Total-Count"] = str(total)
    return rows


@app.get("/claims/filter-options")
def claims_filter_options(
    user: DemoUser = Depends(require_roles("Analista", "Jefatura", "Auditoria")),
) -> dict[str, list[str]]:
    ensure_app_ready()
    return list_risk_case_options(db_path=DEFAULT_DB_PATH)


@app.get("/claims/{id_siniestro}")
def claim_detail(
    id_siniestro: str,
    background_tasks: BackgroundTasks,
    user: DemoUser = Depends(require_roles("Analista", "Jefatura", "Auditoria")),
) -> dict[str, Any]:
    ensure_app_ready()
    detail = get_claim_detail(id_siniestro.upper(), db_path=DEFAULT_DB_PATH)
    if "error" not in detail:
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
    request: Request,
    user: DemoUser = Depends(current_user),
) -> dict[str, Any]:
    ensure_app_ready()
    enforce_rate_limit(request, "agent")
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
    request: Request,
    file: UploadFile = File(...),
    user: DemoUser = Depends(require_roles("Analista", "Jefatura")),
) -> dict[str, Any]:
    ensure_app_ready()
    enforce_rate_limit(request, "upload")
    content = await file.read(MAX_CSV_UPLOAD_BYTES + 1)
    if len(content) > MAX_CSV_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"CSV supera el limite de {MAX_CSV_UPLOAD_BYTES} bytes.",
        )
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
            tmp.write(content)
            temp_path = Path(tmp.name)
        frame = pd.read_csv(temp_path)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"CSV invalido: {exc}") from exc
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass

    stem = Path(file.filename or "").stem
    required = REQUIRED_COLUMNS.get(stem, set())
    missing = sorted(missing_required_columns(stem, frame.columns)) if required else []
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


@app.post("/vision/analyze")
async def vision_analyze(
    background_tasks: BackgroundTasks,
    request: Request,
    file: UploadFile = File(...),
    id_siniestro: str | None = None,
    user: DemoUser = Depends(current_user),
) -> dict[str, Any]:
    ensure_app_ready()
    enforce_rate_limit(request, "vision")
    content = await file.read(MAX_IMAGE_BYTES + 1)
    if len(content) > MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Imagen supera el limite de {MAX_IMAGE_BYTES} bytes.",
        )
    claim_context: dict[str, Any] = {
        "filename": file.filename or "imagen_siniestro",
        "mime_type": file.content_type or "application/octet-stream",
    }
    if id_siniestro:
        detail = get_claim_detail(id_siniestro.upper(), db_path=DEFAULT_DB_PATH)
        if "error" not in detail:
            claim_context.update(
                {
                    "id_siniestro": detail.get("id_siniestro"),
                    "ramo": detail.get("ramo"),
                    "cobertura": detail.get("cobertura"),
                    "nivel_riesgo": detail.get("nivel_riesgo"),
                    "score_final": detail.get("score_final"),
                    "descripcion": detail.get("descripcion"),
                }
            )
    result = analyze_claim_image(content, file.content_type or "application/octet-stream", claim_context)
    queue_log_event(
        background_tasks,
        user.email,
        user.role,
        "vision.image_analyzed",
        "claim" if id_siniestro else "vision",
        id_siniestro.upper() if id_siniestro else file.filename or "upload",
        {"status": result.get("status"), "mime_type": file.content_type, "bytes": len(content)},
    )
    return result


@app.get("/alerts/aggregate")
def alerts_aggregate(
    group_by: str = Query(default="proveedor", pattern="^(proveedor|ramo|ciudad|documentos)$"),
    user: DemoUser = Depends(require_roles("Analista", "Jefatura", "Auditoria")),
) -> list[dict[str, Any]]:
    ensure_app_ready()
    return aggregate_alerts(group_by=group_by, db_path=DEFAULT_DB_PATH)


@app.get("/alerts/provider-pareto")
def alerts_provider_pareto(
    user: DemoUser = Depends(require_roles("Analista", "Jefatura", "Auditoria")),
) -> list[dict[str, Any]]:
    ensure_app_ready()
    return provider_red_alert_pareto(db_path=DEFAULT_DB_PATH)


@app.get("/relationships")
def relationships(
    limit: int = Query(default=60, ge=10, le=120),
    user: DemoUser = Depends(require_roles("Analista", "Jefatura", "Auditoria")),
) -> dict[str, list[dict[str, Any]]]:
    ensure_app_ready()
    return get_relationship_network(limit=limit, db_path=DEFAULT_DB_PATH)


@app.get("/report/summary")
def report_summary(
    user: DemoUser = Depends(require_roles("Analista", "Jefatura", "Auditoria")),
) -> dict[str, Any]:
    ensure_app_ready()
    return executive_report(db_path=DEFAULT_DB_PATH)


@app.post("/score-candidate")
def score_candidate(
    payload: CandidateScorePayload,
    request: Request,
    user: DemoUser = Depends(require_roles("Analista", "Jefatura", "Auditoria")),
) -> dict[str, Any]:
    enforce_rate_limit(request, "score-candidate")
    data = candidate_payload_data(payload)
    errors = validate_candidate_payload(data)
    if errors:
        raise HTTPException(status_code=422, detail=errors)
    return score_candidate_claim(data)


@app.get("/metrics")
def metrics(
    user: DemoUser = Depends(require_roles("Analista", "Jefatura", "Auditoria")),
) -> list[dict[str, Any]]:
    ensure_app_ready()
    return get_model_metrics(db_path=DEFAULT_DB_PATH)
