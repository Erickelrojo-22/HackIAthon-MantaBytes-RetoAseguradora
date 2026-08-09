from __future__ import annotations

import os
import sqlite3
from copy import deepcopy
from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
from threading import Lock
from typing import Any

import pandas as pd

from fraudia_claims.config import DEFAULT_DB_PATH

try:
    from sqlalchemy import create_engine, inspect, text
    from sqlalchemy.engine import Engine
    from sqlalchemy.pool import NullPool
except Exception:  # pragma: no cover - exercised when optional dependency is missing.
    create_engine = None
    inspect = None
    text = None
    NullPool = None
    Engine = Any  # type: ignore


SUPPORTED_BACKENDS = {"sqlite", "postgres"}
_ENGINE_CACHE: dict[tuple[str, str], Engine] = {}
_ENGINE_LOCK = Lock()


@dataclass(frozen=True)
class DatabaseSettings:
    backend: str
    url: str | None
    sqlite_path: Path


def _normalize_postgres_url(url: str) -> str:
    """Upgrade a bare postgres(ql):// URL to the psycopg (v3) dialect.

    Supabase, Heroku-style providers, etc. hand out connection strings with no
    driver suffix (postgres:// or postgresql://). SQLAlchemy's default DBAPI for
    that scheme is psycopg2, which this project does not install (requirements.txt
    ships psycopg[binary], i.e. psycopg v3) - so pasting a URL as-is crashes the
    app at startup with "ModuleNotFoundError: No module named 'psycopg2'". Rewrite
    it so FRAUDIA_DATABASE_URL works whether or not the driver suffix is included.
    """
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix) :]
    return url


def database_settings(db_path: Path = DEFAULT_DB_PATH) -> DatabaseSettings:
    backend = os.getenv("FRAUDIA_DB_BACKEND", "sqlite").strip().lower() or "sqlite"
    if backend == "postgresql":
        backend = "postgres"
    if backend not in SUPPORTED_BACKENDS:
        raise ValueError(f"FRAUDIA_DB_BACKEND debe ser sqlite o postgres, no {backend!r}.")
    url = os.getenv("FRAUDIA_DATABASE_URL", "").strip() or None
    if url:
        url = _normalize_postgres_url(url)
    sqlite_path = Path(os.getenv("FRAUDIA_DB_PATH", str(db_path)))
    if backend == "postgres" and not url:
        raise ValueError("FRAUDIA_DATABASE_URL es requerido cuando FRAUDIA_DB_BACKEND=postgres.")
    return DatabaseSettings(backend=backend, url=url, sqlite_path=sqlite_path)


def active_backend(db_path: Path = DEFAULT_DB_PATH) -> str:
    return database_settings(db_path).backend


def database_label(db_path: Path = DEFAULT_DB_PATH) -> str:
    settings = database_settings(db_path)
    if settings.backend == "postgres":
        return "postgres"
    return f"sqlite:{settings.sqlite_path}"


def _cache_key(db_path: Path = DEFAULT_DB_PATH) -> tuple[str, str, str, str, str]:
    settings = database_settings(db_path)
    url_hash = sha256(settings.url.encode("utf-8")).hexdigest() if settings.url else ""
    return (
        settings.backend,
        url_hash,
        str(settings.sqlite_path.resolve()),
        os.getenv("FRAUDIA_DATA_SOURCE", "demo"),
        os.getenv("FRAUDIA_COMPANY_DATA_DIR", ""),
    )


def _params_key(params: dict[str, Any] | None = None) -> tuple[tuple[str, Any], ...]:
    return tuple(sorted((params or {}).items()))


def clear_query_cache() -> None:
    _read_sql_cached.cache_clear()
    _execute_rows_cached.cache_clear()


def _sqlite_connection(db_path: Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    settings = database_settings(db_path)
    settings.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.sqlite_path)
    conn.row_factory = sqlite3.Row
    return conn


def get_engine(db_path: Path = DEFAULT_DB_PATH) -> Engine:
    if create_engine is None:
        raise RuntimeError("SQLAlchemy no esta instalado. Ejecuta pip install -r requirements.txt.")
    settings = database_settings(db_path)
    if settings.backend == "postgres":
        assert settings.url is not None
        key = (settings.backend, settings.url)
        with _ENGINE_LOCK:
            engine = _ENGINE_CACHE.get(key)
            if engine is None:
                engine = create_engine(settings.url, pool_pre_ping=True)
                _ENGINE_CACHE[key] = engine
            return engine
    settings.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{settings.sqlite_path.as_posix()}", poolclass=NullPool)


def read_sql(query: str, params: dict[str, Any] | None = None, db_path: Path = DEFAULT_DB_PATH) -> pd.DataFrame:
    settings = database_settings(db_path)
    params = params or {}
    if settings.backend == "sqlite":
        conn = _sqlite_connection(db_path)
        try:
            return pd.read_sql_query(query, conn, params=params)
        finally:
            conn.close()
    engine = get_engine(db_path)
    assert text is not None
    with engine.connect() as conn:
        return pd.read_sql_query(text(query), conn, params=params)


