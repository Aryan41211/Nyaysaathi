"""Compatibility wrapper for dataset import script.

Allows running:
  python scripts/import_dataset.py --file ../nyaysaathi_part1.json
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path


if __name__ == "__main__":
    target = Path(__file__).resolve().parents[1] / "import_dataset.py"
    sys.argv = [str(target), *sys.argv[1:]]
    runpy.run_path(str(target), run_name="__main__")
