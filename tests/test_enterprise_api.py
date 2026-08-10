from __future__ import annotations

import sqlite3
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fastapi.testclient import TestClient

from fraudia_claims.api import app
from fraudia_claims.config import DEFAULT_DB_PATH, RATE_LIMIT_MAX_REQUESTS
from fraudia_claims.storage import initialize_demo_data
from fraudia_claims.vision import MAX_IMAGE_BYTES


class EnterpriseApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        initialize_demo_data(force=False)
        cls.client = TestClient(app)
        login = cls.client.post("/auth/login", json={"email": "analista@fraudia.demo", "password": "demo123"})
        cls.analyst_token = login.json()["access_token"]
        audit_login = cls.client.post("/auth/login", json={"email": "auditoria@fraudia.demo", "password": "demo123"})
        cls.audit_token = audit_login.json()["access_token"]

    def auth(self, token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}

    def test_login_demo_roles(self) -> None:
        response = self.client.post("/auth/login", json={"email": "jefatura@fraudia.demo", "password": "demo123"})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("access_token", body)
        self.assertEqual(body["user"]["role"], "Jefatura")

        bad = self.client.post("/auth/login", json={"email": "jefatura@fraudia.demo", "password": "bad"})
        self.assertEqual(bad.status_code, 401)

    def test_dashboard_kpis_requires_auth_and_matches_shape(self) -> None:
        self.assertEqual(self.client.get("/dashboard/kpis").status_code, 401)
        response = self.client.get("/dashboard/kpis", headers=self.auth(self.analyst_token))
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("kpis", body)
        self.assertIn("proveedores_criticos", body)
        self.assertGreater(body["kpis"]["total_siniestros"], 0)

    def test_sensitive_reads_require_auth(self) -> None:
        for path in (
            "/claims/risk?limit=1",
            "/relationships?limit=20",
            "/report/summary",
            "/alerts/aggregate",
            "/metrics",
        ):
            self.assertEqual(self.client.get(path).status_code, 401, path)

        authorized = self.client.get("/claims/risk?limit=1", headers=self.auth(self.analyst_token))
        self.assertEqual(authorized.status_code, 200)
        self.assertGreater(len(authorized.json()), 0)

    def test_review_decision_persists_without_modifying_scores_and_logs_event(self) -> None:
        claim_id = self.client.get("/claims/risk?limit=1", headers=self.auth(self.analyst_token)).json()[0]["id_siniestro"]
        with sqlite3.connect(DEFAULT_DB_PATH) as conn:
            before = conn.execute("SELECT COUNT(*) FROM scores").fetchone()[0]

        response = self.client.post(
            f"/claims/{claim_id}/review-decision",
            json={"status": "Escalado", "comentario": "Revision humana demo."},
            headers=self.auth(self.analyst_token),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "Escalado")

        history = self.client.get(f"/claims/{claim_id}/review-history", headers=self.auth(self.analyst_token))
        self.assertEqual(history.status_code, 200)
        self.assertTrue(any(row["status"] == "Escalado" for row in history.json()))

        audit = self.client.get(
            "/audit-log?action=review_decision.created",
            headers=self.auth(self.audit_token),
        )
        self.assertEqual(audit.status_code, 200)
        self.assertTrue(any(row["resource_id"] == claim_id for row in audit.json()))

        with sqlite3.connect(DEFAULT_DB_PATH) as conn:
            after = conn.execute("SELECT COUNT(*) FROM scores").fetchone()[0]
        self.assertEqual(before, after)

    def test_agent_question_and_csv_validation(self) -> None:
        claim_id = self.client.get("/claims/risk?limit=1", headers=self.auth(self.analyst_token)).json()[0]["id_siniestro"]
        agent = self.client.post(
            "/agent/question",
            json={"question": "Explica este caso", "id_siniestro": claim_id, "scope": "claim"},
            headers=self.auth(self.analyst_token),
        )
        self.assertEqual(agent.status_code, 200)
        self.assertIn("answer", agent.json())
        self.assertIn("disclaimer", agent.json())

        upload = self.client.post(
            "/claims/upload-csv",
            files={"file": ("siniestros.csv", b"id_siniestro,ramo\nSINX,Vehiculos\n", "text/csv")},
            headers=self.auth(self.analyst_token),
        )
        self.assertEqual(upload.status_code, 200)
        self.assertEqual(upload.json()["status"], "revisar")
        self.assertIn("id_poliza", upload.json()["missing_columns"])

        oversized = self.client.post(
            "/claims/upload-csv",
            files={"file": ("huge.csv", b"x" * (2 * 1024 * 1024 + 10), "text/csv")},
            headers=self.auth(self.analyst_token),
        )
        self.assertEqual(oversized.status_code, 413)

    def test_rbac_denies_roles_without_permission(self) -> None:
        claim_id = self.client.get("/claims/risk?limit=1", headers=self.auth(self.analyst_token)).json()[0]["id_siniestro"]

        # Auditoria no puede registrar decisiones humanas (solo Analista/Jefatura).
        forbidden_review = self.client.post(
            f"/claims/{claim_id}/review-decision",
            json={"status": "Escalado", "comentario": "No deberia poder."},
            headers=self.auth(self.audit_token),
        )
        self.assertEqual(forbidden_review.status_code, 403)

        # Analista no puede leer el log de auditoria (solo Jefatura/Auditoria).
        forbidden_audit = self.client.get("/audit-log", headers=self.auth(self.analyst_token))
        self.assertEqual(forbidden_audit.status_code, 403)

    def test_audit_log_pagination_and_total_count(self) -> None:
        # Genera actividad suficiente para paginar.
        for _ in range(3):
            self.client.get("/dashboard/kpis", headers=self.auth(self.analyst_token))

        # El propio GET /audit-log queda registrado como evento "audit_log.viewed"
        # (via BackgroundTasks), asi que consultarlo inserta una fila nueva cada
        # vez. Sin fijar un corte temporal, la fila que agrega la primera pagina
        # desplaza el offset de la segunda y produce solapamiento falso. Se fija
        # un snapshot ("date_to") para que ambas paginas lean el mismo universo.
        snapshot = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

        first_page = self.client.get(f"/audit-log?limit=2&offset=0&date_to={snapshot}", headers=self.auth(self.audit_token))
        self.assertEqual(first_page.status_code, 200)
        total = int(first_page.headers["X-Total-Count"])
        self.assertGreaterEqual(total, 3)
        self.assertEqual(len(first_page.json()), 2)

        second_page = self.client.get(f"/audit-log?limit=2&offset=2&date_to={snapshot}", headers=self.auth(self.audit_token))
        first_ids = {row["id_event"] for row in first_page.json()}
        second_ids = {row["id_event"] for row in second_page.json()}
        self.assertTrue(first_ids.isdisjoint(second_ids))

    def test_vision_analyze_rejects_oversized_upload(self) -> None:
        oversized_image = self.client.post(
            "/vision/analyze",
            files={"file": ("huge.jpg", b"x" * (MAX_IMAGE_BYTES + 10), "image/jpeg")},
            headers=self.auth(self.analyst_token),
        )
        self.assertEqual(oversized_image.status_code, 413)

    def test_rate_limit_blocks_excessive_requests(self) -> None:
        payload = {
            "ramo": "Vehiculos",
            "cobertura": "Perdida Total por Robo",
            "monto_reclamado": 29500,
            "suma_asegurada": 30000,
            "dias_desde_inicio_poliza": 1,
            "dias_desde_fin_poliza": 364,
            "dias_entre_ocurrencia_reporte": 5,
            "denuncia_horas": 72,
            "documentos_completos": False,
        }
        statuses = [
            self.client.post("/score-candidate", json=payload, headers=self.auth(self.analyst_token)).status_code
            for _ in range(RATE_LIMIT_MAX_REQUESTS + 15)
        ]
        self.assertIn(429, statuses)


if __name__ == "__main__":
    unittest.main()
