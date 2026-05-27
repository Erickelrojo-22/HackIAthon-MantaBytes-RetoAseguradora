from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fraudia_claims.offline_agent import answer_offline
from fraudia_claims.storage import initialize_demo_data


class AgentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        initialize_demo_data(force=False)

    def test_required_questions_return_grounded_answers(self) -> None:
        questions = [
            "Cuales son los 10 siniestros con mayor riesgo?",
            "Que proveedores concentran mas alertas rojas?",
            "Que documentos faltan en los casos criticos?",
            "Cual es el ahorro potencial simulado?",
        ]
        for question in questions:
            answer = answer_offline(question)
            self.assertGreater(len(answer), 80)
            self.assertIn("revision", answer.lower())


if __name__ == "__main__":
    unittest.main()
