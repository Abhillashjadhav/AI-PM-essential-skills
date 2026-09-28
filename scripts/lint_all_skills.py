#!/usr/bin/env python3
"""Lint every Git-tracked SKILL.md, including internal skills and unusual paths."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def tracked_skills(root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"], cwd=root, capture_output=True, check=True
    )
    return sorted(
        root / os.fsdecode(raw)
        for raw in result.stdout.split(b"\0")
        if raw and Path(os.fsdecode(raw)).name == "SKILL.md"
    )


def main() -> int:
    paths = tracked_skills(ROOT)
    if not paths:
        print("SKILL LINT: FAIL (no tracked skills)", file=sys.stderr)
        return 1
    failed = []
    for path in paths:
        result = subprocess.run(
            [sys.executable, str(ROOT / "tests/lint_skill.py"), str(path)],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )
        if result.returncode:
            failed.append(path)
            print(f"FAIL {path.relative_to(ROOT)!s}\n{result.stdout}{result.stderr}")
    print(f"SKILL LINT: {'FAIL' if failed else 'PASS'} "
          f"({len(paths) - len(failed)}/{len(paths)} skills)")
    return int(bool(failed))


if __name__ == "__main__":
    raise SystemExit(main())
