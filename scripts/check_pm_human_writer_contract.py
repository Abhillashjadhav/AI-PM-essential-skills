#!/usr/bin/env python3
"""Validate PM Human Writer's synthetic behavioural contract fixtures."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = ROOT / "pm-human-writer" / "fixtures" / "validation-cases.json"
VOICE_CASES_PATH = ROOT / "pm-human-writer" / "fixtures" / "voice-profile-cases.json"
REQUIRED_CASE_IDS = {
    "fire-linkedin-rewrite",
    "no-fire-factual-question",
    "known-answer-product-system",
    "missing-metric-placeholder",
    "minimum-edit-clean-draft",
}
REQUIRED_VOICE_CASE_IDS = {
    "calibrate-mixed-sources",
    "sparse-samples-provisional",
    "source-weighting-final-over-prompt",
    "roughness-is-not-voice",
    "privacy-excludes-raw-details",
    "voice-guided-minimum-edit",
}
SOURCE_TYPES = {
    "draft_final_pair",
    "accepted_final",
    "raw_prompt",
    "accepted_ai_draft",
    "ai_draft",
}
BANNED_OUTPUT_PATTERNS = (
    "what most people miss",
    "the best part:",
    "here's the thing",
    "let me be clear",
    "changes everything",
    "game changer",
    "cutting-edge",
    "paradigm shift",
)
NUMBER_PATTERN = re.compile(r"(?<![\w.])\d+(?:\.\d+)?%?")


def contains(text: str, fragment: str) -> bool:
    return fragment.casefold() in text.casefold()


def _load_payload(path: Path, label: str) -> tuple[dict[str, Any] | None, list[str]]:
    if not path.is_file():
        return None, [f"missing {label} cases: {path.relative_to(ROOT)}"]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return None, [f"invalid {label} cases: {exc}"]
    if not isinstance(payload, dict):
        return None, [f"{label}: top-level value must be an object"]
    return payload, []


def _validate_text_edit(
    *,
    label: str,
    draft: str,
    output: str,
    must_preserve: list[str],
    must_remove: list[str],
    must_not_add: list[str],
    enforce_no_change: bool,
) -> list[str]:
    failures: list[str] = []
    for fragment in must_preserve:
        if not contains(draft, fragment):
            failures.append(f"{label}: preserved fragment absent from draft: {fragment!r}")
        if not contains(output, fragment):
            failures.append(f"{label}: expected output lost required fact: {fragment!r}")

    for fragment in must_remove:
        if not contains(draft, fragment):
            failures.append(f"{label}: removable pattern absent from draft: {fragment!r}")
        if contains(output, fragment):
            failures.append(f"{label}: banned pattern remains in output: {fragment!r}")

    for fragment in must_not_add:
        if contains(draft, fragment):
            failures.append(f"{label}: anti-invention fragment already exists in draft: {fragment!r}")
        if contains(output, fragment):
            failures.append(f"{label}: expected output invents forbidden detail: {fragment!r}")

    invented_numbers = sorted(
        set(NUMBER_PATTERN.findall(output)) - set(NUMBER_PATTERN.findall(draft))
    )
    if invented_numbers:
        failures.append(f"{label}: expected output invents numbers: {invented_numbers}")

    for pattern in BANNED_OUTPUT_PATTERNS:
        if contains(output, pattern):
            failures.append(f"{label}: expected output contains banned pattern: {pattern!r}")

    if enforce_no_change and output != draft:
        failures.append(f"{label}: minimum-edit case changed the supplied draft")
    return failures


def _string_list(case: dict[str, Any], field: str, label: str) -> tuple[list[str], list[str]]:
    value = case.get(field)
    if not isinstance(value, list) or not all(
        isinstance(fragment, str) and fragment for fragment in value
    ):
        return [], [f"{label}: {field} must be a string list"]
    return value, []


def validate_rewrite_contract(path: Path = CASES_PATH) -> list[str]:
    payload, failures = _load_payload(path, "PM Human Writer rewrite contract")
    if payload is None:
        return failures

    if payload.get("version") != 1:
        failures.append("PM Human Writer rewrite contract: version must be 1")

    cases = payload.get("cases")
    if not isinstance(cases, list):
        return failures + ["PM Human Writer rewrite contract: cases must be a list"]

    seen_ids: set[str] = set()
    for index, case in enumerate(cases):
        label = f"PM Human Writer rewrite case #{index + 1}"
        if not isinstance(case, dict):
            failures.append(f"{label}: case must be an object")
            continue

        case_id = case.get("id")
        if not isinstance(case_id, str) or not case_id.strip():
            failures.append(f"{label}: missing string id")
            continue
        label = f"PM Human Writer rewrite case {case_id}"
        if case_id in seen_ids:
            failures.append(f"{label}: duplicate id")
        seen_ids.add(case_id)

        if not isinstance(case.get("should_trigger"), bool):
            failures.append(f"{label}: should_trigger must be boolean")
            continue
        if not isinstance(case.get("request"), str) or not case["request"].strip():
            failures.append(f"{label}: request must be non-empty")

        if not case["should_trigger"]:
            continue

        for field in ("audience", "reader_outcome", "draft", "expected_output"):
            if not isinstance(case.get(field), str) or not case[field].strip():
                failures.append(f"{label}: {field} must be non-empty")

        draft = case.get("draft", "")
        output = case.get("expected_output", "")
        if not isinstance(draft, str) or not isinstance(output, str):
            continue

        fragments: dict[str, list[str]] = {}
        for field in ("must_preserve", "must_remove", "must_not_add"):
            fragments[field], field_failures = _string_list(case, field, label)
            failures.extend(field_failures)

        failures.extend(
            _validate_text_edit(
                label=label,
                draft=draft,
                output=output,
                must_preserve=fragments["must_preserve"],
                must_remove=fragments["must_remove"],
                must_not_add=fragments["must_not_add"],
                enforce_no_change=case.get("enforce_no_change") is True,
            )
        )

    missing = REQUIRED_CASE_IDS - seen_ids
    unexpected = seen_ids - REQUIRED_CASE_IDS
    if missing or unexpected:
        failures.append(
            "PM Human Writer rewrite case set mismatch: "
            f"missing={sorted(missing)}, unexpected={sorted(unexpected)}"
        )

    if not any(case.get("should_trigger") is True for case in cases if isinstance(case, dict)):
        failures.append("PM Human Writer rewrite contract: missing trigger case")
    if not any(case.get("should_trigger") is False for case in cases if isinstance(case, dict)):
        failures.append("PM Human Writer rewrite contract: missing no-trigger case")
    return failures


def validate_voice_contract(path: Path = VOICE_CASES_PATH) -> list[str]:
    payload, failures = _load_payload(path, "PM Human Writer voice contract")
    if payload is None:
        return failures

    if payload.get("version") != 1:
        failures.append("PM Human Writer voice contract: version must be 1")

    cases = payload.get("cases")
    if not isinstance(cases, list):
        return failures + ["PM Human Writer voice contract: cases must be a list"]

    seen_ids: set[str] = set()
    for index, case in enumerate(cases):
        label = f"PM Human Writer voice case #{index + 1}"
        if not isinstance(case, dict):
            failures.append(f"{label}: case must be an object")
            continue

        case_id = case.get("id")
        if not isinstance(case_id, str) or not case_id.strip():
            failures.append(f"{label}: missing string id")
            continue
        label = f"PM Human Writer voice case {case_id}"
        if case_id in seen_ids:
            failures.append(f"{label}: duplicate id")
        seen_ids.add(case_id)

        mode = case.get("mode")
        if mode not in {"calibrate", "apply"}:
            failures.append(f"{label}: mode must be calibrate or apply")
            continue

        if mode == "apply":
            if case.get("voice_profile_status") not in {"provisional", "calibrated"}:
                failures.append(f"{label}: invalid voice_profile_status")
            draft = case.get("draft")
            output = case.get("expected_output")
            if not isinstance(draft, str) or not draft.strip():
                failures.append(f"{label}: draft must be non-empty")
                continue
            if not isinstance(output, str) or not output.strip():
                failures.append(f"{label}: expected_output must be non-empty")
                continue
            fragments: dict[str, list[str]] = {}
            for field in ("must_preserve", "must_remove", "must_not_add"):
                fragments[field], field_failures = _string_list(case, field, label)
                failures.extend(field_failures)
            failures.extend(
                _validate_text_edit(
                    label=label,
                    draft=draft,
                    output=output,
                    must_preserve=fragments["must_preserve"],
                    must_remove=fragments["must_remove"],
                    must_not_add=fragments["must_not_add"],
                    enforce_no_change=case.get("enforce_no_change") is True,
                )
            )
            continue

        sources = case.get("sources")
        if not isinstance(sources, list) or not sources:
            failures.append(f"{label}: sources must be a non-empty list")
            continue

        source_by_id: dict[str, dict[str, Any]] = {}
        for source in sources:
            if not isinstance(source, dict):
                failures.append(f"{label}: every source must be an object")
                continue
            source_id = source.get("id")
            source_type = source.get("type")
            if not isinstance(source_id, str) or not source_id:
                failures.append(f"{label}: every source needs a string id")
                continue
            if source_id in source_by_id:
                failures.append(f"{label}: duplicate source id {source_id!r}")
            source_by_id[source_id] = source
            if source_type not in SOURCE_TYPES:
                failures.append(f"{label}: unsupported source type for {source_id!r}")
            if not isinstance(source.get("positive"), bool):
                failures.append(f"{label}: source {source_id!r} needs boolean positive")
            if not isinstance(source.get("text"), str) or not source["text"].strip():
                failures.append(f"{label}: source {source_id!r} needs non-empty text")
            if (
                source_type == "ai_draft"
                and source.get("positive") is True
                and source.get("accepted") is not True
            ):
                failures.append(
                    f"{label}: unaccepted AI draft {source_id!r} cannot be positive evidence"
                )

        expected = case.get("expected")
        if not isinstance(expected, dict):
            failures.append(f"{label}: expected must be an object")
            continue
        status = expected.get("profile_status")
        if status not in {"provisional", "calibrated"}:
            failures.append(f"{label}: invalid profile_status")

        signals = expected.get("signals")
        if not isinstance(signals, list) or not signals:
            failures.append(f"{label}: expected signals must be a non-empty list")
            continue

        observed_count = 0
        observed_source_types: set[str] = set()
        evidence_union: set[str] = set()
        signal_ids: set[str] = set()
        for signal in signals:
            if not isinstance(signal, dict):
                failures.append(f"{label}: every signal must be an object")
                continue
            signal_id = signal.get("id")
            if not isinstance(signal_id, str) or not signal_id:
                failures.append(f"{label}: every signal needs a string id")
                continue
            if signal_id in signal_ids:
                failures.append(f"{label}: duplicate signal id {signal_id!r}")
            signal_ids.add(signal_id)
            if not isinstance(signal.get("description"), str) or not signal["description"].strip():
                failures.append(f"{label}: signal {signal_id!r} needs a description")
            confidence = signal.get("confidence")
            if confidence not in {"provisional", "observed"}:
                failures.append(f"{label}: signal {signal_id!r} has invalid confidence")
            evidence_ids = signal.get("evidence_ids")
            if not isinstance(evidence_ids, list) or not evidence_ids or not all(
                isinstance(source_id, str) and source_id for source_id in evidence_ids
            ):
                failures.append(f"{label}: signal {signal_id!r} needs evidence_ids")
                continue
            if len(evidence_ids) != len(set(evidence_ids)):
                failures.append(f"{label}: signal {signal_id!r} repeats evidence ids")
            unknown = set(evidence_ids) - set(source_by_id)
            if unknown:
                failures.append(
                    f"{label}: signal {signal_id!r} cites unknown sources {sorted(unknown)}"
                )
            evidence_union.update(evidence_ids)
            positive_ids = [
                source_id
                for source_id in evidence_ids
                if source_id in source_by_id
                and source_by_id[source_id].get("positive") is True
            ]
            if confidence == "observed":
                observed_count += 1
                if len(set(positive_ids)) < 3:
                    failures.append(
                        f"{label}: observed signal {signal_id!r} needs three positive sources"
                    )
                for source_id in positive_ids:
                    source_type = source_by_id[source_id].get("type")
                    if isinstance(source_type, str):
                        observed_source_types.add(source_type)

        if status == "calibrated" and (
            observed_count < 3 or len(observed_source_types) < 2
        ):
            failures.append(
                f"{label}: calibrated profile needs three observed signals across two source types"
            )

        polish_boundary = expected.get("polish_boundary")
        if not isinstance(polish_boundary, dict):
            failures.append(f"{label}: expected polish_boundary must be an object")
            polish_boundary = {}
        for field in ("preserve", "clean"):
            value = polish_boundary.get(field)
            if not isinstance(value, list) or not all(
                isinstance(item, str) and item for item in value
            ):
                failures.append(f"{label}: polish_boundary.{field} must be a string list")

        for field, destination in (
            ("required_preserve_terms", polish_boundary.get("preserve", [])),
            ("required_clean_terms", polish_boundary.get("clean", [])),
        ):
            required = case.get(field, [])
            if not isinstance(required, list) or not all(
                isinstance(item, str) and item for item in required
            ):
                failures.append(f"{label}: {field} must be a string list")
                continue
            folded_destination = {
                item.casefold() for item in destination if isinstance(item, str)
            }
            missing_terms = [
                item for item in required if item.casefold() not in folded_destination
            ]
            if missing_terms:
                failures.append(f"{label}: {field} missing {missing_terms}")

        for field in ("must_use_source_ids", "must_not_use_source_ids", "must_not_persist"):
            if not isinstance(case.get(field), list) or not all(
                isinstance(item, str) for item in case[field]
            ):
                failures.append(f"{label}: {field} must be a string list")

        must_use = set(case.get("must_use_source_ids", []))
        must_not_use = set(case.get("must_not_use_source_ids", []))
        if must_use - evidence_union:
            failures.append(f"{label}: expected signals omit required sources {sorted(must_use - evidence_union)}")
        if must_not_use & evidence_union:
            failures.append(f"{label}: expected signals use excluded sources {sorted(must_not_use & evidence_union)}")

        serialized_expected = json.dumps(expected, sort_keys=True).casefold()
        for fragment in case.get("must_not_persist", []):
            if fragment.casefold() in serialized_expected:
                failures.append(f"{label}: expected profile persists private/raw detail {fragment!r}")

    missing = REQUIRED_VOICE_CASE_IDS - seen_ids
    unexpected = seen_ids - REQUIRED_VOICE_CASE_IDS
    if missing or unexpected:
        failures.append(
            "PM Human Writer voice case set mismatch: "
            f"missing={sorted(missing)}, unexpected={sorted(unexpected)}"
        )
    return failures


def validate_contract(
    path: Path = CASES_PATH,
    voice_path: Path = VOICE_CASES_PATH,
) -> list[str]:
    return validate_rewrite_contract(path) + validate_voice_contract(voice_path)


def main() -> int:
    failures = validate_contract()
    if failures:
        print("PM HUMAN WRITER CONTRACT: FAIL", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1

    total = len(REQUIRED_CASE_IDS) + len(REQUIRED_VOICE_CASE_IDS)
    print(f"PM HUMAN WRITER CONTRACT: PASS ({total} synthetic cases)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
