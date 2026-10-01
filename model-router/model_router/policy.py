"""Routing policy: hard role floors, upward fallback, and the narrow
implementation-thread capacity exception (spec section 5.3).

The retired 80/20 priority/usage formula is intentionally absent.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .contracts import (
    POLICY_VERSION,
    CapacityEstimate,
    CapacityState,
    Clarity,
    RiskFlag,
    RiskLevel,
    Role,
    TaskAssessment,
    TaskKind,
)

ROLE_FLOORS: dict[TaskKind, tuple[Role, str, str]] = {
    TaskKind.ARCHITECTURE: (Role.HIGHEST, "RF-ARCH", "architecture decision"),
    TaskKind.PRODUCT_DECISION: (Role.HIGHEST, "RF-PRODUCT", "product decision"),
    TaskKind.UI_DECISION: (Role.HIGHEST, "RF-UI", "UI decision"),
    TaskKind.TRADEOFF: (Role.HIGHEST, "RF-TRADEOFF", "difficult trade-off"),
    TaskKind.HIGH_CREDIBILITY_WRITING: (Role.HIGHEST, "RF-CREDIBILITY", "high-credibility writing"),
    TaskKind.CONSEQUENTIAL_ASSESSMENT: (Role.HIGHEST, "RF-CONSEQUENCE", "consequential assessment"),
    TaskKind.HIGH_RISK_CODING: (Role.HIGHEST, "RF-RISK-CODE", "coding that touches money, privacy or security"),
    TaskKind.IMPLEMENTATION: (Role.MIDDLE, "RF-IMPL", "implementation from an agreed design"),
    TaskKind.ROUTINE_TEXT: (Role.LOWEST, "RF-ROUTINE", "routine text work"),
    TaskKind.RESOURCE_EXTRACTION: (Role.LOWEST, "RF-EXTRACT", "specified collection or literal extraction"),
    TaskKind.UNKNOWN: (Role.HIGHEST, "RF-UNKNOWN", "task not recognised, so routed conservatively"),
}

HIGHEST_RISK_FLAGS = frozenset({RiskFlag.MONEY_MOVEMENT, RiskFlag.PRIVACY, RiskFlag.SECURITY})


@dataclass
class RolePlan:
    role: Role
    rule_ids: list[str]
    reasons: list[str]
    uncertainty: list[str] = field(default_factory=list)
    upward_fallback: bool = False
    policy_version: str = POLICY_VERSION

    def explanation(self) -> str:
        return self.reasons[0] if self.reasons else self.role.plain


def required_role(assessment: TaskAssessment) -> RolePlan:
    """Role floor for a new ordinary thread. Consequences beat labels."""
    kinds = [assessment.task_kind, *assessment.secondary_kinds]
    role = Role.LOWEST
    rule_ids: list[str] = []
    reasons: list[str] = []
    for kind in kinds:
        floor, rule_id, reason = ROLE_FLOORS[kind]
        if floor.rank > role.rank or not rule_ids:
            role = Role.max(role, floor)
        rule_ids.append(rule_id)
        reasons.append(reason)
    # Order reasons so the one that set the role is first.
    ordered = sorted(
        zip(rule_ids, reasons, kinds), key=lambda item: -ROLE_FLOORS[item[2]][0].rank
    )
    rule_ids = [item[0] for item in ordered]
    reasons = [item[1] for item in ordered]

    uncertainty = list(assessment.uncertainty)
    upward = False
    if assessment.ambiguous and role is not Role.HIGHEST:
        role = Role.HIGHEST if assessment.task_kind is TaskKind.UNKNOWN else _one_up(role)
        rule_ids.append("RF-UPWARD")
        reasons.append("uncertain task, routed one level up")
        upward = True
    if assessment.task_kind is TaskKind.UNKNOWN:
        upward = True
    return RolePlan(role=role, rule_ids=rule_ids, reasons=reasons, uncertainty=uncertainty, upward_fallback=upward)


def _one_up(role: Role) -> Role:
    return {Role.LOWEST: Role.MIDDLE, Role.MIDDLE: Role.HIGHEST, Role.HIGHEST: Role.HIGHEST}[role]


@dataclass
class ImplementationFacts:
    """Inputs for the section 5.3 decision. All evidence-derived."""

    requires_highest: bool
    requires_highest_reasons: list[str]
    clarity: Clarity
    clarity_evidence: list[str]
    risk: RiskLevel
    lowest_candidate_ok: bool
    lowest_candidate_note: str


def implementation_role(facts: ImplementationFacts, capacity: CapacityEstimate) -> RolePlan:
    """Choose the implementation role exactly once (never re-evaluated mid-thread)."""
    if facts.requires_highest:
        return RolePlan(
            role=Role.HIGHEST,
            rule_ids=["IMPL-HIGHEST"],
            reasons=["implementation needs highest reasoning: " + "; ".join(facts.requires_highest_reasons)],
        )
    if (
        capacity.state is CapacityState.TIGHT
        and facts.clarity is Clarity.CLEAR_AND_SIMPLE
        and facts.risk is RiskLevel.LOW_RISK
        and facts.lowest_candidate_ok
    ):
        return RolePlan(
            role=Role.LOWEST,
            rule_ids=["IMPL-CAPACITY-EXCEPTION"],
            reasons=[
                "the steps are clear, the work is low risk, and included usage looks tight (estimated)"
            ],
        )
    reasons = ["implementation from the agreed architecture"]
    uncertainty: list[str] = []
    if capacity.state is CapacityState.UNKNOWN:
        uncertainty.append("capacity unknown, so no automatic downgrade")
    elif capacity.state is CapacityState.TIGHT:
        if facts.clarity is not Clarity.CLEAR_AND_SIMPLE:
            uncertainty.append("capacity tight but architecture not proven clear and simple")
        if facts.risk is not RiskLevel.LOW_RISK:
            uncertainty.append("capacity tight but work is not low risk")
        if not facts.lowest_candidate_ok:
            uncertainty.append("capacity tight but no approved capable lowest model: " + facts.lowest_candidate_note)
    return RolePlan(role=Role.MIDDLE, rule_ids=["IMPL-DEFAULT-MIDDLE"], reasons=reasons, uncertainty=uncertainty)


def assessment_requires_highest(assessment: TaskAssessment) -> list[str]:
    reasons = []
    flags = set(assessment.risk_flags)
    for flag in sorted(flags & HIGHEST_RISK_FLAGS, key=lambda f: f.value):
        reasons.append(f"{flag.value.replace('_', ' ')} risk")
    return reasons
