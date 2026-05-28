from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fraudia_claims.config import DEFAULT_DB_PATH
from fraudia_claims.database import execute_rows, execute_statement, execute_write


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def ensure_audit_table(db_path: Path = DEFAULT_DB_PATH) -> None:
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


def list_audit_events(
    actor_email: str | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 100,
    db_path: Path = DEFAULT_DB_PATH,
) -> list[dict[str, Any]]:
    ensure_audit_table(db_path)
    clauses = []
    params: dict[str, Any] = {"limit": int(limit)}
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
    where = "WHERE " + " AND ".join(clauses) if clauses else ""
    rows = execute_rows(
        f"""
        SELECT *
        FROM audit_log
        {where}
        ORDER BY created_at DESC
        LIMIT :limit
        """,
        params,
        db_path=db_path,
    )
    for row in rows:
        row["metadata"] = json.loads(row.pop("metadata_json") or "{}")
    return rows
