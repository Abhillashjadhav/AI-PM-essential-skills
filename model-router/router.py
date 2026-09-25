#!/usr/bin/env python3
"""Model router launcher: `python3 model-router/router.py --help`."""

from __future__ import annotations

import sys
from pathlib import Path

if sys.version_info < (3, 11):
    sys.exit("model-router needs Python 3.11 or newer")

sys.path.insert(0, str(Path(__file__).resolve().parent))

from model_router.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
