"""Typed, versioned domain contracts for the model router.

Everything that crosses a module boundary or is persisted is one of these
dataclasses/enums. ``validate`` methods reject invalid states instead of
coercing them; ``to_dict``/``from_dict`` give a stable JSON shape.
"""

from __future__ import annotations

import dataclasses
import enum
import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Mapping

CONTRACT_VERSION = "1.0"
POLICY_VERSION = "policy-2026-09-25.1"
CLASSIFIER_VERSION = "rules-2026-09-25.1"
EVENT_SCHEMA_VERSION = "1"
REPORT_SCHEMA_VERSION = "weekly-report.1"
HANDOFF_SCHEMA_VERSION = "handoff.1"
ARCHITECTURE_SCHEMA_VERSION = "architecture-record.1"
CAPACITY_METHOD_VERSION = "capacity-range.1"


class ContractError(ValueError):
    """Raised when a contract instance or payload is invalid."""


# ---------------------------------------------------------------------------
# helpers


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def parse_utc(value: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise ContractError(f"expected UTC timestamp string, got {value!r}")
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ContractError(f"invalid timestamp {value!r}") from exc
    if parsed.tzinfo is None:
        raise ContractError(f"timestamp must carry a UTC offset: {value!r}")
    return parsed.astimezone(timezone.utc)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:20]}"


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def content_hash(value: Any) -> str:
    """Integrity reference for a JSON-able value. Not anonymisation."""
    return sha256_text(canonical_json(value))


def _enum_value(value: Any) -> Any:
    if isinstance(value, enum.Enum):
        return value.value
    if isinstance(value, (list, tuple)):
        return [_enum_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _enum_value(item) for key, item in value.items()}
    return value


def _coerce_enum(enum_type: type[enum.Enum], value: Any, field: str) -> enum.Enum:
    if isinstance(value, enum_type):
        return value
    try:
        return enum_type(value)
    except ValueError as exc:
        allowed = ", ".join(member.value for member in enum_type)
        raise ContractError(f"{field}: {value!r} is not one of [{allowed}]") from exc


def _require_str(value: Any, field: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise ContractError(f"{field}: expected string, got {type(value).__name__}")
    if not allow_empty and not value.strip():
        raise ContractError(f"{field}: must not be empty")
    return value


def _require_list_of_str(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ContractError(f"{field}: expected list of strings")
    return value


class Record:
    """Mixin: dataclass JSON round trip with enum coercion and validation."""

    def to_dict(self) -> dict[str, Any]:
        return {field.name: _enum_value(getattr(self, field.name)) for field in dataclasses.fields(self)}  # type: ignore[arg-type]

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]):  # type: ignore[no-untyped-def]
        if not isinstance(payload, Mapping):
            raise ContractError(f"{cls.__name__}: expected object")
        names = {field.name for field in dataclasses.fields(cls)}  # type: ignore[arg-type]
        missing = [
            field.name
            for field in dataclasses.fields(cls)  # type: ignore[arg-type]
            if field.name not in payload
            and field.default is dataclasses.MISSING
            and field.default_factory is dataclasses.MISSING  # type: ignore[misc]
        ]
        if missing:
            raise ContractError(f"{cls.__name__}: missing required fields {missing}")
        kwargs = {key: value for key, value in payload.items() if key in names}
        instance = cls(**kwargs)  # type: ignore[call-arg]
        instance.validate()
        return instance

    def validate(self) -> None:  # pragma: no cover - overridden
        return None


# ---------------------------------------------------------------------------
# enums


class Role(str, enum.Enum):
    HIGHEST = "highest"
    MIDDLE = "middle"
    LOWEST = "lowest"

    @property
    def rank(self) -> int:
        return {"lowest": 0, "middle": 1, "highest": 2}[self.value]

    @staticmethod
    def max(*roles: "Role") -> "Role":
        return max(roles, key=lambda role: role.rank)

    @property
    def plain(self) -> str:
        return {"highest": "Highest", "middle": "Middle", "lowest": "Lowest"}[self.value]


