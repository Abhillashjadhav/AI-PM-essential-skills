#!/usr/bin/env python3
"""Offline acceptance checks through actual CLI subprocesses; fictional records only."""
import csv
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile

SKILL = Path(__file__).resolve().parents[1]
EXAMPLES = SKILL / "examples"
END = "2026-09-08T00:00:00Z"
ARMS = ("standard_workflow", "ai_workflow")


def run(*args, exit_code=0):
    result = subprocess.run([sys.executable, str(SKILL / "trial_kit.py"), *args, "--format", "json"],
                            text=True, capture_output=True, timeout=15)
    if result.returncode != exit_code:
        raise AssertionError(f"CLI exit {result.returncode}, expected {exit_code}: {result.stdout} {result.stderr}")
    return json.loads(result.stdout)


def check(condition, message):
    if not condition:
        raise AssertionError(message)
    print("PASS | " + message)


def csv_bytes(rows):
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader(); writer.writerows(rows)
    return output.getvalue().encode()


def main():
    with tempfile.TemporaryDirectory(prefix="workflow-trial-uat-") as tmp:
        folder = Path(tmp)
        plan_path = folder / "plan.json"
        plan = run("plan", "--design", str(EXAMPLES / "design.json"), "--units", str(EXAMPLES / "units.csv"), "--out", str(plan_path))
        check(len(plan["assignments"]) == 32 and all(sum(a["assigned_arm"] == arm for a in plan["assignments"]) == 16 for arm in ARMS),
              "32 frozen units; 16 per original assignment")
        blank = folder / "results-blank.csv"
        run("results-template", "--plan", str(plan_path), "--out", str(blank))
        with blank.open(newline="") as source:
            blank_rows = list(csv.DictReader(source))
        blocked = run("audit", "--plan", str(plan_path), "--results", str(blank), "--as-of", END, exit_code=2)
        check({r["unit_id"] for r in blank_rows} == {a["unit_id"] for a in plan["assignments"]}
              and all(r["draft_minutes"] == "" for r in blank_rows) and blocked["status"] == "BLOCKED",
              "Ready-to-fill template keeps every ID; blanks are not observations")
        for name, successes, effort, efficiency in (("fast_draft", 10, 400, 1.5), ("favorable", 15, 160, 5.625), ("ratio_tradeoff", 10, 80, 7.5)):
            report = run("audit", "--plan", str(plan_path), "--results", str(EXAMPLES / f"results_{name}.csv"), "--as-of", END)
            standard, ai = (report["by_assignment"][arm] for arm in ARMS)
            check(report["accounted_units"] == 32 and report["plan_sha256"] == plan["manifest"]["plan_sha256"]
                  and (standard["successes"], standard["total_measured_human_minutes"], standard["successful_outcomes_per_measured_human_hour"]) == (14, 320, 2.625)
                  and (ai["successes"], ai["total_measured_human_minutes"], ai["successful_outcomes_per_measured_human_hour"]) == (successes, effort, efficiency)
                  and all(r["assigned_units"] == 16 and r["assignment_deviations"] == 1 for r in (standard, ai)),
                  f"SYNTHETIC {name}: customer successes beside measured effort; original N retained")
            if name == "fast_draft":
                check(standard["labor_minutes"] == dict(zip(("draft_minutes", "review_minutes", "rework_minutes", "followup_minutes"), (192, 64, 32, 32)))
                      and ai["labor_minutes"] == dict(zip(("draft_minutes", "review_minutes", "rework_minutes", "followup_minutes"), (64, 112, 160, 64)))
                      and (ai["failed"], ai["unfinished"]) == (5, 1), "All four effort stages and mature unresolved work counted")
        gap = run("audit", "--plan", str(plan_path), "--results", str(EXAMPLES / "results_gap.csv"), "--as-of", END, exit_code=2)
        immature = run("audit", "--plan", str(plan_path), "--results", str(EXAMPLES / "results_fast_draft.csv"), "--as-of", "2026-09-07T00:00:00Z", exit_code=2)
        check(gap["reason"] == "missing_assigned_units" and immature["reason"] == "immature_window", "Missing unit and immature horizon block comparison")
        with (EXAMPLES / "results_fast_draft.csv").open(newline="") as source:
            rows = list(csv.DictReader(source))
        for row in rows:
            for key in ("draft_minutes", "review_minutes", "rework_minutes", "followup_minutes"):
                row[key] = "0"
        zeros = folder / "zero-observed.csv"; zeros.write_bytes(csv_bytes(rows))
        report = run("audit", "--plan", str(plan_path), "--results", str(zeros), "--as-of", END)
        check(all(report["by_assignment"][arm]["successful_outcomes_per_measured_human_hour"] is None for arm in ARMS)
              and report["by_assignment"][ARMS[0]]["successes"] == 14, "Observed zero effort: undefined ratio, visible success counts")
        before = plan_path.read_bytes()
        blocked = run("plan", "--design", str(EXAMPLES / "design.json"), "--units", str(EXAMPLES / "units.csv"), "--out", str(plan_path), exit_code=2)
        check(blocked["reason"] == "output_exists" and plan_path.read_bytes() == before, "Frozen plan survives attempted overwrite")
    print("UAT PASS | 9 checks | SYNTHETIC, local CLI only; no provider calls or causal result")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
