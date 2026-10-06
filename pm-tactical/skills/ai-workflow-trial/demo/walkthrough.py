#!/usr/bin/env python3
"""Teach measurement using real local CLI output and explicitly fictional records."""
import argparse
import csv
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

SKILL = Path(__file__).resolve().parents[1]
EXAMPLES = SKILL / "examples"
END = "2026-09-08T00:00:00Z"
ARMS = ("standard_workflow", "ai_workflow")


def run(*args, expected=0):
    proc = subprocess.run([sys.executable, str(SKILL / "trial_kit.py"), *args, "--format", "json"],
                          capture_output=True, text=True, timeout=15)
    if proc.returncode != expected:
        raise RuntimeError(f"Unexpected CLI exit {proc.returncode}: {proc.stdout} {proc.stderr}")
    return json.loads(proc.stdout)


def table(report):
    print("Original arm  N  Customer success   Draft Review Rework Follow-up  Human min  Success/h")
    for arm, name in zip(ARMS, ("Standard", "AI")):
        group = report["by_assignment"][arm]
        labor = group["labor_minutes"]
        rate = group["success_rate"] * 100
        ratio = group["successful_outcomes_per_measured_human_hour"]
        shown = "undefined" if ratio is None else f"{ratio:.3f}"
        print(f"{name:<12} {group['assigned_units']:2}  {group['successes']:2}/{group['assigned_units']} ({rate:5.2f}%)"
              f"   {labor['draft_minutes']:5.0f} {labor['review_minutes']:6.0f} {labor['rework_minutes']:6.0f}"
              f" {labor['followup_minutes']:9.0f} {group['total_measured_human_minutes']:10.0f} {shown:>10}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pause-seconds", type=float, default=14, help="reading hold per page in seconds")
    args = parser.parse_args()
    if not 0 <= args.pause_seconds <= 30:
        parser.error("pause must be between 0 and 30 seconds")

    def page(step, title):
        print("\033[2J\033[H", end="")
        print(f"STEP {step}/5 | {title}")
        print("SYNTHETIC teaching data | real local CLI | descriptive accounting only\n")

    def hold():
        sys.stdout.flush()
        time.sleep(args.pause_seconds)

    with tempfile.TemporaryDirectory(prefix="workflow-trial-demo-") as tmp:
        folder = Path(tmp); plan_path = folder / "plan.json"
        design = json.loads((EXAMPLES / "design.json").read_text())
        page(1, "DEFINE THE OUTCOME AND HUMAN WORK")
        print("Your task: compare one workflow change against today's standard workflow.")
        print("Example customer outcome: " + design["outcome"])
        print("Common horizon: " + design["window_end"])
        print("Before assignment: freeze eligible task IDs, strata, seed and follow-up rule.\n")
        print("Ready-to-fill templates: design.json, units.csv, effort-log.csv")
        print("Log per person/task/stage: active minutes, activity, recorded_at_utc.")
        print("Include preparation + prompting + draft, review, corrections + recovery,")
        print("and coordination + handoff + customer follow-up. Name omitted work.")
        print("Allocate each person's active minute once; passive model wait is not labor.")
        print("Spillover yes/unknown? Stop for design review; do not force a 'no'.")
        hold()

        page(2, "FREEZE ASSIGNMENTS; GET YOUR BLANK RESULTS SHEET")
        print("Recipe: python3 trial_kit.py plan --design YOUR_DESIGN --units YOUR_UNITS --out NEW_PLAN")
        plan = run("plan", "--design", str(EXAMPLES / "design.json"), "--units", str(EXAMPLES / "units.csv"), "--out", str(plan_path))
        sizes = {arm: sum(a["assigned_arm"] == arm for a in plan["assignments"]) for arm in ARMS}
        strata_count = len({a["stratum"] for a in plan["assignments"]})
        print(f"Actual example CLI: {len(plan['assignments'])} units; {sizes[ARMS[0]]} Standard + {sizes[ARMS[1]]} AI, {strata_count} balanced strata.")
        print("Plan digest: " + plan["manifest"]["plan_sha256"][:20] + "... (full digest in JSON)")
        print("\nRecipe: python3 trial_kit.py results-template --plan NEW_PLAN --out YOUR_RESULTS.csv")
        template_path = folder / "results.csv"
        run("results-template", "--plan", str(plan_path), "--out", str(template_path))
        rows = list(csv.DictReader(io.StringIO(template_path.read_text())))
        print(f"Actual example CLI wrote {len(rows)} blank rows with every frozen ID.")
        print("Fill actual workflow, status, yes/no success, and four observed effort fields.")
        print("Zero = observed zero. Blank = missing. Keep failed and unfinished tasks.")
        print("The prefilled required horizon is not proof that follow-up occurred.")
        print("Hashes support reproducibility; they do not certify design or honest logging.")
        hold()

        page(3, "LOG HUMAN EFFORT; CHECK CUSTOMER SUCCESS BESIDE IT")
        print("Recipe: python3 trial_kit.py audit --plan NEW_PLAN --results YOUR_RESULTS --as-of CUTOFF")
        fast = run("audit", "--plan", str(plan_path), "--results", str(EXAMPLES / "results_fast_draft.csv"), "--as-of", END)
        print(f"Actual example CLI: accounted {fast['accounted_units']}/{fast['assigned_units']} original assignments.")
        standard, ai = (fast["by_assignment"][arm] for arm in ARMS)
        means = [ai["labor_minutes"][k] / ai["assigned_units"] for k in ("draft_minutes", "review_minutes", "rework_minutes", "followup_minutes")]
        print(f"Fictional mean AI-assigned effort: {means[0]:g} draft + {means[1]:g} review + {means[2]:g} rework + {means[3]:g} follow-up min.")
        print("Convert your own person-stage log into these four per-task totals.\n")
        table(fast)
        draft_base = standard["labor_minutes"]["draft_minutes"]
        effort_base = standard["total_measured_human_minutes"]
        if draft_base:
            draft_change = (ai["labor_minutes"]["draft_minutes"] / draft_base - 1) * 100
            drafting = f"{abs(draft_change):.1f}% {'less' if draft_change < 0 else 'more'} drafting time"
        else:
            drafting = "Drafting percent change undefined (zero Standard draft minutes)"
        effort_change = "undefined" if not effort_base else f"{(ai['total_measured_human_minutes'] / effort_base - 1) * 100:+.0f}%"
        print(f"\n{drafting}; measured human effort change: {effort_change} (AI vs Standard).")
        print(f"Customer successes: Standard {standard['successes']}; AI {ai['successes']}. Read beside labor.")
        print(f"AI failed={ai['failed']}, unfinished={ai['unfinished']}; both stay in N and labor.")
        print("Human min = declared measured scope. No omissions declared in these fictional rows.")
        print("This is an accounting example, not a genuine workflow result.")
        hold()

        page(4, "READ THE OUTCOME AND EFFORT TRADEOFF TOGETHER")
        favorable = run("audit", "--plan", str(plan_path), "--results", str(EXAMPLES / "results_favorable.csv"), "--as-of", END)
        print("SYNTHETIC alternative rows, same frozen assignments:")
        table(favorable)
        print("\nSYNTHETIC ratio tradeoff rows, same frozen assignments:")
        tradeoff = run("audit", "--plan", str(plan_path), "--results", str(EXAMPLES / "results_ratio_tradeoff.csv"), "--as-of", END)
        table(tradeoff)
        control, alternative = (tradeoff["by_assignment"][arm] for arm in ARMS)
        ratio = alternative["successful_outcomes_per_measured_human_hour"]
        ratio_text = "undefined" if ratio is None else f"{ratio:.3f}"
        print(f"\nAI ratio = {ratio_text}; customer successes: Standard {control['successes']}, AI {alternative['successes']}.")
        print("Review customer outcomes, measured scope, omitted work and deviations together.")
        print("A ratio alone names no winner. No causal, statistical, ROI or launch verdict.")
        hold()

        page(5, "FIX GAPS; REUSE THE METHOD ON YOUR OWN WORKFLOW")
        print("Actual CLI test: one assigned result row removed from the fictional input.")
        gap = run("audit", "--plan", str(plan_path), "--results", str(EXAMPLES / "results_gap.csv"), "--as-of", END, expected=2)
        print("BLOCKED [" + gap["reason"] + "]: " + gap["message"])
        print("\n1. Copy templates/ into a new private trial folder and replace placeholders.")
        print("2. Freeze an appropriate eligible list and plan before assignment.")
        print("3. Fill every result from active human-time logs and observed customer outcomes.")
        print("4. At the mature common horizon, audit all original units, including failures.")
        print("5. Discuss successes and human effort together; get separate design review.")
        print("\nUsable in a spreadsheet too; this CLI makes missing records visible.")
        print("Scripted local CLI walkthrough; synthetic data; no model call or real-productivity claim.")
        hold()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
