"""Normalised subscription-adapter interface.

The router core depends only on these types, never on a provider wire format.
An unsupported operation raises ``UnsupportedOperation``; there are no
pass-through TODOs that pretend to succeed.
"""

from __future__ import annotations

import abc
import dataclasses
from dataclasses import dataclass, field
from typing import Any, Callable, Iterator

from ..contracts import Binding, ModelInfo, SpendDecision, TurnStatus, UsageSnapshot


class AdapterError(RuntimeError):
    """Provider/transport failure. ``executed`` says what is known about execution."""

    def __init__(self, message: str, *, executed: str = "unknown", code: str | None = None) -> None:
        super().__init__(message)
        self.executed = executed  # "no" | "unknown" | "yes"
        self.code = code


class UnsupportedOperation(AdapterError):
    def __init__(self, message: str) -> None:
        super().__init__(message, executed="no", code="unsupported")


class DispatchUncertain(AdapterError):
    """The request may or may not have reached the provider."""

    def __init__(self, message: str) -> None:
        super().__init__(message, executed="unknown", code="uncertain")


@dataclass
class AdapterCapabilities:
    adapter: str
    adapter_version: str
    protocol: str
    synthetic: bool
    operations: dict[str, str]  # name -> "supported" | "unsupported" | "unverified"
    tools: dict[str, str]  # web_search/edit/shell -> status
    pin: dict[str, Any] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


@dataclass
class AccountState:
    authenticated: bool
    auth_mode: str | None  # "chatgpt" | "apiKey" | "amazonBedrock" | None
    account_scope: str | None  # stable local fingerprint of the account/workspace
    plan_type: str | None
    config_ok: bool
    config_problems: list[str]
    synthetic: bool
    observed_at: str
    raw_redacted: dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelCatalogue:
    models: list[ModelInfo]
    observed_at: str
    synthetic: bool
    complete: bool = True


@dataclass
class ProviderThread:
    provider_thread_id: str
    model_id: str | None
    reasoning_effort: str | None
    raw_redacted: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProviderTurnRecord:
    provider_turn_id: str
    status: TurnStatus
    client_message_id: str | None
    text: str | None
    error: str | None = None


@dataclass
class ProviderThreadState:
    provider_thread_id: str
    model_id: str | None
    status: str
    turns: list[ProviderTurnRecord]


@dataclass
class ApprovalRequest:
    kind: str  # "command" | "file_change" | "permissions" | "user_input" | "other"
    summary: str
    command: str | None
    cwd: str | None
    paths: list[str]
    raw_method: str


@dataclass
class TurnEvent:
    kind: str
    # "acknowledged" | "delta" | "warning" | "error" | "rerouted" | "usage_changed"
    # | "account_changed" | "approval" | "item" | "completed"
    text: str | None = None
    provider_turn_id: str | None = None
    status: TurnStatus | None = None
    error: str | None = None
    error_code: str | None = None
    will_retry: bool | None = None
    fatal: bool = False
    from_model: str | None = None
    to_model: str | None = None
    item: dict[str, Any] | None = None
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        out = dataclasses.asdict(self)
        if self.status is not None:
            out["status"] = self.status.value
        return out


ApprovalHandler = Callable[[ApprovalRequest], str]  # returns "accept" | "decline" | "cancel"


class SubscriptionAdapter(abc.ABC):
    name = "abstract"

    @abc.abstractmethod
    def initialise(self) -> AdapterCapabilities: ...

    @abc.abstractmethod
    def read_account(self) -> AccountState: ...

    @abc.abstractmethod
    def list_models(self) -> ModelCatalogue: ...

    @abc.abstractmethod
    def read_usage(self) -> UsageSnapshot: ...

    @abc.abstractmethod
    def check_spend_boundary(self, account: AccountState, usage: UsageSnapshot) -> SpendDecision: ...

    @abc.abstractmethod
    def create_thread(
        self, binding: Binding, *, developer_instructions: str | None, workspace: str | None, sandbox: str
    ) -> ProviderThread: ...

    @abc.abstractmethod
    def read_thread(self, provider_thread_id: str) -> ProviderThreadState: ...

    @abc.abstractmethod
    def resume_thread(self, provider_thread_id: str, expected: Binding, *, workspace: str | None, sandbox: str) -> ProviderThread: ...

    @abc.abstractmethod
    def start_turn(
        self,
        provider_thread_id: str,
        text: str,
        dispatch_id: str,
        *,
        binding: Binding,
        approval_handler: ApprovalHandler,
        on_sent: Callable[[], None] | None = None,
    ) -> Iterator[TurnEvent]: ...

    @abc.abstractmethod
    def interrupt_turn(self, provider_thread_id: str, provider_turn_id: str) -> dict[str, Any]: ...

    @abc.abstractmethod
    def close(self) -> dict[str, Any]: ...
