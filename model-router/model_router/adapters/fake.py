"""In-process simulator adapter for the demo and offline tests.

Every value it returns is marked ``synthetic``. A synthetic spend decision can
never authorise a live dispatch (the eligibility gate rejects it in live mode).
"""

from __future__ import annotations

import itertools
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterator

from ..contracts import (
    Binding,
    CreditsState,
    ModelInfo,
    SpendDecision,
    SpendStatus,
    TurnStatus,
    UsageBucket,
    UsageSnapshot,
    new_id,
    utc_now,
)
from .base import (
    AccountState,
    AdapterCapabilities,
    AdapterError,
    ApprovalHandler,
    ApprovalRequest,
    ModelCatalogue,
    ProviderThread,
    ProviderThreadState,
    ProviderTurnRecord,
    SubscriptionAdapter,
    TurnEvent,
    UnsupportedOperation,
)

SYNTHETIC_MODELS = (
    ModelInfo(
        model_id="sim-astra-1",
        display_name="Simulated Astra (highest)",
        provider="simulator",
        reasoning_efforts=["medium", "high"],
        default_effort="high",
        input_modalities=["text"],
    ),
    ModelInfo(
        model_id="sim-sol-1",
        display_name="Simulated Sol (middle)",
        provider="simulator",
        reasoning_efforts=["low", "medium"],
        default_effort="medium",
        input_modalities=["text"],
    ),
    ModelInfo(
        model_id="sim-luna-1",
        display_name="Simulated Luna (low-tier candidate)",
        provider="simulator",
        reasoning_efforts=["low"],
        default_effort="low",
        input_modalities=["text"],
    ),
)


class SimulatedCrash(BaseException):
    """Stands in for process death. Deliberately not an ``Exception``."""


@dataclass
class FakeScenario:
    auth_mode: str | None = "chatgpt"
    account_id: str = "sim-account-1"
    plan_type: str | None = "plus"
    config_ok: bool = True
    config_problems: list[str] = field(default_factory=list)
    models: list[ModelInfo] = field(default_factory=lambda: list(SYNTHETIC_MODELS))
    ordinary_usage_allowed: bool | None = True
    buckets: list[dict[str, Any]] = field(
        default_factory=lambda: [
            {"limit_id": "codex", "label": "Codex usage", "used_percent": 20.0, "window_minutes": 300, "resets_at": None}
        ]
    )
    credits: dict[str, Any] | None = None  # None = not reported
    spend_status: SpendStatus = SpendStatus.ALLOWED_INCLUDED_ONLY
    reset_offers: int | None = None
    tools: dict[str, str] = field(default_factory=lambda: {"edit": "supported", "shell": "supported", "web_search": "unsupported"})
    turn_scripts: list[list[dict[str, Any]]] = field(default_factory=list)
    crash_at: str | None = None  # "before_send" | "after_send_before_ack" | "create_thread_after_send"
    echo_client_id: bool = True
    resume_model: str | None = None  # simulate provider changing model on resume
    create_thread_error: str | None = None


