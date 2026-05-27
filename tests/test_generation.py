from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fraudia_claims.scoring import score_claims
from fraudia_claims.synthetic_data import SyntheticConfig, generate_all


class GenerationTests(unittest.TestCase):
    def test_small_dataset_has_three_ramos_and_scores(self) -> None:
        tables = generate_all(SyntheticConfig(n_per_ramo=30, seed=2026))
        self.assertEqual(len(tables["siniestros"]), 90)
        self.assertEqual(set(tables["siniestros"]["ramo"]), {"Vehiculos", "Salud", "Hogar"})
        scores, alerts = score_claims(tables)
        self.assertEqual(len(scores), 90)
        self.assertFalse(alerts.empty)
        self.assertTrue(set(scores["nivel_riesgo"]).issubset({"Verde", "Amarillo", "Rojo"}))


if __name__ == "__main__":
    unittest.main()
