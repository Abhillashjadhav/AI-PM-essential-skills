"""Evaluation runner: offline routing fixtures now; finite, gated live plans.

Offline runs need no account and make no model call. Live comparisons obey the
same spend/tool gates as user work, run from a visible finite plan, yield to
foreground work, and never make a candidate the automatic choice.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..classifier import ClassifierInput, classify
from ..contracts import (
    CapacityEstimate,
    CapacityState,
    Clarity,
    GradeStatus,
    RiskLevel,
    Role,
    TaskKind,
    new_id,
    utc_now,
)
from ..policy import ImplementationFacts, implementation_role, required_role
from ..store import Store, dumps
from .graders import GRADER_VERSION, SEEDED_CASES, check_judge, grade_assertions

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"
ROUTING_CASES = FIXTURES / "routing-cases.json"
IMPLEMENTATION_CASES = FIXTURES / "implementation-cases.json"


def load_cases(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if "dataset_version" not in data or not isinstance(data.get("cases"), list):
        raise ValueError(f"{path} is not a versioned case file")
    ids = [c["id"] for c in data["cases"]]
    if len(ids) != len(set(ids)):
        raise ValueError(f"{path} has duplicate case ids")
    return data


def synthetic_capacity(state: str) -> CapacityEstimate:
    known = state != "UNKNOWN"
    return CapacityEstimate(
        state=CapacityState(state),
        buckets=["synthetic:primary"] if known else [],
        observed_at=utc_now(),
        plan_type="synthetic",
        account_scope="synthetic",
        forecast_low=10.0 if known else None,
        forecast_high=20.0 if known else None,
        method="synthetic test estimate",
        method_version="synthetic",
        observations=[],
        uncertainty=["explicitly synthetic estimate for branch coverage"],
        synthetic=True,
    )


def run_routing_case(case: dict[str, Any]) -> dict[str, Any]:
    assessment = classify(
        ClassifierInput(
            text=case["prompt"],
            attachment_manifest=case.get("attachments", []),
            explicit_urgency=case.get("urgency"),
        )
    )
    plan = required_role(assessment)
    checks = [{"check": "role", "ok": plan.role.value == case["expected_role"], "expected": case["expected_role"], "observed": plan.role.value}]
    if "expected_kind" in case:
        checks.append({"check": "kind", "ok": assessment.task_kind.value == case["expected_kind"], "expected": case["expected_kind"], "observed": assessment.task_kind.value})
    if case.get("expect_uncertainty"):
        checks.append({"check": "uncertainty_stated", "ok": bool(assessment.uncertainty) or plan.upward_fallback, "observed": assessment.uncertainty})
    if "forbid_role" in case:
        checks.append({"check": "forbidden_role", "ok": plan.role.value != case["forbid_role"], "observed": plan.role.value})
    ok = all(c["ok"] for c in checks)
    return {
        "case_id": case["id"],
        "status": (GradeStatus.PASS if ok else GradeStatus.FAIL).value,
        "checks": checks,
        "rule_ids": plan.rule_ids,
        "reason_codes": assessment.reason_codes,
        "confidence_score": None,  # never fabricated
    }


def run_implementation_case(case: dict[str, Any]) -> dict[str, Any]:
    facts = ImplementationFacts(
        requires_highest=case["requires_highest"],
        requires_highest_reasons=["synthetic high-risk flag"] if case["requires_highest"] else [],
        clarity=Clarity(case["clarity"]),
        clarity_evidence=[],
        risk=RiskLevel(case["risk"]),
        lowest_candidate_ok=case["lowest_candidate_ok"],
        lowest_candidate_note="synthetic",
    )
    plan = implementation_role(facts, synthetic_capacity(case["capacity"]))
    ok = plan.role.value == case["expected_role"]
    return {
        "case_id": case["id"],
        "status": (GradeStatus.PASS if ok else GradeStatus.FAIL).value,
        "checks": [{"check": "role", "ok": ok, "expected": case["expected_role"], "observed": plan.role.value}],
        "rule_ids": plan.rule_ids,
    }


def reference_judge(case: dict[str, Any]) -> bool:
    """Deterministic rule judge used to exercise the seeded self-check."""
    specs = {
        "seed-correct": {"anchors": ["12 March", "unchanged"]},
        "seed-wrong-but-plausible": {"anchors": ["12 March", "unchanged"]},
        "seed-missing-requirement": {"required": ["churn", "latency", "cost"]},
        "seed-unsupported-claim": {"prohibited_regex": [r"\d+\s?%"]},
        "seed-prohibited-action": {"prohibited_regex": [r"rm\s+-rf"]},
    }
    return grade_assertions(case["output"], specs[case["id"]]).status is GradeStatus.PASS


def run_offline(store: Store, *, routing_path: Path = ROUTING_CASES, implementation_path: Path = IMPLEMENTATION_CASES) -> dict[str, Any]:
    routing = load_cases(routing_path)
    implementation = load_cases(implementation_path)
    run_id = new_id("evr")
    plan = {
        "kind": "offline",
        "datasets": {routing_path.name: routing["dataset_version"], implementation_path.name: implementation["dataset_version"]},
        "cases": len(routing["cases"]) + len(implementation["cases"]) + len(SEEDED_CASES),
        "model_calls": 0,
        "grader_version": GRADER_VERSION,
    }
    store.execute(
        "INSERT INTO eval_runs(id, kind, plan, status, created_at) VALUES (?,?,?,?,?)",
        (run_id, "offline", dumps(plan), "RUNNING", utc_now()),
    )
    store.event("evaluation.started", {"run_id": run_id, "plan": plan})
    results = [run_routing_case(c) for c in routing["cases"]] + [run_implementation_case(c) for c in implementation["cases"]]
    judge = check_judge(reference_judge, judge_id="reference-rules")
    for result in results:
        store.execute(
            "INSERT INTO evaluations(id, run_id, case_id, payload, status, synthetic, created_at) VALUES (?,?,?,?,?,?,?)",
            (new_id("evl"), run_id, result["case_id"], dumps(result), result["status"], 1, utc_now()),
        )
        store.event("evaluation.graded", {"run_id": run_id, "case_id": result["case_id"], "status": result["status"]})
    failed = [r for r in results if r["status"] != GradeStatus.PASS.value]
    status = "PASSED" if not failed and judge.usable else "FAILED"
    store.execute("UPDATE eval_runs SET status=?, finished_at=? WHERE id=?", (status, utc_now(), run_id))
    return {
        "run_id": run_id,
        "status": status,
        "plan": plan,
        "passed": len(results) - len(failed),
        "failed": [{"case_id": r["case_id"], "checks": [c for c in r["checks"] if not c["ok"]]} for r in failed],
        "judge_self_check": judge.to_dict(),
        "note": "offline routing-policy evidence only; says nothing about answer quality on real prompts",
    }


@dataclass
class LivePlan:
    id: str
    cases: list[dict[str, Any]]
    models: list[str]
    turns: int
    authorised_by: str | None

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "cases": [c["id"] for c in self.cases], "models": self.models, "turns": self.turns, "authorised_by": self.authorised_by}


def build_live_plan(cases: list[dict[str, Any]], models: list[str], *, max_turns: int = 50) -> LivePlan:
    turns = len(cases) * len(models)
    if turns == 0:
        raise ValueError("a live plan needs at least one case and one model")
    if turns > max_turns:
        raise ValueError(f"plan needs {turns} turns, above the finite cap {max_turns}; split it")
    return LivePlan(id=new_id("lvp"), cases=cases, models=models, turns=turns, authorised_by=None)


def run_live(
    plan: LivePlan,
    coordinator,
    *,
    project: str,
    authorised_by: str | None,
    allow_simulated: bool = False,
) -> dict[str, Any]:
    """Execute a finite, owner-authorised comparison plan through the normal
    gates. Candidate models may be compared here but never become automatic
    bindings. Foreground user work keeps precedence: the run stops (and can be
    re-run) when a user job is waiting."""
    if not authorised_by:
        return {"status": "BLOCKED", "reason": "live comparison plan not authorised by the owner", "plan": plan.to_dict()}
    if not coordinator.live and not allow_simulated:
        return {"status": "BLOCKED", "reason": "not connected to a live adapter", "plan": plan.to_dict()}
    store = coordinator.store
    plan.authorised_by = authorised_by
    run_id = new_id("evr")
    store.execute(
        "INSERT INTO eval_runs(id, kind, plan, status, created_at) VALUES (?,?,?,?,?)",
        (run_id, "live" if coordinator.live else "simulated", dumps(plan.to_dict()), "RUNNING", utc_now()),
    )
    store.event("evaluation.started", {"run_id": run_id, "plan": plan.to_dict()})
    records: list[dict[str, Any]] = []
    status = "COMPLETED"
    reason = None
    try:
        for case in plan.cases:
            for model_id in plan.models:
                waiting_user = store.one(
                    "SELECT COUNT(*) AS n FROM jobs WHERE kind='user_turn' AND state IN ('SELECTED','READY') AND cancelled=0"
                )["n"]
                if waiting_user:
                    status, reason = "YIELDED", "foreground user work is waiting; re-run the plan later"
                    raise StopIteration
                usage_before = _usage_row(store)
                job = coordinator.create_evaluation_job(project, model_id, case["prompt"], run_id=run_id)
                final = coordinator.run(job["job_id"])
                answer = store.one(
                    "SELECT content FROM messages WHERE thread_id=? AND role='assistant' ORDER BY created_at DESC LIMIT 1",
                    (job["thread_id"],),
                )
                output = answer["content"] if answer and final.value == "SUCCEEDED" else None
                grade = grade_assertions(output, case.get("spec", {}))
                record = {
                    "case_id": case["id"],
                    "model_id": model_id,
                    "job_state": final.value,
                    "grade": grade.to_dict(),
                    "usage_before": usage_before,
                    "usage_after": _usage_row(store),
                    "usage_note": "percent deltas are rounded, delayed and shared; not a per-model price",
                    "synthetic": not coordinator.live,
                }
                records.append(record)
                store.execute(
                    "INSERT INTO evaluations(id, run_id, case_id, payload, status, synthetic, created_at) VALUES (?,?,?,?,?,?,?)",
                    (new_id("evl"), run_id, case["id"], dumps(record), grade.status.value if final.value == "SUCCEEDED" else GradeStatus.BLOCKED.value,
                     int(not coordinator.live), utc_now()),
                )
                event = "evaluation.graded" if final.value == "SUCCEEDED" else "evaluation.blocked"
                store.event(event, {"run_id": run_id, "case_id": case["id"], "model_id": model_id, "state": final.value})
                if final.value != "SUCCEEDED":
                    status, reason = "BLOCKED", f"{model_id}: job ended {final.value}"
                    raise StopIteration
    except StopIteration:
        pass
    except KeyboardInterrupt:
        status, reason = "CANCELLED", "cancelled by the owner"
    store.execute("UPDATE eval_runs SET status=?, finished_at=? WHERE id=?", (status, utc_now(), run_id))
    return {"run_id": run_id, "status": status, "reason": reason, "records": records, "plan": plan.to_dict()}


def _usage_row(store: Store) -> dict[str, Any] | None:
    row = store.one("SELECT id, observed_at FROM usage_snapshots ORDER BY observed_at DESC LIMIT 1")
    return dict(row) if row else None


__all__ = ["build_live_plan", "load_cases", "run_live", "run_offline", "Role", "TaskKind"]
