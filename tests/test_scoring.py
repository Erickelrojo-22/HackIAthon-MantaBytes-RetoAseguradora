from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fraudia_claims.agent_tools import score_candidate_claim
from fraudia_claims.scoring import level_from_score


class ScoringTests(unittest.TestCase):
    def test_score_boundaries(self) -> None:
        self.assertEqual(level_from_score(40), "Verde")
        self.assertEqual(level_from_score(41), "Amarillo")
        self.assertEqual(level_from_score(75), "Amarillo")
        self.assertEqual(level_from_score(76), "Rojo")

    def test_critical_vehicle_claim_escalates_to_red(self) -> None:
        result = score_candidate_claim(
            {
                "ramo": "Vehiculos",
                "cobertura": "Perdida Total por Robo",
                "monto_reclamado": 29500,
                "suma_asegurada": 30000,
                "dias_desde_inicio_poliza": 1,
                "dias_desde_fin_poliza": 364,
                "dias_entre_ocurrencia_reporte": 5,
                "denuncia_horas": 72,
                "documentos_completos": False,
                "documentos_inconsistentes": True,
                "tercero_identificado": False,
            }
        )
        self.assertEqual(result["nivel_riesgo"], "Rojo")
        self.assertGreaterEqual(result["score_final"], 76)
        self.assertTrue(any(alert["es_critica"] for alert in result["alertas"]))

    def test_non_critical_low_case_stays_green(self) -> None:
        result = score_candidate_claim(
            {
                "ramo": "Hogar",
                "cobertura": "Danio Agua",
                "monto_reclamado": 900,
                "suma_asegurada": 40000,
                "dias_desde_inicio_poliza": 120,
                "dias_desde_fin_poliza": 200,
                "dias_entre_ocurrencia_reporte": 1,
                "documentos_completos": True,
            }
        )
        self.assertEqual(result["nivel_riesgo"], "Verde")
        self.assertEqual(result["score_final"], 0)


if __name__ == "__main__":
    unittest.main()
