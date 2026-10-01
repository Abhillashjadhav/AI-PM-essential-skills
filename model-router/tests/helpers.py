"""Shared synthetic test harness. No network, no account, no model call."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from model_router.adapters.base import ApprovalRequest  # noqa: E402
from model_router.adapters.fake import FakeAdapter, FakeScenario  # noqa: E402
from model_router.contracts import Role  # noqa: E402
from model_router.coordinator import Coordinator, RouterUI  # noqa: E402
from model_router.registry import mapping_hash_for  # noqa: E402
from model_router.store import Store  # noqa: E402

FAKE_CODEX = ROOT / "tests" / "fakes" / "fake_codex.py"
BINDINGS = ((Role.HIGHEST, "sim-astra-1", "high"), (Role.MIDDLE, "sim-sol-1", "medium"), (Role.LOWEST, "sim-luna-1", "low"))

ARCH_RECORD = {
    "goal": "Add CSV export to the reports page",
    "scope": "Export the visible table as CSV",
    "decisions": [{"title": "CSV only", "status": "decided"}],
    "constraints": ["no new dependencies"],
    "components": [{"name": "exporter"}],
    "interfaces": [{"name": "export_csv", "contract": "rows -> str"}],
    "files": ["app/export.py", "tests/test_export.py"],
    "steps": [{"description": "write export_csv"}, {"description": "add the button"}],
    "risks": [],
    "tests": [{"name": "empty", "check": "export_csv([]) == ''"}],
    "blocking_questions": [],
}


class RecordingUI(RouterUI):
    def __init__(self, approval: str = "decline") -> None:
        self.notices: list[str] = []
        self.streamed: list[str] = []
        self.approvals: list[ApprovalRequest] = []
        self.approval = approval

    def notify(self, text: str) -> None:
        self.notices.append(text)

    def stream(self, text: str) -> None:
        self.streamed.append(text)

    def ask_approval(self, request: ApprovalRequest) -> str:
        self.approvals.append(request)
        return self.approval


class RouterTestCase(unittest.TestCase):
    """Fresh store + simulator + coordinator with approved synthetic bindings."""

    approve = BINDINGS
    live = False

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="router-test-")
        self.tmp = Path(self._tmp.name)
        self.store = Store(self.tmp / "data")
        self.scenario = FakeScenario()
        self.adapter = FakeAdapter(self.scenario)
        self.ui = RecordingUI()
        self.coordinator = self.make_coordinator()
        self.coordinator.start()
        self.account = self.coordinator.account_scope
        for role, model, effort in self.approve:
            self.coordinator.registry.approve_mapping(
                self.account, role, model, effort, actor="test-owner", confirm_hash=mapping_hash_for(self.account, role, model, effort)
            )
        self.project_dir = self.tmp / "project"
        self.project_dir.mkdir()
        self.coordinator.add_project("Portfolio", str(self.project_dir))

    def tearDown(self) -> None:
        self.coordinator.close()
        self.store.close()
        self._tmp.cleanup()

    def make_coordinator(self, **kwargs) -> Coordinator:
        return Coordinator(self.store, self.adapter, live=self.live, ui=self.ui, **kwargs)

    # conveniences ---------------------------------------------------------

    def submit_and_run(self, text: str, *, script: list | None = None, thread_id: str | None = None):
        if script is not None:
            self.scenario.turn_scripts.append(script)
        result = self.coordinator.submit("Portfolio", text, thread_id=thread_id)
        state = self.coordinator.run(result.job_id) if result.job_id else None
        return result, state

    def architecture_thread(self, record: dict | None = None, prose_prefix: str = "Architecture:\n") -> str:
        block = "```architecture-record\n" + json.dumps(record or ARCH_RECORD) + "\n```"
        result, state = self.submit_and_run(
            "Review this product architecture for CSV export.",
            script=[{"kind": "delta", "text": prose_prefix + block}, {"kind": "completed", "status": "completed"}],
        )
        self.assertEqual(state.value, "SUCCEEDED")
        return result.thread_id

    def job_state(self, job_id: str) -> str:
        return self.store.job(job_id)["state"]

    def events(self, event_type: str) -> list[dict]:
        return self.store.events(event_type=event_type)
