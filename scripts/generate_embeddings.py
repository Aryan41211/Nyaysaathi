"""Project-level wrapper for embedding generation script."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"


def main() -> int:
    cmd = [sys.executable, "generate_embeddings.py", *sys.argv[1:]]
    return subprocess.call(cmd, cwd=BACKEND_DIR)


if __name__ == "__main__":
    raise SystemExit(main())
