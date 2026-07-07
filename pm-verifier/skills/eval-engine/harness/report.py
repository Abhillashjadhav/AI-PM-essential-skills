#!/usr/bin/env python3
"""Render results.json as report.md: pass/fail table + score distribution.

Scores shown are judge-assigned, not objective measurements. Pure stdlib.
"""
import json
import sys
from statistics import mean
from pathlib import Path

ROOT = Path(__file__).parent


def bar(count, width=20, total=None):
    if not total:
        return ""
    filled = round(width * count / total)
    return "█" * filled + "·" * (width - filled)


def main() -> int:
    try:
        results = json.loads((ROOT / "results.json").read_text())
        rubric = json.loads((ROOT / "rubric.json").read_text())
    except FileNotFoundError as e:
        print(f"ERROR: {e.filename} not found — run run.py first", file=sys.stderr)
        return 1

    lines = ["# Eval report", "",
             "Scores are judge-assigned via your own LLM session — calibrated judgments, not objective measurements.", "",
             "## Per-case results", "",
             "| Case | Verdict | Failed gates | Mean score |",
             "|---|---|---|---|"]
    for r in results:
        scores = r["scores"] or {}
        mean_s = f"{mean(scores.values()):.1f}" if scores else "—"
        gates = ", ".join(r["failed_gates"]) or "—"
        lines.append(f"| {r['id']} | {r['verdict']} | {gates} | {mean_s} |")

    passed = sum(1 for r in results if r["verdict"] == "PASS")
    failed = sum(1 for r in results if r["verdict"] == "FAIL")
    pending = sum(1 for r in results if r["verdict"] == "PENDING")
    lines += ["", f"**{passed} PASS / {failed} FAIL"
              + (f" / {pending} PENDING" if pending else "") + f" of {len(results)} case(s).**"]

    scored = [r for r in results if r["scores"]]
    if scored:
        lines += ["", "## Score distribution (scored cases only)", ""]
        for c in rubric:
            values = [r["scores"][c["id"]] for r in scored]
            lines += [f"### {c['id']}: {c['name']} — mean {mean(values):.1f}", "", "```"]
            for s in range(1, 6):
                n = values.count(s)
                lines.append(f"{s} | {bar(n, total=len(values))} {n}")
            lines += ["```", ""]

    (ROOT / "report.md").write_text("\n".join(lines) + "\n")
    print(f"report.md written ({passed} PASS / {failed} FAIL"
          + (f" / {pending} PENDING" if pending else "") + ")")
    return 0


if __name__ == "__main__":
    sys.exit(main())
