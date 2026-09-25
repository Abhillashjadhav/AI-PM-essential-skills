"""Model registry: discovered candidates, approved role mappings, revisions.

* Default configuration contains no executable model IDs. The owner's family
  examples (Astra = highest, Sol = middle) are labels only.
* Discovery creates CANDIDATE records; nothing is promoted automatically.
* Approval binds to the exact mapping hash and activates a new registry
  revision atomically. Activation affects new threads only.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Iterable

from .contracts import (
    Approval,
    Binding,
    ContractError,
    ModelInfo,
    ModelStatus,
    Role,
    RoleMapping,
    content_hash,
    new_id,
    utc_now,
)
from .store import Store, dumps, loads

DEFAULT_ROLE_LABELS: dict[Role, str] = {
    Role.HIGHEST: "Astra (owner's example family for highest reasoning)",
    Role.MIDDLE: "Sol (owner's example family for middle reasoning)",
    Role.LOWEST: "an evaluated low-tier candidate (to be chosen after comparison)",
}
DEFAULT_FAMILY_PREFERENCES: dict[Role, str | None] = {
    Role.HIGHEST: "astra",
    Role.MIDDLE: "sol",
    Role.LOWEST: None,
}
CODING_TOOLS = ("edit", "shell")


class RegistryError(ContractError):
    pass


@dataclass
class Proposal:
    role: Role
    model_id: str
    reasoning_effort: str | None
    rationale: str
    mapping_hash: str
    evaluation_ids: list[str]


class Registry:
    def __init__(self, store: Store) -> None:
        self.store = store

    # -- discovery -----------------------------------------------------------

    def record_discovery(
        self, account_scope: str, catalogue: Iterable[ModelInfo], *, provider: str
    ) -> dict[str, list[str]]:
        """Upsert discovered models as candidates; mark vanished ones unavailable."""
        now = utc_now()
        seen: set[str] = set()
        new: list[str] = []
        with self.store.transaction() as conn:
            for model in catalogue:
                model.validate()
                seen.add(model.model_id)
                row = conn.execute(
                    "SELECT id, status FROM registry_models WHERE provider=? AND account_scope=? AND model_id=?",
                    (provider, account_scope, model.model_id),
                ).fetchone()
                if row is None:
                    conn.execute(
                        "INSERT INTO registry_models(id, provider, account_scope, model_id, display_name, payload, status, "
                        "available, first_seen, last_seen) VALUES (?,?,?,?,?,?,?,?,?,?)",
                        (
                            new_id("mdl"),
                            provider,
                            account_scope,
                            model.model_id,
                            model.display_name,
                            dumps(model.to_dict()),
                            ModelStatus.CANDIDATE.value,
                            1,
                            now,
                            now,
                        ),
                    )
                    new.append(model.model_id)
                    self.store.event(
                        "model.discovered",
                        {"model_id": model.model_id, "status": "candidate", "account_scope": account_scope},
                        conn=conn,
                    )
                else:
                    conn.execute(
                        "UPDATE registry_models SET payload=?, display_name=?, available=1, last_seen=? WHERE id=?",
                        (dumps(model.to_dict()), model.display_name, now, row["id"]),
                    )
            vanished = [
                row["model_id"]
                for row in conn.execute(
                    "SELECT model_id FROM registry_models WHERE provider=? AND account_scope=? AND available=1",
                    (provider, account_scope),
                )
                if row["model_id"] not in seen
            ]
            for model_id in vanished:
                conn.execute(
                    "UPDATE registry_models SET available=0 WHERE provider=? AND account_scope=? AND model_id=?",
                    (provider, account_scope, model_id),
                )
                self.store.event(
                    "model.unavailable",
                    {"model_id": model_id, "account_scope": account_scope, "action": "owner notified; no thread moved"},
                    conn=conn,
                )
        return {"new_candidates": new, "unavailable": vanished}

    def models(self, account_scope: str) -> list[dict[str, Any]]:
        rows = self.store.all(
            "SELECT * FROM registry_models WHERE account_scope=? ORDER BY model_id", (account_scope,)
        )
        return [
            {
                "model_id": row["model_id"],
                "display_name": row["display_name"],
                "status": row["status"],
                "available": bool(row["available"]),
                "info": loads(row["payload"]),
                "first_seen": row["first_seen"],
                "last_seen": row["last_seen"],
            }
            for row in rows
        ]

    def model(self, account_scope: str, model_id: str) -> dict[str, Any] | None:
        for entry in self.models(account_scope):
            if entry["model_id"] == model_id:
                return entry
        return None

    def is_available(self, account_scope: str, model_id: str) -> bool:
        entry = self.model(account_scope, model_id)
        return bool(entry and entry["available"] and entry["status"] != ModelStatus.RETIRED.value)

    # -- proposals and approvals ----------------------------------------------

    def propose(
        self,
        account_scope: str,
        preferences: dict[Role, str | None] | None = None,
        evaluation_ids: dict[Role, list[str]] | None = None,
    ) -> list[Proposal]:
        """Suggest role bindings from discovered models and family labels.

        A suggestion is not an approval. Family matching is by name only and is
        flagged as such; release date never implies stronger reasoning.
        """
        preferences = preferences or DEFAULT_FAMILY_PREFERENCES
        proposals: list[Proposal] = []
        available = [m for m in self.models(account_scope) if m["available"]]
        for role, family in preferences.items():
            if not family:
                continue
            matches = [
                m
                for m in available
                if family.lower() in m["model_id"].lower() or family.lower() in (m["display_name"] or "").lower()
            ]
            if not matches:
                continue
            choice = sorted(matches, key=lambda m: m["model_id"])[0]
            info = choice["info"]
            effort = info.get("default_effort")
            evals = (evaluation_ids or {}).get(role, [])
            mapping = self.build_mapping(
                account_scope, role, choice["model_id"], effort, evals, list(CODING_TOOLS), ["*"], "pending"
            )
            proposals.append(
                Proposal(
                    role=role,
                    model_id=choice["model_id"],
                    reasoning_effort=effort,
                    rationale=f"name matches the owner's family label '{family}' (name match only; not evidence of quality)",
                    mapping_hash=mapping.binding_hash(),
                    evaluation_ids=evals,
                )
            )
        return proposals

    def build_mapping(
        self,
        account_scope: str,
        role: Role,
        model_id: str,
        reasoning_effort: str | None,
        evaluation_ids: list[str],
        tool_scope: list[str],
        task_scope: list[str],
        approval_id: str,
    ) -> RoleMapping:
        return RoleMapping(
            role=role,
            model_id=model_id,
            reasoning_effort=reasoning_effort,
            task_scope=task_scope,
            tool_scope=tool_scope,
            evaluation_ids=evaluation_ids,
            approval_id=approval_id,
            account_scope=account_scope,
        )

    def approve_mapping(
        self,
        account_scope: str,
        role: Role,
        model_id: str,
        reasoning_effort: str | None,
        *,
        actor: str,
        confirm_hash: str,
        tool_scope: list[str] | None = None,
        task_scope: list[str] | None = None,
        evaluation_ids: list[str] | None = None,
        note: str | None = None,
    ) -> dict[str, Any]:
        entry = self.model(account_scope, model_id)
        if entry is None:
            raise RegistryError(f"model {model_id!r} was not discovered for this account; run discovery first")
        if not entry["available"]:
            raise RegistryError(f"model {model_id!r} is currently unavailable to this account")
        efforts = entry["info"].get("reasoning_efforts") or []
        if reasoning_effort is not None and efforts and reasoning_effort not in efforts:
            raise RegistryError(f"reasoning effort {reasoning_effort!r} is not supported by {model_id} ({efforts})")
        mapping = self.build_mapping(
            account_scope,
            Role(role),
            model_id,
            reasoning_effort,
            evaluation_ids or [],
            tool_scope if tool_scope is not None else list(CODING_TOOLS),
            task_scope or ["*"],
            "pending",
        )
        expected = mapping.binding_hash()
        if confirm_hash != expected:
            raise RegistryError(
                "approval must name the exact mapping hash being approved; "
                f"expected {expected}, got {confirm_hash}"
            )
        approval = Approval(
            id=new_id("apr"),
            actor=actor,
            item_type="role_mapping",
            item_id=f"{account_scope}:{Role(role).value}:{model_id}:{reasoning_effort}",
            item_hash=expected,
            decision="approved",
            at=utc_now(),
        )
        approval.validate()
        mapping.approval_id = approval.id
        now = utc_now()
        with self.store.transaction() as conn:
            conn.execute(
                "INSERT INTO approvals(id, actor, item_type, item_id, item_hash, decision, at) VALUES (?,?,?,?,?,?,?)",
                tuple(approval.to_dict()[k] for k in ("id", "actor", "item_type", "item_id", "item_hash", "decision", "at")),
            )
            parent = conn.execute(
                "SELECT revision FROM registry_revisions WHERE account_scope=? AND active=1", (account_scope,)
            ).fetchone()
            cursor = conn.execute(
                "INSERT INTO registry_revisions(account_scope, parent, note, active, created_at) VALUES (?,?,?,0,?)",
                (account_scope, parent["revision"] if parent else None, note, now),
            )
            revision = int(cursor.lastrowid)
            if parent:
                for row in conn.execute("SELECT * FROM role_mappings WHERE revision=?", (parent["revision"],)):
                    if row["role"] == Role(role).value:
                        continue
                    conn.execute(
                        "INSERT INTO role_mappings(id, revision, role, payload, binding_hash, approval_id, effective_at) "
                        "VALUES (?,?,?,?,?,?,?)",
                        (new_id("map"), revision, row["role"], row["payload"], row["binding_hash"], row["approval_id"], now),
                    )
            conn.execute(
                "INSERT INTO role_mappings(id, revision, role, payload, binding_hash, approval_id, effective_at) VALUES (?,?,?,?,?,?,?)",
                (new_id("map"), revision, Role(role).value, dumps(mapping.to_dict()), expected, approval.id, now),
            )
            # Atomic activation: exactly one active revision per account.
            conn.execute("UPDATE registry_revisions SET active=0 WHERE account_scope=?", (account_scope,))
            conn.execute(
                "UPDATE registry_revisions SET active=1, activated_at=? WHERE revision=?", (now, revision)
            )
            conn.execute(
                "UPDATE registry_models SET status=? WHERE account_scope=? AND model_id=? AND status=?",
                (ModelStatus.APPROVED.value, account_scope, model_id, ModelStatus.CANDIDATE.value),
            )
            self.store.event(
                "model.approval",
                {
                    "approval_id": approval.id,
                    "role": Role(role).value,
                    "model_id": model_id,
                    "reasoning_effort": reasoning_effort,
                    "mapping_hash": expected,
                    "evaluation_ids": evaluation_ids or [],
                    "revision": revision,
                    "actor": actor,
                },
                conn=conn,
            )
        return {"revision": revision, "approval_id": approval.id, "mapping_hash": expected}

    # -- lookup --------------------------------------------------------------

    def active_revision(self, account_scope: str) -> int | None:
        row = self.store.one(
            "SELECT revision FROM registry_revisions WHERE account_scope=? AND active=1", (account_scope,)
        )
        return int(row["revision"]) if row else None

    def active_mappings(self, account_scope: str) -> dict[Role, RoleMapping]:
        revision = self.active_revision(account_scope)
        if revision is None:
            return {}
        result: dict[Role, RoleMapping] = {}
        for row in self.store.all("SELECT * FROM role_mappings WHERE revision=?", (revision,)):
            mapping = RoleMapping.from_dict(json.loads(row["payload"]))
            result[mapping.role] = mapping
        return result

    def binding_for(
        self, account_scope: str, role: Role, required_tools: Iterable[str] = ()
    ) -> tuple[Binding | None, str]:
        """Exact approved binding for ``role``; never a silent replacement."""
        mapping = self.active_mappings(account_scope).get(role)
        if mapping is None:
            return None, f"no approved {role.value} model is configured"
        missing_tools = sorted(set(required_tools) - set(mapping.tool_scope))
        if missing_tools:
            return None, f"approved {role.value} model {mapping.model_id} is not approved for tools {missing_tools}"
        if not self.is_available(account_scope, mapping.model_id):
            return None, f"approved {role.value} model {mapping.model_id} is not currently available"
        return (
            Binding(
                role=role,
                model_id=mapping.model_id,
                reasoning_effort=mapping.reasoning_effort,
                registry_revision=self.active_revision(account_scope),
            ),
            f"approved {role.value} binding",
        )

    def lowest_candidate_ok(self, account_scope: str, required_tools: Iterable[str]) -> tuple[bool, str]:
        binding, note = self.binding_for(account_scope, Role.LOWEST, required_tools)
        return binding is not None, note

    def role_of_model(self, account_scope: str, model_id: str) -> Role | None:
        for role, mapping in self.active_mappings(account_scope).items():
            if mapping.model_id == model_id:
                return role
        return None


def mapping_hash_for(
    account_scope: str,
    role: Role,
    model_id: str,
    reasoning_effort: str | None,
    tool_scope: list[str] | None = None,
    task_scope: list[str] | None = None,
    evaluation_ids: list[str] | None = None,
) -> str:
    return RoleMapping(
        role=role,
        model_id=model_id,
        reasoning_effort=reasoning_effort,
        task_scope=task_scope or ["*"],
        tool_scope=tool_scope if tool_scope is not None else list(CODING_TOOLS),
        evaluation_ids=evaluation_ids or [],
        approval_id="pending",
        account_scope=account_scope,
    ).binding_hash()


__all__ = [
    "CODING_TOOLS",
    "DEFAULT_FAMILY_PREFERENCES",
    "DEFAULT_ROLE_LABELS",
    "Proposal",
    "Registry",
    "RegistryError",
    "content_hash",
    "mapping_hash_for",
]
