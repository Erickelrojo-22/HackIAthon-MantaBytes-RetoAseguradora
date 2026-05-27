from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fraudia_claims.storage import initialize_demo_data


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic FraudIA demo data.")
    parser.add_argument("--force", action="store_true", help="Regenerate CSV and SQLite files.")
    parser.add_argument("--n-per-ramo", type=int, default=1000, help="Number of claims per insurance line.")
    args = parser.parse_args()
    db_path = initialize_demo_data(force=args.force, n_per_ramo=args.n_per_ramo)
    print(f"Demo data ready: {db_path}")


if __name__ == "__main__":
    main()
