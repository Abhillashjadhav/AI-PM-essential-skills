#!/usr/bin/env python3
"""Dependency-free command line validation for experimental ContextPack 0.1."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


FORMAT = "contextpack"
FORMAT_VERSION = "0.1"
CLI_VERSION = "0.1.0"
DISPOSITIONS = {"copied", "transformed", "skipped", "failed", "ambiguous", "unsupported"}
ITEM_TYPES = {"project", "conversation", "message", "content_block", "attachment"}
ROLES = {"user", "assistant", "system", "tool", "unknown"}
SHA256 = re.compile(r"^[0-9a-f]{64}$")
MAX_INSPECTION_BYTES = 50 * 1024 * 1024
MAX_INSPECTION_NODES = 1_000_000
EXIT_CODES = {
    "success": 0,
    "validation_failed": 1,
    "invalid_input": 2,
    "decision_required": 3,
    "review_rejected": 4,
    "reconciliation_differences": 5,
    "sync_conflict": 6,
    "destination_unsupported": 7,
    "session_stale": 8,
}


def capabilities() -> dict[str, Any]:
    """Return a deterministic public inventory without probing accounts or networks."""
    return {
        "cli_version": CLI_VERSION,
        "contextpack_version": FORMAT_VERSION,
        "runtime_dependencies": [],
        "network_required": False,
        "destination_writes_supported": False,
        "commands": [
            "capabilities",
            "chatgpt-adapt",
            "claude-convert",
            "handoff",
            "inspect",
            "reconcile-plan",
            "reconstruct-plan",
            "release-check",
            "review-decision",
            "review-html",
            "review-package",
            "segregate",
            "sync-plan",
            "validate",
        ],
        "exit_codes": EXIT_CODES,
    }


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key {key!r}")
        result[key] = value
    return result


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


def _json_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    return "object"


def inspect_structure(document: Any) -> list[dict[str, Any]]:
    """Inventory JSON paths and types without returning scalar values."""
    observations: dict[str, dict[str, Any]] = {}
    pending: list[tuple[str, Any]] = [("$", document)]
    visited = 0
    while pending:
        path, value = pending.pop()
        visited += 1
        if visited > MAX_INSPECTION_NODES:
            raise ValueError(f"inspection exceeds {MAX_INSPECTION_NODES} JSON nodes")
        observation = observations.setdefault(path, {"path": path, "types": set(), "occurrences": 0})
        observation["types"].add(_json_type(value))
        observation["occurrences"] += 1
        if isinstance(value, dict):
            for key in sorted(value, reverse=True):
                escaped_key = key.replace("~", "~0").replace("/", "~1")
                pending.append((f"{path}/{escaped_key}", value[key]))
        elif isinstance(value, list):
            for item in reversed(value):
                pending.append((f"{path}/*", item))
    return [
        {"path": item["path"], "types": sorted(item["types"]), "occurrences": item["occurrences"]}
        for item in sorted(observations.values(), key=lambda item: item["path"])
    ]


def inspect_file(path: Path, classification: str) -> dict[str, Any]:
    """Inspect a JSON artifact locally without emitting content values."""
    if path.stat().st_size > MAX_INSPECTION_BYTES:
        raise ValueError(f"artifact exceeds {MAX_INSPECTION_BYTES} byte inspection limit")
    raw = path.read_bytes()
    if len(raw) > MAX_INSPECTION_BYTES:
        raise ValueError(f"artifact exceeds {MAX_INSPECTION_BYTES} byte inspection limit")
    document = json.loads(raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys)
    return {
        "report_version": "0.1",
        "classification": classification,
        "artifact_name": path.name,
        "artifact_bytes": len(raw),
        "artifact_sha256": hashlib.sha256(raw).hexdigest(),
        "inspected_at": datetime.now(timezone.utc).isoformat(),
        "top_level_type": _json_type(document),
        "observations": inspect_structure(document),
        "values_emitted": False,
        "schema_interpretation": "UNKNOWN",
    }


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
    parser.add_argument("--version", action="version", version=f"ContextPort {CLI_VERSION}")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("capabilities", help="print deterministic machine-readable CLI capabilities")
    handoff_parser = subparsers.add_parser("handoff", help="regenerate canonical SESSION.md and SESSION.json")
    handoff_parser.add_argument("--repository", type=Path, default=Path.cwd())
    handoff_parser.add_argument("--check", action="store_true", help="check freshness without writing")
    release_parser = subparsers.add_parser("release-check", help="audit release readiness without publishing")
    release_parser.add_argument("--repository", type=Path, default=Path.cwd())
    release_parser.add_argument("--write", action="store_true", help="write canonical reports under context-port/reports")
    validate_parser = subparsers.add_parser("validate", help="validate one ContextPack JSON document")
    validate_parser.add_argument("path", type=Path)
    inspect_parser = subparsers.add_parser("inspect", help="inspect JSON structure locally without emitting values")
    inspect_parser.add_argument("path", type=Path)
    inspect_parser.add_argument(
        "--classification",
        required=True,
        choices=("synthetic", "approved-private"),
        help="declare whether the artifact is synthetic or separately approved private input",
    )
    segregate_parser = subparsers.add_parser(
        "segregate", help="build a deterministic project and conversation membership plan"
    )
    segregate_parser.add_argument("path", type=Path, help="validated ContextPack JSON document")
    segregate_parser.add_argument("--mappings", type=Path, help="optional project mapping JSON document")
    review_package_parser = subparsers.add_parser(
        "review-package", help="build a deterministic metadata-only human review package"
    )
    review_package_parser.add_argument("path", type=Path, help="validated ContextPack JSON document")
    review_package_parser.add_argument("--mappings", type=Path, help="optional project mapping JSON document")
    review_html_parser = subparsers.add_parser("review-html", help="render a review package as standalone HTML")
    review_html_parser.add_argument("path", type=Path, help="review package JSON document")
    review_decision_parser = subparsers.add_parser(
        "review-decision", help="validate a human decision against a review package"
    )
    review_decision_parser.add_argument("package", type=Path, help="review package JSON document")
    review_decision_parser.add_argument("decision", type=Path, help="human decision JSON document")
    reconstruct_parser = subparsers.add_parser(
        "reconstruct-plan", help="build an approved assistant-neutral dry-run reconstruction plan"
    )
    reconstruct_parser.add_argument("path", type=Path, help="validated ContextPack JSON document")
    reconstruct_parser.add_argument("--mappings", type=Path, required=True)
    reconstruct_parser.add_argument("--review-package", type=Path, required=True)
    reconstruct_parser.add_argument("--decision", type=Path, required=True)
    reconcile_parser = subparsers.add_parser(
        "reconcile-plan", help="independently compare a ContextPack with a reconstruction plan"
    )
    reconcile_parser.add_argument("source", type=Path)
    reconcile_parser.add_argument("plan", type=Path)
    sync_parser = subparsers.add_parser("sync-plan", help="detect incremental ContextPack changes and conflicts")
    sync_parser.add_argument("previous", type=Path)
    sync_parser.add_argument("current", type=Path)
    sync_parser.add_argument("--peer-state", type=Path)
    chatgpt_parser = subparsers.add_parser(
        "chatgpt-adapt", help="assess a reconstruction plan against verified public ChatGPT capabilities"
    )
    chatgpt_parser.add_argument("plan", type=Path)
    claude_parser = subparsers.add_parser(
        "claude-convert", help="convert an approved local Claude export without inference"
    )
    claude_parser.add_argument("export", type=Path)
    claude_parser.add_argument("output", type=Path)
    arguments = parser.parse_args(argv)
    if arguments.command == "capabilities":
        print(json.dumps(capabilities(), indent=2, sort_keys=True))
        return EXIT_CODES["success"]
    if arguments.command == "handoff":
        from session import SessionError, generate_session

        try:
            fresh, state = generate_session(arguments.repository, check=arguments.check)
        except (SessionError, OSError, ValueError, RecursionError) as exc:
            print(f"FAIL: {exc}", file=sys.stderr)
            return EXIT_CODES["invalid_input"]
        if arguments.check and not fresh:
            print("STALE: regenerate with `contextport handoff`", file=sys.stderr)
            return EXIT_CODES["session_stale"]
        print(json.dumps({"status": "fresh" if arguments.check else "generated", "session": state}, indent=2, sort_keys=True))
        return EXIT_CODES["success"]
    if arguments.command == "release-check":
        from readiness import ReadinessError, collect_readiness, write_reports

        try:
            report = collect_readiness(arguments.repository)
            if arguments.write:
                write_reports(arguments.repository, report)
        except (ReadinessError, OSError, ValueError, RecursionError) as exc:
            print(f"FAIL: {exc}", file=sys.stderr)
            return EXIT_CODES["invalid_input"]
        print(json.dumps(report, indent=2, sort_keys=True))
        return EXIT_CODES["success"] if report["synthetic_mvp_status"] == "ready" else EXIT_CODES["validation_failed"]
    if arguments.command == "validate":
        return _validate_file(arguments.path)
    if arguments.command == "inspect":
        try:
            report = inspect_file(arguments.path, arguments.classification)
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
            print(f"FAIL {arguments.path}: {exc}", file=sys.stderr)
            return 2
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    if arguments.command == "segregate":
        from segregation import SegregationError, segregate

        try:
            document = json.loads(
                arguments.path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_keys
            )
            mappings = (
                json.loads(
                    arguments.mappings.read_text(encoding="utf-8"),
                    object_pairs_hook=_reject_duplicate_keys,
                )
                if arguments.mappings
                else None
            )
            result = segregate(document, mappings, validator=validate)
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
            print(f"FAIL {arguments.path}: {exc}", file=sys.stderr)
            return 2
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 3 if result["status"] == "decision_required" else 0
    if arguments.command == "review-package":
        from review import ReviewError, build_review_package
        from segregation import SegregationError, segregate

        try:
            document = json.loads(
                arguments.path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_keys
            )
            mappings = (
                json.loads(arguments.mappings.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_keys)
                if arguments.mappings
                else None
            )
            plan = segregate(document, mappings, validator=validate)
            if plan["status"] != "ready":
                print(json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True))
                return 3
            package = build_review_package(document, plan)
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
            print(f"FAIL {arguments.path}: {exc}", file=sys.stderr)
            return 2
        print(json.dumps(package, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if arguments.command == "review-html":
        from review import render_review_html

        try:
            package = json.loads(arguments.path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_keys)
            rendered = render_review_html(package)
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
            print(f"FAIL {arguments.path}: {exc}", file=sys.stderr)
            return 2
        print(rendered)
        return 0
    if arguments.command == "review-decision":
        from review import validate_decision

        try:
            package = json.loads(arguments.package.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_keys)
            decision = json.loads(arguments.decision.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_keys)
            validated = validate_decision(package, decision)
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
            print(f"FAIL {arguments.decision}: {exc}", file=sys.stderr)
            return 2
        print(json.dumps(validated, ensure_ascii=False, indent=2, sort_keys=True))
        return 4 if validated["decision"] == "reject" else 0
    if arguments.command == "reconstruct-plan":
        from reconstruction import build_reconstruction_plan
        from review import build_review_package
        from segregation import segregate

        try:
            load = lambda path: json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_keys)
            document = load(arguments.path)
            mappings = load(arguments.mappings)
            supplied_package = load(arguments.review_package)
            decision = load(arguments.decision)
            segregation_plan = segregate(document, mappings, validator=validate)
            if segregation_plan["status"] != "ready":
                print(json.dumps(segregation_plan, ensure_ascii=False, indent=2, sort_keys=True))
                return 3
            expected_package = build_review_package(document, segregation_plan)
            if supplied_package != expected_package:
                raise ValueError("supplied review package does not exactly match approved inputs")
            plan = build_reconstruction_plan(document, segregation_plan, supplied_package, decision)
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
            print(f"FAIL {arguments.path}: {exc}", file=sys.stderr)
            return 2
        print(json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if arguments.command == "reconcile-plan":
        from reconciliation import reconcile

        try:
            load = lambda path: json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_keys)
            report = reconcile(load(arguments.source), load(arguments.plan))
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
            print(f"FAIL {arguments.plan}: {exc}", file=sys.stderr)
            return 2
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if report["status"] == "clean" else 5
    if arguments.command == "sync-plan":
        from sync import plan_sync

        try:
            load = lambda path: json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_keys)
            plan = plan_sync(
                load(arguments.previous),
                load(arguments.current),
                load(arguments.peer_state) if arguments.peer_state else None,
                validator=validate,
            )
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
            print(f"FAIL {arguments.current}: {exc}", file=sys.stderr)
            return 2
        print(json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True))
        return 6 if plan["status"] == "conflict" else 0
    if arguments.command == "chatgpt-adapt":
        from chatgpt_adapter import build_chatgpt_adapter_report

        try:
            plan = json.loads(arguments.plan.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_keys)
            report = build_chatgpt_adapter_report(plan)
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
            print(f"FAIL {arguments.plan}: {exc}", file=sys.stderr)
            return 2
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        return 7 if report["status"] == "blocked_unsupported" else 0
    if arguments.command == "claude-convert":
        from claude_converter import ClaudeConversionError, write_migration

        try:
            digests = write_migration(arguments.export, arguments.output)
        except (ClaudeConversionError, OSError, ValueError, RecursionError) as exc:
            print(f"FAIL {arguments.export}: {exc}", file=sys.stderr)
            return 2
        print(json.dumps({"status": "converted", "files": digests}, indent=2, sort_keys=True))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
