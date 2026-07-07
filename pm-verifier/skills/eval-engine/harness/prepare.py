#!/usr/bin/env python3
"""Validate test cases in cases/ and write prepared_cases.json.

Each case is one JSON file: {"id": str, "input": str|object, "output": str|object}.
Optional: "expected" (free-form notes for humans; the harness ignores it).
Pure stdlib. Exit 0 on success, 1 on any invalid case.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent
CASES_DIR = ROOT / "cases"
OUT_FILE = ROOT / "prepared_cases.json"
REQUIRED = ("id", "input", "output")


def main() -> int:
    if not CASES_DIR.is_dir():
        print(f"ERROR: no cases/ directory at {CASES_DIR}", file=sys.stderr)
        return 1
    files = sorted(CASES_DIR.glob("*.json"))
    if not files:
        print("ERROR: cases/ contains no .json files", file=sys.stderr)
        return 1

    cases, errors, seen_ids = [], [], set()
    for f in files:
        try:
            case = json.loads(f.read_text())
        except json.JSONDecodeError as e:
            errors.append(f"{f.name}: invalid JSON ({e})")
            continue
        missing = [k for k in REQUIRED if k not in case or case[k] in ("", None)]
        if missing:
            errors.append(f"{f.name}: missing required field(s) {missing}")
            continue
        if case["id"] in seen_ids:
            errors.append(f"{f.name}: duplicate id {case['id']!r}")
            continue
        seen_ids.add(case["id"])
        cases.append(case)

    if errors:
        print("INVALID CASES:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    OUT_FILE.write_text(json.dumps(cases, indent=2))
    print(f"prepared {len(cases)} case(s) -> {OUT_FILE.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