@lru_cache(maxsize=128)
def _read_sql_cached(
    query: str,
    params: tuple[tuple[str, Any], ...],
    db_path_value: str,
    cache_key: tuple[str, str, str, str, str],
) -> pd.DataFrame:
    del cache_key
    return read_sql(query, params=dict(params), db_path=Path(db_path_value))


def read_sql_cached(query: str, params: dict[str, Any] | None = None, db_path: Path = DEFAULT_DB_PATH) -> pd.DataFrame:
    return _read_sql_cached(query, _params_key(params), str(db_path), _cache_key(db_path)).copy(deep=True)


def execute_rows(query: str, params: dict[str, Any] | None = None, db_path: Path = DEFAULT_DB_PATH) -> list[dict[str, Any]]:
    settings = database_settings(db_path)
    params = params or {}
    if settings.backend == "sqlite":
        conn = _sqlite_connection(db_path)
        try:
            return [dict(row) for row in conn.execute(query, params).fetchall()]
        finally:
            conn.close()
    engine = get_engine(db_path)
    assert text is not None
    with engine.connect() as conn:
        return [dict(row) for row in conn.execute(text(query), params).mappings().all()]


@lru_cache(maxsize=256)
def _execute_rows_cached(
    query: str,
    params: tuple[tuple[str, Any], ...],
    db_path_value: str,
    cache_key: tuple[str, str, str, str, str],
) -> list[dict[str, Any]]:
    del cache_key
    return execute_rows(query, params=dict(params), db_path=Path(db_path_value))


def execute_rows_cached(query: str, params: dict[str, Any] | None = None, db_path: Path = DEFAULT_DB_PATH) -> list[dict[str, Any]]:
    return deepcopy(_execute_rows_cached(query, _params_key(params), str(db_path), _cache_key(db_path)))


def execute_one(query: str, params: dict[str, Any] | None = None, db_path: Path = DEFAULT_DB_PATH) -> dict[str, Any] | None:
    rows = execute_rows(query, params=params, db_path=db_path)
    return rows[0] if rows else None


def execute_one_cached(query: str, params: dict[str, Any] | None = None, db_path: Path = DEFAULT_DB_PATH) -> dict[str, Any] | None:
    rows = execute_rows_cached(query, params=params, db_path=db_path)
    return rows[0] if rows else None


def table_names(db_path: Path = DEFAULT_DB_PATH) -> set[str]:
    settings = database_settings(db_path)
    if settings.backend == "sqlite":
        conn = _sqlite_connection(db_path)
        try:
            return {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        finally:
            conn.close()
    engine = get_engine(db_path)
    assert inspect is not None
    return set(inspect(engine).get_table_names())


def table_columns(table_name: str, db_path: Path = DEFAULT_DB_PATH) -> set[str]:
    settings = database_settings(db_path)
    if settings.backend == "sqlite":
        conn = _sqlite_connection(db_path)
        try:
            return {row[1] for row in conn.execute(f"PRAGMA table_info({table_name})")}
        finally:
            conn.close()
    engine = get_engine(db_path)
    assert inspect is not None
    return {column["name"] for column in inspect(engine).get_columns(table_name)}


def write_frame(name: str, frame: pd.DataFrame, if_exists: str = "replace", db_path: Path = DEFAULT_DB_PATH) -> None:
    settings = database_settings(db_path)
    if settings.backend == "sqlite":
        conn = _sqlite_connection(db_path)
        try:
            frame.to_sql(name, conn, index=False, if_exists=if_exists)
        finally:
            conn.close()
        return
    engine = get_engine(db_path)
    frame.to_sql(name, engine, index=False, if_exists=if_exists)


def execute_statement(statement: str, db_path: Path = DEFAULT_DB_PATH) -> None:
    settings = database_settings(db_path)
    if settings.backend == "sqlite":
        conn = _sqlite_connection(db_path)
        try:
            conn.execute(statement)
            conn.commit()
        finally:
            conn.close()
        return
    engine = get_engine(db_path)
    assert text is not None
    with engine.begin() as conn:
        conn.execute(text(statement))


def execute_write(
    statement: str,
    params: dict[str, Any] | None = None,
    db_path: Path = DEFAULT_DB_PATH,
) -> None:
    settings = database_settings(db_path)
    params = params or {}
    if settings.backend == "sqlite":
        conn = _sqlite_connection(db_path)
        try:
            conn.execute(statement, params)
            conn.commit()
        finally:
            conn.close()
        return
    engine = get_engine(db_path)
    assert text is not None
    with engine.begin() as conn:
        conn.execute(text(statement), params)