class TaskKind(str, enum.Enum):
    ARCHITECTURE = "architecture"
    PRODUCT_DECISION = "product_decision"
    UI_DECISION = "ui_decision"
    TRADEOFF = "tradeoff"
    HIGH_CREDIBILITY_WRITING = "high_credibility_writing"
    CONSEQUENTIAL_ASSESSMENT = "consequential_assessment"
    HIGH_RISK_CODING = "high_risk_coding"
    IMPLEMENTATION = "implementation"
    ROUTINE_TEXT = "routine_text"
    RESOURCE_EXTRACTION = "resource_extraction"
    UNKNOWN = "unknown"


class RiskFlag(str, enum.Enum):
    MONEY_MOVEMENT = "money_movement"
    PRIVACY = "privacy"
    SECURITY = "security"
    DESTRUCTIVE = "destructive"
    PRODUCTION = "production"
    HIGH_CREDIBILITY = "high_credibility"


class Urgency(str, enum.Enum):
    NOW = "now"
    NORMAL = "normal"
    LATER = "later"


class JobState(str, enum.Enum):
    DRAFT = "DRAFT"
    ROUTING = "ROUTING"
    AWAITING_MANUAL_MODEL = "AWAITING_MANUAL_MODEL"
    SELECTED = "SELECTED"
    BLOCKED_AUTH = "BLOCKED_AUTH"
    BLOCKED_SPEND = "BLOCKED_SPEND"
    BLOCKED_CAPABILITY = "BLOCKED_CAPABILITY"
    WAITING_USAGE = "WAITING_USAGE"
    READY = "READY"
    DISPATCHING = "DISPATCHING"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


TERMINAL_JOB_STATES = frozenset({JobState.SUCCEEDED, JobState.FAILED, JobState.CANCELLED})
WAITING_JOB_STATES = frozenset(
    {
        JobState.BLOCKED_AUTH,
        JobState.BLOCKED_SPEND,
        JobState.BLOCKED_CAPABILITY,
        JobState.WAITING_USAGE,
        JobState.PAUSED,
    }
)

# Allowed transitions. Guards beyond the table live in ``check_transition``.
JOB_TRANSITIONS: dict[JobState, frozenset[JobState]] = {
    JobState.DRAFT: frozenset({JobState.ROUTING, JobState.SELECTED, JobState.CANCELLED}),
    JobState.ROUTING: frozenset({JobState.SELECTED, JobState.AWAITING_MANUAL_MODEL, JobState.CANCELLED}),
    JobState.AWAITING_MANUAL_MODEL: frozenset({JobState.SELECTED, JobState.CANCELLED}),
    JobState.SELECTED: frozenset(
        {
            JobState.READY,
            JobState.BLOCKED_AUTH,
            JobState.BLOCKED_SPEND,
            JobState.BLOCKED_CAPABILITY,
            JobState.WAITING_USAGE,
            JobState.CANCELLED,
        }
    ),
    JobState.READY: frozenset(
        {
            JobState.DISPATCHING,
            JobState.BLOCKED_AUTH,
            JobState.BLOCKED_SPEND,
            JobState.BLOCKED_CAPABILITY,
            JobState.WAITING_USAGE,
            JobState.CANCELLED,
        }
    ),
    JobState.DISPATCHING: frozenset(
        {
            JobState.RUNNING,
            JobState.PAUSED,
            JobState.RECOVERY_REQUIRED,
            JobState.FAILED,
            JobState.BLOCKED_AUTH,
            JobState.BLOCKED_SPEND,
            JobState.BLOCKED_CAPABILITY,
            JobState.WAITING_USAGE,
        }
    ),
    JobState.RUNNING: frozenset(
        {
            JobState.SUCCEEDED,
            JobState.FAILED,
            JobState.PAUSED,
            JobState.RECOVERY_REQUIRED,
            JobState.CANCELLED,
        }
    ),
    JobState.PAUSED: frozenset(
        {
            JobState.READY,
            JobState.WAITING_USAGE,
            JobState.BLOCKED_AUTH,
            JobState.BLOCKED_SPEND,
            JobState.BLOCKED_CAPABILITY,
            JobState.CANCELLED,
        }
    ),
    JobState.RECOVERY_REQUIRED: frozenset(
        {
            JobState.RUNNING,
            JobState.SUCCEEDED,
            JobState.FAILED,
            JobState.PAUSED,
            JobState.READY,
            JobState.CANCELLED,
        }
    ),
    JobState.SUCCEEDED: frozenset(),
    JobState.FAILED: frozenset(),
    JobState.CANCELLED: frozenset(),
}
for _waiting in (JobState.BLOCKED_AUTH, JobState.BLOCKED_SPEND, JobState.BLOCKED_CAPABILITY, JobState.WAITING_USAGE):
    JOB_TRANSITIONS[_waiting] = frozenset(
        {
            JobState.READY,
            JobState.BLOCKED_AUTH,
            JobState.BLOCKED_SPEND,
            JobState.BLOCKED_CAPABILITY,
            JobState.WAITING_USAGE,
            JobState.CANCELLED,
        }
    )


