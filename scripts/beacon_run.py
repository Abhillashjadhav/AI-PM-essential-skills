#!/usr/bin/env python3
"""Register an additional skill command without inspecting its arguments or IO."""
import os
from pathlib import Path
import sys


def main():
    args = sys.argv[1:]
    if args[:1] == ["--"]:
        args = args[1:]
    if not args:
        print("Usage: python scripts/beacon_run.py -- COMMAND [ARGS...]", file=sys.stderr)
        return 2
    try:
        import workflow_beacon  # noqa: F401
    except Exception:
        os.execvp(args[0], args)
    os.execv(sys.executable, [sys.executable, "-m", "workflow_beacon", "run",
             "--workflow", "ai-pm-skills.command", "--project-root",
             str(Path(__file__).resolve().parents[1]), "--", *args])


if __name__ == "__main__":
    raise SystemExit(main())
