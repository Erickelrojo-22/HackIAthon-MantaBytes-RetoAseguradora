from __future__ import annotations

from pathlib import Path

from fraudia_claims.agent_responses import build_agent_answer
from fraudia_claims.config import DEFAULT_DB_PATH


def answer_offline(
    question: str,
    db_path: Path = DEFAULT_DB_PATH,
    session_cases: list[dict] | None = None,
) -> str:
    return build_agent_answer(question, db_path=db_path, session_cases=session_cases)
