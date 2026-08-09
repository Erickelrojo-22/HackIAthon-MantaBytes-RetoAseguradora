from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fraudia_claims.database import clear_query_cache, database_settings, execute_rows_cached, read_sql, table_names, write_frame
from fraudia_claims.storage import database_status


class DatabaseLayerTests(unittest.TestCase):
    def test_default_backend_is_sqlite(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            settings = database_settings(Path("tmp/demo.db"))
        self.assertEqual(settings.backend, "sqlite")
        self.assertEqual(settings.sqlite_path, Path("tmp/demo.db"))

    def test_postgres_requires_url(self) -> None:
        with patch.dict("os.environ", {"FRAUDIA_DB_BACKEND": "postgres"}, clear=True):
            with self.assertRaises(ValueError):
                database_settings()

    def test_postgres_url_is_accepted(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "FRAUDIA_DB_BACKEND": "postgres",
                "FRAUDIA_DATABASE_URL": "postgresql+psycopg://user:pass@localhost:5432/fraudia",
            },
            clear=True,
        ):
            settings = database_settings()
        self.assertEqual(settings.backend, "postgres")
        self.assertEqual(settings.url, "postgresql+psycopg://user:pass@localhost:5432/fraudia")

    def test_bare_postgres_url_is_upgraded_to_psycopg_dialect(self) -> None:
        # Supabase and Heroku-style providers hand out postgres:// / postgresql://
        # with no driver suffix. SQLAlchemy would default that to psycopg2, which
        # isn't installed here (we ship psycopg v3), so it must be rewritten.
        cases = {
            "postgres://user:pass@localhost:5432/fraudia": "postgresql+psycopg://user:pass@localhost:5432/fraudia",
            "postgresql://user:pass@localhost:5432/fraudia": "postgresql+psycopg://user:pass@localhost:5432/fraudia",
        }
        for raw, expected in cases.items():
            with patch.dict(
                "os.environ",
                {"FRAUDIA_DB_BACKEND": "postgres", "FRAUDIA_DATABASE_URL": raw},
                clear=True,
            ):
                settings = database_settings()
            self.assertEqual(settings.url, expected)

    def test_sqlite_roundtrip_uses_abstraction(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "roundtrip.db"
            with patch.dict("os.environ", {"FRAUDIA_DB_BACKEND": "sqlite"}, clear=True):
                write_frame("demo", pd.DataFrame([{"id": 1, "nombre": "ok"}]), db_path=db_path)
                result = read_sql("SELECT * FROM demo WHERE id = :id", {"id": 1}, db_path=db_path)
                status = database_status(db_path)
                names = table_names(db_path)
        self.assertEqual(result.iloc[0]["nombre"], "ok")
        self.assertIn("demo", names)
        self.assertEqual(status["backend"], "sqlite")

    def test_cached_rows_reuse_read_query_results(self) -> None:
        clear_query_cache()
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "cache.db"
            with patch.dict("os.environ", {"FRAUDIA_DB_BACKEND": "sqlite"}, clear=True):
                with patch("fraudia_claims.database.execute_rows", return_value=[{"id": 1}]) as mocked:
                    first = execute_rows_cached("SELECT 1 AS id", db_path=db_path)
                    first[0]["id"] = 99
                    second = execute_rows_cached("SELECT 1 AS id", db_path=db_path)

        self.assertEqual(mocked.call_count, 1)
        self.assertEqual(second, [{"id": 1}])
        clear_query_cache()


if __name__ == "__main__":
    unittest.main()
