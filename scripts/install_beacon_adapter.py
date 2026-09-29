#!/usr/bin/env python3
"""Install the optional shared Beacon adapter from a reviewed immutable Git commit.

Run with the same virtualenv Python used by the workflow. This script deliberately
does not install Beacon itself, modify global Python, or open a report.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import sys


def main() -> int:
    lock = json.loads((Path(__file__).resolve().parents[1] / "beacon-source.lock.json").read_text())
    commit = lock["commit"]
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        print("Adapter source has not been pinned to a reviewed commit yet.", file=sys.stderr)
        return 2
    if sys.prefix == sys.base_prefix:
        print("Use a virtualenv Python; see docs/BEACON.md.", file=sys.stderr)
        return 2
    requirement = (
        f"workflow-beacon @ git+{lock['repository']}@{commit}"
        f"#subdirectory={lock['subdirectory']}"
    )
    return subprocess.call([sys.executable, "-m", "pip", "install", "--no-deps", requirement])


if __name__ == "__main__":
    raise SystemExit(main())

