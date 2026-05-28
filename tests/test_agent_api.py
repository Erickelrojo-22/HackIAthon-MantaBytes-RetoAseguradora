from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fastapi.testclient import TestClient

from fraudia_claims.api import app
from fraudia_claims.offline_agent import answer_offline
from fraudia_claims.storage import initialize_demo_data


class AgentAndApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        initialize_demo_data(force=False)

    def test_agent_answers_pdf_questions(self) -> None:
        answer = answer_offline("Que proveedores concentran el 80% de las alertas rojas?")
        self.assertIn("80%", answer)
        self.assertIn("alertas_rojas", answer)

        answer = answer_offline("Que asegurados tienen mayor frecuencia de reclamos?")
        self.assertIn("id_asegurado", answer)

        answer = answer_offline("Que metricas tiene el modelo supervisado?")
        self.assertIn("precision", answer)

    def test_api_health_metrics_and_candidate_score(self) -> None:
        client = TestClient(app)
        health = client.get("/health")
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json()["status"], "ok")

        metrics = client.get("/metrics")
        self.assertEqual(metrics.status_code, 200)
        self.assertTrue(any(row["metrica"] == "f1" for row in metrics.json()))

        pareto = client.get("/alerts/provider-pareto")
        self.assertEqual(pareto.status_code, 200)
        self.assertIsInstance(pareto.json(), list)

        relationships = client.get("/relationships?limit=20")
        self.assertEqual(relationships.status_code, 200)
        self.assertIn("nodes", relationships.json())
        self.assertIn("edges", relationships.json())

        report = client.get("/report/summary")
        self.assertEqual(report.status_code, 200)
        self.assertIn("resumen", report.json())

        candidate = client.post(
            "/score-candidate",
            json={
                "ramo": "Vehiculos",
                "cobertura": "Perdida Total por Robo",
                "monto_reclamado": 29500,
                "suma_asegurada": 30000,
                "dias_desde_inicio_poliza": 1,
                "dias_desde_fin_poliza": 364,
                "dias_entre_ocurrencia_reporte": 5,
                "denuncia_horas": 72,
                "documentos_completos": False,
            },
        )
        self.assertEqual(candidate.status_code, 200)
        self.assertEqual(candidate.json()["nivel_riesgo"], "Rojo")


if __name__ == "__main__":
    unittest.main()
