"""Deterministic incremental change and conflict planning."""

from __future__ import annotations

from typing import Any, Callable

from review import canonical_digest


SYNC_VERSION = "0.1"


class SyncError(ValueError):
    pass


def _inventory(document: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    fields = {
        "project": ("projects", ("source_ref", "title")),
        "conversation": ("conversations", ("source_ref", "project_id", "title", "ordinal")),
        "message": ("messages", ("source_ref", "conversation_id", "role", "ordinal", "content")),
        "attachment": ("attachments", ("source_ref", "filename", "media_type", "payload_status")),
    }
    result: dict[tuple[str, str], dict[str, Any]] = {}
    for item_type, (collection, names) in fields.items():
        for item in document[collection]:
            payload = {name: item.get(name) for name in names}
            result[(item_type, item["id"])] = {
                "item_type": item_type,
                "item_id": item["id"],
                "payload": payload,
                "sha256": canonical_digest(payload),
            }
    return result


def _change_kind(item_type: str, before: dict[str, Any] | None, after: dict[str, Any] | None) -> str:
    if before is None:
        return "append" if item_type == "message" else "add"
    if after is None:
        return "delete"
    changed = {key for key in set(before) | set(after) if before.get(key) != after.get(key)}
    if changed == {"title"}:
        return "rename"
    parent = "project_id" if item_type == "conversation" else "conversation_id"
    if changed == {parent}:
        return "move"
    if changed == {"ordinal"}:
        return "reorder"
    return "edit"


def plan_sync(
    previous: dict[str, Any],
    current: dict[str, Any],
    peer_state: Any = None,
    *,
    validator: Callable[[Any], list[str]],
) -> dict[str, Any]:
    for label, document in (("previous", previous), ("current", current)):
        errors = validator(document)
        if errors:
            raise SyncError(f"{label} ContextPack validation failed: {'; '.join(errors)}")
    before = _inventory(previous)
    after = _inventory(current)
    peer: dict[tuple[str, str], dict[str, Any]] = {}
    if peer_state is not None:
        if not isinstance(peer_state, dict) or not isinstance(peer_state.get("items"), list):
            raise SyncError("peer_state.items must be an array")
        for row in peer_state["items"]:
            peer[(row.get("item_type"), row.get("item_id"))] = row

    changes: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    tombstones: list[dict[str, Any]] = []
    for key in sorted(set(before) | set(after)):
        old = before.get(key)
        new = after.get(key)
        if old and new and old["sha256"] == new["sha256"]:
            continue
        item_type, item_id = key
        kind = _change_kind(item_type, old["payload"] if old else None, new["payload"] if new else None)
        change = {
            "change_id": f"{item_type}:{item_id}:{kind}",
            "kind": kind,
            "item_type": item_type,
            "item_id": item_id,
            "before_sha256": old["sha256"] if old else None,
            "after_sha256": new["sha256"] if new else None,
            "before": old["payload"] if old else None,
            "after": new["payload"] if new else None,
        }
        changes.append(change)
        if kind == "delete":
            tombstones.append({"item_type": item_type, "item_id": item_id, "last_sha256": old["sha256"]})
        peer_row = peer.get(key)
        if peer_row and old and peer_row.get("base_sha256") == old["sha256"] and peer_row.get("current_sha256") != old["sha256"]:
            conflicts.append(
                {
                    "item_type": item_type,
                    "item_id": item_id,
                    "source_change_id": change["change_id"],
                    "base_sha256": old["sha256"],
                    "source_sha256": new["sha256"] if new else None,
                    "peer_sha256": peer_row.get("current_sha256"),
                    "resolution": "human_required",
                }
            )

    plan = {
        "sync_version": SYNC_VERSION,
        "status": "conflict" if conflicts else "ready",
        "checkpoints": {
            "previous_source_sha256": previous["manifest"]["source"]["artifact_sha256"],
            "current_source_sha256": current["manifest"]["source"]["artifact_sha256"],
        },
        "changes": changes,
        "tombstones": tombstones,
        "conflicts": conflicts,
        "automatic_apply_performed": False,
        "automatic_conflict_resolution": False,
    }
    plan["replay_key"] = canonical_digest(plan)
    return plan