class InvalidTransition(ContractError):
    pass


def check_transition(
    current: JobState,
    target: JobState,
    *,
    manual: bool = False,
    eligibility_passed: bool = False,
    owner_confirmed_not_executed: bool = False,
) -> None:
    """Raise ``InvalidTransition`` unless the transition is permitted.

    * Only an explicit manual choice leaves AWAITING_MANUAL_MODEL.
    * Entering READY requires a passing eligibility check.
    * RECOVERY_REQUIRED may return to READY only when the owner confirmed the
      uncertain operation did not execute.
    """
    current = JobState(current)
    target = JobState(target)
    if target not in JOB_TRANSITIONS[current]:
        raise InvalidTransition(f"job transition {current.value} -> {target.value} is not allowed")
    if current is JobState.AWAITING_MANUAL_MODEL and target is JobState.SELECTED and not manual:
        raise InvalidTransition("only an explicit manual model choice can leave AWAITING_MANUAL_MODEL")
    if target is JobState.READY and not eligibility_passed:
        raise InvalidTransition(f"{current.value} -> READY requires a passing eligibility check")
    if (
        current is JobState.RECOVERY_REQUIRED
        and target in {JobState.READY, JobState.PAUSED}
        and not owner_confirmed_not_executed
    ):
        raise InvalidTransition(f"RECOVERY_REQUIRED -> {target.value} requires owner confirmation that nothing executed")


class DispatchPhase(str, enum.Enum):
    PREPARED = "PREPARED"
    SENT = "SENT"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    UNCERTAIN = "UNCERTAIN"
    NOT_EXECUTED = "NOT_EXECUTED"
    TERMINAL = "TERMINAL"


class TurnStatus(str, enum.Enum):
    COMPLETED = "completed"
    INTERRUPTED = "interrupted"
    FAILED = "failed"
    IN_PROGRESS = "inProgress"
    PARTIAL = "partial"
    UNKNOWN = "unknown"


class CapacityState(str, enum.Enum):
    SUFFICIENT = "SUFFICIENT"
    TIGHT = "TIGHT"
    UNKNOWN = "UNKNOWN"


class SpendStatus(str, enum.Enum):
    ALLOWED_INCLUDED_ONLY = "ALLOWED_INCLUDED_ONLY"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"


class EvidenceStatus(str, enum.Enum):
    ENFORCED = "enforced"
    SUPPORTING = "supporting"
    UNKNOWN = "unknown"


class Clarity(str, enum.Enum):
    CLEAR_AND_SIMPLE = "CLEAR_AND_SIMPLE"
    UNCLEAR = "UNCLEAR"


class RiskLevel(str, enum.Enum):
    LOW_RISK = "LOW_RISK"
    HIGH_RISK = "HIGH_RISK"


class OutcomeKind(str, enum.Enum):
    RESOLVED = "resolved"
    PARTIAL = "partial"
    FAILED = "failed"
    ABANDONED = "abandoned"
    UNKNOWN = "unknown"


class OverrideReason(str, enum.Enum):
    ANSWER_QUALITY = "answer_quality"
    DIFFERENT_TASK = "different_task"
    PERSONAL_PREFERENCE = "personal_preference"
    UNKNOWN = "unknown"


class ModelStatus(str, enum.Enum):
    CANDIDATE = "candidate"
    APPROVED = "approved"
    RETIRED = "retired"


class ThreadKind(str, enum.Enum):
    ORDINARY = "ordinary"
    IMPLEMENTATION = "implementation"
    EVALUATION = "evaluation"
    IMPORTED = "imported"


class GateStatus(str, enum.Enum):
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    NOT_RUN = "NOT_RUN"


