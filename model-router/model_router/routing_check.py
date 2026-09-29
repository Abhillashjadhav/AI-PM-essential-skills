"""Two real task probes. Request labels and simulated answers cannot certify model use."""
from __future__ import annotations

import json

from .adapters.base import AdapterError
from .contracts import JobState, Role, SpendStatus, new_id, utc_now
from .store import atomic_write


CASES = (
    ("simple", Role.LOWEST,
     "Reformat this supplied list as three bullet points, keeping the words unchanged: apples; pears; figs."),
    ("difficult", Role.HIGHEST,
     "Design the architecture for a multi-tenant task-management service. Compare a shared database with "
     "isolated databases, tenant authorization, consistency, failure recovery, and migration trade-offs. "
     "Recommend an approach and state assumptions. Explain in at most 200 words; do not run commands or change files."),
)


def verdict(row: dict) -> str:
    """Absence of runtime model evidence is unknown, never agreement with our request."""
    if not row["routing_correct"]:
        return "FAIL_ROUTING"
    if row["job_state"] != "SUCCEEDED" or not row.get("response_complete") or not (row.get("response") or "").strip():
        return "FAIL_EXECUTION"
    dispatch = row.get("dispatch", {})
    if dispatch.get("requested_model") != row["expected_model"]:
        return "FAIL_REQUESTED_MODEL"
    if not dispatch.get("provider_turn_id") or dispatch.get("turn_status") != "completed":
        return "INCOMPLETE_TURN_EVIDENCE"
    observed = dispatch.get("observed_model")
    if observed is None:
        return "MODEL_USE_UNVERIFIED"
    return "PASS" if observed == row["expected_model"] else "FAIL_OBSERVED_MODEL"


def run_routing_check(coordinator, *, allow_simulated: bool = False) -> dict:
    """At most one explicit dispatch per case. No scheduler, retries, handoffs or promotion.

    Normal Codex turns currently leave observed_model empty. Even a matching
    thread/start configuration plus an answer is therefore reported as
    MODEL_USE_UNVERIFIED, not as proof of the model that executed the turn.
    """
    store = coordinator.store
    run_id = new_id("routing-check")
    path = store.data_dir / "routing-checks" / run_id / "report.json"
    report = {
        "run_id": run_id, "started_at": utc_now(), "live": coordinator.live,
        "status": "RUNNING", "passed": False, "blocked": None,
        "max_dispatch_attempts": 2, "dispatch_attempts": 0,
        "cases": [{"case": name, "prompt": prompt, "expected_role": role.value, "status": "NOT_RUN"}
                  for name, role, prompt in CASES],
        "note": "Two public probes, not a routing-accuracy evaluation. Review answer quality yourself. "
                "Thread configuration and model self-identification are not per-turn model evidence.",
        "saved_to": str(path),
    }

    def save() -> dict:
        # The durable pre-send marker survives an interruption before run() returns.
        # It is a conservative attempt count, not proof of execution or billing.
        report["dispatch_attempts"] = sum(
            store.one("SELECT count(*) n FROM events WHERE job_id=? AND type='dispatch.sent'", (row["job_id"],))["n"]
            for row in report["cases"] if row.get("job_id")
        )
        atomic_write(path, json.dumps(report, indent=2))
        return report

    def stop(reason: str) -> dict:
        report.update(status="BLOCKED", blocked=reason, finished_at=utc_now())
        return save()

    save()
    try:
        coordinator.start()
        account = coordinator.adapter.read_account()
        usage = coordinator.adapter.read_usage()
        spend = coordinator.adapter.check_spend_boundary(account, usage)
        report["spend"] = {"status": spend.status.value, "reasons": spend.reasons, "missing": spend.missing}
        report["plan"] = account.plan_type
        if spend.status is not SpendStatus.ALLOWED_INCLUDED_ONLY:
            return stop("GPT spending check did not allow a send; no classifier or GPT task was called.")
        if spend.synthetic and (coordinator.live or not allow_simulated):
            return stop("Synthetic evidence cannot authorize this live test.")
        mappings = coordinator.registry.active_mappings(coordinator.account_scope or "")
        missing = [role.value for _, role, _ in CASES if role not in mappings]
        if missing:
            return stop("Approve models for these roles first: " + ", ".join(missing))
        expected_models = {role: mappings[role].model_id for _, role, _ in CASES}
        if len(set(expected_models.values())) != 2:
            return stop("Lowest and highest must have different approved models for this comparison.")

        project_dir = path.parent / "project"
        project_dir.mkdir(parents=True)
        coordinator.add_project(run_id, str(project_dir))
        for row, (_, role, prompt) in zip(report["cases"], CASES):
            row["expected_model"] = expected_models[role]
            row["status"] = "ROUTING"
            save()
            result = coordinator.submit(run_id, prompt, evaluation=True)
            row.update(thread_id=result.thread_id, job_id=result.job_id,
                       selected_role=result.role.value if result.role else None,
                       selected_model=result.model_id, explanation=result.explanation,
                       routing_ms=result.timings_ms.get("submit_to_selection_ms"),
                       routing_correct=result.role is role and result.model_id == expected_models[role])
            coordinator.ui.notify(f"Routing check {row['case']}: expected {role.value}; selected {result.model_id or 'none'}.")
            if not row["routing_correct"]:
                row["status"] = "FAIL_ROUTING"
                save()
                continue  # never spend GPT usage on a known wrong selection
            row["status"] = "DISPATCHING"
            save()
            state = coordinator.run(result.job_id)
            row["job_state"] = state.value
            dispatch = store.one(
                "SELECT requested_model, observed_model, observed_model_note, provider_turn_id, turn_status, phase "
                "FROM dispatches WHERE job_id=? ORDER BY created_at DESC LIMIT 1", (result.job_id,))
            row["dispatch"] = dict(dispatch) if dispatch else {}
            messages = [m for m in store.messages(result.thread_id) if m["role"] == "assistant"]
            row["response"] = messages[-1]["content"] if messages else None
            row["response_complete"] = bool(messages and messages[-1]["complete"])
            created = store.events(event_type="thread.provider_created", thread_id=result.thread_id)
            row["thread_configured_model"] = created[-1]["payload"].get("model") if created else None
            row["status"] = verdict(row)
            coordinator.ui.notify(f"Routing check {row['case']}: {row['status']}; "
                                  f"per-turn model: {row['dispatch'].get('observed_model') or 'not reported'}.")
            save()
            if state is not JobState.SUCCEEDED:
                report["blocked"] = store.job(result.job_id)["blocker"] or state.value
                break  # no repeat, queue drain or further send after an execution failure

        statuses = [row["status"] for row in report["cases"]]
        if not coordinator.live:
            report["status"] = "SIMULATED"
        elif all(status == "PASS" for status in statuses):
            report.update(status="PASS", passed=True)
        elif all(status in {"PASS", "MODEL_USE_UNVERIFIED"} for status in statuses):
            report["status"] = "MODEL_USE_UNVERIFIED"
        else:
            report["status"] = "NOT_PASSED"
    except AdapterError as exc:
        return stop(str(exc))
    except KeyboardInterrupt:
        report["status"] = "INTERRUPTED"
    report["finished_at"] = utc_now()
    return save()
