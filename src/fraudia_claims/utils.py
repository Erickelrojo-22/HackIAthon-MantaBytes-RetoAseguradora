from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime
from typing import Any


def normalize_text(value: Any) -> str:
    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-zA-Z0-9\s]", " ", text.lower())
    return re.sub(r"\s+", " ", text).strip()


def money(value: float | int | None) -> str:
    if value is None:
        return "$0.00"
    return f"${float(value):,.2f}"


def parse_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return datetime.fromisoformat(str(value)[:10]).date()


def bool_to_si_no(value: bool) -> str:
    return "Si" if bool(value) else "No"
