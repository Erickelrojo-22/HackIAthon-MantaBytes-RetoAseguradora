from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fraudia_claims.agent_tools import score_candidate_claim


class BusinessRuleTests(unittest.TestCase):
    def _codes(self, result: dict) -> set[str]:
        return {alert["codigo"] for alert in result["alertas"]}

    def test_pdf_critical_rules_escalate_to_red(self) -> None:
        scenarios = [
            {"ramo": "Vehiculos", "cobertura": "Perdida Total por Robo"},
            {"adulteracion_documental": True},
            {"proveedor_lista_restrictiva": True},
            {"ramo": "Vehiculos", "dinamica_imposible": True},
        ]
        for extra in scenarios:
            payload = {
                "ramo": "Vehiculos",
                "cobertura": "Choque",
                "monto_reclamado": 1000,
                "suma_asegurada": 30000,
                "dias_desde_inicio_poliza": 120,
                "dias_desde_fin_poliza": 200,
                "dias_entre_ocurrencia_reporte": 1,
                "documentos_completos": True,
                **extra,
            }
            result = score_candidate_claim(payload)
            self.assertEqual(result["nivel_riesgo"], "Rojo")
            self.assertGreaterEqual(result["score_final"], 76)
            self.assertTrue(any(alert["es_critica"] for alert in result["alertas"]))

    def test_pdf_common_signals_are_traceable(self) -> None:
        result = score_candidate_claim(
            {
                "ramo": "Vehiculos",
                "cobertura": "Robo",
                "monto_reclamado": 28500,
                "suma_asegurada": 30000,
                "dias_desde_inicio_poliza": 8,
                "dias_desde_fin_poliza": 357,
                "dias_entre_ocurrencia_reporte": 9,
                "denuncia_horas": 72,
                "documentos_completos": False,
                "documentos_inconsistentes": True,
                "tercero_identificado": False,
            }
        )
        self.assertTrue({"RF-05", "RF-06", "RF-10", "RF-11", "RF-12", "RF-14", "RF-20"}.issubset(self._codes(result)))
        self.assertGreaterEqual(result["score_reglas"], 40)


if __name__ == "__main__":
    unittest.main()
