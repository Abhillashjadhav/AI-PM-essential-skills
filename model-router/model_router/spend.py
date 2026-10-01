"""The zero-added-spend boundary.

Three separate questions, never merged:

1. **Paid API credentials / paid API fallback.** Prevented structurally: the
   adapter refuses API-key auth and provider overrides, strips API-key
   variables, and never calls a paid API.
2. **Automatic credit purchase or reload.** The router never calls a purchase,
   reset or credit method. Whether *the account* has automatic reload on is
   not exposed by the Codex protocol, so the router cannot observe it.
3. **Can this request consume purchased credits (or trigger a purchase)?**
   Only a provider control whose live state the router can read can answer
   "no". That is decided here, per dispatch and again mid-turn, from signals
   the adapter read from the provider moments earlier.

ALLOWED_INCLUDED_ONLY comes only from a mechanism in ``MECHANISMS``: code that
checks live provider signals whose meaning is documented. No file, record,
flag, owner attestation, screenshot or usage percentage can add a mechanism or
satisfy one.

Personal plans (Free/Go/Plus/Pro) have **no verified included-only
mechanism**. ``assess_personal_plan`` records exactly what can be verified
live (zero balance, no unlimited credits, ordinary usage allowed) and names the
guarantee that is missing (the automatic-reload setting is not readable, and
no documented rule says a zero-balance account stops rather than reloads).
See docs/capability-evidence.md for the evidence and its sources.
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

PERSONAL_PLAN_TYPES = frozenset({"free", "go", "plus", "pro", "prolite", "promax"})

# The guarantees a personal plan would need and that the router cannot verify
# through the Codex App Server. Kept as data so setup, the pilot and the docs
# report the same wording.
PERSONAL_MISSING_GUARANTEES = (
    "the automatic-reload setting (and any maximum monthly reload spend) is not exposed to Codex clients, so the "
    "router cannot verify that no credit purchase can be triggered",
    "no documented provider rule says a personal account with a zero credit balance stops at the included-usage "
    "limit instead of reloading; a purchase during a task would only be seen after it happened, on the next "
    "usage read",
)
PERSONAL_PLAN_GAP = "no verified included-only mechanism for this personal plan: " + "; ".join(PERSONAL_MISSING_GUARANTEES)
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
    # "documented_not_observed" until a real account has shown the provider
    # behaving as documented (recorded by the live pilot); then "observed".
    verification: str = "documented_not_observed"


@dataclass(frozen=True)
class PersonalPlanAssessment:
    """What the router verified live for a personal plan, and what it could not."""

    verified: list[str]
    failed: list[str]
    missing: list[str]


def _decimal(value: str | None) -> Decimal | None:
    if value is None:
        return None
    try:
        number = Decimal(str(value).strip())
        if not number.is_finite():
            return None
        return number
    except Exception:  # InvalidOperation, ValueError, signalling NaN, odd types
        return None


def _plan(value) -> str | None:
    return value.strip().lower() if isinstance(value, str) and value.strip() else None


def verify_workspace_member_zero_credit_limit(account: AccountState, usage: UsageSnapshot) -> MechanismResult:
    """A Business/Enterprise/Edu member whose provider-enforced monthly credit
    limit is zero cannot consume credits: Codex pauses at the limit."""
    account_plan, usage_plan = _plan(account.plan_type), _plan(usage.plan_type)
    if account_plan is None or usage_plan is None:
        return MechanismResult(bool(account_plan in WORKSPACE_PLAN_TYPES or usage_plan in WORKSPACE_PLAN_TYPES), False,
                               ["both the account and the usage signals must report the plan"], [])
    if account_plan != usage_plan:
        return MechanismResult(True, False, [f"account plan {account_plan!r} and usage plan {usage_plan!r} disagree"], [])
    if account_plan not in WORKSPACE_PLAN_TYPES:
        return MechanismResult(False, False, [f"plan {account_plan!r} has no provider spend controls"], [])
    if usage.synthetic or account.synthetic:
        return MechanismResult(True, False, ["simulated signals cannot prove enforcement"], [])
    if usage.credits.reported and usage.credits.unlimited:
        return MechanismResult(True, False, ["credits are reported as unlimited"], [])
    controls = {c.limit_id: c for c in usage.spend_controls}
    if not controls:
        return MechanismResult(True, False, ["no spend control reported for this member"], [])
    # Every reported limit must carry a zero member limit: a snapshot that
    # omits credit or spend-control fields is unknown, never safe.
    covered = set(usage.credit_limit_ids) | set(controls) | {b.limit_id.split(":", 1)[0] for b in usage.buckets}
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


def assess_personal_plan(account: AccountState, usage: UsageSnapshot) -> PersonalPlanAssessment:
    """Observable facts for a personal plan. Never grants ALLOWED: even when every
    observable condition holds, the guarantees in PERSONAL_MISSING_GUARANTEES
    cannot be verified through Codex."""
    verified: list[str] = []
    failed: list[str] = []
    source = "simulated" if (usage.synthetic or account.synthetic) else "live"
    if not usage.credits.reported:
        failed.append("the provider did not report a credit balance for this account")
    else:
        if usage.credits.unlimited:
            failed.append("credits are reported as unlimited")
        balance = _decimal(usage.credits.balance)
        if balance is None:
            failed.append(f"credit balance {usage.credits.balance!r} is not a number")
        elif balance != 0:
            failed.append(f"purchased credit balance is {usage.credits.balance}: the provider draws purchased credits "
                          "automatically after included usage")
        else:
            verified.append(f"credit balance is 0 ({source}, this read)")
        if usage.credits.has_credits:
            failed.append("the provider reports hasCredits=true")
        elif balance == 0:
            verified.append(f"hasCredits=false ({source}, this read)")
    if usage.ordinary_usage_allowed is True:
        verified.append(f"included usage is allowed right now ({source}, this read)")
    elif usage.ordinary_usage_allowed is None:
        failed.append("the provider did not report whether included usage is allowed")
    return PersonalPlanAssessment(verified, failed, list(PERSONAL_MISSING_GUARANTEES))


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
        try:
            result = mechanism.verify(account, usage)
        except Exception as exc:  # malformed signals are never evidence
            reasons.append(f"{mechanism.id}: could not evaluate ({type(exc).__name__})")
            continue
        if result.applies and result.enforced:
            evidence = supporting + result.evidence + [
                {"mechanism": mechanism.id, "documentation": mechanism.documentation, "verification": mechanism.verification}
            ]
            return decision(SpendStatus.ALLOWED_INCLUDED_ONLY, [], evidence=evidence, mechanism=mechanism.id)
        reasons.extend(f"{mechanism.id}: {r}" for r in result.reasons)
    account_plan, usage_plan = _plan(account.plan_type), _plan(usage.plan_type)
    plan = account_plan or usage_plan or "unknown"
    if plan in PERSONAL_PLAN_TYPES and usage_plan in (None, plan):
        personal = assess_personal_plan(account, usage)
        evidence = supporting + [{"personal_plan_verified": personal.verified, "personal_plan_failed": personal.failed,
                                  "status": "no verified included-only mechanism"}]
        mechanism_reasons = reasons
        reasons = [f"personal plan {plan!r}: no verified included-only mechanism"]
        reasons += [f"verified: {v}" for v in personal.verified] + [f"not satisfied: {f}" for f in personal.failed]
        reasons += mechanism_reasons
        return decision(SpendStatus.UNKNOWN, reasons, missing=personal.missing, evidence=evidence)
    if plan in WORKSPACE_PLAN_TYPES:
        missing = ["a workspace member credit limit of 0 set by the workspace owner/admin (ChatGPT Business spend controls)"]
    else:
        missing = [f"a verified included-only mechanism for plan {plan!r}"]
    return decision(SpendStatus.UNKNOWN, reasons or ["no supported enforcement mechanism applies"], missing=missing)
