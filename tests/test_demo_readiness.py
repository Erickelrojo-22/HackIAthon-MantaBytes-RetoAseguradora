from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fraudia_claims.agent_tools import score_candidate_claim
from fraudia_claims.demo import featured_claims
from fraudia_claims.storage import initialize_demo_data


class DemoReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        initialize_demo_data(force=False)

    def test_featured_claims_include_green_yellow_red_and_fire_test(self) -> None:
        cases = featured_claims()
        self.assertEqual(cases["caso_rojo"]["nivel_riesgo"], "Rojo")
        self.assertEqual(cases["caso_amarillo"]["nivel_riesgo"], "Amarillo")
        self.assertEqual(cases["caso_verde"]["nivel_riesgo"], "Verde")

        fire_test = score_candidate_claim(cases["prueba_fuego"])
        self.assertEqual(fire_test["nivel_riesgo"], "Rojo")
        self.assertTrue(any(alert["codigo"] == "RF-01" for alert in fire_test["alertas"]))


if __name__ == "__main__":
    unittest.main()
