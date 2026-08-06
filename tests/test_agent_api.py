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
from fraudia_claims.utils import normalize_text


class AgentAndApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        initialize_demo_data(force=False)

    def test_agent_answers_pdf_questions(self) -> None:
        answer = answer_offline("Que proveedores concentran el 80% de las alertas rojas?")
        self.assertIn("alertas rojas", normalize_text(answer))
        self.assertIn("proveedores", normalize_text(answer))

        answer = answer_offline("Que asegurados tienen mayor frecuencia de reclamos?")
        self.assertIn("asegurados", normalize_text(answer))

        answer = answer_offline("Que metricas tiene el modelo supervisado?")
        self.assertTrue("precision" in normalize_text(answer) or "skipped" in normalize_text(answer) or "metricas" in normalize_text(answer))

    def test_api_health_metrics_and_candidate_score(self) -> None:
        client = TestClient(app)
        auth = {"Authorization": "Bearer demo-token-analista"}

        health = client.get("/health")
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json()["status"], "ok")

        self.assertEqual(client.get("/metrics").status_code, 401)
        metrics = client.get("/metrics", headers=auth)
        self.assertEqual(metrics.status_code, 200)
        self.assertTrue(any(row["metrica"] in {"f1", "status"} for row in metrics.json()))

        pareto = client.get("/alerts/provider-pareto", headers=auth)
        self.assertEqual(pareto.status_code, 200)
        self.assertIsInstance(pareto.json(), list)

        relationships = client.get("/relationships?limit=20", headers=auth)
        self.assertEqual(relationships.status_code, 200)
        self.assertIn("nodes", relationships.json())
        self.assertIn("edges", relationships.json())

        report = client.get("/report/summary", headers=auth)
        self.assertEqual(report.status_code, 200)
        self.assertIn("resumen", report.json())

        vision = client.post(
            "/vision/analyze",
            files={"file": ("demo.jpg", b"fake-image", "image/jpeg")},
            headers=auth,
        )
        self.assertEqual(vision.status_code, 200)
        self.assertIn("disclaimer", vision.json())

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
            headers=auth,
        )
        self.assertEqual(candidate.status_code, 200)
        self.assertEqual(candidate.json()["nivel_riesgo"], "Rojo")

        invalid_branch = client.post(
            "/score-candidate",
            json={
                "ramo": "Vehiculosdasdasdad",
                "cobertura": "Perdida Total por Robo",
                "monto_reclamado": 29500,
                "suma_asegurada": 30000,
                "dias_desde_inicio_poliza": 1,
                "dias_desde_fin_poliza": 364,
                "dias_entre_ocurrencia_reporte": 5,
                "denuncia_horas": 72,
                "documentos_completos": False,
            },
            headers=auth,
        )
        self.assertEqual(invalid_branch.status_code, 422)

        invalid_amount = client.post(
            "/score-candidate",
            json={
                "ramo": "Vehiculos",
                "cobertura": "Perdida Total por Robo",
                "monto_reclamado": 35000,
                "suma_asegurada": 30000,
                "dias_desde_inicio_poliza": 1,
                "dias_desde_fin_poliza": 364,
                "dias_entre_ocurrencia_reporte": 5,
                "denuncia_horas": 72,
                "documentos_completos": False,
            },
            headers=auth,
        )
        self.assertEqual(invalid_amount.status_code, 422)


if __name__ == "__main__":
    unittest.main()
