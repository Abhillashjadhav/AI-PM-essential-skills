"""Write transparent fictional fixtures to a chosen directory; never overwrite."""
import argparse
import csv
import io
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from trial_kit import ARMS, LABOR, RESULT_COLUMNS, build_plan

DESIGN = {
    "schema_version": 1, "trial_id": "fictional-support-32", "data_classification": "synthetic",
    "design": "unit_randomized_parallel", "outcome": "Correct resolution with no reopen by the fixed horizon",
    "window_start": "2026-09-01T00:00:00Z", "window_end": "2026-09-08T00:00:00Z",
    "eligibility_frozen": True, "eligibility_rule": "All 32 fictional support tasks listed before assignment",
    "spillover": "no", "independence_basis": "Fictional independent tasks with no shared customer or worker carryover",
    "human_effort_method": "Observed active person-minutes through the common horizon; each person's minute allocated once across stages/tasks, summed across people; passive agent waiting excluded",
    "labor_scope": {"draft_minutes": "preparation/prompting/drafting", "review_minutes": "review",
                    "rework_minutes": "rework/recovery", "followup_minutes": "coordination/handoff/customer follow-up"},
    "unmeasured_work": [], "seed": 20261007,
}


def csv_text(columns, rows):
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def fixtures():
    units = [{"unit_id": f"TASK-{i+1:03}", "stratum": ("account", "billing", "complex", "simple")[i // 8]}
             for i in range(32)]
    design_raw = (json.dumps(DESIGN, indent=2, sort_keys=True) + "\n").encode()
    units_raw = csv_text(("unit_id", "stratum"), units).encode()
    plan = build_plan(design_raw, units_raw)
    outputs = {"design.json": design_raw.decode(), "units.csv": units_raw.decode()}
    for name, ai_success, ai_effort in (("fast_draft", 10, (4, 7, 10, 4)),
                                      ("favorable", 15, (4, 3, 2, 1)),
                                      ("ratio_tradeoff", 10, (2, 1, 1, 1))):
        rows, indexes = [], {arm: 0 for arm in ARMS}
        for assignment in plan["assignments"]:
            arm = assignment["assigned_arm"]
            index = indexes[arm]
            indexes[arm] += 1
            successes = 14 if arm == ARMS[0] else ai_success
            effort = (12, 4, 2, 2) if arm == ARMS[0] else ai_effort
            status = "completed" if index < successes else ("unfinished" if index == 15 else "failed")
            row = {"unit_id": assignment["unit_id"], "actual_arm": ARMS[1 - ARMS.index(arm)] if index == 0 else arm,
                   "status": status, "success": "yes" if status == "completed" else "no",
                   "observed_through": DESIGN["window_end"], **dict(zip(LABOR, effort))}
            rows.append(row)
        outputs[f"results_{name}.csv"] = csv_text(RESULT_COLUMNS, rows)
        if name == "fast_draft":
            outputs["results_gap.csv"] = csv_text(RESULT_COLUMNS, rows[:-1])
    return outputs


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="new or existing directory without these fixture files")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    data = fixtures()
    if any((args.out / name).exists() for name in data):
        parser.error("a fixture already exists; choose a new directory")
    for name, text in data.items():
        (args.out / name).write_text(text, encoding="utf-8")
    print(f"Wrote {len(data)} SYNTHETIC fixture files; no observations or model calls.")
