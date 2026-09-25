"""Reproducible synthetic demo. No account, no network, no model call.

Everything shown is SIMULATED: the adapter is the in-process simulator and the
"owner" approvals are scripted demo approvals in a throwaway data directory.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from typing import Callable

from .adapters.base import ApprovalRequest
from .adapters.fake import FakeAdapter, FakeScenario, SimulatedCrash
from .capacity import CalibrationArtifact, CapacityEstimator
from .contracts import AcceptanceEvidence, Role, SpendStatus, utc_now
from .coordinator import Coordinator, RouterUI
from .evals.metrics import iso_week, render_markdown, weekly_report
from .evals.runner import run_offline
from .registry import mapping_hash_for
from .store import Store

SIM_BINDINGS = ((Role.HIGHEST, "sim-astra-1", "high"), (Role.MIDDLE, "sim-sol-1", "medium"), (Role.LOWEST, "sim-luna-1", "low"))


class PrintUI(RouterUI):
    def __init__(self, out: Callable[[str], None]) -> None:
        self.out = out
        self._streaming = False

    def notify(self, text: str) -> None:
        self._end_stream()
        for line in text.splitlines():
            self.out(line if line.startswith("Router:") else f"Router: {line}" if not line.startswith(" ") else line)

    def stream(self, text: str) -> None:
        if not self._streaming:
            sys.stdout.write("  ")
            self._streaming = True
        sys.stdout.write(text)
        sys.stdout.flush()

    def _end_stream(self) -> None:
        if self._streaming:
            sys.stdout.write("\n")
            self._streaming = False

    def ask_approval(self, request: ApprovalRequest) -> str:
        self.notify(f"Router: approval requested — {request.kind}: {request.command or request.paths} (demo declines)")
        return "decline"


def approve_simulated_bindings(coordinator: Coordinator, actor: str = "demo-owner") -> None:
    account = coordinator.account_scope
    assert account is not None
    for role, model, effort in SIM_BINDINGS:
        coordinator.registry.approve_mapping(
            account, role, model, effort, actor=actor, confirm_hash=mapping_hash_for(account, role, model, effort)
        )


ARCH_RECORD = {
    "goal": "Add CSV export to the reports page",
    "scope": "Export the visible report table as CSV; no new dependencies",
    "decisions": [{"title": "CSV only, UTF-8, comma separated", "status": "decided"}],
    "constraints": ["standard library only", "no schema changes"],
    "components": [{"name": "exporter", "responsibility": "rows to CSV text"}],
    "interfaces": [{"name": "export_csv", "contract": "list[dict[str, str]] -> str"}],
    "files": ["app/export.py", "app/reports_view.py", "tests/test_export.py"],
    "steps": [
        {"description": "Write export_csv in app/export.py"},
        {"description": "Add an Export button to the reports view", "depends_on": [0]},
        {"description": "Add unit tests for empty and quoted values", "depends_on": [0]},
    ],
    "risks": [],
    "tests": [{"name": "empty", "check": "export_csv([]) == ''"}, {"name": "quotes", "check": "values with commas are quoted"}],
    "blocking_questions": [],
    "nonblocking_items": ["Excel-specific BOM can come later"],
}


def run_demo(data_dir: Path | None = None, out: Callable[[str], None] = print) -> dict:
    temp = None
    if data_dir is None:
        temp = tempfile.TemporaryDirectory(prefix="model-router-demo-")
        data_dir = Path(temp.name)
    summary: dict = {"data_dir": str(data_dir), "simulated": True}
    try:
        return _run(data_dir, out, summary)
    finally:
        if temp is not None:
            temp.cleanup()


def _run(data_dir: Path, out: Callable[[str], None], summary: dict) -> dict:
    out("SIMULATED DEMO — no account, network, or model is used. Answers below are synthetic.")
    out("")
    store = Store(data_dir / "data")
    scenario = FakeScenario()
    adapter = FakeAdapter(scenario)
    ui = PrintUI(out)
    coordinator = Coordinator(store, adapter, live=False, ui=ui)
    coordinator.start()
    approve_simulated_bindings(coordinator)
    project_dir = data_dir / "portfolio"
    project_dir.mkdir(parents=True, exist_ok=True)
    coordinator.add_project("Portfolio", str(project_dir))

    def turn(project: str, text: str, *, thread: str | None = None, script: list | None = None):
        out(f"You: {text}")
        if script is not None:
            scenario.turn_scripts.append(script)
        result = coordinator.submit(project, text, thread_id=thread)
        if result.handoff is not None:
            return result
        if thread is None:
            out(f"Router: {result.explanation}")
            out(f"        (route decided in {result.timings_ms.get('submit_to_selection_ms')} ms, stored before any send)")
        state = coordinator.run(result.job_id)
        ui._end_stream()
        result.state = state
        return result

    out("Project: Portfolio")
    record_block = "```architecture-record\n" + json.dumps(ARCH_RECORD) + "\n```"
    arch = turn(
        "Portfolio",
        "Review this product architecture for CSV export and finalise it.",
        script=[{"kind": "delta", "text": "Proposed architecture: an exporter module, a button, tests.\n"}, {"kind": "delta", "text": record_block},
                {"kind": "completed", "status": "completed"}],
    )
    summary["architecture"] = {"role": arch.role.value if arch.role else None, "model": arch.model_id, "state": arch.state.value}
    out("")
    out("You: Approved, implement this.")
    accepted = coordinator.submit("Portfolio", "Approved, implement this.", thread_id=arch.thread_id)
    handoff = accepted.handoff
    assert handoff is not None
    if handoff.status == "CREATED":
        out("Router: Architecture saved. Opening implementation in this project.")
        out(f"Router: {handoff.role.plain} reasoning — implementation from the agreed architecture.")
        out(f"        (capacity {handoff.capacity['state']}: {handoff.capacity['uncertainty'][0]})")
        scenario.turn_scripts.append([{"kind": "delta", "text": "Implemented export_csv and tests (simulated)."}, {"kind": "completed", "status": "completed"}])
        coordinator.run(handoff.job_id)
        ui._end_stream()
    again = coordinator.finalise_architecture(arch.thread_id, acceptance=AcceptanceEvidence(source="finalise_command", reference="demo", text="/finalise"))
    out(f"Router: repeated finalise → {again.status} (still one implementation thread)")
    summary["handoff"] = {"status": handoff.status, "role": handoff.role.value if handoff.role else None, "model": handoff.model_id, "repeat": again.status}

    out("")
    note = turn("Portfolio", "Format my private notes into bullet points.")
    summary["routine"] = {"role": note.role.value if note.role else None, "model": note.model_id}
    override = coordinator.override_model(note.thread_id, "sim-sol-1", reason="personal preference")
    out(f"Router: Model changed for this chat: {override.old_model} → {override.new_model} (reason: {override.reason.value}). Saved.")

    out("")
    out("— Included usage runs out —")
    scenario.ordinary_usage_allowed = False
    scenario.buckets[0]["resets_at"] = "2026-09-25T18:00:00Z"
    queued = turn("Portfolio", "Implement the CSV import button per the agreed architecture.")
    summary["queued_state"] = queued.state.value
    out("— Included usage is restored (the owner, not the router, handled any reset) —")
    scenario.ordinary_usage_allowed = True
    woke = coordinator.wake()
    ui._end_stream()
    summary["after_wake"] = [state.value for _, state in woke]
    out(f"Router: resumed on the same model: {coordinator.store.thread(queued.thread_id)['pinned_model']}")

    out("")
    out("— Crash after sending, before the acknowledgement was saved —")
    scenario.crash_at = "after_send_before_ack"
    crash = coordinator.submit("Portfolio", "Summarize this meeting transcript.")
    try:
        coordinator.run(crash.job_id)
    except SimulatedCrash:
        out("Router: (process died)")
    restarted = Coordinator(store, adapter, live=False, ui=ui)
    restarted.start()
    report = restarted.recover()
    sends = sum(1 for s in adapter.sent_turns if s["dispatch_id"].startswith("dsp_"))
    out(f"Router: recovery → {report[-1]['action']} ({report[-1]['state']}); provider sends so far: {sends} (no blind resend)")
    summary["recovery"] = report

    out("")
    out("— Narrow downgrade: synthetic, owner-validated calibration + tight usage —")
    calibration = CalibrationArtifact(
        model_id="sim-sol-1", reasoning_effort="medium", plan_type="plus", bucket_ids=["codex"], forecast_low=30.0, forecast_high=45.0,
        observation_ids=["synthetic-1"], validated=True, approval_id="demo-approval", synthetic=True,
    )
    scenario.buckets[0]["used_percent"] = 90.0
    restarted.estimator = CapacityEstimator([calibration])
    restarted.gate.check(None, thread_account_scope=None)  # fresh usage snapshot
    arch2 = turn(
        "Portfolio",
        "Review the architecture for a settings-page label rename.",
        script=[{"kind": "delta", "text": "```architecture-record\n" + json.dumps(ARCH_RECORD | {"goal": "Rename settings label"}) + "\n```"},
                {"kind": "completed", "status": "completed"}],
    )
    small = restarted.finalise_architecture(arch2.thread_id, acceptance=AcceptanceEvidence(source="finalise_command", reference="demo-2", text="/finalise"))
    if small.role is Role.LOWEST:
        out("Router: Using the approved lower model for this new coding chat:")
        out("the steps are clear, the work is low risk, and included usage looks tight.")
    summary["downgrade"] = {"role": small.role.value if small.role else None, "capacity": small.capacity["state"] if small.capacity else None}

    out("")
    evaluation = run_offline(store)
    out(f"Offline evaluation: {evaluation['passed']} cases passed, {len(evaluation['failed'])} failed; judge self-check usable={evaluation['judge_self_check']['usable']}")
    week = iso_week(utc_now())
    weekly = weekly_report(store, week, include_synthetic=True)
    out("")
    out(render_markdown(weekly).split("## Proposed")[0].rstrip())
    summary["evaluation"] = {"passed": evaluation["passed"], "failed": len(evaluation["failed"])}
    summary["weekly_guardrail"] = weekly["guardrail"]
    summary["spend_note"] = f"simulator spend status {SpendStatus.ALLOWED_INCLUDED_ONLY.value} is synthetic and cannot authorise live sends"
    restarted.close()
    coordinator.close()
    store.close()
    return summary
