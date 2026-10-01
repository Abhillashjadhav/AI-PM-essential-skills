"""Local owner confirmation. This is not a provider billing control."""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path

from .contracts import ContractError, new_id, parse_utc, utc_now
from .store import Store

PERSONAL_POLICY = "personal_subscription_owner_confirmed_v1"
KEY = "billing.personal_confirmation.v1"
DEPENDENCY = (
    "Automatic credit purchases are OFF according to your saved confirmation. "
    "The router cannot read that setting or prevent billing changes elsewhere. "
    "Disable this mode before enabling reload or buying credits."
)


@dataclasses.dataclass(frozen=True)
class PersonalConfirmation:
    id: str
    account_scope: str
    plan_type: str
    adapter_pin: str
    profile: str
    confirmed_at: str
    policy: str = PERSONAL_POLICY
    enabled: bool = True
    automatic_reload_off: bool = True
    dependency_accepted: bool = True

    def validate(self) -> None:
        for field in ("id", "account_scope", "plan_type", "adapter_pin", "profile"):
            if not isinstance(getattr(self, field), str) or not getattr(self, field).strip():
                raise ContractError(f"billing confirmation requires {field}")
        if self.policy != PERSONAL_POLICY or type(self.enabled) is not bool:
            raise ContractError("unsupported billing confirmation")
        if self.automatic_reload_off is not True or self.dependency_accepted is not True:
            raise ContractError("billing confirmation must acknowledge reload off and the account-setting dependency")
        if (parse_utc(self.confirmed_at) - parse_utc(utc_now())).total_seconds() > 5:
            raise ContractError("billing confirmation is in the future")

    @classmethod
    def from_json(cls, text: str) -> "PersonalConfirmation":
        value = json.loads(text)
        if not isinstance(value, dict) or set(value) != {f.name for f in dataclasses.fields(cls)}:
            raise ContractError("invalid billing confirmation shape")
        result = cls(**value)
        result.validate()
        return result


class BillingPolicy:
    """Use the private SQLite store for atomic, cross-process enable/disable.

    No local file can prove provider enforcement. This record only carries the
    explicit owner choice; live account/usage validation is separate.
    """

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir

    def load(self) -> tuple[PersonalConfirmation | None, str | None]:
        store = Store(self.data_dir)
        try:
            row = store.one("SELECT value FROM meta WHERE key=?", (KEY,))
            if row is None:
                return None, "not enabled; run router.py setup"
            try:
                result = PersonalConfirmation.from_json(row["value"])
            except (ValueError, TypeError, KeyError):
                return None, "invalid saved confirmation; run router.py setup"
            return result, None if result.enabled else "disabled; run router.py setup to confirm again"
        finally:
            store.close()

    def confirm(self, *, account_scope: str, plan_type: str, adapter_pin: str, profile: str) -> PersonalConfirmation:
        result = PersonalConfirmation(new_id("billing"), account_scope, plan_type, adapter_pin, profile, utc_now())
        result.validate()
        store = Store(self.data_dir)
        try:
            with store.transaction() as conn:
                conn.execute("INSERT INTO meta(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                             (KEY, json.dumps(dataclasses.asdict(result), sort_keys=True)))
                store.event("billing.confirmed", dataclasses.asdict(result) | {"source": "owner_confirmation"}, conn=conn)
        finally:
            store.close()
        return result

    def disable(self, reason: str = "owner disabled", *, expected_id: str | None = None) -> bool:
        store = Store(self.data_dir)
        try:
            with store.transaction() as conn:
                row = conn.execute("SELECT value FROM meta WHERE key=?", (KEY,)).fetchone()
                if row is None:
                    return False
                try:
                    current = PersonalConfirmation.from_json(row["value"])
                except (ValueError, TypeError, KeyError):
                    return False  # unreadable policy already blocks; preserve the record
                if not current.enabled or (expected_id and current.id != expected_id):
                    return False  # a stale reader must not revoke a newer confirmation
                disabled = dataclasses.replace(current, enabled=False)
                conn.execute("UPDATE meta SET value=? WHERE key=?", (json.dumps(dataclasses.asdict(disabled)), KEY))
                store.event("billing.disabled", {"confirmation_id": current.id, "reason": reason}, conn=conn)
                return True
        finally:
            store.close()

    def status(self) -> dict:
        current, problem = self.load()
        if current is None:
            invalid = bool(problem and problem.startswith("invalid saved confirmation"))
            source = "invalid_local_record" if invalid else "none"
            note = (
                "The saved local confirmation is invalid and cannot enable personal subscription mode. "
                "The router cannot verify the provider's current credit settings."
                if invalid else
                "No owner confirmation is saved. The router cannot verify whether automatic "
                "credit purchases are off in the provider account."
            )
        elif current.enabled:
            source = "owner_confirmation"
            note = DEPENDENCY
        else:
            source = "owner_confirmation"
            note = (
                "The saved owner confirmation is disabled. It records a prior choice, not the "
                "provider's current credit settings; confirm account settings again before setup."
            )
        return {"enabled": bool(current and current.enabled), "confirmed_at": current.confirmed_at if current else None,
                "policy": PERSONAL_POLICY, "source": source, "provider_verified": False,
                "problem": problem, "note": note}
