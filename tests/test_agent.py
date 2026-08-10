from __future__ import annotations

import json
import os
import sys
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fraudia_claims.agent_intents import detect_intent
from fraudia_claims.offline_agent import answer_offline
from fraudia_claims.openai_agent import _is_fast_local_question, _json_safe, _with_disclaimer, ask_agent_with_status
from fraudia_claims.storage import initialize_demo_data
from fraudia_claims.utils import normalize_text


class _FakeItem:
    def __init__(self, type_: str, **kwargs) -> None:
        self.type = type_
        for key, value in kwargs.items():
            setattr(self, key, value)


class _FakeResponse:
    def __init__(self, response_id: str, output=None, output_text=None) -> None:
        self.id = response_id
        self.output = output or []
        self.output_text = output_text


def _set_openai_env(key: str = "test-key", model: str = "test-model"):
    previous_key = os.environ.get("OPENAI_API_KEY")
    previous_model = os.environ.get("OPENAI_MODEL")
    os.environ["OPENAI_API_KEY"] = key
    os.environ["OPENAI_MODEL"] = model
    return previous_key, previous_model


def _restore_openai_env(previous_key, previous_model) -> None:
    if previous_key is None:
        os.environ.pop("OPENAI_API_KEY", None)
    else:
        os.environ["OPENAI_API_KEY"] = previous_key
    if previous_model is None:
        os.environ.pop("OPENAI_MODEL", None)
    else:
        os.environ["OPENAI_MODEL"] = previous_model


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
            self.assertIn("revision", normalize_text(answer))
            self.assertNotIn("ProgrammingError", answer)
            self.assertNotIn("\n|", answer)

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
        self.assertIn("revision humana", normalize_text(answer))

    def test_openai_tool_output_serializes_database_decimals(self) -> None:
        payload = {"rows": [{"score_promedio": Decimal("76.50"), "nested": (Decimal("1.25"),)}]}
        self.assertEqual(_json_safe(payload), {"rows": [{"score_promedio": 76.5, "nested": [1.25]}]})

    def test_fast_local_route_only_matches_demo_questions(self) -> None:
        self.assertTrue(_is_fast_local_question("Que proveedores concentran mas alertas rojas?"))
        self.assertTrue(_is_fast_local_question("Genera un resumen ejecutivo de los casos criticos."))
        self.assertTrue(_is_fast_local_question("Recomienda que casos deberia revisar primero el analizta"))
        self.assertTrue(_is_fast_local_question("¿Qué patrones se repiten en los reclamos sospechosos?"))
        self.assertTrue(_is_fast_local_question("Recomienda qué casos debería revisar primero el analízta"))
        self.assertFalse(_is_fast_local_question("Explica con detalle si SIN00001 tiene riesgo por documentos."))

    def test_documents_answer_is_actionable_when_no_missing_rows_exist(self) -> None:
        answer = answer_offline("Que documentos faltan en los casos criticos?")
        self.assertIn("Revisión documental", answer)
        self.assertNotIn("No encontre resultados", answer)
        self.assertNotIn("\n|", answer)

    def test_repeated_patterns_answer_prioritizes_actionable_review(self) -> None:
        answer = answer_offline("que patrones se repiten en los reclamos sospechosos")
        self.assertIn("Patrones narrativos", answer)
        self.assertIn("señal", answer)
        self.assertIn("Revisar narrativa", answer)
        self.assertNotIn("\n|", answer)

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
        self.assertIn("revision", normalize_text(answer))

    def test_disclaimer_detection_handles_accents(self) -> None:
        answer = "El score es una alerta de revisión humana, no una acusación."
        self.assertEqual(_with_disclaimer(answer), answer)

    def test_router_no_longer_captures_free_form_questions_by_single_keyword(self) -> None:
        # Antes 'modelo' in normalized bastaba para clasificar cualquier
        # pregunta libre como intent "metrics", incluso con OPENAI_API_KEY
        # configurada. Ahora solo las preguntas canonicas (o casi) de la demo
        # se resuelven localmente; el resto debe llegar a OpenAI.
        self.assertEqual(detect_intent("Como funciona tu modelo de deteccion de fraude?").name, "fallback")
        self.assertEqual(detect_intent("Que tan seguro es tu sistema de alertas?").name, "fallback")
        self.assertFalse(_is_fast_local_question("Como funciona tu modelo de deteccion de fraude?"))

    def test_claim_detail_intent_triggers_on_valid_sin_without_keyword(self) -> None:
        # Antes se exigia ademas una palabra clave como "explica" o "detalle";
        # "cuentame sobre SIN-1023" no disparaba el intent correcto.
        intent = detect_intent("Cuentame sobre SIN-1023")
        self.assertEqual(intent.name, "claim_detail")
        self.assertEqual(intent.claim_id, "SIN-1023")

    def test_openai_processes_multiple_tool_calling_rounds(self) -> None:
        previous_key, previous_model = _set_openai_env()
        first_call = _FakeItem("function_call", name="list_risk_cases", arguments="{}", call_id="call_1")
        second_call = _FakeItem(
            "function_call",
            name="get_claim_detail",
            arguments=json.dumps({"id_siniestro": "SIN00001"}),
            call_id="call_2",
        )
        responses = [
            _FakeResponse("resp-1", output=[first_call]),
            _FakeResponse("resp-2", output=[second_call]),  # segunda ronda: pide OTRA herramienta
            _FakeResponse("resp-3", output=[], output_text="Respuesta final basada en dos herramientas."),
        ]
        fake_client = MagicMock()
        fake_client.responses.create.side_effect = responses
        try:
            with patch("openai.OpenAI", return_value=fake_client):
                answer, source = ask_agent_with_status("Pregunta libre que necesita encadenar dos herramientas")
        finally:
            _restore_openai_env(previous_key, previous_model)
        self.assertEqual(fake_client.responses.create.call_count, 3)
        self.assertIn("Respuesta final basada en dos herramientas", answer)
        self.assertTrue(source.startswith("OpenAI activo"))

    def test_openai_stops_after_max_tool_rounds_and_falls_back_offline(self) -> None:
        previous_key, previous_model = _set_openai_env()
        endless_call = _FakeItem("function_call", name="get_model_metrics", arguments="{}", call_id="call_x")
        # El modelo nunca deja de pedir herramientas: se agotan las rondas y,
        # como no hay output_text, cae a la respuesta offline en vez de
        # colgarse en un loop infinito.
        responses = [_FakeResponse(f"resp-{i}", output=[endless_call]) for i in range(6)]
        fake_client = MagicMock()
        fake_client.responses.create.side_effect = responses
        try:
            with patch("openai.OpenAI", return_value=fake_client):
                answer, source = ask_agent_with_status("Pregunta que agota las rondas de herramientas")
        finally:
            _restore_openai_env(previous_key, previous_model)
        self.assertEqual(source, "Offline")
        self.assertIn("revisión humana", answer)

    def test_session_cases_flow_end_to_end_through_ask_agent_with_status(self) -> None:
        # session_cases ahora se puede pasar sin API key configurada (usa la
        # ruta local de sesion) y sin ella (usa el fallback local generico).
        answer, source = ask_agent_with_status(
            "Explica el ultimo caso evaluado en vivo",
            session_cases=[{"id_temporal": "TMP-XYZ", "nivel_riesgo": "Rojo", "score_final": 88}],
        )
        self.assertEqual(source, "Sesion local")
        self.assertIn("TMP-XYZ", answer)

    def test_openai_fallback_hides_internal_exception_names(self) -> None:
        previous_key = os.environ.get("OPENAI_API_KEY")
        previous_model = os.environ.get("OPENAI_MODEL")
        os.environ["OPENAI_API_KEY"] = ""
        os.environ["OPENAI_MODEL"] = "test-model-not-used"
        try:
            with patch("fraudia_claims.openai_agent.LOGGER.exception"), patch(
                "fraudia_claims.openai_agent.answer_offline",
                side_effect=RuntimeError("ProgrammingError"),
            ):
                answer, source = ask_agent_with_status("Pregunta desconocida para forzar fallback")
        finally:
            if previous_key is None:
                os.environ.pop("OPENAI_API_KEY", None)
            else:
                os.environ["OPENAI_API_KEY"] = previous_key
            if previous_model is None:
                os.environ.pop("OPENAI_MODEL", None)
            else:
                os.environ["OPENAI_MODEL"] = previous_model
        self.assertEqual(source, "Offline")
        self.assertIn("revisión humana", answer)
        self.assertNotIn("ProgrammingError", answer)


if __name__ == "__main__":
    unittest.main()
