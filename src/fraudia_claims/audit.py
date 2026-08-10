from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

from fraudia_claims.config import DEFAULT_DB_PATH
from fraudia_claims.database import database_label, execute_one, execute_rows, execute_statement, execute_write


_AUDIT_TABLES_READY: set[str] = set()
_AUDIT_LOCK = Lock()


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def ensure_audit_table(db_path: Path = DEFAULT_DB_PATH) -> None:
    key = database_label(db_path)
    if key in _AUDIT_TABLES_READY:
        return
    with _AUDIT_LOCK:
        if key in _AUDIT_TABLES_READY:
            return
        execute_statement(
            """
            CREATE TABLE IF NOT EXISTS audit_log (
                id_event TEXT PRIMARY KEY,
                actor_email TEXT NOT NULL,
                actor_role TEXT NOT NULL,
                action TEXT NOT NULL,
                resource_type TEXT NOT NULL,
                resource_id TEXT NOT NULL,
                metadata_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """,
            db_path=db_path,
        )
        execute_statement("CREATE INDEX IF NOT EXISTS idx_audit_actor ON audit_log(actor_email)", db_path=db_path)
        execute_statement("CREATE INDEX IF NOT EXISTS idx_audit_resource ON audit_log(resource_type, resource_id)", db_path=db_path)
        execute_statement("CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_log(created_at)", db_path=db_path)
        _AUDIT_TABLES_READY.add(key)


def log_event(
    actor_email: str,
    actor_role: str,
    action: str,
    resource_type: str,
    resource_id: str,
    metadata: dict[str, Any] | None = None,
    db_path: Path = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    ensure_audit_table(db_path)
    row = {
        "id_event": f"EVT-{uuid.uuid4().hex[:12].upper()}",
        "actor_email": actor_email,
        "actor_role": actor_role,
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "metadata_json": json.dumps(metadata or {}, ensure_ascii=False),
        "created_at": utc_now(),
    }
    execute_write(
        """
        INSERT INTO audit_log (
            id_event, actor_email, actor_role, action, resource_type, resource_id, metadata_json, created_at
        ) VALUES (
            :id_event, :actor_email, :actor_role, :action, :resource_type, :resource_id, :metadata_json, :created_at
        )
        """,
        row,
        db_path=db_path,
    )
    return row


def _audit_filters(
    actor_email: str | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> tuple[list[str], dict[str, Any]]:
    clauses: list[str] = []
    params: dict[str, Any] = {}
    filters = {
        "actor_email": actor_email,
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
    }
    for column, value in filters.items():
        if value:
            clauses.append(f"{column} = :{column}")
            params[column] = value
    if date_from:
        clauses.append("created_at >= :date_from")
        params["date_from"] = date_from
    if date_to:
        clauses.append("created_at <= :date_to")
        params["date_to"] = date_to
    return clauses, params


def list_audit_events(
    actor_email: str | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db_path: Path = DEFAULT_DB_PATH,
) -> list[dict[str, Any]]:
    ensure_audit_table(db_path)
    clauses, params = _audit_filters(actor_email, action, resource_type, resource_id, date_from, date_to)
    params["limit"] = int(limit)
    params["offset"] = int(offset)
    where = "WHERE " + " AND ".join(clauses) if clauses else ""
    rows = execute_rows(
        f"""
        SELECT *
        FROM audit_log
        {where}
        ORDER BY created_at DESC, id_event DESC
        LIMIT :limit OFFSET :offset
        """,
        params,
        db_path=db_path,
    )
    for row in rows:
        row["metadata"] = json.loads(row.pop("metadata_json") or "{}")
    return rows


def count_audit_events(
    actor_email: str | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    db_path: Path = DEFAULT_DB_PATH,
) -> int:
    ensure_audit_table(db_path)
    clauses, params = _audit_filters(actor_email, action, resource_type, resource_id, date_from, date_to)
    where = "WHERE " + " AND ".join(clauses) if clauses else ""
    row = execute_one(f"SELECT COUNT(*) AS total FROM audit_log {where}", params, db_path=db_path)
    return int(row["total"]) if row else 0
