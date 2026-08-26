from __future__ import annotations

import json
import re
from typing import Any

from .io import EvidenceError, get_path


SUPPORTED_CHECKS = {
    "equals_expected",
    "equals",
    "field_present",
    "max_length",
    "regex",
    "not_regex",
    "contains_all",
    "trace_step_equals",
}


def validate_grader(grader: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    grader_id = grader.get("id", "<missing>")
    for field in ("id", "name"):
        if not isinstance(grader.get(field), str) or not grader[field].strip():
            errors.append(f"grader {grader_id}: {field} must be a non-empty string")
    if grader.get("check") not in SUPPORTED_CHECKS:
        errors.append(f"grader {grader_id}: unsupported check {grader.get('check')!r}")
    if grader.get("scope") not in {"outcome", "trajectory"}:
        errors.append(f"grader {grader_id}: scope must be outcome or trajectory")
    if grader.get("category") not in {"quality", "safety", "privacy"}:
        errors.append(f"grader {grader_id}: invalid category")
    if grader.get("gate") is not True:
        errors.append(f"grader {grader_id}: deterministic release checks must be gates")
    check = grader.get("check")
    params = grader.get("params", {})
    if not isinstance(params, dict):
        errors.append(f"grader {grader_id}: params must be an object")
        params = {}
    if check == "trace_step_equals":
        for field in ("step_name", "field"):
            if not isinstance(params.get(field), str) or not params[field].strip():
                errors.append(f"grader {grader_id}: params.{field} is required")
        if not isinstance(grader.get("expected_path"), str) or not grader["expected_path"]:
            errors.append(f"grader {grader_id}: expected_path is required")
    else:
        if not isinstance(grader.get("actual_path"), str) or not grader["actual_path"]:
            errors.append(f"grader {grader_id}: actual_path is required")
    if check == "equals_expected" and (
        not isinstance(grader.get("expected_path"), str) or not grader["expected_path"]
    ):
        errors.append(f"grader {grader_id}: expected_path is required")
    if check == "max_length":
        chars = params.get("chars")
        if not isinstance(chars, int) or isinstance(chars, bool) or chars < 0:
            errors.append(f"grader {grader_id}: params.chars must be an integer >= 0")
    if check == "contains_all" and not isinstance(params.get("values"), list):
        errors.append(f"grader {grader_id}: params.values must be a list")
    if grader.get("check") in {"regex", "not_regex"}:
        patterns = params.get("patterns")
        if not isinstance(patterns, list) or not patterns:
            errors.append(f"grader {grader_id}: regex patterns must be a non-empty list")
        else:
            for pattern in patterns:
                try:
                    re.compile(pattern)
                except (re.error, TypeError) as exc:
                    errors.append(f"grader {grader_id}: invalid regex {pattern!r}: {exc}")
    return errors


def _text(value: Any) -> str:
    return value if isinstance(value, str) else json.dumps(value, sort_keys=True)


def grade_deterministic(
    grader: dict[str, Any], trial: dict[str, Any], case: dict[str, Any]
) -> dict[str, Any]:
    check = grader["check"]
    params = grader.get("params", {})
    actual: Any = None
    expected: Any = None
    passed = False
    reason = ""

    try:
        if check == "trace_step_equals":
            step_name = params["step_name"]
            matching = [step for step in trial["trajectory"] if step.get("name") == step_name]
            expected = get_path(case, grader["expected_path"])
            if not matching:
                reason = f"required trace step {step_name!r} is absent"
            else:
                actual = get_path(matching[-1], params["field"])
                passed = actual == expected
                reason = (
                    "trace value matches expected evidence"
                    if passed
                    else f"trace value {actual!r} != expected {expected!r}"
                )
        else:
            actual = get_path(trial, grader.get("actual_path", ""))
            if check == "equals_expected":
                expected = get_path(case, grader["expected_path"])
                passed = actual == expected
                reason = "value matches expected evidence" if passed else f"{actual!r} != {expected!r}"
            elif check == "equals":
                expected = params.get("value")
                passed = actual == expected
                reason = "value matches configured requirement" if passed else f"{actual!r} != {expected!r}"
            elif check == "field_present":
                passed = actual not in (None, "", [], {})
                reason = "required evidence is present" if passed else "required evidence is absent"
            elif check == "max_length":
                expected = int(params["chars"])
                passed = len(_text(actual)) <= expected
                reason = f"length {len(_text(actual))} <= {expected}" if passed else f"length {len(_text(actual))} > {expected}"
            elif check in {"regex", "not_regex"}:
                matches = [pattern for pattern in params["patterns"] if re.search(pattern, _text(actual), re.I)]
                passed = bool(matches) if check == "regex" else not matches
                reason = (
                    "configured pattern condition passed"
                    if passed
                    else f"pattern condition failed; matches={matches}"
                )
            elif check == "contains_all":
                missing = [item for item in params.get("values", []) if item not in actual]
                passed = not missing
                reason = "all required values are present" if passed else f"missing values: {missing}"
    except (KeyError, TypeError, ValueError) as exc:
        reason = f"required trial evidence is absent or invalid: {exc}"

    return {
        "grader_id": grader["id"],
        "name": grader["name"],
        "scope": grader["scope"],
        "category": grader["category"],
        "kind": "deterministic",
        "passed": passed,
        "actual": actual,
        "expected": expected,
        "reason": reason,
    }
