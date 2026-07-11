"""Deterministic project segregation for validated ContextPack documents."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from typing import Any, Callable


SEGREGATION_VERSION = "0.1"
MAPPING_VERSION = "0.1"


class SegregationError(ValueError):
    """Raised when a segregation input is invalid rather than ambiguous."""


def _canonical_digest(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _mapping_index(mappings: Any, project_ids: set[str]) -> tuple[dict[str, str], list[dict[str, Any]]]:
    if mappings is None:
        return {}, []
    if not isinstance(mappings, dict) or mappings.get("mapping_version") != MAPPING_VERSION:
        raise SegregationError(f"mapping_version must be {MAPPING_VERSION!r}")
    rows = mappings.get("project_mappings")
    if not isinstance(rows, list):
        raise SegregationError("project_mappings must be an array")

    destinations: dict[str, set[str]] = defaultdict(set)
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise SegregationError(f"project_mappings[{index}] must be an object")
        project_id = row.get("source_project_id")
        destination_id = row.get("destination_container_id")
        if not isinstance(project_id, str) or not project_id:
            raise SegregationError(f"project_mappings[{index}].source_project_id must be a non-empty string")
        if project_id not in project_ids:
            raise SegregationError(f"project_mappings[{index}] references unknown source project {project_id!r}")
        if not isinstance(destination_id, str) or not destination_id:
            raise SegregationError(
                f"project_mappings[{index}].destination_container_id must be a non-empty string"
            )
        destinations[project_id].add(destination_id)

    ambiguous = [
        {"source_project_id": project_id, "destination_container_ids": sorted(destination_ids)}
        for project_id, destination_ids in sorted(destinations.items())
        if len(destination_ids) > 1
    ]
    resolved = {
        project_id: next(iter(destination_ids))
        for project_id, destination_ids in destinations.items()
        if len(destination_ids) == 1
    }
    return resolved, ambiguous


def segregate(
    document: Any,
    mappings: Any = None,
    *,
    validator: Callable[[Any], list[str]],
) -> dict[str, Any]:
    """Return a content-free, deterministic segregation plan or decision artifact."""
    validation_errors = validator(document)
    if validation_errors:
        raise SegregationError("ContextPack validation failed: " + "; ".join(validation_errors))

    projects = document["projects"]
    conversations = document["conversations"]
    messages = document["messages"]
    project_ids = {project["id"] for project in projects}
    resolved_mappings, ambiguous = _mapping_index(mappings, project_ids)
    if ambiguous:
        return {
            "segregation_version": SEGREGATION_VERSION,
            "status": "decision_required",
            "reason": "ambiguous_project_mapping",
            "ambiguities": ambiguous,
            "plan_emitted": False,
        }

    conversations_by_project: dict[str | None, list[dict[str, Any]]] = defaultdict(list)
    for conversation in conversations:
        conversations_by_project[conversation["project_id"]].append(conversation)
    messages_by_conversation: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for message in messages:
        messages_by_conversation[message["conversation_id"]].append(message)

    def conversation_entry(conversation: dict[str, Any]) -> dict[str, Any]:
        ordered_messages = sorted(messages_by_conversation[conversation["id"]], key=lambda item: item["ordinal"])
        return {
            "conversation_id": conversation["id"],
            "source_ref": conversation["source_ref"],
            "title": conversation["title"],
            "ordinal": conversation["ordinal"],
            "message_ids": [message["id"] for message in ordered_messages],
            "message_count": len(ordered_messages),
        }

    groups: list[dict[str, Any]] = []
    for project in projects:
        project_conversations = sorted(
            conversations_by_project[project["id"]], key=lambda item: item["ordinal"]
        )
        destination_id = resolved_mappings.get(project["id"])
        groups.append(
            {
                "group_kind": "project",
                "project_id": project["id"],
                "source_ref": project["source_ref"],
                "title": project["title"],
                "mapping_status": "mapped" if destination_id else "unmapped",
                "destination_container_id": destination_id,
                "conversations": [conversation_entry(item) for item in project_conversations],
            }
        )

    ungrouped = sorted(conversations_by_project[None], key=lambda item: item["ordinal"])
    if ungrouped:
        groups.append(
            {
                "group_kind": "ungrouped",
                "project_id": None,
                "source_ref": None,
                "title": None,
                "mapping_status": "not_applicable",
                "destination_container_id": None,
                "conversations": [conversation_entry(item) for item in ungrouped],
            }
        )

    membership = [
        {"conversation_id": conversation["conversation_id"], "group_project_id": group["project_id"]}
        for group in groups
        for conversation in group["conversations"]
    ]
    plan = {
        "segregation_version": SEGREGATION_VERSION,
        "status": "ready",
        "source_artifact_sha256": document["manifest"]["source"]["artifact_sha256"],
        "groups": groups,
        "membership": membership,
        "summary": {
            "project_groups": len(projects),
            "ungrouped_groups": 1 if ungrouped else 0,
            "conversations": len(conversations),
            "messages": len(messages),
        },
        "content_emitted": False,
    }
    plan["plan_sha256"] = _canonical_digest(plan)
    return plan
