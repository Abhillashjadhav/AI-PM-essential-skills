"""Independent source-versus-plan reconciliation."""

from __future__ import annotations

from collections import Counter
from typing import Any

from review import canonical_digest


RECONCILIATION_VERSION = "0.1"


def reconcile(document: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    """Compare source inventory and exact payloads without trusting writer flags."""
    differences: list[dict[str, str]] = []
    unsigned = {key: value for key, value in plan.items() if key != "reconstruction_plan_sha256"}
    if canonical_digest(unsigned) != plan.get("reconstruction_plan_sha256"):
        differences.append({"category": "integrity_failure", "item_type": "plan", "source_id": "plan", "detail": "plan digest mismatch"})
    source_digest = document["manifest"]["source"]["artifact_sha256"]
    if plan.get("source_artifact_sha256") != source_digest:
        differences.append({"category": "integrity_failure", "item_type": "source", "source_id": "source", "detail": "source digest mismatch"})

    operations = plan.get("operations") if isinstance(plan.get("operations"), list) else []
    operation_ids = [item.get("operation_id") for item in operations if isinstance(item, dict)]
    for operation_id, count in Counter(operation_ids).items():
        if count > 1:
            differences.append({"category": "duplicate", "item_type": "operation", "source_id": str(operation_id), "detail": f"operation appears {count} times"})
    by_id = {item.get("operation_id"): item for item in operations if isinstance(item, dict)}

    expected_ids: set[str] = set()
    for project in document["projects"]:
        operation_id = f"container:{project['id']}"
        expected_ids.add(operation_id)
        operation = by_id.get(operation_id)
        if operation is None:
            differences.append({"category": "omission", "item_type": "project", "source_id": project["id"], "detail": "container operation missing"})
        elif operation.get("payload", {}).get("title") != project["title"]:
            differences.append({"category": "content_difference", "item_type": "project", "source_id": project["id"], "detail": "project title differs"})

    messages_by_conversation: dict[str, list[dict[str, Any]]] = {}
    for message in document["messages"]:
        messages_by_conversation.setdefault(message["conversation_id"], []).append(message)
    for conversation in document["conversations"]:
        operation_id = f"conversation:{conversation['id']}"
        expected_ids.add(operation_id)
        operation = by_id.get(operation_id)
        if operation is None:
            differences.append({"category": "omission", "item_type": "conversation", "source_id": conversation["id"], "detail": "conversation operation missing"})
        else:
            payload = operation.get("payload", {})
            if payload.get("title") != conversation["title"]:
                differences.append({"category": "content_difference", "item_type": "conversation", "source_id": conversation["id"], "detail": "conversation title differs"})
            if payload.get("ordinal") != conversation["ordinal"]:
                differences.append({"category": "ordering_difference", "item_type": "conversation", "source_id": conversation["id"], "detail": "conversation ordinal differs"})
        for message in messages_by_conversation.get(conversation["id"], []):
            message_operation_id = f"message:{message['id']}"
            expected_ids.add(message_operation_id)
            message_operation = by_id.get(message_operation_id)
            if message_operation is None:
                differences.append({"category": "omission", "item_type": "message", "source_id": message["id"], "detail": "message operation missing"})
                continue
            payload = message_operation.get("payload", {})
            if payload.get("role") != message["role"] or payload.get("content") != message["content"]:
                differences.append({"category": "content_difference", "item_type": "message", "source_id": message["id"], "detail": "role or content blocks differ"})
            if payload.get("ordinal") != message["ordinal"]:
                differences.append({"category": "ordering_difference", "item_type": "message", "source_id": message["id"], "detail": "message ordinal differs"})

    for extra in sorted(set(str(item) for item in operation_ids) - expected_ids):
        differences.append({"category": "extra", "item_type": "operation", "source_id": extra, "detail": "operation has no source record"})

    counts = Counter(item["category"] for item in differences)
    report = {
        "reconciliation_version": RECONCILIATION_VERSION,
        "status": "clean" if not differences else "failed",
        "source_artifact_sha256": source_digest,
        "reconstruction_plan_sha256": plan.get("reconstruction_plan_sha256"),
        "writer_status_flags_used": False,
        "differences": differences,
        "difference_counts": dict(sorted(counts.items())),
        "summary": {
            "source_projects": len(document["projects"]),
            "source_conversations": len(document["conversations"]),
            "source_messages": len(document["messages"]),
            "plan_operations": len(operations),
            "differences": len(differences),
        },
    }
    report["reconciliation_report_sha256"] = canonical_digest(report)
    return report