class GradeStatus(str, enum.Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    INCONCLUSIVE = "INCONCLUSIVE"
    BLOCKED = "BLOCKED"


# ---------------------------------------------------------------------------
# records


@dataclasses.dataclass
class Project(Record):
    id: str
    name: str
    root: str
    worktree: str | None = None
    write_scope: list[str] = dataclasses.field(default_factory=list)
    created_at: str = dataclasses.field(default_factory=utc_now)

    def validate(self) -> None:
        _require_str(self.id, "project.id")
        _require_str(self.name, "project.name")
        _require_str(self.root, "project.root")
        if not self.root.startswith("/"):
            raise ContractError("project.root must be an absolute canonical path")
        _require_list_of_str(self.write_scope, "project.write_scope")
        parse_utc(self.created_at)


@dataclasses.dataclass
class TaskAssessment(Record):
    id: str
    original_goal: str
    task_kind: TaskKind
    secondary_kinds: list[TaskKind]
    risk_flags: list[RiskFlag]
    priority: str | None
    urgency: Urgency | None
    ambiguous: bool
    uncertainty: list[str]
    evidence: list[str]
    reason_codes: list[str]
    policy_version: str = POLICY_VERSION
    classifier_version: str = CLASSIFIER_VERSION
    segment: int = 1

    def __post_init__(self) -> None:
        self.task_kind = _coerce_enum(TaskKind, self.task_kind, "task_kind")  # type: ignore[assignment]
        self.secondary_kinds = [_coerce_enum(TaskKind, k, "secondary_kinds") for k in self.secondary_kinds]  # type: ignore[misc]
        self.risk_flags = [_coerce_enum(RiskFlag, k, "risk_flags") for k in self.risk_flags]  # type: ignore[misc]
        if self.urgency is not None:
            self.urgency = _coerce_enum(Urgency, self.urgency, "urgency")  # type: ignore[assignment]

    def validate(self) -> None:
        _require_str(self.id, "assessment.id")
        _require_str(self.original_goal, "assessment.original_goal", allow_empty=True)
        if self.ambiguous and not self.uncertainty:
            raise ContractError("ambiguous assessment must state its uncertainty")
        if self.segment < 1:
            raise ContractError("assessment.segment must be >= 1")


@dataclasses.dataclass
class RouteDecision(Record):
    id: str
    request_id: str
    thread_id: str
    route_attempt_id: str
    role: Role | None
    candidate_id: str | None
    model_id: str | None
    reasoning_effort: str | None
    rule_ids: list[str]
    reasons: list[str]
    uncertainty: list[str]
    capacity_ref: str | None
    manual: bool
    missing_binding: bool
    created_at: str = dataclasses.field(default_factory=utc_now)
    timings_ms: dict[str, float] = dataclasses.field(default_factory=dict)
    policy_version: str = POLICY_VERSION

    def __post_init__(self) -> None:
        if self.role is not None:
            self.role = _coerce_enum(Role, self.role, "role")  # type: ignore[assignment]

    def validate(self) -> None:
        for name in ("id", "request_id", "thread_id", "route_attempt_id"):
            _require_str(getattr(self, name), f"route.{name}")
        if not self.manual and self.role is None:
            raise ContractError("automatic route decision needs a role")
        if self.model_id is None and not self.missing_binding:
            raise ContractError("route decision without model must be marked missing_binding")
        if not self.rule_ids and not self.manual:
            raise ContractError("automatic route decision needs rule ids")


@dataclasses.dataclass
class ModelInfo(Record):
    """An account-discovered provider model (never invented)."""

    model_id: str
    display_name: str
    provider: str
    reasoning_efforts: list[str]
    default_effort: str | None
    input_modalities: list[str]
    hidden: bool = False
    is_default: bool = False
    upgrade: str | None = None
    raw_ref: str | None = None

    def validate(self) -> None:
        _require_str(self.model_id, "model.model_id")
        _require_str(self.provider, "model.provider")
        _require_list_of_str(self.reasoning_efforts, "model.reasoning_efforts")
        if self.default_effort is not None and self.reasoning_efforts and self.default_effort not in self.reasoning_efforts:
            raise ContractError("model.default_effort must be one of reasoning_efforts")


@dataclasses.dataclass
class RoleMapping(Record):
    role: Role
    model_id: str
    reasoning_effort: str | None
    task_scope: list[str]
    tool_scope: list[str]
    evaluation_ids: list[str]
    approval_id: str
    account_scope: str
    family_label: str | None = None

    def __post_init__(self) -> None:
        self.role = _coerce_enum(Role, self.role, "role")  # type: ignore[assignment]

    def validate(self) -> None:
        _require_str(self.model_id, "mapping.model_id")
        _require_str(self.approval_id, "mapping.approval_id")
        _require_str(self.account_scope, "mapping.account_scope")
        _require_list_of_str(self.tool_scope, "mapping.tool_scope")

    def binding_hash(self) -> str:
        return content_hash(
            {
                "role": self.role.value,
                "model_id": self.model_id,
                "reasoning_effort": self.reasoning_effort,
                "task_scope": sorted(self.task_scope),
                "tool_scope": sorted(self.tool_scope),
                "evaluation_ids": sorted(self.evaluation_ids),
                "account_scope": self.account_scope,
            }
        )


@dataclasses.dataclass
class Binding(Record):
    """The exact model/settings a thread is pinned to."""

    role: Role | None
    model_id: str
    reasoning_effort: str | None
    registry_revision: int | None
    manual: bool = False

    def __post_init__(self) -> None:
        if self.role is not None:
            self.role = _coerce_enum(Role, self.role, "role")  # type: ignore[assignment]

    def validate(self) -> None:
        _require_str(self.model_id, "binding.model_id")

    def key(self) -> tuple[str, str | None]:
        return (self.model_id, self.reasoning_effort)


@dataclasses.dataclass
class UsageBucket(Record):
    limit_id: str
    label: str | None
    used_percent: float | None
    window_minutes: int | None
    resets_at: str | None
    applicable_models: list[str] | None = None
    reached_type: str | None = None

    def validate(self) -> None:
        _require_str(self.limit_id, "bucket.limit_id")
        if self.used_percent is not None and not (0 <= self.used_percent <= 100):
            raise ContractError("bucket.used_percent must be within 0..100")

    @property
    def remaining_percent(self) -> float | None:
        return None if self.used_percent is None else max(0.0, 100.0 - float(self.used_percent))


@dataclasses.dataclass
class CreditsState(Record):
    """Optional credit fields. ``None`` means not reported, never zero."""

    has_credits: bool | None
    unlimited: bool | None
    balance: str | None
    reported: bool

    def validate(self) -> None:
        if not self.reported and any(v is not None for v in (self.has_credits, self.unlimited, self.balance)):
            raise ContractError("unreported credits must not carry values")

    def describe(self) -> str:
        if not self.reported:
            return "credits: not reported (unknown)"
        return f"credits: hasCredits={self.has_credits} unlimited={self.unlimited} balance={self.balance if self.balance is not None else 'not reported'}"


# Workspace plans whose owners/admins can set per-member credit spend limits
# (ChatGPT Business / Enterprise / Edu spend controls). Personal plans have none.
WORKSPACE_PLAN_TYPES = frozenset(
    {
        "team",
        "business",
        "self_serve_business_prolite",
        "self_serve_business_usage_based",
        "enterprise",
        "ent26",
        "enterprise_cbp_automation",
        "enterprise_cbp_usage_based",
        "edu",
        "edu_plus",
        "edu_pro",
    }
)


@dataclasses.dataclass
class SpendControlObservation(Record):
    """A provider-reported spend control for one usage snapshot (read live)."""

    limit_id: str
    reached: bool | None
    limit: str | None
    used: str | None
    remaining_percent: int | None
    resets_at: str | None
    source: str | None = None

    def validate(self) -> None:
        _require_str(self.limit_id, "spend_control.limit_id")


@dataclasses.dataclass
class UsageSnapshot(Record):
    id: str
    account_scope: str | None
    plan_type: str | None
    schema_version: str
    buckets: list[UsageBucket]
    credits: CreditsState
    ordinary_usage_allowed: bool | None
    spend_control_reached: bool | None
    reset_offer_available: int | None
    observed_at: str
    source: str
    synthetic: bool
    spend_controls: list[SpendControlObservation] = dataclasses.field(default_factory=list)
    # limit ids whose snapshot carried a credits object (credits can apply there)
    credit_limit_ids: list[str] = dataclasses.field(default_factory=list)

    def __post_init__(self) -> None:
        self.buckets = [b if isinstance(b, UsageBucket) else UsageBucket.from_dict(b) for b in self.buckets]
        if not isinstance(self.credits, CreditsState):
            self.credits = CreditsState.from_dict(self.credits)
        self.spend_controls = [
            s if isinstance(s, SpendControlObservation) else SpendControlObservation.from_dict(s) for s in self.spend_controls
        ]

    def validate(self) -> None:
        _require_str(self.id, "usage.id")
        parse_utc(self.observed_at)
        for bucket in self.buckets:
            bucket.validate()
        self.credits.validate()

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["buckets"] = [b.to_dict() for b in self.buckets]
        data["credits"] = self.credits.to_dict()
        data["spend_controls"] = [s.to_dict() for s in self.spend_controls]
        return data

    def included_usage_available(self) -> bool | None:
        """True/False only when the provider reported it; None = unknown."""
        if self.ordinary_usage_allowed is False:
            return False
        if any(b.reached_type for b in self.buckets):
            return False
        if self.ordinary_usage_allowed is True:
            return True
        return None

    def earliest_reset(self) -> str | None:
        resets = sorted(b.resets_at for b in self.buckets if b.resets_at)
        return resets[0] if resets else None


@dataclasses.dataclass
class SpendEvidence(Record):
    id: str
    control_type: str
    scope: str
    source: str  # "live" | "synthetic" | "fixture" | "owner_attestation" | "screenshot"
    status: EvidenceStatus
    observed_at: str
    expires_at: str | None
    detail: str
    adapter_pin: str | None = None
    invalidated_at: str | None = None

    def __post_init__(self) -> None:
        self.status = _coerce_enum(EvidenceStatus, self.status, "status")  # type: ignore[assignment]

    def validate(self) -> None:
        _require_str(self.control_type, "spend_evidence.control_type")
        parse_utc(self.observed_at)
        if self.source in {"owner_attestation", "screenshot"} and self.status is EvidenceStatus.ENFORCED:
            raise ContractError("an attestation or screenshot can only be supporting evidence")


@dataclasses.dataclass
class SpendDecision(Record):
    status: SpendStatus
    reasons: list[str]
    evidence: list[dict[str, Any]]
    account_scope: str | None
    decided_at: str
    synthetic: bool
    missing: list[str] = dataclasses.field(default_factory=list)
    # The code-defined enforcement mechanism that justified ALLOWED (never free text).
    mechanism: str | None = None

    def __post_init__(self) -> None:
        self.status = _coerce_enum(SpendStatus, self.status, "status")  # type: ignore[assignment]

    def validate(self) -> None:
        parse_utc(self.decided_at)
        if self.status is SpendStatus.ALLOWED_INCLUDED_ONLY and not self.evidence:
            raise ContractError("ALLOWED_INCLUDED_ONLY requires evidence")
        if self.status is SpendStatus.ALLOWED_INCLUDED_ONLY and not self.synthetic and not self.mechanism:
            raise ContractError("a live ALLOWED_INCLUDED_ONLY decision must name the verified enforcement mechanism")
        if self.status is not SpendStatus.ALLOWED_INCLUDED_ONLY and not (self.reasons or self.missing):
            raise ContractError("a non-allowed spend decision must explain why")


@dataclasses.dataclass
class CapacityEstimate(Record):
    state: CapacityState
    buckets: list[str]
    observed_at: str | None
    plan_type: str | None
    account_scope: str | None
    forecast_low: float | None
    forecast_high: float | None
    method: str
    method_version: str
    observations: list[str]
    uncertainty: list[str]
    synthetic: bool = False
    label: str = "estimated"

    def __post_init__(self) -> None:
        self.state = _coerce_enum(CapacityState, self.state, "state")  # type: ignore[assignment]

    def validate(self) -> None:
        if self.label != "estimated":
            raise ContractError("capacity estimates are always labelled 'estimated'")
        if self.state is CapacityState.UNKNOWN and not self.uncertainty:
            raise ContractError("UNKNOWN capacity must state why")
        if self.state is not CapacityState.UNKNOWN and (self.forecast_low is None or self.forecast_high is None):
            raise ContractError("a SUFFICIENT/TIGHT estimate needs a forecast range")


ARCHITECTURE_REQUIRED_FIELDS = (
    "goal",
    "scope",
    "decisions",
    "constraints",
    "components",
    "interfaces",
    "files",
    "steps",
    "risks",
    "tests",
    "blocking_questions",
)


@dataclasses.dataclass
class ArchitectureRecord(Record):
    goal: str
    scope: str
    decisions: list[dict[str, Any]]
    constraints: list[str]
    components: list[dict[str, Any]]
    interfaces: list[dict[str, Any]]
    files: list[str]
    steps: list[dict[str, Any]]
    risks: list[dict[str, Any]]
    tests: list[dict[str, Any]]
    blocking_questions: list[str]
    nonblocking_items: list[str] = dataclasses.field(default_factory=list)
    repository: str | None = None
    self_assessed_simple: bool | None = None  # recorded, never trusted
    schema_version: str = ARCHITECTURE_SCHEMA_VERSION

    def validate(self) -> None:
        _require_str(self.goal, "architecture.goal")
        _require_str(self.scope, "architecture.scope")
        for name in ("decisions", "components", "interfaces", "steps", "risks", "tests"):
            value = getattr(self, name)
            if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
                raise ContractError(f"architecture.{name}: expected list of objects")
        for name in ("constraints", "files", "blocking_questions", "nonblocking_items"):
            _require_list_of_str(getattr(self, name), f"architecture.{name}")
        for index, risk in enumerate(self.risks):
            if "kind" not in risk:
                raise ContractError(f"architecture.risks[{index}] needs a kind")


@dataclasses.dataclass
class AcceptanceEvidence(Record):
    source: str  # "owner_message" | "finalise_command"
    reference: str
    text: str
    recorded_at: str = dataclasses.field(default_factory=utc_now)

    def validate(self) -> None:
        if self.source not in {"owner_message", "finalise_command"}:
            raise ContractError("acceptance must come from an owner message or the finalise command")
        _require_str(self.reference, "acceptance.reference")


@dataclasses.dataclass
class Outcome(Record):
    id: str
    thread_id: str
    task_id: str | None
    outcome: OutcomeKind
    source: str
    satisfaction: int | None
    note: str | None
    recorded_at: str = dataclasses.field(default_factory=utc_now)

    def __post_init__(self) -> None:
        self.outcome = _coerce_enum(OutcomeKind, self.outcome, "outcome")  # type: ignore[assignment]

    def validate(self) -> None:
        if self.source not in {"owner", "owner_abandon_action", "import", "synthetic"}:
            raise ContractError("outcome source must be explicit (owner/abandon action/import/synthetic)")
        if self.satisfaction is not None and not 1 <= self.satisfaction <= 5:
            raise ContractError("satisfaction is 1..5 when supplied")


@dataclasses.dataclass
class Override(Record):
    id: str
    thread_id: str
    task_id: str | None
    old_model: str | None
    new_model: str
    reason: OverrideReason
    reason_text: str | None
    at: str
    execution_result: str

    def __post_init__(self) -> None:
        self.reason = _coerce_enum(OverrideReason, self.reason, "reason")  # type: ignore[assignment]

    def validate(self) -> None:
        _require_str(self.new_model, "override.new_model")


@dataclasses.dataclass
class Approval(Record):
    id: str
    actor: str
    item_type: str
    item_id: str
    item_hash: str
    decision: str
    at: str

    def validate(self) -> None:
        if self.decision not in {"approved", "rejected"}:
            raise ContractError("approval decision must be approved/rejected")
        if len(self.item_hash) != 64:
            raise ContractError("approval must bind to an exact sha256 item hash")
        if self.actor in {"router", "model", "candidate"}:
            raise ContractError("approvals must come from a human actor")


def parse_override_reason(text: str | None) -> tuple[OverrideReason, str | None]:
    """Map an optional free-text reason. Blank stays unknown; never invented."""
    if text is None or not text.strip():
        return OverrideReason.UNKNOWN, None
    lowered = text.strip().lower()
    aliases = {
        OverrideReason.ANSWER_QUALITY: ("quality", "answer quality", "bad answer", "wrong", "q"),
        OverrideReason.DIFFERENT_TASK: ("different task", "new task", "task", "d"),
        OverrideReason.PERSONAL_PREFERENCE: ("preference", "personal preference", "prefer", "p"),
        OverrideReason.UNKNOWN: ("unknown", "u", "skip"),
    }
    for reason, words in aliases.items():
        if lowered in words or lowered == reason.value:
            return reason, None
    return OverrideReason.UNKNOWN, text.strip()
