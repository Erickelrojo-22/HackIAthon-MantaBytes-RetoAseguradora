from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fraudia_claims.analytics import executive_kpis, provider_pareto, top_cases
from fraudia_claims.storage import initialize_demo_data


class AnalyticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        initialize_demo_data(force=False)

    def test_executive_kpis_are_consistent(self) -> None:
        kpis = executive_kpis()
        self.assertIn(kpis["total_siniestros"], {500, 3000})
        self.assertGreater(kpis["casos_priorizados"], 0)
        self.assertGreaterEqual(kpis["monto_expuesto"], kpis["monto_priorizado"])

    def test_top_cases_and_provider_pareto_return_rows(self) -> None:
        self.assertEqual(len(top_cases(5)), 5)
        self.assertFalse(provider_pareto(5).empty)


if __name__ == "__main__":
    unittest.main()
