"""Assistant-neutral, deterministic reconstruction planning."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from review import ReviewError, canonical_digest, validate_decision


RECONSTRUCTION_VERSION = "0.1"


class ReconstructionError(ValueError):
    """Raised when an approved dry-run plan cannot be built safely."""


def _key(source_digest: str, kind: str, source_id: str) -> str:
    raw = f"{source_digest}\0{kind}\0{source_id}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def build_reconstruction_plan(
    document: dict[str, Any],
    segregation_plan: dict[str, Any],
    review_package: dict[str, Any],
    decision: dict[str, Any],
) -> dict[str, Any]:
    """Build an exact-content dry-run plan after explicit human approval."""
    try:
        validated_decision = validate_decision(review_package, decision)
    except ReviewError as exc:
        raise ReconstructionError(str(exc)) from exc
    if validated_decision["decision"] != "approve":
        raise ReconstructionError("reconstruction requires an approved review decision")
    if review_package.get("segregation_plan_sha256") != segregation_plan.get("plan_sha256"):
        raise ReconstructionError("review package does not match segregation plan")
    if review_package.get("source_artifact_sha256") != document["manifest"]["source"]["artifact_sha256"]:
        raise ReconstructionError("review package does not match ContextPack source")

    source_digest = document["manifest"]["source"]["artifact_sha256"]
    conversations = {item["id"]: item for item in document["conversations"]}
    messages_by_conversation: dict[str, list[dict[str, Any]]] = {}
    for message in document["messages"]:
        messages_by_conversation.setdefault(message["conversation_id"], []).append(message)

    operations: list[dict[str, Any]] = []
    dispositions: list[dict[str, Any]] = []
    for group in segregation_plan["groups"]:
        container_operation_id: str | None = None
        if group["group_kind"] == "project":
            target = group.get("destination_container_id")
            if not target:
                raise ReconstructionError(f"project {group['project_id']!r} has no approved destination mapping")
            container_operation_id = f"container:{group['project_id']}"
            operations.append(
                {
                    "operation_id": container_operation_id,
                    "kind": "ensure_container",
                    "idempotency_key": _key(source_digest, "container", group["project_id"]),
                    "depends_on": [],
                    "target": {"container_ref": target},
                    "payload": {"source_project_id": group["project_id"], "title": group["title"]},
                }
            )
        else:
            target = "default"

        for planned in group["conversations"]:
            conversation = conversations[planned["conversation_id"]]
            conversation_operation_id = f"conversation:{conversation['id']}"
            operations.append(
                {
                    "operation_id": conversation_operation_id,
                    "kind": "ensure_conversation",
                    "idempotency_key": _key(source_digest, "conversation", conversation["id"]),
                    "depends_on": [container_operation_id] if container_operation_id else [],
                    "target": {"container_ref": target},
                    "payload": {
                        "source_conversation_id": conversation["id"],
                        "title": conversation["title"],
                        "ordinal": conversation["ordinal"],
                    },
                }
            )
            messages = sorted(messages_by_conversation.get(conversation["id"], []), key=lambda item: item["ordinal"])
            for message in messages:
                operation_id = f"message:{message['id']}"
                operations.append(
                    {
                        "operation_id": operation_id,
                        "kind": "append_message",
                        "idempotency_key": _key(source_digest, "message", message["id"]),
                        "depends_on": [conversation_operation_id],
                        "target": {"conversation_ref": conversation_operation_id},
                        "payload": {
                            "source_message_id": message["id"],
                            "role": message["role"],
                            "ordinal": message["ordinal"],
                            "content": message["content"],
                        },
                    }
                )
                dispositions.append(
                    {"source_ref": message["source_ref"], "item_type": "message", "status": "planned"}
                )

    plan = {
        "reconstruction_version": RECONSTRUCTION_VERSION,
        "status": "dry_run_ready",
        "source_artifact_sha256": source_digest,
        "segregation_plan_sha256": segregation_plan["plan_sha256"],
        "review_package_sha256": review_package["review_package_sha256"],
        "review_decision": "approve",
        "operations": operations,
        "dispositions": dispositions,
        "writes_performed": False,
        "summary": {
            "operations": len(operations),
            "containers": sum(item["kind"] == "ensure_container" for item in operations),
            "conversations": sum(item["kind"] == "ensure_conversation" for item in operations),
            "messages": sum(item["kind"] == "append_message" for item in operations),
        },
    }
    plan["reconstruction_plan_sha256"] = canonical_digest(plan)
    return plan
