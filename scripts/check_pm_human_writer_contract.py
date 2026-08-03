#!/usr/bin/env python3
"""Validate PM Human Writer's synthetic behavioural contract fixtures."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = ROOT / "pm-human-writer" / "fixtures" / "validation-cases.json"
REQUIRED_CASE_IDS = {
    "fire-linkedin-rewrite",
    "no-fire-factual-question",
    "known-answer-product-system",
    "missing-metric-placeholder",
    "minimum-edit-clean-draft",
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


def validate_contract(path: Path = CASES_PATH) -> list[str]:
    failures: list[str] = []
    if not path.is_file():
        return [f"missing PM Human Writer contract cases: {path.relative_to(ROOT)}"]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return [f"invalid PM Human Writer contract cases: {exc}"]

    if payload.get("version") != 1:
        failures.append("PM Human Writer contract: version must be 1")

    cases = payload.get("cases")
    if not isinstance(cases, list):
        return failures + ["PM Human Writer contract: cases must be a list"]

    seen_ids: set[str] = set()
    for index, case in enumerate(cases):
        label = f"PM Human Writer case #{index + 1}"
        if not isinstance(case, dict):
            failures.append(f"{label}: case must be an object")
            continue

        case_id = case.get("id")
        if not isinstance(case_id, str) or not case_id.strip():
            failures.append(f"{label}: missing string id")
            continue
        label = f"PM Human Writer case {case_id}"
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

        required_text_fields = ("audience", "reader_outcome", "draft", "expected_output")
        for field in required_text_fields:
            if not isinstance(case.get(field), str) or not case[field].strip():
                failures.append(f"{label}: {field} must be non-empty")

        draft = case.get("draft", "")
        output = case.get("expected_output", "")
        if not isinstance(draft, str) or not isinstance(output, str):
            continue

        fragment_lists: dict[str, list[str]] = {}
        for field in ("must_preserve", "must_remove", "must_not_add"):
            fragments = case.get(field)
            if not isinstance(fragments, list) or not all(
                isinstance(fragment, str) and fragment for fragment in fragments
            ):
                failures.append(f"{label}: {field} must be a string list")
                fragment_lists[field] = []
            else:
                fragment_lists[field] = fragments

        for fragment in fragment_lists["must_preserve"]:
            if not contains(draft, fragment):
                failures.append(f"{label}: preserved fragment absent from draft: {fragment!r}")
            if not contains(output, fragment):
                failures.append(f"{label}: expected output lost required fact: {fragment!r}")

        for fragment in fragment_lists["must_remove"]:
            if not contains(draft, fragment):
                failures.append(f"{label}: removable pattern absent from draft: {fragment!r}")
            if contains(output, fragment):
                failures.append(f"{label}: banned pattern remains in output: {fragment!r}")

        for fragment in fragment_lists["must_not_add"]:
            if contains(draft, fragment):
                failures.append(f"{label}: anti-invention fragment already exists in draft: {fragment!r}")
            if contains(output, fragment):
                failures.append(f"{label}: expected output invents forbidden detail: {fragment!r}")

        invented_numbers = sorted(set(NUMBER_PATTERN.findall(output)) - set(NUMBER_PATTERN.findall(draft)))
        if invented_numbers:
            failures.append(f"{label}: expected output invents numbers: {invented_numbers}")

        for pattern in BANNED_OUTPUT_PATTERNS:
            if contains(output, pattern):
                failures.append(f"{label}: expected output contains banned pattern: {pattern!r}")

        if case.get("enforce_no_change") is True and output != draft:
            failures.append(f"{label}: minimum-edit case changed the supplied draft")

    missing = REQUIRED_CASE_IDS - seen_ids
    unexpected = seen_ids - REQUIRED_CASE_IDS
    if missing or unexpected:
        failures.append(
            "PM Human Writer contract case set mismatch: "
            f"missing={sorted(missing)}, unexpected={sorted(unexpected)}"
        )

    if not any(case.get("should_trigger") is True for case in cases if isinstance(case, dict)):
        failures.append("PM Human Writer contract: missing trigger case")
    if not any(case.get("should_trigger") is False for case in cases if isinstance(case, dict)):
        failures.append("PM Human Writer contract: missing no-trigger case")

    return failures


def main() -> int:
    failures = validate_contract()
    if failures:
        print("PM HUMAN WRITER CONTRACT: FAIL", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1

    print(f"PM HUMAN WRITER CONTRACT: PASS ({len(REQUIRED_CASE_IDS)} synthetic cases)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
