"""Offline human-review packages, HTML rendering, and decision validation."""

from __future__ import annotations

import hashlib
import html
import json
from collections import Counter
from typing import Any


REVIEW_VERSION = "0.1"
DECISION_VERSION = "0.1"
REQUIRED_CONFIRMATIONS = (
    "project_boundaries",
    "conversation_titles_and_order",
    "roles_and_content_kinds",
    "attachment_and_unsupported_dispositions",
    "destination_mappings_and_transformations",
)


class ReviewError(ValueError):
    """Raised when review input or a decision artifact is invalid."""


def canonical_digest(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _sample_conversations(conversations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(conversations) <= 2:
        return conversations
    return [conversations[0], conversations[-1]]


def build_review_package(document: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    """Build a deterministic metadata-only review package from a ready plan."""
    if plan.get("status") != "ready" or not isinstance(plan.get("plan_sha256"), str):
        raise ReviewError("a ready segregation plan with plan_sha256 is required")
    unsigned_plan = {key: value for key, value in plan.items() if key != "plan_sha256"}
    if canonical_digest(unsigned_plan) != plan["plan_sha256"]:
        raise ReviewError("segregation plan digest does not match plan content")
    if plan.get("source_artifact_sha256") != document["manifest"]["source"]["artifact_sha256"]:
        raise ReviewError("segregation plan source digest does not match ContextPack")
    document_conversation_ids = [item["id"] for item in document["conversations"]]
    membership_ids = [item["conversation_id"] for item in plan.get("membership", [])]
    if sorted(document_conversation_ids) != sorted(membership_ids) or len(membership_ids) != len(set(membership_ids)):
        raise ReviewError("segregation plan membership does not exactly cover ContextPack conversations")

    conversations = {item["id"]: item for item in document["conversations"]}
    messages_by_conversation: dict[str, list[dict[str, Any]]] = {}
    for message in document["messages"]:
        messages_by_conversation.setdefault(message["conversation_id"], []).append(message)

    groups: list[dict[str, Any]] = []
    for group in plan["groups"]:
        samples: list[dict[str, Any]] = []
        for planned in _sample_conversations(group["conversations"]):
            try:
                conversation = conversations[planned["conversation_id"]]
            except KeyError as exc:
                raise ReviewError(f"segregation plan references unknown conversation {exc.args[0]!r}") from exc
            messages = sorted(messages_by_conversation.get(conversation["id"], []), key=lambda item: item["ordinal"])
            kinds = Counter(
                block["kind"]
                for message in messages
                for block in message["content"]
            )
            samples.append(
                {
                    "conversation_id": conversation["id"],
                    "title": conversation["title"],
                    "ordinal": conversation["ordinal"],
                    "message_count": len(messages),
                    "role_sequence": [message["role"] for message in messages],
                    "content_kind_counts": dict(sorted(kinds.items())),
                    "attachment_references": kinds.get("attachment", 0),
                }
            )
        groups.append(
            {
                "group_kind": group["group_kind"],
                "project_id": group["project_id"],
                "title": group["title"],
                "mapping_status": group["mapping_status"],
                "destination_container_id": group["destination_container_id"],
                "conversation_count": len(group["conversations"]),
                "samples": samples,
            }
        )

    disposition_counts = Counter(item["status"] for item in document["dispositions"])
    package = {
        "review_version": REVIEW_VERSION,
        "status": "awaiting_human_review",
        "segregation_plan_sha256": plan["plan_sha256"],
        "source_artifact_sha256": plan["source_artifact_sha256"],
        "selection": {
            "algorithm": "first-and-last-per-group-v1",
            "maximum_conversations_per_group": 2,
            "all_groups_represented": True,
        },
        "groups": groups,
        "disposition_counts": dict(sorted(disposition_counts.items())),
        "required_confirmations": list(REQUIRED_CONFIRMATIONS),
        "message_text_emitted": False,
        "unknown_raw_payload_emitted": False,
    }
    package["review_package_sha256"] = canonical_digest(package)
    return package


def validate_decision(package: dict[str, Any], decision: Any) -> dict[str, Any]:
    """Validate and normalize a review decision bound to one review package."""
    if not isinstance(decision, dict) or decision.get("decision_version") != DECISION_VERSION:
        raise ReviewError(f"decision_version must be {DECISION_VERSION!r}")
    if decision.get("review_package_sha256") != package.get("review_package_sha256"):
        raise ReviewError("decision does not match review package digest")
    verdict = decision.get("decision")
    if verdict not in {"approve", "reject"}:
        raise ReviewError("decision must be 'approve' or 'reject'")
    confirmations = decision.get("confirmations")
    if not isinstance(confirmations, dict):
        raise ReviewError("confirmations must be an object")
    normalized_confirmations: dict[str, bool] = {}
    for name in REQUIRED_CONFIRMATIONS:
        value = confirmations.get(name)
        if not isinstance(value, bool):
            raise ReviewError(f"confirmation {name!r} must be boolean")
        normalized_confirmations[name] = value
    if verdict == "approve" and not all(normalized_confirmations.values()):
        raise ReviewError("approval requires every confirmation")
    note = decision.get("note", "")
    if not isinstance(note, str):
        raise ReviewError("note must be a string")
    return {
        "decision_version": DECISION_VERSION,
        "review_package_sha256": package["review_package_sha256"],
        "decision": verdict,
        "confirmations": normalized_confirmations,
        "note": note,
        "automatic_repair_authorized": False,
    }


def render_review_html(package: dict[str, Any]) -> str:
    """Render a standalone HTML review form with inert, escaped metadata."""
    digest = html.escape(package["review_package_sha256"], quote=True)
    group_sections: list[str] = []
    for group in package["groups"]:
        title = "Ungrouped" if group["title"] is None else str(group["title"])
        samples = "".join(
            "<li><strong>" + html.escape(str(sample["title"])) + "</strong> "
            + "<code>" + html.escape(sample["conversation_id"]) + "</code> "
            + f"— {sample['message_count']} message(s); roles: "
            + html.escape(", ".join(sample["role_sequence"]) or "none")
            + "; kinds: " + html.escape(json.dumps(sample["content_kind_counts"], sort_keys=True))
            + "</li>"
            for sample in group["samples"]
        ) or "<li>No conversations in this group.</li>"
        group_sections.append(
            "<section><h2>" + html.escape(title) + "</h2>"
            + "<p>Project ID: <code>" + html.escape(str(group["project_id"])) + "</code>; "
            + "mapping: " + html.escape(group["mapping_status"]) + "; "
            + f"conversations: {group['conversation_count']}</p><ul>{samples}</ul></section>"
        )
    checkboxes = "".join(
        f'<label><input type="checkbox" data-confirmation="{html.escape(name, quote=True)}"> '
        + html.escape(name.replace("_", " ").title()) + "</label>"
        for name in REQUIRED_CONFIRMATIONS
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>ContextPort human review</title>
<style>body{{font:16px system-ui;max-width:900px;margin:2rem auto;padding:0 1rem}}section{{border:1px solid #ccc;padding:1rem;margin:1rem 0}}label{{display:block;margin:.5rem 0}}button{{margin:.5rem .5rem .5rem 0;padding:.6rem 1rem}}code{{overflow-wrap:anywhere}}</style></head>
<body><h1>ContextPort human review</h1><p>Review package: <code>{digest}</code></p>
<p>This page contains metadata only. Imported values are displayed as inert escaped text.</p>
{''.join(group_sections)}
<section><h2>Required confirmations</h2>{checkboxes}
<label>Optional note <textarea id="note"></textarea></label>
<button type="button" onclick="downloadDecision('approve')">Approve</button>
<button type="button" onclick="downloadDecision('reject')">Reject</button></section>
<script>
function downloadDecision(verdict) {{
  const checks = [...document.querySelectorAll('[data-confirmation]')];
  const confirmations = Object.fromEntries(checks.map(x => [x.dataset.confirmation, x.checked]));
  if (verdict === 'approve' && !checks.every(x => x.checked)) {{ alert('Approval requires every confirmation.'); return; }}
  const decision = {{decision_version:'0.1',review_package_sha256:'{digest}',decision:verdict,confirmations,note:document.getElementById('note').value}};
  const link = document.createElement('a');
  link.href = URL.createObjectURL(new Blob([JSON.stringify(decision, null, 2)], {{type:'application/json'}}));
  link.download = 'contextport-review-decision.json'; link.click(); URL.revokeObjectURL(link.href);
}}
</script></body></html>"""
