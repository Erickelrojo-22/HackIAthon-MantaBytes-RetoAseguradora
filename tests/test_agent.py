from __future__ import annotations

import os
import sys
import unittest
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fraudia_claims.offline_agent import answer_offline
from fraudia_claims.openai_agent import _is_fast_local_question, _json_safe, _with_disclaimer, ask_agent_with_status
from fraudia_claims.storage import initialize_demo_data


class AgentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        initialize_demo_data(force=False)

    def test_required_questions_return_grounded_answers(self) -> None:
        questions = [
            "Cuales son los 10 siniestros con mayor riesgo?",
            "Que proveedores concentran mas alertas rojas?",
            "Que ramos tienen mayor porcentaje de casos sospechosos?",
            "Que ciudades presentan mayor concentracion de alertas?",
            "Que asegurados tienen mayor frecuencia de reclamos?",
            "Que documentos faltan en los casos criticos?",
            "Que casos tienen montos atipicos?",
            "Que siniestros ocurrieron cerca del inicio de la poliza?",
            "Que patrones se repiten en los reclamos sospechosos?",
            "Cual es el ahorro potencial simulado?",
            "Genera un resumen ejecutivo de los casos criticos.",
            "Recomienda que casos deberia revisar primero el analista.",
        ]
        for question in questions:
            answer = answer_offline(question)
            self.assertGreater(len(answer), 80)
            self.assertIn("revision", answer.lower())

    def test_agent_explains_last_session_case(self) -> None:
        answer = answer_offline(
            "Explica el ultimo caso evaluado en vivo",
            session_cases=[
                {
                    "id_temporal": "TMP001",
                    "ramo": "Vehiculos",
                    "cobertura": "Robo",
                    "score_final": 41,
                    "score_reglas": 8,
                    "score_anomalia": 0,
                    "score_nlp": 0,
                    "nivel_riesgo": "Amarillo",
                    "monto_reclamado": 1200,
                    "accion_sugerida": "Escalar a revision documental.",
                    "alertas": [
                        {
                            "codigo": "RF-05",
                            "descripcion": "Siniestro muy cercano al borde de vigencia.",
                            "puntos": 8,
                            "evidencia": "1 dias al borde.",
                        }
                    ],
                }
            ],
        )
        self.assertIn("TMP001", answer)
        self.assertIn("revision humana", answer.lower())

    def test_openai_tool_output_serializes_database_decimals(self) -> None:
        payload = {"rows": [{"score_promedio": Decimal("76.50"), "nested": (Decimal("1.25"),)}]}
        self.assertEqual(_json_safe(payload), {"rows": [{"score_promedio": 76.5, "nested": [1.25]}]})

    def test_fast_local_route_only_matches_demo_questions(self) -> None:
        self.assertTrue(_is_fast_local_question("Que proveedores concentran mas alertas rojas?"))
        self.assertTrue(_is_fast_local_question("Genera un resumen ejecutivo de los casos criticos."))
        self.assertFalse(_is_fast_local_question("Explica con detalle si SIN00001 tiene riesgo por documentos."))

    def test_fast_local_questions_bypass_openai_status(self) -> None:
        previous_key = os.environ.get("OPENAI_API_KEY")
        previous_model = os.environ.get("OPENAI_MODEL")
        os.environ["OPENAI_API_KEY"] = "test-key-not-used"
        os.environ["OPENAI_MODEL"] = "test-model-not-used"
        try:
            answer, source = ask_agent_with_status("Que documentos faltan en los casos criticos?")
        finally:
            if previous_key is None:
                os.environ.pop("OPENAI_API_KEY", None)
            else:
                os.environ["OPENAI_API_KEY"] = previous_key
            if previous_model is None:
                os.environ.pop("OPENAI_MODEL", None)
            else:
                os.environ["OPENAI_MODEL"] = previous_model
        self.assertEqual(source, "Herramientas locales rapidas")
        self.assertIn("revision", answer.lower())

    def test_disclaimer_detection_handles_accents(self) -> None:
        answer = "El score es una alerta de revisión humana, no una acusación."
        self.assertEqual(_with_disclaimer(answer), answer)


if __name__ == "__main__":
    unittest.main()
