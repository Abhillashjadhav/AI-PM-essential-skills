"""Eligibility gate, evaluated fresh before every dispatch and resume.

Order: auth/config -> account binding -> included usage -> spend boundary ->
model availability -> tools. Capacity uncertainty never blocks a request on its
normal model; spend uncertainty always does. The gate never buys credits,
redeems resets, or switches to a paid path.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Iterable

from .adapters.base import AccountState, AdapterError, SubscriptionAdapter
from .contracts import (
    Binding,
    JobState,
    SpendDecision,
    SpendStatus,
    UsageSnapshot,
    new_id,
    utc_now,
)
from .registry import Registry
from .store import Store, dumps


@dataclass
class EligibilityResult:
    ok: bool
    state: JobState  # READY when ok, otherwise the blocking state
    blocker: str | None
    reset_at: str | None = None
    account: AccountState | None = None
    usage: UsageSnapshot | None = None
    spend: SpendDecision | None = None
    notes: list[str] = field(default_factory=list)
    elapsed_ms: float = 0.0
    checks: dict[str, str] = field(default_factory=dict)

    def summary(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "state": self.state.value,
            "blocker": self.blocker,
            "reset_at": self.reset_at,
            "notes": self.notes,
            "elapsed_ms": round(self.elapsed_ms, 2),
            "checks": self.checks,
            "spend": self.spend.to_dict() if self.spend else None,
        }


class EligibilityGate:
    def __init__(self, store: Store, adapter: SubscriptionAdapter, registry: Registry, *, live: bool) -> None:
        self.store = store
        self.adapter = adapter
        self.registry = registry
        self.live = live
        self._last_account_fingerprint: str | None = None
        self._capabilities = None

    def invalidate(self, reason: str) -> None:
        """Invalidate stored spend evidence (account/config/limit transition)."""
        now = utc_now()
        self.store.execute("UPDATE spend_evidence SET invalidated_at=? WHERE invalidated_at IS NULL", (now,))
        self.store.event("spend.evidence_invalidated", {"reason": reason})
        self._capabilities = None

    def check(
        self,
        binding: Binding | None,
        *,
        thread_account_scope: str | None,
        required_tools: Iterable[str] = (),
        thread_id: str | None = None,
    ) -> EligibilityResult:
        started = time.monotonic()
        checks: dict[str, str] = {}

        def done(result: EligibilityResult) -> EligibilityResult:
            result.elapsed_ms = (time.monotonic() - started) * 1000
            result.checks = checks
            self.store.event("eligibility.checked", result.summary(), thread_id=thread_id)
            return result

        def blocked(state: JobState, why: str, **extra: Any) -> EligibilityResult:
            return done(EligibilityResult(ok=False, state=state, blocker=why, **extra))

        try:
            account = self.adapter.read_account()
        except AdapterError as exc:
            checks["auth"] = "error"
            return blocked(JobState.BLOCKED_AUTH, f"could not read the account: {exc}")
        fingerprint = f"{account.account_scope}|{account.auth_mode}|{account.plan_type}"
        if self._last_account_fingerprint and fingerprint != self._last_account_fingerprint:
            self.invalidate("account, workspace or plan changed since the last check")
        self._last_account_fingerprint = fingerprint

        if not account.authenticated or account.auth_mode is None:
            checks["auth"] = "missing"
            return blocked(JobState.BLOCKED_AUTH, "not signed in with ChatGPT; run the supported Codex login", account=account)
        if account.auth_mode != "chatgpt":
            checks["auth"] = f"refused:{account.auth_mode}"
            return blocked(
                JobState.BLOCKED_AUTH,
                f"authentication mode '{account.auth_mode}' is not allowed; only ChatGPT sign-in is permitted",
                account=account,
            )
        if not account.config_ok:
            checks["config"] = "incompatible"
            return blocked(
                JobState.BLOCKED_AUTH,
                "incompatible provider configuration: " + "; ".join(account.config_problems or ["unspecified"]),
                account=account,
            )
        checks["auth"] = "chatgpt"
        if self.live and account.synthetic:
            checks["account_source"] = "synthetic"
            return blocked(JobState.BLOCKED_SPEND, "simulated account state cannot authorise a live dispatch", account=account)
        if self.live and binding is not None and not thread_account_scope:
            checks["account_binding"] = "unbound"
            return blocked(JobState.BLOCKED_AUTH, "this thread is not bound to a signed-in account, so it will not be sent", account=account)
        if thread_account_scope and account.account_scope != thread_account_scope:
            checks["account_binding"] = "mismatch"
            return blocked(
                JobState.BLOCKED_AUTH,
                "this thread belongs to a different signed-in account or workspace; it will not be resumed on this one",
                account=account,
            )
        checks["account_binding"] = "ok"

        try:
            usage = self.adapter.read_usage()
        except AdapterError as exc:
            checks["usage"] = "error"
            return blocked(JobState.BLOCKED_SPEND, f"could not read usage, so spend cannot be checked: {exc}", account=account)
        self._record_usage(usage)
        if usage.account_scope is not None and usage.account_scope != account.account_scope:
            checks["usage"] = "foreign_account"
            return blocked(JobState.BLOCKED_SPEND, "usage evidence belongs to another account", account=account, usage=usage)
        notes: list[str] = []
        if usage.reset_offer_available:
            notes.append(
                f"{usage.reset_offer_available} usage reset offer(s) reported; the router never redeems them (owner's choice)"
            )
        available = usage.included_usage_available()
        if available is False:
            checks["usage"] = "exhausted"
            reset = usage.earliest_reset()
            return blocked(
                JobState.WAITING_USAGE,
                "included usage is unavailable"
                + (f"; a reset is reported for {reset}" if reset else "; availability time is unknown"),
                reset_at=reset,
                account=account,
                usage=usage,
                notes=notes,
            )
        checks["usage"] = "available" if available else "unknown"
        if available is None:
            notes.append("included-usage availability not reported (unknown, not unlimited)")

        try:
            spend = self.adapter.check_spend_boundary(account, usage)
            spend.validate()
        except Exception as exc:  # any failure to decide is a block, never a pass
            checks["spend"] = "error"
            return blocked(JobState.BLOCKED_SPEND, f"spend boundary could not be evaluated: {exc}", account=account, usage=usage)
        self._record_spend(spend)
        if self.live and spend.synthetic:
            checks["spend"] = "synthetic_rejected"
            return blocked(
                JobState.BLOCKED_SPEND,
                "a simulated or fixture spend decision cannot certify live dispatch",
                account=account,
                usage=usage,
                spend=spend,
            )
        if spend.account_scope != account.account_scope:
            checks["spend"] = "foreign_account"
            return blocked(JobState.BLOCKED_SPEND, "spend evidence belongs to another account", account=account, usage=usage, spend=spend)
        if spend.status is not SpendStatus.ALLOWED_INCLUDED_ONLY:
            checks["spend"] = spend.status.value
            missing = ("; missing: " + "; ".join(spend.missing)) if spend.missing else ""
            return blocked(
                JobState.BLOCKED_SPEND,
                f"spend boundary is {spend.status.value}: " + "; ".join(spend.reasons) + missing,
                account=account,
                usage=usage,
                spend=spend,
                notes=notes,
            )
        checks["spend"] = "allowed_included_only"

        if binding is not None:
            try:
                catalogue = self.adapter.list_models()
                self.registry.record_discovery(account.account_scope or "unknown", catalogue.models, provider=self.adapter.name)
            except AdapterError as exc:
                checks["model"] = "error"
                return blocked(JobState.BLOCKED_CAPABILITY, f"could not confirm model availability: {exc}", account=account, usage=usage, spend=spend)
            if binding.model_id not in {m.model_id for m in catalogue.models}:
                checks["model"] = "unavailable"
                return blocked(
                    JobState.BLOCKED_CAPABILITY,
                    f"pinned model {binding.model_id} is not available to this account; the thread keeps its pin and waits",
                    account=account,
                    usage=usage,
                    spend=spend,
                )
            checks["model"] = "available"

        required = sorted(set(required_tools))
        if required:
            if self._capabilities is None:
                self._capabilities = self.adapter.initialise()
            missing_tools = [t for t in required if self._capabilities.tools.get(t) != "supported"]
            if missing_tools:
                checks["tools"] = "missing:" + ",".join(missing_tools)
                return blocked(
                    JobState.BLOCKED_CAPABILITY,
                    f"required tool(s) not available: {', '.join(missing_tools)}; nothing will be pretended",
                    account=account,
                    usage=usage,
                    spend=spend,
                )
            checks["tools"] = "ok"
        return done(EligibilityResult(ok=True, state=JobState.READY, blocker=None, account=account, usage=usage, spend=spend, notes=notes))

    # -- persistence -----------------------------------------------------------

    def _record_usage(self, usage: UsageSnapshot) -> None:
        previous = self.store.one(
            "SELECT payload FROM usage_snapshots WHERE account_scope IS ? ORDER BY observed_at DESC LIMIT 1",
            (usage.account_scope,),
        )
        self.store.execute(
            "INSERT INTO usage_snapshots(id, account_scope, plan_type, payload, raw_redacted, observed_at, source, synthetic) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (
                usage.id,
                usage.account_scope,
                usage.plan_type,
                dumps(usage.to_dict()),
                None,
                usage.observed_at,
                usage.source,
                int(usage.synthetic),
            ),
        )
        if previous is not None:
            old = json.loads(previous["payload"])
            new = usage.to_dict()
            limit_or_credit = (
                old.get("ordinary_usage_allowed") != usage.ordinary_usage_allowed
                or old.get("credits") != new["credits"]
                or old.get("spend_control_reached") != usage.spend_control_reached
            )
            if limit_or_credit or old.get("buckets") != new["buckets"]:
                self.store.event("usage.changed", {"snapshot_id": usage.id, "synthetic": usage.synthetic})
            if limit_or_credit:
                self.invalidate("reported limit or credit transition")

    def _record_spend(self, spend: SpendDecision) -> None:
        self.store.execute(
            "INSERT INTO spend_evidence(id, account_scope, payload, status, source, observed_at, expires_at) VALUES (?,?,?,?,?,?,?)",
            (
                new_id("spd"),
                spend.account_scope,
                dumps(spend.to_dict()),
                spend.status.value,
                "synthetic" if spend.synthetic else "live",
                spend.decided_at,
                None,
            ),
        )
