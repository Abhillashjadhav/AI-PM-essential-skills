"""CapacityEstimator: SUFFICIENT / TIGHT / UNKNOWN, always "estimated".

Percent-used is not "tokens left", and a context window is not subscription
capacity. The estimator never divides context length or guessed prices.

Method ``capacity-range.1`` (an engineering hypothesis, not an owner-approved
accuracy claim):

* A *calibration artifact* holds forecast ranges, in the provider's own units
  (percentage points of an applicable usage bucket), for one model/settings
  combination under one plan regime. It is built only from clean before/after
  observations of comparable implementations. Contaminated intervals
  (concurrent sessions, resets inside the interval) are excluded.
* The artifact is unusable until ``validated`` is true, which requires an
  explicit owner approval record. Unvalidated -> UNKNOWN.
* SUFFICIENT when the forecast upper bound is below the remaining capacity in
  every applicable bucket; TIGHT when the lower bound is above the remaining
  capacity of any applicable bucket; otherwise UNKNOWN.
* Stale usage, unknown bucket applicability, coarse rounding, mismatched plan,
  or missing buckets -> UNKNOWN.

Shipped default: no calibration artifact, so every estimate is UNKNOWN.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from .contracts import (
    CAPACITY_METHOD_VERSION,
    CapacityEstimate,
    CapacityState,
    ContractError,
    UsageSnapshot,
    parse_utc,
    utc_now,
)

DEFAULT_MAX_USAGE_AGE = timedelta(minutes=10)
DEFAULT_MIN_CLEAN_OBSERVATIONS = 5  # hypothesis, documented in docs/decisions.md


@dataclass
class UsageObservation:
    """One before/after measurement around a comparable implementation."""

    id: str
    model_id: str
    reasoning_effort: str | None
    plan_type: str | None
    bucket_id: str
    used_before: float
    used_after: float
    workflow_size: str
    prompt_chars: int
    tool_calls: int
    turns: int
    reset_inside: bool = False
    concurrent_sessions: bool = False
    synthetic: bool = False

    @property
    def clean(self) -> bool:
        return not self.reset_inside and not self.concurrent_sessions and self.used_after >= self.used_before

    @property
    def delta(self) -> float:
        return self.used_after - self.used_before


@dataclass
class CalibrationArtifact:
    model_id: str
    reasoning_effort: str | None
    plan_type: str | None
    bucket_ids: list[str]
    forecast_low: float
    forecast_high: float
    observation_ids: list[str]
    method: str = CAPACITY_METHOD_VERSION
    validated: bool = False
    approval_id: str | None = None
    rounding_step: float = 1.0
    synthetic: bool = False
    notes: list[str] = field(default_factory=list)

    def validate(self) -> None:
        if self.forecast_low < 0 or self.forecast_high < self.forecast_low:
            raise ContractError("calibration forecast range is invalid")
        if self.validated and not self.approval_id:
            raise ContractError("a validated calibration needs an approval record")

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "CalibrationArtifact":
        artifact = cls(**payload)
        artifact.validate()
        return artifact


def build_calibration(
    observations: list[UsageObservation],
    *,
    model_id: str,
    reasoning_effort: str | None,
    plan_type: str | None,
    min_clean: int = DEFAULT_MIN_CLEAN_OBSERVATIONS,
) -> tuple[CalibrationArtifact | None, list[str]]:
    """Build an *unvalidated* artifact from comparable clean observations."""
    notes: list[str] = []
    comparable = [
        o
        for o in observations
        if o.model_id == model_id and o.reasoning_effort == reasoning_effort and o.plan_type == plan_type
    ]
    excluded = [o.id for o in comparable if not o.clean]
    if excluded:
        notes.append(f"excluded contaminated observations: {excluded}")
    clean = [o for o in comparable if o.clean]
    if len(clean) < min_clean:
        notes.append(f"only {len(clean)} clean comparable observations (need {min_clean})")
        return None, notes
    deltas = sorted(o.delta for o in clean)
    low, high = deltas[0], deltas[-1]
    # Widen by one rounding step each side: provider percentages are integers.
    artifact = CalibrationArtifact(
        model_id=model_id,
        reasoning_effort=reasoning_effort,
        plan_type=plan_type,
        bucket_ids=sorted({o.bucket_id for o in clean}),
        forecast_low=max(0.0, low - 1.0),
        forecast_high=high + 1.0,
        observation_ids=[o.id for o in clean],
        synthetic=any(o.synthetic for o in clean),
        notes=notes + ["min/max of clean deltas widened by one rounding step"],
    )
    return artifact, notes


class CapacityEstimator:
    def __init__(
        self,
        calibrations: list[CalibrationArtifact] | None = None,
        *,
        max_usage_age: timedelta = DEFAULT_MAX_USAGE_AGE,
        now=utc_now,
    ) -> None:
        self.calibrations = calibrations or []
        self.max_usage_age = max_usage_age
        self._now = now

    def estimate(
        self,
        *,
        model_id: str | None,
        reasoning_effort: str | None,
        usage: UsageSnapshot | None,
    ) -> CapacityEstimate:
        base = dict(
            buckets=[],
            observed_at=usage.observed_at if usage else None,
            plan_type=usage.plan_type if usage else None,
            account_scope=usage.account_scope if usage else None,
            method="before/after range comparison",
            method_version=CAPACITY_METHOD_VERSION,
        )

        def unknown(*why: str, observations: list[str] | None = None, synthetic: bool = bool(usage and usage.synthetic)) -> CapacityEstimate:
            return CapacityEstimate(
                state=CapacityState.UNKNOWN,
                forecast_low=None,
                forecast_high=None,
                observations=observations or [],
                uncertainty=list(why),
                synthetic=synthetic,
                **base,
            )

        if model_id is None:
            return unknown("no model binding to estimate for")
        if usage is None:
            return unknown("no usage snapshot")
        age = parse_utc(self._now()) - parse_utc(usage.observed_at)
        if age > self.max_usage_age:
            return unknown(f"usage snapshot is stale ({int(age.total_seconds())}s old)")
        calibration = next(
            (
                c
                for c in self.calibrations
                if c.model_id == model_id and c.reasoning_effort == reasoning_effort
            ),
            None,
        )
        if calibration is None:
            return unknown("no calibration artifact for this model/settings")
        if not calibration.validated:
            return unknown("calibration artifact not validated by the owner", observations=calibration.observation_ids)
        if calibration.plan_type != usage.plan_type:
            return unknown(
                f"calibration plan {calibration.plan_type!r} differs from reported plan {usage.plan_type!r}",
                observations=calibration.observation_ids,
            )
        if calibration.synthetic != usage.synthetic:
            return unknown("synthetic and live evidence cannot be mixed")
        by_id = {b.limit_id: b for b in usage.buckets}
        applicable = []
        for bucket_id in calibration.bucket_ids:
            bucket = by_id.get(bucket_id)
            if bucket is None or bucket.remaining_percent is None:
                return unknown(
                    f"applicable bucket {bucket_id!r} not reported (absent is not unlimited)",
                    observations=calibration.observation_ids,
                    synthetic=calibration.synthetic,
                )
            applicable.append(bucket)
        if not applicable:
            return unknown("no applicable usage bucket identified")
        base["buckets"] = [b.limit_id for b in applicable]
        low, high = calibration.forecast_low, calibration.forecast_high
        remaining = [b.remaining_percent for b in applicable]
        step = calibration.rounding_step
        if all(high + step <= r for r in remaining if r is not None):
            state = CapacityState.SUFFICIENT
            why: list[str] = [f"forecast upper bound {high} + rounding {step} below remaining {remaining}"]
        elif any(low - step > r for r in remaining if r is not None):
            state = CapacityState.TIGHT
            why = [f"forecast lower bound {low} - rounding {step} above remaining {remaining}"]
        else:
            return unknown(
                f"forecast range {low}..{high} overlaps remaining {remaining}",
                observations=calibration.observation_ids,
                synthetic=calibration.synthetic,
            )
        return CapacityEstimate(
            state=state,
            forecast_low=low,
            forecast_high=high,
            observations=calibration.observation_ids,
            uncertainty=why + ["estimated, not guaranteed"],
            synthetic=calibration.synthetic,
            **base,
        )


def wilson_interval(successes: int, total: int, z: float = 1.96) -> tuple[float, float] | None:
    if total <= 0:
        return None
    p = successes / total
    denom = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denom
    margin = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denom
    return max(0.0, centre - margin), min(1.0, centre + margin)
