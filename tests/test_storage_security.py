from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fraudia_claims.storage import load_table


class StorageSecurityTests(unittest.TestCase):
    def test_load_table_rejects_unknown_names(self) -> None:
        with self.assertRaises(ValueError):
            load_table("scores; DROP TABLE siniestros--")


if __name__ == "__main__":
    unittest.main()
