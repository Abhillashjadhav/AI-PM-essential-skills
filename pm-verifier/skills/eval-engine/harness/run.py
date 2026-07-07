#!/usr/bin/env python3
"""Apply gates first, then rubric scores. Any gate failure = automatic FAIL.

Mechanical gates run in code. Judge gates and rubric scores come from your own
LLM session: for each case that needs judgment, this script writes
judgments/<id>.prompt.md — paste it into your Claude session and save the JSON
reply as judgments/<id>.json, then re-run this script to finalize.

No API keys, no network, pure stdlib.

Gate types (gates.json): field_present {field} | contains_none {patterns} |
contains_all {patterns} | max_length {chars, field?} | judge (answered in judgments/).
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent
JUDGMENTS_DIR = ROOT / "judgments"


def output_text(case):
    out = case["output"]
    return out if isinstance(out, str) else json.dumps(out)


def run_mechanical_gate(gate, case):
    """Return True on PASS, False on FAIL."""
    p = gate.get("params", {})
    text = output_text(case)
    if gate["type"] == "field_present":
        out = case["output"]
        return isinstance(out, dict) and out.get(p["field"]) not in ("", None)
    if gate["type"] == "contains_none":
        return not any(re.search(pat, text, re.I) for pat in p["patterns"])
    if gate["type"] == "contains_all":
        return all(re.search(pat, text, re.I) for pat in p["patterns"])
    if gate["type"] == "max_length":
        if "field" in p:
            out = case["output"]
            text = out.get(p["field"], "") if isinstance(out, dict) else text
        return len(text) <= p["chars"]
    raise ValueError(f"unknown gate type: {gate['type']}")


def write_prompt(case, judge_prompt):
    JUDGMENTS_DIR.mkdir(exist_ok=True)
    path = JUDGMENTS_DIR / f"{case['id']}.prompt.md"
    path.write_text(
        f"{judge_prompt}\n\n---\n\n## Case {case['id']}\n\n"
        f"### Input\n```\n{json.dumps(case['input'], indent=2) if not isinstance(case['input'], str) else case['input']}\n```\n\n"
        f"### Output to judge\n```\n{output_text(case)}\n```\n"
    )
    return path.name


def main() -> int:
    try:
        cases = json.loads((ROOT / "prepared_cases.json").read_text())
        gates = json.loads((ROOT / "gates.json").read_text())
        rubric = json.loads((ROOT / "rubric.json").read_text())
        judge_prompt = (ROOT / "judge_prompt.md").read_text()
    except FileNotFoundError as e:
        print(f"ERROR: {e.filename} not found — run prepare.py and generate configs first", file=sys.stderr)
        return 1

    mech_gates = [g for g in gates if g["type"] != "judge"]
    judge_gates = [g for g in gates if g["type"] == "judge"]
    criteria_ids = [c["id"] for c in rubric]

    results, pending = [], []
    for case in cases:
        failed = [g["id"] for g in mech_gates if not run_mechanical_gate(g, case)]
        if failed:
            # Gates always run first: a gate-failed case is never rubric-scored.
            results.append({"id": case["id"], "verdict": "FAIL", "failed_gates": failed,
                            "scores": None, "status": "final"})
            continue

        judgment_file = JUDGMENTS_DIR / f"{case['id']}.json"
        if not judgment_file.exists():
            prompt_name = write_prompt(case, judge_prompt)
            pending.append((case["id"], prompt_name))
            results.append({"id": case["id"], "verdict": "PENDING", "failed_gates": [],
                            "scores": None, "status": "pending"})
            continue

        judgment = json.loads(judgment_file.read_text())
        answers = judgment.get("gate_answers", {})
        failed_judge = [g["id"] for g in judge_gates
                        if str(answers.get(g["id"], "FAIL")).upper() != "PASS"]
        if failed_judge:
            results.append({"id": case["id"], "verdict": "FAIL", "failed_gates": failed_judge,
                            "scores": None, "status": "final"})
            continue

        scores = judgment.get("scores", {})
        missing = [c for c in criteria_ids if c not in scores]
        if missing:
            print(f"ERROR: judgment for {case['id']} missing scores for {missing}", file=sys.stderr)
            return 1
        results.append({"id": case["id"], "verdict": "PASS", "failed_gates": [],
                        "scores": {c: scores[c] for c in criteria_ids}, "status": "final"})

    (ROOT / "results.json").write_text(json.dumps(results, indent=2))
    done = [r for r in results if r["status"] == "final"]
    print(f"{len(done)}/{len(results)} case(s) final -> results.json")
    if pending:
        print("\nPENDING — paste each prompt into your Claude session, save the JSON reply "
              "as judgments/<id>.json, then re-run run.py:")
        for cid, prompt_name in pending:
            print(f"  - {cid}: judgments/{prompt_name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