class FakeAdapter(SubscriptionAdapter):
    name = "simulator"

    def __init__(
        self,
        scenario: FakeScenario | None = None,
        *,
        delta_hook: Callable[[str], None] | None = None,
        state_path: str | None = None,
    ) -> None:
        self.scenario = scenario or FakeScenario()
        self.state_path = state_path
        self.threads: dict[str, dict[str, Any]] = self._load_state()
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.sent_turns: list[dict[str, Any]] = []
        self._ids = itertools.count(1 + sum(1 + len(t["turns"]) for t in self.threads.values()))
        self.delta_hook = delta_hook
        self.closed = False

    # -- helpers ---------------------------------------------------------------

    def _load_state(self) -> dict[str, dict[str, Any]]:
        if not self.state_path or not os.path.exists(self.state_path):
            return {}
        data = json.loads(open(self.state_path, encoding="utf-8").read())
        for thread in data.values():
            for turn in thread["turns"]:
                turn["status"] = TurnStatus(turn["status"])
        return data

    def _save_state(self) -> None:
        if not self.state_path:
            return
        from ..store import atomic_write

        payload = {
            key: {**value, "turns": [{**t, "status": TurnStatus(t["status"]).value} for t in value["turns"]]}
            for key, value in self.threads.items()
        }
        atomic_write(Path(self.state_path), json.dumps(payload))

    def _log(self, name: str, **data: Any) -> None:
        self.calls.append((name, data))

    @property
    def model_sends(self) -> int:
        return len(self.sent_turns)

    # -- interface -------------------------------------------------------------

    def initialise(self) -> AdapterCapabilities:
        self._log("initialise")
        return AdapterCapabilities(
            adapter="simulator",
            adapter_version="sim-1",
            protocol="in-process",
            synthetic=True,
            operations={name: "supported" for name in (
                "read_account", "list_models", "read_usage", "create_thread", "read_thread",
                "resume_thread", "start_turn", "interrupt_turn",
            )},
            tools=dict(self.scenario.tools),
            notes=["SIMULATED: no provider is contacted; answers are synthetic"],
        )

    def read_account(self) -> AccountState:
        self._log("read_account")
        s = self.scenario
        return AccountState(
            authenticated=s.auth_mode is not None,
            auth_mode=s.auth_mode,
            account_scope=f"sim:{s.account_id}" if s.auth_mode else None,
            plan_type=s.plan_type,
            config_ok=s.config_ok,
            config_problems=list(s.config_problems),
            synthetic=True,
            observed_at=utc_now(),
        )

    def list_models(self) -> ModelCatalogue:
        self._log("list_models")
        return ModelCatalogue(models=list(self.scenario.models), observed_at=utc_now(), synthetic=True)

    def read_usage(self) -> UsageSnapshot:
        self._log("read_usage")
        s = self.scenario
        credits = (
            CreditsState(has_credits=None, unlimited=None, balance=None, reported=False)
            if s.credits is None
            else CreditsState(
                has_credits=s.credits.get("has_credits"),
                unlimited=s.credits.get("unlimited"),
                balance=s.credits.get("balance"),
                reported=True,
            )
        )
        return UsageSnapshot(
            id=new_id("use"),
            account_scope=f"sim:{s.account_id}" if s.auth_mode else None,
            plan_type=s.plan_type,
            schema_version="simulator",
            buckets=[UsageBucket(**b) for b in s.buckets],
            credits=credits,
            ordinary_usage_allowed=s.ordinary_usage_allowed,
            spend_control_reached=None,
            reset_offer_available=s.reset_offers,
            observed_at=utc_now(),
            source="simulator",
            synthetic=True,
        )

    def check_spend_boundary(self, account: AccountState, usage: UsageSnapshot) -> SpendDecision:
        self._log("check_spend_boundary")
        status = self.scenario.spend_status
        return SpendDecision(
            status=status,
            reasons=[] if status is SpendStatus.ALLOWED_INCLUDED_ONLY else [f"simulated spend status {status.value}"],
            evidence=[{"source": "synthetic", "detail": "simulator-declared spend boundary; cannot certify a live adapter"}],
            account_scope=account.account_scope,
            decided_at=utc_now(),
            synthetic=True,
        )

    def create_thread(self, binding: Binding, *, developer_instructions: str | None, workspace: str | None, sandbox: str) -> ProviderThread:
        self._log("create_thread", model=binding.model_id, sandbox=sandbox, workspace=workspace)
        if sandbox == "danger-full-access":
            raise AdapterError("refusing danger-full-access", executed="no")
        if self.scenario.create_thread_error:
            raise AdapterError(self.scenario.create_thread_error, executed="no")
        thread_id = f"sim-thread-{next(self._ids)}"
        self.threads[thread_id] = {
            "model": binding.model_id,
            "effort": binding.reasoning_effort,
            "turns": [],
            "instructions": developer_instructions,
        }
        self._save_state()
        if self.scenario.crash_at == "create_thread_after_send":
            self.scenario.crash_at = None
            raise SimulatedCrash("crash after thread/start was sent")
        return ProviderThread(provider_thread_id=thread_id, model_id=binding.model_id, reasoning_effort=binding.reasoning_effort)

    def read_thread(self, provider_thread_id: str) -> ProviderThreadState:
        self._log("read_thread", thread=provider_thread_id)
        thread = self.threads.get(provider_thread_id)
        if thread is None:
            raise AdapterError(f"unknown provider thread {provider_thread_id}", executed="no")
        return ProviderThreadState(
            provider_thread_id=provider_thread_id,
            model_id=thread["model"],
            status="idle",
            turns=[
                ProviderTurnRecord(
                    provider_turn_id=t["id"],
                    status=t["status"],
                    client_message_id=t["client_id"] if self.scenario.echo_client_id else None,
                    text=t["text"],
                )
                for t in thread["turns"]
            ],
        )

    def resume_thread(self, provider_thread_id: str, expected: Binding, *, workspace: str | None, sandbox: str) -> ProviderThread:
        self._log("resume_thread", thread=provider_thread_id, model=expected.model_id)
        thread = self.threads.get(provider_thread_id)
        if thread is None:
            raise AdapterError(f"unknown provider thread {provider_thread_id}", executed="no")
        model = self.scenario.resume_model or expected.model_id
        return ProviderThread(provider_thread_id=provider_thread_id, model_id=model, reasoning_effort=expected.reasoning_effort)

    def start_turn(
        self,
        provider_thread_id: str,
        text: str,
        dispatch_id: str,
        *,
        binding: Binding,
        approval_handler: ApprovalHandler,
        on_sent: Callable[[], None] | None = None,
    ) -> Iterator[TurnEvent]:
        thread = self.threads.get(provider_thread_id)
        if thread is None:
            raise AdapterError(f"unknown provider thread {provider_thread_id}", executed="no")
        if self.scenario.crash_at == "before_send":
            self.scenario.crash_at = None
            raise SimulatedCrash("crash before send")
        turn_id = f"sim-turn-{next(self._ids)}"
        script = self.scenario.turn_scripts.pop(0) if self.scenario.turn_scripts else None
        turn = {"id": turn_id, "client_id": dispatch_id, "status": TurnStatus.IN_PROGRESS, "text": ""}
        thread["turns"].append(turn)
        self.sent_turns.append({"thread": provider_thread_id, "dispatch_id": dispatch_id, "model": binding.model_id, "text": text})
        self._log("start_turn", thread=provider_thread_id, dispatch_id=dispatch_id, model=binding.model_id)
        if on_sent:
            on_sent()
        if self.scenario.crash_at == "after_send_before_ack":
            self.scenario.crash_at = None
            turn["status"] = TurnStatus.COMPLETED
            turn["text"] = "(answer produced while the router was down)"
            raise SimulatedCrash("crash after send, before acknowledgement was saved")
        return self._run_script(turn, binding, text, script, approval_handler)

    def _run_script(self, turn, binding, text, script, approval_handler) -> Iterator[TurnEvent]:
        yield TurnEvent(kind="acknowledged", provider_turn_id=turn["id"])
        if script is None:
            answer = f"[SIMULATED {binding.model_id}] Answer for: {text.strip().splitlines()[0][:80] if text.strip() else '(empty)'}"
            script = [{"kind": "delta", "text": chunk} for chunk in _chunks(answer)] + [
                {"kind": "completed", "status": "completed"}
            ]
        for step in script:
            kind = step["kind"]
            if kind == "delta":
                turn["text"] += step["text"]
                yield TurnEvent(kind="delta", text=step["text"], provider_turn_id=turn["id"])
            elif kind == "approval":
                request = ApprovalRequest(
                    kind=step.get("approval_kind", "command"),
                    summary=step.get("summary", ""),
                    command=step.get("command"),
                    cwd=step.get("cwd"),
                    paths=step.get("paths", []),
                    raw_method="simulated",
                )
                decision = approval_handler(request)
                yield TurnEvent(kind="approval", text=request.summary, data={"decision": decision, "command": request.command, "paths": request.paths})
            elif kind == "warning":
                yield TurnEvent(kind="warning", text=step.get("text"), provider_turn_id=turn["id"], fatal=False)
            elif kind == "error":
                yield TurnEvent(
                    kind="error",
                    error=step.get("text", "error"),
                    error_code=step.get("code"),
                    will_retry=step.get("will_retry", False),
                    fatal=not step.get("will_retry", False),
                    provider_turn_id=turn["id"],
                )
            elif kind == "rerouted":
                yield TurnEvent(kind="rerouted", from_model=binding.model_id, to_model=step["to_model"], provider_turn_id=turn["id"])
            elif kind == "usage_changed":
                yield TurnEvent(kind="usage_changed", data=step.get("data", {}))
            elif kind == "item":
                yield TurnEvent(kind="item", item=step["item"], provider_turn_id=turn["id"])
            elif kind == "completed":
                status = TurnStatus(step.get("status", "completed"))
                turn["status"] = status
                self._save_state()
                yield TurnEvent(kind="completed", status=status, provider_turn_id=turn["id"], error=step.get("error"))
                return
            else:
                raise UnsupportedOperation(f"unknown simulated step {kind}")
        turn["status"] = TurnStatus.UNKNOWN

    def interrupt_turn(self, provider_thread_id: str, provider_turn_id: str) -> dict[str, Any]:
        self._log("interrupt_turn", thread=provider_thread_id, turn=provider_turn_id)
        return {"interrupted": True, "synthetic": True}

    def close(self) -> dict[str, Any]:
        self.closed = True
        return {"closed": True}


def _chunks(text: str, size: int = 24) -> list[str]:
    return [text[i : i + size] for i in range(0, len(text), size)] or [""]
