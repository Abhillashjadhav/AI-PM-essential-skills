"""The zero-added-spend boundary.

Three separate questions, never merged:

1. **Paid API credentials / paid API fallback.** Prevented structurally: the
   adapter refuses API-key auth and provider overrides, strips API-key
   variables, and never calls a paid API.
2. **Automatic credit purchase or reload.** The router never calls a purchase
   or reset method. Whether *the account* has automatic reload on is not
   exposed by the Codex protocol, so the router cannot observe it.
3. **Can this request consume already-purchased credits?** Only a provider
   control that stops credit consumption for this account can answer "no".
   That is decided here, per dispatch, from signals the adapter read live from
   the provider moments earlier.

ALLOWED_INCLUDED_ONLY comes only from a mechanism in ``MECHANISMS``: code that
checks live provider signals whose meaning is documented. No file, record,
flag, owner attestation or usage percentage can add a mechanism or satisfy
one. Personal ChatGPT plans have no such control today (credits apply
automatically after included usage; see docs/capability-evidence.md), so on a
personal plan the decision is UNKNOWN and live sends stay blocked.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Callable

from .adapters.base import AccountState
from .contracts import (
    WORKSPACE_PLAN_TYPES,
    SpendDecision,
    SpendStatus,
    UsageSnapshot,
    utc_now,
)

PERSONAL_PLAN_GAP = (
    "OpenAI provides no control that stops purchased credits being applied after included usage on personal "
    "ChatGPT plans (credits apply automatically; the requested toggle, openai/codex#28382, is still open), and "
    "the automatic-reload setting is not exposed to Codex clients"
)
WORKSPACE_LIMIT_DOC = (
    "OpenAI Help Center, 'Managing credits and spend controls in ChatGPT Business': owners/admins set monthly credit "
    "limits per seat type and per member; when a member reaches the limit, Codex usage pauses. Exposed to clients as "
    "rateLimits.individualLimit {limit, used} and spendControlReached (openai/codex backend-client SpendControlStatusDetails)."
)


@dataclass(frozen=True)
class MechanismResult:
    applies: bool  # the account is of a kind this mechanism covers
    enforced: bool  # the live signals prove credits cannot be consumed now
    reasons: list[str]
    evidence: list[dict]


@dataclass(frozen=True)
class Mechanism:
    id: str
    description: str
    documentation: str
    verify: Callable[[AccountState, UsageSnapshot], MechanismResult]


def _decimal(value: str | None) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return None


def verify_workspace_member_zero_credit_limit(account: AccountState, usage: UsageSnapshot) -> MechanismResult:
    """A Business/Enterprise/Edu member whose provider-enforced monthly credit
    limit is zero cannot consume credits: Codex pauses at the limit."""
    plan = (usage.plan_type or account.plan_type or "").lower()
    if plan not in WORKSPACE_PLAN_TYPES:
        return MechanismResult(False, False, [f"plan {plan or 'unknown'!r} has no provider spend controls"], [])
    if usage.synthetic or account.synthetic:
        return MechanismResult(True, False, ["simulated signals cannot prove enforcement"], [])
    if usage.credits.reported and usage.credits.unlimited:
        return MechanismResult(True, False, ["credits are reported as unlimited"], [])
    controls = {c.limit_id: c for c in usage.spend_controls}
    if not controls:
        return MechanismResult(True, False, ["no spend control reported for this member"], [])
    # Every snapshot where credits can apply must carry a zero member limit.
    covered = set(usage.credit_limit_ids) | set(controls)
    evidence: list[dict] = []
    for limit_id in sorted(covered):
        control = controls.get(limit_id)
        if control is None:
            return MechanismResult(True, False, [f"credits can apply to {limit_id!r} but it reports no spend control"], evidence)
        limit = _decimal(control.limit)
        if limit is None:
            return MechanismResult(True, False, [f"{limit_id!r} member limit {control.limit!r} is not a number"], evidence)
        if limit != 0:
            return MechanismResult(True, False, [f"{limit_id!r} member credit limit is {control.limit}, not 0"], evidence)
        evidence.append(
            {"source": "live", "limit_id": limit_id, "member_credit_limit": control.limit, "used": control.used,
             "reached": control.reached, "status": "enforced"}
        )
    return MechanismResult(True, True, [], evidence)


MECHANISMS: tuple[Mechanism, ...] = (
    Mechanism(
        id="workspace_member_zero_credit_limit",
        description="provider-enforced member credit limit of 0 on a ChatGPT workspace plan",
        documentation=WORKSPACE_LIMIT_DOC,
        verify=verify_workspace_member_zero_credit_limit,
    ),
)


def supporting_observations(usage: UsageSnapshot) -> list[dict]:
    return [
        {"source": "live" if not usage.synthetic else "synthetic", "field": "ordinaryUsageAllowed", "value": usage.ordinary_usage_allowed, "status": "supporting"},
        {"source": "live" if not usage.synthetic else "synthetic", "field": "credits", "value": usage.credits.describe(), "status": "supporting"},
        {"source": "live" if not usage.synthetic else "synthetic", "field": "spendControlReached", "value": usage.spend_control_reached, "status": "supporting"},
    ]


def decide_spend(
    account: AccountState,
    usage: UsageSnapshot,
    *,
    pin_state: str,
    mechanisms: tuple[Mechanism, ...] = MECHANISMS,
) -> SpendDecision:
    now = utc_now()
    supporting = supporting_observations(usage)

    def decision(status: SpendStatus, reasons: list[str], *, missing: list[str] | None = None, evidence=None, mechanism=None):
        return SpendDecision(status, reasons, evidence if evidence is not None else supporting, account.account_scope, now,
                             account.synthetic or usage.synthetic, missing=missing or [], mechanism=mechanism)

    if account.auth_mode != "chatgpt":
        return decision(SpendStatus.BLOCKED, ["not a ChatGPT-authenticated account (paid API paths are refused)"])
    if usage.account_scope is not None and usage.account_scope != account.account_scope:
        return decision(SpendStatus.BLOCKED, ["usage signals belong to another account"])
    if usage.spend_control_reached or any(c.reached for c in usage.spend_controls):
        return decision(SpendStatus.BLOCKED, ["the provider reports a spend control has been reached"])
    if usage.ordinary_usage_allowed is False:
        return decision(SpendStatus.BLOCKED, ["included usage is not allowed right now; a send could draw on purchased credits"])
    if pin_state != "valid":
        return decision(SpendStatus.UNKNOWN, [f"adapter pin is {pin_state}; live signals are not trusted until it is valid"],
                        missing=["a valid adapter pin"])
    reasons: list[str] = []
    for mechanism in mechanisms:
        result = mechanism.verify(account, usage)
        if result.applies and result.enforced:
            evidence = supporting + result.evidence + [{"mechanism": mechanism.id, "documentation": mechanism.documentation}]
            return decision(SpendStatus.ALLOWED_INCLUDED_ONLY, [], evidence=evidence, mechanism=mechanism.id)
        reasons.extend(f"{mechanism.id}: {r}" for r in result.reasons)
    plan = (usage.plan_type or account.plan_type or "unknown").lower()
    missing = [PERSONAL_PLAN_GAP] if plan not in WORKSPACE_PLAN_TYPES else [
        "a workspace member credit limit of 0 set by the workspace owner/admin (ChatGPT Business spend controls)"
    ]
    return decision(SpendStatus.UNKNOWN, reasons or ["no supported enforcement mechanism applies"], missing=missing)
