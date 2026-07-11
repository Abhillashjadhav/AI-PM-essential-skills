#!/usr/bin/env python3
"""Dependency-free command line validation for experimental ContextPack 0.1."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any


FORMAT = "contextpack"
FORMAT_VERSION = "0.1"
DISPOSITIONS = {"copied", "transformed", "skipped", "failed", "ambiguous", "unsupported"}
ITEM_TYPES = {"project", "conversation", "message", "content_block", "attachment"}
ROLES = {"user", "assistant", "system", "tool", "unknown"}
SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _is_string(value: Any) -> bool:
    return isinstance(value, str)


def _require_object(value: Any, path: str, errors: list[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        errors.append(f"{path}: expected object")
        return {}
    return value


def _require_array(value: Any, path: str, errors: list[str]) -> list[Any]:
    if not isinstance(value, list):
        errors.append(f"{path}: expected array")
        return []
    return value


def _required_string(obj: dict[str, Any], key: str, path: str, errors: list[str]) -> str:
    value = obj.get(key)
    if not _is_string(value) or not value:
        errors.append(f"{path}.{key}: expected non-empty string")
        return ""
    return value


def _ordinal(obj: dict[str, Any], path: str, errors: list[str]) -> int | None:
    value = obj.get("ordinal")
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        errors.append(f"{path}.ordinal: expected non-negative integer")
        return None
    return value


def _unique_ids(records: list[Any], path: str, errors: list[str]) -> set[str]:
    ids: list[str] = []
    for index, value in enumerate(records):
        record = _require_object(value, f"{path}[{index}]", errors)
        identifier = _required_string(record, "id", f"{path}[{index}]", errors)
        if identifier:
            ids.append(identifier)
    for identifier, count in Counter(ids).items():
        if count > 1:
            errors.append(f"{path}: duplicate id {identifier!r}")
    return set(ids)


def _check_unique_ordinals(pairs: list[tuple[str, int]], path: str, errors: list[str]) -> None:
    for pair, count in Counter(pairs).items():
        if count > 1:
            errors.append(f"{path}: duplicate ordinal {pair[1]} within {pair[0]!r}")


def validate(document: Any) -> list[str]:
    """Return all deterministic validation errors for a decoded ContextPack."""
    errors: list[str] = []
    root = _require_object(document, "$", errors)
    if not root:
        return errors

    if root.get("format") != FORMAT:
        errors.append(f"$.format: expected {FORMAT!r}")
    if root.get("format_version") != FORMAT_VERSION:
        errors.append(f"$.format_version: expected {FORMAT_VERSION!r}")

    manifest = _require_object(root.get("manifest"), "$.manifest", errors)
    _required_string(manifest, "generator", "$.manifest", errors)
    _required_string(manifest, "generator_version", "$.manifest", errors)
    _required_string(manifest, "created_at", "$.manifest", errors)
    if manifest.get("privacy") not in {"synthetic", "private"}:
        errors.append("$.manifest.privacy: expected 'synthetic' or 'private'")
    source = _require_object(manifest.get("source"), "$.manifest.source", errors)
    _required_string(source, "system", "$.manifest.source", errors)
    _required_string(source, "artifact_ref", "$.manifest.source", errors)
    source_digest = _required_string(source, "artifact_sha256", "$.manifest.source", errors)
    if source_digest and not SHA256.fullmatch(source_digest):
        errors.append("$.manifest.source.artifact_sha256: expected lowercase SHA-256")

    projects = _require_array(root.get("projects"), "$.projects", errors)
    conversations = _require_array(root.get("conversations"), "$.conversations", errors)
    messages = _require_array(root.get("messages"), "$.messages", errors)
    attachments = _require_array(root.get("attachments"), "$.attachments", errors)
    transformations = _require_array(root.get("transformations"), "$.transformations", errors)
    dispositions = _require_array(root.get("dispositions"), "$.dispositions", errors)

    project_ids = _unique_ids(projects, "$.projects", errors)
    conversation_ids = _unique_ids(conversations, "$.conversations", errors)
    _unique_ids(messages, "$.messages", errors)
    attachment_ids = _unique_ids(attachments, "$.attachments", errors)
    transformation_ids = _unique_ids(transformations, "$.transformations", errors)
    represented_items: set[tuple[str, str]] = set()

    for index, value in enumerate(projects):
        record = _require_object(value, f"$.projects[{index}]", errors)
        source_ref = _required_string(record, "source_ref", f"$.projects[{index}]", errors)
        if source_ref:
            represented_items.add(("project", source_ref))
        if not _is_string(record.get("title")):
            errors.append(f"$.projects[{index}].title: expected string")

    conversation_ordinals: list[tuple[str, int]] = []
    for index, value in enumerate(conversations):
        path = f"$.conversations[{index}]"
        record = _require_object(value, path, errors)
        source_ref = _required_string(record, "source_ref", path, errors)
        if source_ref:
            represented_items.add(("conversation", source_ref))
        if not _is_string(record.get("title")):
            errors.append(f"{path}.title: expected string")
        project_id = record.get("project_id")
        if project_id is not None and project_id not in project_ids:
            errors.append(f"{path}.project_id: unresolved reference {project_id!r}")
        ordinal = _ordinal(record, path, errors)
        if ordinal is not None:
            conversation_ordinals.append((str(project_id), ordinal))
    _check_unique_ordinals(conversation_ordinals, "$.conversations", errors)

    message_ordinals: list[tuple[str, int]] = []
    for index, value in enumerate(messages):
        path = f"$.messages[{index}]"
        record = _require_object(value, path, errors)
        source_ref = _required_string(record, "source_ref", path, errors)
        if source_ref:
            represented_items.add(("message", source_ref))
        conversation_id = record.get("conversation_id")
        if conversation_id not in conversation_ids:
            errors.append(f"{path}.conversation_id: unresolved reference {conversation_id!r}")
        if record.get("role") not in ROLES:
            errors.append(f"{path}.role: unsupported role {record.get('role')!r}")
        ordinal = _ordinal(record, path, errors)
        if ordinal is not None:
            message_ordinals.append((str(conversation_id), ordinal))
        blocks = _require_array(record.get("content"), f"{path}.content", errors)
        block_ordinals: list[tuple[str, int]] = []
        for block_index, block_value in enumerate(blocks):
            block_path = f"{path}.content[{block_index}]"
            block = _require_object(block_value, block_path, errors)
            block_source_ref = _required_string(block, "source_ref", block_path, errors)
            if block_source_ref:
                represented_items.add(("content_block", block_source_ref))
            block_ordinal = _ordinal(block, block_path, errors)
            if block_ordinal is not None:
                block_ordinals.append((str(record.get("id")), block_ordinal))
            kind = block.get("kind")
            if kind == "text":
                text = block.get("text")
                digest = block.get("sha256")
                if not _is_string(text):
                    errors.append(f"{block_path}.text: expected string")
                elif digest != hashlib.sha256(text.encode("utf-8")).hexdigest():
                    errors.append(f"{block_path}.sha256: digest does not match exact text")
            elif kind == "attachment":
                if block.get("attachment_id") not in attachment_ids:
                    errors.append(f"{block_path}.attachment_id: unresolved reference {block.get('attachment_id')!r}")
            elif kind == "unknown":
                _required_string(block, "reason", block_path, errors)
            else:
                errors.append(f"{block_path}.kind: unsupported kind {kind!r}")
        _check_unique_ordinals(block_ordinals, f"{path}.content", errors)
    _check_unique_ordinals(message_ordinals, "$.messages", errors)

    for index, value in enumerate(attachments):
        path = f"$.attachments[{index}]"
        record = _require_object(value, path, errors)
        source_ref = _required_string(record, "source_ref", path, errors)
        if source_ref:
            represented_items.add(("attachment", source_ref))
        _required_string(record, "filename", path, errors)
        _required_string(record, "media_type", path, errors)
        if record.get("payload_status") not in {"referenced", "unsupported"}:
            errors.append(f"{path}.payload_status: expected 'referenced' or 'unsupported'")

    for index, value in enumerate(transformations):
        path = f"$.transformations[{index}]"
        record = _require_object(value, path, errors)
        _required_string(record, "source_ref", path, errors)
        _required_string(record, "kind", path, errors)
        _required_string(record, "reason", path, errors)

    seen_dispositions: set[tuple[str, str]] = set()
    for index, value in enumerate(dispositions):
        path = f"$.dispositions[{index}]"
        record = _require_object(value, path, errors)
        source_ref = _required_string(record, "source_ref", path, errors)
        item_type = record.get("item_type")
        status = record.get("status")
        if item_type not in ITEM_TYPES:
            errors.append(f"{path}.item_type: unsupported item type {item_type!r}")
        if status not in DISPOSITIONS:
            errors.append(f"{path}.status: unsupported disposition {status!r}")
        key = (str(item_type), source_ref)
        if source_ref and key in seen_dispositions:
            errors.append(f"{path}: duplicate disposition for {item_type!r} {source_ref!r}")
        seen_dispositions.add(key)
        if status != "copied":
            _required_string(record, "reason", path, errors)
        if status == "transformed" and record.get("transformation_id") not in transformation_ids:
            errors.append(f"{path}.transformation_id: unresolved transformation")

    for item_type, source_ref in sorted(represented_items - seen_dispositions):
        errors.append(f"$.dispositions: missing disposition for {item_type!r} {source_ref!r}")

    return sorted(errors)


def _validate_file(path: Path) -> int:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"FAIL {path}: {exc}", file=sys.stderr)
        return 2
    errors = validate(document)
    if errors:
        print(f"FAIL {path}: {len(errors)} error(s)")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"PASS {path}: ContextPack {FORMAT_VERSION} is valid")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="contextport", description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate_parser = subparsers.add_parser("validate", help="validate one ContextPack JSON document")
    validate_parser.add_argument("path", type=Path)
    arguments = parser.parse_args(argv)
    if arguments.command == "validate":
        return _validate_file(arguments.path)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
