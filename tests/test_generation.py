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

    def test_supervised_metrics_are_generated(self) -> None:
        tables = generate_all(SyntheticConfig(n_per_ramo=60, seed=2026))
        scores, alerts, metrics = score_claims(tables, include_metrics=True)
        self.assertIn("probabilidad_modelo", scores.columns)
        self.assertIn("score_modelo", scores.columns)
        self.assertFalse(alerts.empty)
        self.assertIn("f1", set(metrics["metrica"]))
        self.assertIn("auc_roc", set(metrics["metrica"]))


if __name__ == "__main__":
    unittest.main()
