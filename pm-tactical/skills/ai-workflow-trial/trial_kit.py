#!/usr/bin/env python3
"""Frozen, local workflow-trial planning and descriptive human-effort accounting.

Python standard library only. No provider, network, credential or account access.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import datetime
import hashlib
import io
import json
import math
from pathlib import Path
import re
import sys

VERSION = "0.1.0"
ARMS = ("standard_workflow", "ai_workflow")
LABOR = ("draft_minutes", "review_minutes", "rework_minutes", "followup_minutes")
RESULT_COLUMNS = ("unit_id", "actual_arm", "status", "success", "observed_through", *LABOR)
DESIGN_KEYS = {"schema_version", "trial_id", "data_classification", "design", "outcome",
               "window_start", "window_end", "eligibility_frozen", "eligibility_rule",
               "spillover", "independence_basis", "human_effort_method", "labor_scope", "unmeasured_work", "seed"}
ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}\Z")
SHA = re.compile(r"[0-9a-f]{64}\Z")
METHOD = "sha256_rank_v1_even_strata"


class TrialBlocked(Exception):
    def __init__(self, code: str, message: str):
        self.code, self.message = code, message
        super().__init__(message)


def require(condition, code, message):
    if not condition:
        raise TrialBlocked(code, message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def read_bytes(path):
    try:
        return Path(path).read_bytes()
    except OSError:
        raise TrialBlocked("input_unreadable", "An input file could not be read.") from None


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate_json_key", "JSON keys must be unique.")
        result[key] = value
    return result


def read_json(raw):
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (UnicodeError, ValueError):
        raise TrialBlocked("invalid_json", "Use UTF-8 JSON with finite values.") from None


def timestamp(value):
    require(isinstance(value, str) and re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", value),
            "invalid_timestamp", "Use an explicit UTC timestamp: YYYY-MM-DDTHH:MM:SSZ.")
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        raise TrialBlocked("invalid_timestamp", "Use a valid UTC calendar timestamp.") from None


def validate_design(design):
    require(isinstance(design, dict) and set(design) == DESIGN_KEYS,
            "design_fields", "Design fields must match the documented version-1 contract.")
    require(type(design["schema_version"]) is int and design["schema_version"] == 1,
            "design_version", "Only design schema version 1 is supported.")
    require(design["design"] == "unit_randomized_parallel",
            "unsupported_design", "Only fixed-unit parallel randomization is supported; seek design review for other designs.")
    require(design["eligibility_frozen"] is True, "eligibility_not_frozen",
            "Freeze the eligible unit IDs and strata before assigning workflows.")
    require(design["spillover"] == "no", "spillover_not_resolved",
            "Known or unknown spillover is unsupported; resolve interference with a design specialist.")
    require(design["data_classification"] in ("synthetic", "observed"),
            "data_classification", "Declare synthetic or observed data.")
    require(isinstance(design["trial_id"], str) and ID.fullmatch(design["trial_id"]),
            "trial_id", "Use a 1–64 character ASCII trial ID.")
    for key in ("outcome", "eligibility_rule", "independence_basis", "human_effort_method"):
        require(isinstance(design[key], str) and bool(design[key].strip()),
                "missing_declaration", "Declare outcome, eligibility, independence and human-effort measurement.")
    scope = design["labor_scope"]
    require(isinstance(scope, dict) and set(scope) == set(LABOR)
            and all(isinstance(v, str) and bool(v.strip()) for v in scope.values()),
            "labor_scope", "Name the measured work covered by each of the four effort fields.")
    omitted = design["unmeasured_work"]
    require(isinstance(omitted, list) and all(isinstance(v, str) and bool(v.strip()) for v in omitted),
            "unmeasured_work", "Explicitly list omitted human work; an empty list is a declaration, not proof.")
    require(timestamp(design["window_start"]) < timestamp(design["window_end"]),
            "invalid_window", "The fixed observation window must end after it starts.")
    require(type(design["seed"]) is int and 0 <= design["seed"] < 2**63,
            "invalid_seed", "Use a declared integer seed from 0 through 2^63−1.")
    return design


def csv_rows(raw, columns):
    try:
        reader = csv.DictReader(io.StringIO(raw.decode("utf-8")), strict=True)
        require(reader.fieldnames == list(columns), "csv_columns",
                "CSV headers must exactly match the documented columns and order.")
        rows = list(reader)
    except (UnicodeError, csv.Error):
        raise TrialBlocked("invalid_csv", "Use well-formed UTF-8 CSV.") from None
    require(all(set(row) == set(columns) and all(v is not None for v in row.values()) for row in rows),
            "csv_row_shape", "Every CSV row must have exactly one value for every column.")
    return rows


def validate_units(units):
    require(isinstance(units, list) and bool(units), "no_units", "Supply frozen eligible units.")
    seen = set()
    for unit in units:
        require(isinstance(unit, dict) and set(unit) == {"unit_id", "stratum"},
                "unit_fields", "Each eligible unit needs only unit_id and stratum.")
        require(isinstance(unit["unit_id"], str) and ID.fullmatch(unit["unit_id"]),
                "invalid_unit_id", "Use unique 1–64 character ASCII unit IDs.")
        require(unit["unit_id"] not in seen, "duplicate_unit", "Eligible unit IDs must be unique.")
        seen.add(unit["unit_id"])
        s = unit["stratum"]
        require(isinstance(s, str) and s == s.strip() and 0 < len(s) <= 80,
                "invalid_stratum", "Supply a nonblank, trimmed stratum of at most 80 characters.")
    counts = Counter(u["stratum"] for u in units)
    require(all(n >= 2 and n % 2 == 0 for n in counts.values()), "unbalanced_stratum",
            "This design requires at least two units and an even unit count in every stratum.")
    return sorted(units, key=lambda u: u["unit_id"])


def assign(units, seed):
    """Versioned hash ranking avoids Python random-library shuffle differences."""
    assigned = []
    for stratum in sorted({u["stratum"] for u in units}):
        group = [u for u in units if u["stratum"] == stratum]
        group.sort(key=lambda u: (digest([METHOD, seed, stratum, u["unit_id"]]), u["unit_id"]))
        for index, unit in enumerate(group):
            arm = ARMS[1] if index < len(group) // 2 else ARMS[0]
            assigned.append({**unit, "assigned_arm": arm})
    return sorted(assigned, key=lambda u: u["unit_id"])


def plan_digest(plan):
    payload = {**plan, "manifest": {k: v for k, v in plan["manifest"].items() if k != "plan_sha256"}}
    return digest(payload)


def build_plan(design_raw, units_raw):
    design = validate_design(read_json(design_raw))
    units = validate_units(csv_rows(units_raw, ("unit_id", "stratum")))
    assignments = assign(units, design["seed"])
    plan = {"schema_version": 1, "design": design, "units": units, "assignments": assignments,
            "manifest": {"tool_version": VERSION, "randomization": METHOD,
                         "design_file_sha256": hashlib.sha256(design_raw).hexdigest(),
                         "units_file_sha256": hashlib.sha256(units_raw).hexdigest(),
                         "design_sha256": digest(design), "units_sha256": digest(units),
                         "assignments_sha256": digest(assignments)}}
    plan["manifest"]["plan_sha256"] = plan_digest(plan)
    return plan


def validate_plan(plan):
    require(isinstance(plan, dict) and set(plan) == {"schema_version", "design", "units", "assignments", "manifest"},
            "plan_fields", "Use the complete plan generated by this tool.")
    require(type(plan["schema_version"]) is int and plan["schema_version"] == 1,
            "plan_version", "Only plan schema version 1 is supported.")
    design = validate_design(plan["design"])
    units = validate_units(plan["units"])
    require(plan["units"] == units and plan["assignments"] == assign(units, design["seed"]),
            "assignment_mismatch", "Assignments must reproduce the frozen units, strata and seed.")
    manifest = plan["manifest"]
    keys = {"tool_version", "randomization", "design_file_sha256", "units_file_sha256",
            "design_sha256", "units_sha256", "assignments_sha256", "plan_sha256"}
    require(isinstance(manifest, dict) and set(manifest) == keys,
            "manifest_fields", "Use the complete versioned design/input hash manifest.")
    require(manifest["tool_version"] == VERSION and manifest["randomization"] == METHOD,
            "manifest_version", "This tool cannot interpret that planning version.")
    require(all(isinstance(manifest[k], str) and SHA.fullmatch(manifest[k]) for k in keys if k.endswith("sha256")),
            "manifest_hash", "Manifest hashes must be SHA-256 values.")
    require(manifest["design_sha256"] == digest(design) and manifest["units_sha256"] == digest(units)
            and manifest["assignments_sha256"] == digest(plan["assignments"])
            and manifest["plan_sha256"] == plan_digest(plan), "manifest_mismatch",
            "Plan contents disagree with the recorded hashes; use the original frozen plan.")
    return plan


def labor_value(value):
    try:
        number = float(value)
    except (ValueError, TypeError, OverflowError):
        raise TrialBlocked("invalid_labor", "Every effort field needs an observed nonnegative finite number; blanks are not zero.") from None
    require(math.isfinite(number) and number >= 0, "invalid_labor",
            "Every effort field needs an observed nonnegative finite number; blanks are not zero.")
    return number


def summarize(rows):
    effort = {}
    try:
        for key in LABOR:
            effort[key] = math.fsum(r[key] for r in rows)
        total = math.fsum(effort.values())
        hours = total / 60
        successes = sum(r["success"] for r in rows)
        per_hour = successes * 60 / total if total else None
    except (OverflowError, ZeroDivisionError):
        raise TrialBlocked("unrepresentable_aggregate", "Effort aggregates cannot be represented safely.") from None
    require(all(math.isfinite(x) for x in [*effort.values(), total, hours]
                + ([] if per_hour is None else [per_hour])) and not (total > 0 and hours == 0),
            "unrepresentable_aggregate", "Effort aggregates cannot be represented safely.")
    n = len(rows)
    return {"assigned_units": n, "successes": successes,
            "success_rate": successes / n if n else None,
            "completed": sum(r["status"] == "completed" for r in rows),
            "failed": sum(r["status"] == "failed" for r in rows),
            "unfinished": sum(r["status"] == "unfinished" for r in rows),
            "assignment_deviations": sum(r["actual_arm"] != r["assigned_arm"] for r in rows),
            "labor_minutes": effort, "total_measured_human_minutes": total, "measured_human_hours": hours,
            "successful_outcomes_per_measured_human_hour": per_hour}


def audit(plan, results_raw, as_of):
    validate_plan(plan)
    require(timestamp(as_of) >= timestamp(plan["design"]["window_end"]), "immature_window",
            "The declared observation cutoff is before the frozen window ends; wait for follow-up.")
    results = csv_rows(results_raw, RESULT_COLUMNS)
    expected = {a["unit_id"]: a for a in plan["assignments"]}
    seen, accounted = set(), []
    for row in results:
        uid = row["unit_id"]
        require(uid in expected, "extra_unit", "Results contain a unit outside the frozen assignments.")
        require(uid not in seen, "duplicate_result", "Results contain more than one row for an assigned unit.")
        seen.add(uid)
        require(row["actual_arm"] in (*ARMS, "mixed"), "invalid_actual_arm",
                "Record the actual workflow as standard_workflow, ai_workflow or mixed.")
        require(row["status"] in ("completed", "failed", "unfinished"), "invalid_status",
                "Keep every assigned unit as completed, failed or unfinished.")
        require(row["success"] in ("yes", "no"), "invalid_success", "Record observed success as yes or no.")
        require(row["success"] != "yes" or row["status"] == "completed", "inconsistent_success",
                "A failed or unfinished unit cannot be marked successful.")
        through = timestamp(row["observed_through"])
        horizon = timestamp(plan["design"]["window_end"])
        require(through >= horizon, "immature_unit_window",
                "Every assigned unit needs observed effort and outcome through the common window end.")
        require(through == horizon, "unequal_unit_horizon",
                "Use the same frozen horizon for every unit; exclude effort after that horizon.")
        accounted.append({**expected[uid], "actual_arm": row["actual_arm"], "status": row["status"],
                          "success": row["success"] == "yes", **{k: labor_value(row[k]) for k in LABOR}})
    require(seen == set(expected), "missing_assigned_units",
            f"{len(set(expected) - seen)} assigned unit(s) have no result row. Keep unfinished units and record their effort.")
    groups = {arm: summarize([r for r in accounted if r["assigned_arm"] == arm]) for arm in ARMS}
    strata = {s: {arm: summarize([r for r in accounted if r["stratum"] == s and r["assigned_arm"] == arm])
                  for arm in ARMS} for s in sorted({r["stratum"] for r in accounted})}
    return {"schema_version": 1, "report_kind": "descriptive_accounting",
            "data_classification": plan["design"]["data_classification"], "trial_id": plan["design"]["trial_id"],
            "outcome": plan["design"]["outcome"], "window_start": plan["design"]["window_start"],
            "window_end": plan["design"]["window_end"], "declared_as_of": as_of,
            "human_effort_method": plan["design"]["human_effort_method"],
            "labor_scope": plan["design"]["labor_scope"], "unmeasured_work": plan["design"]["unmeasured_work"],
            "assigned_units": len(expected), "accounted_units": len(accounted), "by_assignment": groups,
            "by_stratum": strata, "plan_sha256": plan["manifest"]["plan_sha256"],
            "results_file_sha256": hashlib.sha256(results_raw).hexdigest(),
            "limitations": ["Declarations and hashes do not prove design validity or honest measurement.",
                            "Selection, interference and concurrent human attention require separate review.",
                            "No significance test, causal-validity certification, ROI or launch decision is produced."]}


def write_new(path, text):
    try:
        with Path(path).open("x", encoding="utf-8", newline="") as output:
            output.write(text)
    except FileExistsError:
        raise TrialBlocked("output_exists", "The output already exists; preserve it and choose a new file.") from None
    except OSError:
        raise TrialBlocked("output_unavailable", "The output could not be written.") from None


def write_json(path, value):
    write_new(path, json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def results_template(plan):
    """Preserve every frozen unit; blanks deliberately fail an outcome audit."""
    validate_plan(plan)
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=RESULT_COLUMNS, lineterminator="\n")
    writer.writeheader()
    for assignment in plan["assignments"]:
        writer.writerow({"unit_id": assignment["unit_id"],
                         "observed_through": plan["design"]["window_end"]})
    return output.getvalue()


def plan_text(plan):
    label = plan["design"]["data_classification"].upper()
    lines = [f"{label} | WORKFLOW TRIAL PLAN | descriptive accounting only",
             f"Frozen units: {len(plan['units'])} | seed: {plan['design']['seed']} | 1:1 within each stratum"]
    for s in sorted({u["stratum"] for u in plan["units"]}):
        counts = Counter(a["assigned_arm"] for a in plan["assignments"] if a["stratum"] == s)
        lines.append(f"  {s}: standard={counts[ARMS[0]]}, AI={counts[ARMS[1]]}")
    lines.extend([f"Plan SHA-256: {plan['manifest']['plan_sha256']}",
                  "Declarations do not prove validity. No model calls made by this tool."])
    return "\n".join(lines)


def report_text(report):
    lines = [f"{report['data_classification'].upper()} | DESCRIPTIVE WORKFLOW ACCOUNTING",
             f"Accounted: {report['accounted_units']}/{report['assigned_units']} assigned units; original assignments retained",
             f"Outcome: {report['outcome']}", f"Window ends: {report['window_end']} | declared cutoff: {report['declared_as_of']}",
             "Arm       N  Success  Rate     Draft  Review  Rework  Followup  Measured min  Outcomes/h"]
    for arm, name in zip(ARMS, ("Standard", "AI")):
        g = report["by_assignment"][arm]
        efficiency = g["successful_outcomes_per_measured_human_hour"]
        shown = "undefined" if efficiency is None else f"{efficiency:.3f}"
        rate = "undefined" if g["success_rate"] is None else f"{g['success_rate'] * 100:.1f}%"
        nums = "  ".join(f"{g['labor_minutes'][k]:6.1f}" for k in LABOR)
        lines.append(f"{name:<8} {g['assigned_units']:2}  {g['successes']:7}  {rate:>6}  {nums}  {g['total_measured_human_minutes']:12.1f}  {shown}")
        lines.append(f"  Completed={g['completed']}; failed={g['failed']}; unfinished={g['unfinished']}; deviations={g['assignment_deviations']}")
    lines.append("Strata (Standard success/N; AI success/N): " + "; ".join(
        f"{s} {g[ARMS[0]]['successes']}/{g[ARMS[0]]['assigned_units']}, {g[ARMS[1]]['successes']}/{g[ARMS[1]]['assigned_units']}"
        for s, g in report["by_stratum"].items()))
    lines.append("Measured scope: " + "; ".join(report["labor_scope"][k] for k in LABOR))
    lines.append("Unmeasured work (declared): " + ("; ".join(report["unmeasured_work"]) or "none; not independently verified"))
    lines.append("Human-time method (declared): " + report["human_effort_method"])
    lines.append("Unresolved at the mature horizon = unsuccessful there; effort retained. Ratio alone names no winner.")
    lines.append("Outcomes/h uses measured active person-time, not elapsed model wait. JSON retains unrounded values.")
    lines.append("Declarations do not prove validity; no causal, statistical or launch verdict. No model calls by this tool.")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version=f"ai-workflow-trial {VERSION}")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("plan", help="freeze design and balanced assignments")
    p.add_argument("--design", required=True)
    p.add_argument("--units", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--format", choices=("text", "json"), default="text")
    t = sub.add_parser("results-template", help="make a blank measurement CSV with every assigned unit")
    t.add_argument("--plan", required=True)
    t.add_argument("--out", required=True)
    t.add_argument("--format", choices=("text", "json"), default="text")
    a = sub.add_parser("audit", help="account for every assigned unit and declared measured human effort")
    a.add_argument("--plan", required=True)
    a.add_argument("--results", required=True)
    a.add_argument("--as-of", required=True, help="declared UTC observation cutoff, not an attestation")
    a.add_argument("--out", help="optional new JSON report file; never overwrites")
    a.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    try:
        if args.command == "plan":
            value = build_plan(read_bytes(args.design), read_bytes(args.units))
            write_json(args.out, value)
            text = plan_text(value)
        elif args.command == "results-template":
            plan = read_json(read_bytes(args.plan))
            write_new(args.out, results_template(plan))
            value = {"status": "BLANK_TEMPLATE", "assigned_units": len(plan["assignments"]),
                     "plan_sha256": plan["manifest"]["plan_sha256"]}
            text = (f"BLANK measurement template: {value['assigned_units']} assigned rows retained.\n"
                    "Fill actual workflow, status, success and observed effort. Blanks never mean zero.\n"
                    "observed_through is the required horizon, not evidence that follow-up occurred.")
        else:
            value = audit(read_json(read_bytes(args.plan)), read_bytes(args.results), args.as_of)
            if args.out:
                write_json(args.out, value)
            text = report_text(value)
        print(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) if args.format == "json" else text)
        return 0
    except TrialBlocked as error:
        blocked = {"status": "BLOCKED", "reason": error.code, "message": error.message}
        print(json.dumps(blocked) if args.format == "json" else f"BLOCKED [{error.code}]: {error.message}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
