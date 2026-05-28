from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fraudia_claims.vision import SUPPORTED_MIME_TYPES, analyze_claim_image, image_analysis_available


class VisionTests(unittest.TestCase):
    def test_offline_without_credentials(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            result = analyze_claim_image(b"fake-image", "image/jpeg", {"ramo": "Vehiculos"})
        self.assertEqual(result["status"], "offline")
        self.assertIn("Vision opera en modo offline", result["observaciones"][0])

    def test_rejects_unsupported_mime_type(self) -> None:
        with patch.dict("os.environ", {"OPENAI_API_KEY": "x", "OPENAI_MODEL": "test-model"}, clear=True):
            result = analyze_claim_image(b"fake-file", "application/pdf", {})
        self.assertEqual(result["status"], "offline")
        self.assertIn("no soportado", result["observaciones"][0])

    def test_availability_requires_key_and_model(self) -> None:
        with patch.dict("os.environ", {"OPENAI_API_KEY": "x"}, clear=True):
            self.assertFalse(image_analysis_available())
        with patch.dict("os.environ", {"OPENAI_API_KEY": "x", "OPENAI_MODEL": "m"}, clear=True):
            self.assertTrue(image_analysis_available())

    def test_supported_types_cover_demo_uploads(self) -> None:
        self.assertIn("image/jpeg", SUPPORTED_MIME_TYPES)
        self.assertIn("image/png", SUPPORTED_MIME_TYPES)
        self.assertIn("image/webp", SUPPORTED_MIME_TYPES)


if __name__ == "__main__":
    unittest.main()
