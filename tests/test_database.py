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

from fraudia_claims.database import database_settings, read_sql, table_names, write_frame
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


if __name__ == "__main__":
    unittest.main()
