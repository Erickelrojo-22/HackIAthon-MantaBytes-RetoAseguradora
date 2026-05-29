from __future__ import annotations

import uuid
from pathlib import Path
from threading import Lock
from typing import Any

from fraudia_claims.audit import log_event, utc_now
from fraudia_claims.config import DEFAULT_DB_PATH
from fraudia_claims.database import clear_query_cache, database_label, execute_rows_cached, execute_statement, execute_write


REVIEW_STATUSES = ("En revision", "Descartado", "Escalado", "Confirmado para investigacion")
_REVIEW_TABLES_READY: set[str] = set()
_REVIEW_LOCK = Lock()


def ensure_review_tables(db_path: Path = DEFAULT_DB_PATH) -> None:
    key = database_label(db_path)
    if key in _REVIEW_TABLES_READY:
        return
    with _REVIEW_LOCK:
        if key in _REVIEW_TABLES_READY:
            return
        execute_statement(
            """
            CREATE TABLE IF NOT EXISTS review_decisions (
                id_decision TEXT PRIMARY KEY,
                id_siniestro TEXT NOT NULL,
                status TEXT NOT NULL,
                comentario TEXT NOT NULL,
                reviewer_email TEXT NOT NULL,
                reviewer_role TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """,
            db_path=db_path,
        )
        execute_statement("CREATE INDEX IF NOT EXISTS idx_review_claim ON review_decisions(id_siniestro)", db_path=db_path)
        execute_statement("CREATE INDEX IF NOT EXISTS idx_review_created ON review_decisions(created_at)", db_path=db_path)
        _REVIEW_TABLES_READY.add(key)


def create_review_decision(
    id_siniestro: str,
    status: str,
    comentario: str,
    reviewer_email: str,
    reviewer_role: str,
    db_path: Path = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    if status not in REVIEW_STATUSES:
        raise ValueError(f"Estado de revision no soportado: {status}")
    ensure_review_tables(db_path)
    row = {
        "id_decision": f"REV-{uuid.uuid4().hex[:12].upper()}",
        "id_siniestro": id_siniestro.upper(),
        "status": status,
        "comentario": comentario.strip(),
        "reviewer_email": reviewer_email,
        "reviewer_role": reviewer_role,
        "created_at": utc_now(),
    }
    execute_write(
        """
        INSERT INTO review_decisions (
            id_decision, id_siniestro, status, comentario, reviewer_email, reviewer_role, created_at
        ) VALUES (
            :id_decision, :id_siniestro, :status, :comentario, :reviewer_email, :reviewer_role, :created_at
        )
        """,
        row,
        db_path=db_path,
    )
    clear_query_cache()
    log_event(
        reviewer_email,
        reviewer_role,
        "review_decision.created",
        "claim",
        row["id_siniestro"],
        {"id_decision": row["id_decision"], "status": status},
        db_path=db_path,
    )
    return row


def list_review_history(id_siniestro: str, db_path: Path = DEFAULT_DB_PATH) -> list[dict[str, Any]]:
    ensure_review_tables(db_path)
    return execute_rows_cached(
        """
        SELECT *
        FROM review_decisions
        WHERE id_siniestro = :id_siniestro
        ORDER BY created_at DESC
        """,
        {"id_siniestro": id_siniestro.upper()},
        db_path=db_path,
    )
