from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fraudia_claims.reports import DISCLAIMER, build_executive_report_html
from fraudia_claims.storage import initialize_demo_data


class ReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        initialize_demo_data(force=False)

    def test_report_contains_core_sections_and_disclaimer(self) -> None:
        html = build_executive_report_html(
            [
                {
                    "id_temporal": "TMP001",
                    "ramo": "Vehiculos",
                    "cobertura": "Robo",
                    "score_final": 41,
                    "nivel_riesgo": "Amarillo",
                    "monto_reclamado": 1200,
                    "alertas": [],
                }
            ]
        )
        self.assertIn("Reporte Ejecutivo FraudIA Claims", html)
        self.assertIn("Top 10 casos para revision", html)
        self.assertIn("Proveedores con mayor concentracion", html)
        self.assertIn("Casos evaluados en vivo", html)
        self.assertIn("TMP001", html)
        self.assertIn(DISCLAIMER, html)


if __name__ == "__main__":
    unittest.main()
