from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fraudia_claims.app.pages import summary_risk_frames
from fraudia_claims.storage import initialize_demo_data, load_table


class DashboardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.db_path = initialize_demo_data(force=False)

    def test_summary_frames_keep_score_amount_column(self) -> None:
        scores = load_table("scores", self.db_path)
        claims = load_table("siniestros", self.db_path)
        by_level, by_ramo = summary_risk_frames(scores, claims)

        self.assertEqual(int(by_level["total"].sum()), len(scores))
        self.assertIn("monto", by_ramo.columns)
        self.assertFalse(any(column.endswith("_x") or column.endswith("_y") for column in by_ramo.columns))
        self.assertGreater(float(by_ramo["monto"].sum()), 0)


if __name__ == "__main__":
    unittest.main()
