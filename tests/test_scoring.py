from __future__ import annotations

import sys
import unittest
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fraudia_claims.agent_tools import score_candidate_claim
from fraudia_claims.config import DEFAULT_DB_PATH
from fraudia_claims.scoring import level_from_score
from fraudia_claims.storage import initialize_demo_data


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

    def test_fire_test_policy_edge_escalates_to_yellow(self) -> None:
        result = score_candidate_claim(
            {
                "ramo": "Hogar",
                "cobertura": "Danio Agua",
                "monto_reclamado": 900,
                "suma_asegurada": 40000,
                "dias_desde_inicio_poliza": 1,
                "dias_desde_fin_poliza": 364,
                "dias_entre_ocurrencia_reporte": 1,
                "documentos_completos": True,
            }
        )
        self.assertEqual(result["nivel_riesgo"], "Amarillo")
        self.assertEqual(result["score_final"], 41)

    def test_atypical_theft_report_delay_escalates_to_yellow(self) -> None:
        result = score_candidate_claim(
            {
                "ramo": "Vehiculos",
                "cobertura": "Robo",
                "monto_reclamado": 1200,
                "suma_asegurada": 30000,
                "dias_desde_inicio_poliza": 100,
                "dias_desde_fin_poliza": 260,
                "dias_entre_ocurrencia_reporte": 1,
                "denuncia_horas": 120,
                "documentos_completos": True,
            }
        )
        self.assertEqual(result["nivel_riesgo"], "Amarillo")
        self.assertEqual(result["score_final"], 41)

    def test_cloned_narrative_escalates_to_yellow(self) -> None:
        result = score_candidate_claim(
            {
                "ramo": "Salud",
                "cobertura": "Consulta Especializada",
                "monto_reclamado": 400,
                "suma_asegurada": 10000,
                "dias_desde_inicio_poliza": 120,
                "dias_desde_fin_poliza": 220,
                "dias_entre_ocurrencia_reporte": 1,
                "documentos_completos": True,
                "narrativa_clonada": True,
            }
        )
        self.assertEqual(result["nivel_riesgo"], "Amarillo")
        self.assertEqual(result["score_final"], 41)

    def test_candidate_score_does_not_write_to_sqlite(self) -> None:
        initialize_demo_data(force=False)
        with sqlite3.connect(DEFAULT_DB_PATH) as conn:
            before = conn.execute("SELECT COUNT(*) FROM scores").fetchone()[0]
        score_candidate_claim(
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
        with sqlite3.connect(DEFAULT_DB_PATH) as conn:
            after = conn.execute("SELECT COUNT(*) FROM scores").fetchone()[0]
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
