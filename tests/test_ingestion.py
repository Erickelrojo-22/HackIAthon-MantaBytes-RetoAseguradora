from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fraudia_claims.ingestion import COMPANY_TABLES, load_validated_company_tables, validate_company_tables
from fraudia_claims.storage import load_tables_from_csv
from fraudia_claims.synthetic_data import SyntheticConfig, generate_all


class IngestionTests(unittest.TestCase):
    def test_generated_demo_shape_passes_company_validator(self) -> None:
        tables = generate_all(SyntheticConfig(n_per_ramo=5, seed=2026))
        issues = validate_company_tables(tables)
        self.assertFalse([issue for issue in issues if issue.severity == "error"])

    def test_missing_column_is_reported(self) -> None:
        tables = generate_all(SyntheticConfig(n_per_ramo=5, seed=2026))
        tables["siniestros"] = tables["siniestros"].drop(columns=["id_conductor"])
        issues = validate_company_tables(tables)
        self.assertTrue(any(issue.table == "siniestros" and "id_conductor" in issue.message for issue in issues))

    def test_load_validated_company_tables_reads_csv_package(self) -> None:
        tables = generate_all(SyntheticConfig(n_per_ramo=3, seed=2026))
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            for table in COMPANY_TABLES:
                tables[table].to_csv(directory / f"{table}.csv", index=False)
            loaded = load_validated_company_tables(directory)
        self.assertEqual(set(COMPANY_TABLES).issubset(loaded), True)
        self.assertIn("contexto_publico", loaded)
        self.assertEqual(len(loaded["siniestros"]), 9)

    def test_load_tables_from_csv_reads_offline_dataset(self) -> None:
        tables = load_tables_from_csv(ROOT / "data" / "synthetic")
        self.assertEqual(set(COMPANY_TABLES).issubset(tables), True)
        self.assertGreater(len(tables["siniestros"]), 0)
        self.assertGreater(len(tables["polizas"]), 0)


if __name__ == "__main__":
    unittest.main()
