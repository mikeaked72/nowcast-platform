"""
Run the macro data-store refresh end to end.

Usage:
    python pipeline/update_all_data.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent

STEPS = [
    "update_fred.py",
    "update_aus.py",
    "update_international.py",
    "build_processed.py",
    "validate_data_store.py",
]


def main() -> int:
    for step in STEPS:
        path = HERE / step
        print(f"\n==> {step}")
        result = subprocess.run([sys.executable, str(path)], cwd=HERE.parent)
        if result.returncode != 0:
            print(f"{step} failed with exit code {result.returncode}", file=sys.stderr)
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
