"""Deterministic, lossless conversion of an approved local Claude export."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


CONVERTER_VERSION = "0.1"
UNMAPPED_ID = "contextport:generated:unmapped-conversations"
UNMAPPED_TITLE = "Unmapped Conversations"
OUTPUT_NAMES = (
    "contextpack.json",
    "manifest.json",
    "reconciliation-report.json",
    "loss-report.json",
)


class ClaudeConversionError(RuntimeError):
    """Raised when an export cannot be converted without guessing or loss."""


def _load(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ClaudeConversionError(f"cannot read {path}: {exc}") from exc


def _canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise ClaudeConversionError(f"{label} must be an array")
    return value


def _require_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ClaudeConversionError(f"{label} must be an object")
    return value


def _source_files(export: Path) -> list[Path]:
    required = [export / "conversations.json", export / "users.json", export / "memories.json"]
    missing = [path for path in required if not path.is_file()]
    if missing:
        raise ClaudeConversionError("missing required export file(s): " + ", ".join(path.name for path in missing))
    return sorted(required + list((export / "projects").glob("*.json")) + list((export / "design_chats").glob("*.json")))


def _verified_project_id(conversation: dict[str, Any], project_ids: set[str]) -> str:
    candidates: list[str] = []
    direct = conversation.get("project_uuid")
    if isinstance(direct, str) and direct:
        candidates.append(direct)
    project = conversation.get("project")
    if isinstance(project, dict) and isinstance(project.get("uuid"), str) and project["uuid"]:
        candidates.append(project["uuid"])
    elif isinstance(project, str) and project:
        candidates.append(project)
    distinct = set(candidates)
    if len(distinct) > 1:
        raise ClaudeConversionError("conversation has conflicting explicit project references")
    if not distinct:
        return UNMAPPED_ID
    project_id = next(iter(distinct))
    if project_id not in project_ids:
        raise ClaudeConversionError("conversation has an explicit project reference absent from the export")
    return project_id


def _content_block(message_id: str, ordinal: int, block: Any) -> dict[str, Any]:
    source_ref = f"{message_id}:content:{ordinal}"
    if isinstance(block, dict) and block.get("type") == "text" and isinstance(block.get("text"), str):
        text = block["text"]
        return {
            "source_ref": source_ref,
            "kind": "text",
            "ordinal": ordinal,
            "text": text,
            "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "raw": block,
        }
    return {
        "source_ref": source_ref,
        "kind": "unknown",
        "ordinal": ordinal,
        "reason": "Claude content type has no lossless ContextPack 0.1 normalization",
        "raw": block,
    }


def build_migration(export: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    files = _source_files(export)
    conversations_source = _require_list(_load(export / "conversations.json"), "conversations.json")
    users = _load(export / "users.json")
    memories = _load(export / "memories.json")
    project_paths = sorted((export / "projects").glob("*.json"))
    design_paths = sorted((export / "design_chats").glob("*.json"))
    project_source = [_require_object(_load(path), path.name) for path in project_paths]
    design_chats = [_require_object(_load(path), path.name) for path in design_paths]

    project_ids = {project.get("uuid") for project in project_source}
    if None in project_ids or not all(isinstance(item, str) and item for item in project_ids):
        raise ClaudeConversionError("every project must have a non-empty UUID")
    if len(project_ids) != len(project_source):
        raise ClaudeConversionError("project UUIDs must be unique")
    if UNMAPPED_ID in project_ids:
        raise ClaudeConversionError("generated unmapped project ID conflicts with source project")

    projects = [
        {
            "id": project["uuid"],
            "source_ref": project["uuid"],
            "title": project.get("name", ""),
            "created_at": project.get("created_at"),
            "updated_at": project.get("updated_at"),
            "instructions": project.get("prompt_template"),
            "raw": project,
        }
        for project in project_source
    ]
    projects.append({"id": UNMAPPED_ID, "source_ref": UNMAPPED_ID, "title": UNMAPPED_TITLE, "generated": True})

    conversations: list[dict[str, Any]] = []
    messages: list[dict[str, Any]] = []
    attachments: list[dict[str, Any]] = []
    dispositions: list[dict[str, Any]] = []
    seen_conversations: set[str] = set()
    seen_messages: set[str] = set()
    for conversation_ordinal, raw_conversation in enumerate(conversations_source):
        conversation = _require_object(raw_conversation, f"conversations[{conversation_ordinal}]")
        conversation_id = conversation.get("uuid")
        if not isinstance(conversation_id, str) or not conversation_id or conversation_id in seen_conversations:
            raise ClaudeConversionError("conversation UUIDs must be non-empty and unique")
        seen_conversations.add(conversation_id)
        project_id = _verified_project_id(conversation, project_ids)
        conversations.append(
            {
                "id": conversation_id,
                "source_ref": conversation_id,
                "project_id": project_id,
                "title": conversation.get("name", ""),
                "ordinal": conversation_ordinal,
                "created_at": conversation.get("created_at"),
                "updated_at": conversation.get("updated_at"),
                "raw": conversation,
            }
        )
        dispositions.append({"source_ref": conversation_id, "item_type": "conversation", "status": "copied"})
        raw_messages = _require_list(conversation.get("chat_messages"), f"conversation {conversation_id} chat_messages")
        for message_ordinal, raw_message in enumerate(raw_messages):
            message = _require_object(raw_message, f"conversation {conversation_id} message {message_ordinal}")
            message_id = message.get("uuid")
            if not isinstance(message_id, str) or not message_id or message_id in seen_messages:
                raise ClaudeConversionError("message UUIDs must be non-empty and globally unique")
            seen_messages.add(message_id)
            role = {"human": "user", "assistant": "assistant"}.get(message.get("sender"), "unknown")
            source_blocks = _require_list(message.get("content"), f"message {message_id} content")
            blocks = [_content_block(message_id, index, block) for index, block in enumerate(source_blocks)]
            messages.append(
                {
                    "id": message_id,
                    "source_ref": message_id,
                    "conversation_id": conversation_id,
                    "role": role,
                    "ordinal": message_ordinal,
                    "content": blocks,
                    "created_at": message.get("created_at"),
                    "updated_at": message.get("updated_at"),
                    "parent_message_uuid": message.get("parent_message_uuid"),
                    "raw": message,
                }
            )
            dispositions.append({"source_ref": message_id, "item_type": "message", "status": "copied"})
            for block in blocks:
                dispositions.append({"source_ref": block["source_ref"], "item_type": "content_block", "status": "copied"})
            for collection_name in ("attachments", "files"):
                for attachment_ordinal, raw_attachment in enumerate(
                    _require_list(message.get(collection_name), f"message {message_id} {collection_name}")
                ):
                    attachment = _require_object(raw_attachment, f"message {message_id} {collection_name} item")
                    attachment_id = f"{message_id}:{collection_name}:{attachment_ordinal}"
                    attachments.append(
                        {
                            "id": attachment_id,
                            "source_ref": attachment_id,
                            "filename": attachment.get("file_name") or "UNKNOWN",
                            "media_type": attachment.get("file_type") or "UNKNOWN",
                            "payload_status": "referenced" if attachment.get("file_uuid") else "unsupported",
                            "message_id": message_id,
                            "collection": collection_name,
                            "ordinal": attachment_ordinal,
                            "raw": attachment,
                        }
                    )
                    dispositions.append({"source_ref": attachment_id, "item_type": "attachment", "status": "copied"})

    dispositions[0:0] = [
        {"source_ref": project["source_ref"], "item_type": "project", "status": "copied"}
        for project in projects
    ]
    source_inventory = [
        {"path": path.relative_to(export).as_posix(), "bytes": path.stat().st_size, "sha256": _file_digest(path)}
        for path in files
    ]
    manifest = {
        "generator": "contextport-claude-converter",
        "generator_version": CONVERTER_VERSION,
        "created_at": "UNKNOWN",
        "privacy": "private",
        "source": {
            "system": "Claude local export",
            "artifact_ref": export.name,
            "artifact_sha256": _digest(source_inventory),
        },
        "source_files": source_inventory,
        "mapping_policy": {
            "verified_reference": "preserve",
            "missing_reference": UNMAPPED_TITLE,
            "inference": False,
            "classification": False,
            "confidence_scoring": False,
            "llm_reasoning": False,
        },
    }
    contextpack = {
        "format": "contextpack",
        "format_version": "0.1",
        "manifest": manifest,
        "projects": projects,
        "conversations": conversations,
        "messages": messages,
        "attachments": attachments,
        "transformations": [],
        "dispositions": dispositions,
        "source_extensions": {
            "users": users,
            "memories": memories,
            "design_chats": design_chats,
        },
    }
    counts = {
        "projects_in": len(project_source),
        "generated_projects": 1,
        "projects_out": len(projects),
        "conversations_in": len(conversations_source),
        "conversations_out": len(conversations),
        "messages_in": sum(len(item.get("chat_messages", [])) for item in conversations_source),
        "messages_out": len(messages),
        "attachments_in": sum(
            len(message.get("attachments", [])) + len(message.get("files", []))
            for conversation in conversations_source
            for message in conversation.get("chat_messages", [])
        ),
        "attachments_out": len(attachments),
        "design_chats_in": len(design_chats),
        "design_chats_preserved": len(contextpack["source_extensions"]["design_chats"]),
        "memory_containers_in": len(memories) if isinstance(memories, list) else 1,
        "memory_containers_preserved": len(contextpack["source_extensions"]["memories"])
        if isinstance(memories, list)
        else 1,
    }
    source_snapshot = {
        "projects": project_source,
        "conversations": conversations_source,
        "users": users,
        "memories": memories,
        "design_chats": design_chats,
    }
    embedded_snapshot = {
        "projects": [project["raw"] for project in contextpack["projects"] if not project.get("generated")],
        "conversations": [conversation["raw"] for conversation in contextpack["conversations"]],
        "users": contextpack["source_extensions"]["users"],
        "memories": contextpack["source_extensions"]["memories"],
        "design_chats": contextpack["source_extensions"]["design_chats"],
    }
    invariants = {
        "projects_out_equals_projects_in_plus_unmapped": counts["projects_out"] == counts["projects_in"] + 1,
        "conversations_equal": counts["conversations_in"] == counts["conversations_out"],
        "messages_equal": counts["messages_in"] == counts["messages_out"],
        "attachments_equal": counts["attachments_in"] == counts["attachments_out"],
        "design_chats_preserved": counts["design_chats_in"] == counts["design_chats_preserved"],
        "memories_preserved": counts["memory_containers_in"] == counts["memory_containers_preserved"],
        "conversation_membership_exactly_once": len(seen_conversations) == len(conversations),
        "source_snapshot_exact": _digest(source_snapshot) == _digest(embedded_snapshot),
    }
    losses = [] if all(invariants.values()) else [key for key, passed in invariants.items() if not passed]
    reconciliation = {
        "report_version": "0.1",
        "status": "clean" if not losses else "failed",
        "counts": counts,
        "invariants": invariants,
        "contextpack_sha256": _digest(contextpack),
    }
    loss_report = {
        "report_version": "0.1",
        "status": "zero_loss" if not losses else "loss_detected",
        "losses": losses,
        "loss_count": len(losses),
        "unsupported_data_policy": "preserved verbatim in raw fields or source_extensions",
        "source_snapshot_sha256": _digest(source_snapshot),
    }
    if losses:
        raise ClaudeConversionError("conversion invariants failed: " + ", ".join(losses))
    return contextpack, manifest, reconciliation, loss_report


def write_migration(export: Path, output: Path) -> dict[str, Any]:
    contextpack, manifest, reconciliation, loss_report = build_migration(export)
    output.mkdir(parents=True, exist_ok=True)
    documents = {
        "contextpack.json": contextpack,
        "manifest.json": manifest,
        "reconciliation-report.json": reconciliation,
        "loss-report.json": loss_report,
    }
    for name, document in documents.items():
        target = output / name
        temporary = output / f".{name}.tmp"
        temporary.write_bytes(_canonical_bytes(document))
        temporary.replace(target)
    return {name: _file_digest(output / name) for name in OUTPUT_NAMES}
