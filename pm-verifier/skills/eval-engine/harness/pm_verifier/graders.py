from __future__ import annotations

import json
import math
import re
from datetime import datetime
from typing import Any

from .io import EvidenceError, get_path


SURFACES = {"outcome", "trajectory", "system", "memory"}
CATEGORIES = {"quality", "safety", "privacy", "reliability", "operational"}
SYSTEM_CHECKS = {
    "system_completed",
    "checkpoint_present",
    "checkpoint_order",
    "checkpoint_passed",
    "identity_preserved",
    "state_continuity",
    "no_silent_loss",
    "first_failure_equals",
    "final_checkpoint_reached",
}
MEMORY_CHECKS = {
    "state_written",
    "state_retrieved",
    "state_equals_expected",
    "state_updated",
    "state_deleted",
    "state_not_present",
    "state_isolated",
    "state_not_stale",
    "state_conflict_resolved",
    "state_temporal_order",
}
SUPPORTED_CHECKS = {
    "equals_expected",
    "equals",
    "field_present",
    "max_length",
    "regex",
    "not_regex",
    "contains_all",
    "trace_step_equals",
    *SYSTEM_CHECKS,
    *MEMORY_CHECKS,
}


def _non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _string_list(value: Any, *, minimum: int = 1) -> bool:
    return (
        isinstance(value, list)
        and len(value) >= minimum
        and all(_non_empty_string(item) for item in value)
        and len(value) == len(set(value))
    )


def _finite_non_negative(value: Any) -> bool:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        number = float(value)
    except (OverflowError, ValueError):
        return False
    return math.isfinite(number) and number >= 0


def validate_grader(grader: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    grader_id = grader.get("id", "<missing>")
    for field in ("id", "name"):
        if not isinstance(grader.get(field), str) or not grader[field].strip():
            errors.append(f"grader {grader_id}: {field} must be a non-empty string")
    check = grader.get("check")
    if not isinstance(check, str) or check not in SUPPORTED_CHECKS:
        errors.append(f"grader {grader_id}: unsupported check {check!r}")
    check_name = check if isinstance(check, str) else ""
    scope = grader.get("scope")
    if not isinstance(scope, str) or scope not in SURFACES:
        errors.append(
            f"grader {grader_id}: scope must be outcome, trajectory, system, or memory"
        )
    category = grader.get("category")
    if not isinstance(category, str) or category not in CATEGORIES:
        errors.append(f"grader {grader_id}: invalid category")
    if not isinstance(grader.get("gate"), bool):
        errors.append(f"grader {grader_id}: gate must be true or false")
    params = grader.get("params", {})
    if not isinstance(params, dict):
        errors.append(f"grader {grader_id}: params must be an object")
        params = {}
    if check_name in SYSTEM_CHECKS and scope != "system":
        errors.append(f"grader {grader_id}: {check_name} requires system scope")
    if check_name in MEMORY_CHECKS and scope != "memory":
        errors.append(f"grader {grader_id}: {check_name} requires memory scope")
    if check_name == "trace_step_equals":
        for field in ("step_name", "field"):
            if not isinstance(params.get(field), str) or not params[field].strip():
                errors.append(f"grader {grader_id}: params.{field} is required")
        if not isinstance(grader.get("expected_path"), str) or not grader["expected_path"]:
            errors.append(f"grader {grader_id}: expected_path is required")
    elif check_name not in SYSTEM_CHECKS | MEMORY_CHECKS:
        if not isinstance(grader.get("actual_path"), str) or not grader["actual_path"]:
            errors.append(f"grader {grader_id}: actual_path is required")
    if check_name in {"equals_expected", "state_equals_expected", "first_failure_equals"} and (
        not isinstance(grader.get("expected_path"), str) or not grader["expected_path"]
    ):
        errors.append(f"grader {grader_id}: expected_path is required")
    if check_name == "max_length":
        chars = params.get("chars")
        if not isinstance(chars, int) or isinstance(chars, bool) or chars < 0:
            errors.append(f"grader {grader_id}: params.chars must be an integer >= 0")
    if check_name == "contains_all" and not isinstance(params.get("values"), list):
        errors.append(f"grader {grader_id}: params.values must be a list")
    if check_name in ("regex", "not_regex"):
        patterns = params.get("patterns")
        if not isinstance(patterns, list) or not patterns:
            errors.append(f"grader {grader_id}: regex patterns must be a non-empty list")
        else:
            for pattern in patterns:
                try:
                    re.compile(pattern)
                except (re.error, TypeError) as exc:
                    errors.append(f"grader {grader_id}: invalid regex {pattern!r}: {exc}")
    if check_name in {"checkpoint_present", "checkpoint_passed", "final_checkpoint_reached"}:
        if not _non_empty_string(params.get("checkpoint")):
            errors.append(f"grader {grader_id}: params.checkpoint is required")
    if check_name in {"checkpoint_order", "no_silent_loss"}:
        minimum = 2 if check_name == "checkpoint_order" else 1
        if not _string_list(params.get("checkpoints"), minimum=minimum):
            errors.append(
                f"grader {grader_id}: params.checkpoints must be a unique string list"
            )
    if check_name in {"identity_preserved", "state_continuity"} and not _string_list(
        params.get("checkpoints")
    ):
        errors.append(
            f"grader {grader_id}: params.checkpoints must be a unique string list"
        )
    if check_name == "identity_preserved" and not _non_empty_string(
        params.get("field", "entity_id")
    ):
        errors.append(f"grader {grader_id}: params.field must be a non-empty string")
    if check_name == "state_continuity" and not _string_list(params.get("fields")):
        errors.append(f"grader {grader_id}: params.fields must be a unique string list")
    if check_name in {
        "state_written",
        "state_retrieved",
        "state_equals_expected",
        "state_updated",
        "state_deleted",
        "state_not_present",
    } and not _non_empty_string(params.get("key")):
        errors.append(f"grader {grader_id}: params.key is required")
    if check_name == "state_isolated" and not _string_list(params.get("dimensions")):
        errors.append(
            f"grader {grader_id}: params.dimensions must be a unique string list"
        )
    if check_name == "state_not_stale" and not _finite_non_negative(
        params.get("maximum_age_seconds")
    ):
        errors.append(
            f"grader {grader_id}: params.maximum_age_seconds must be a finite number >= 0"
        )
    if check_name == "state_conflict_resolved" and not _non_empty_string(
        params.get("policy")
    ):
        errors.append(f"grader {grader_id}: params.policy is required")
    return errors


def _text(value: Any) -> str:
    return value if isinstance(value, str) else json.dumps(value, sort_keys=True)


def _json_equal(actual: Any, expected: Any) -> bool:
    """Compare JSON values without treating booleans as the numbers 0 and 1."""
    if isinstance(actual, bool) or isinstance(expected, bool):
        return isinstance(actual, bool) and isinstance(expected, bool) and actual == expected
    if isinstance(actual, (int, float)) or isinstance(expected, (int, float)):
        return (
            isinstance(actual, (int, float))
            and isinstance(expected, (int, float))
            and actual == expected
        )
    if isinstance(actual, list) or isinstance(expected, list):
        return (
            isinstance(actual, list)
            and isinstance(expected, list)
            and len(actual) == len(expected)
            and all(_json_equal(left, right) for left, right in zip(actual, expected))
        )
    if isinstance(actual, dict) or isinstance(expected, dict):
        return (
            isinstance(actual, dict)
            and isinstance(expected, dict)
            and actual.keys() == expected.keys()
            and all(_json_equal(actual[key], expected[key]) for key in actual)
        )
    return type(actual) is type(expected) and actual == expected


def _checkpoint_map(trial: dict[str, Any]) -> dict[str, dict[str, Any]]:
    checkpoints = get_path(trial, "system.checkpoints")
    if not isinstance(checkpoints, list):
        raise TypeError("system.checkpoints must be a list")
    return {
        checkpoint["name"]: checkpoint
        for checkpoint in checkpoints
        if isinstance(checkpoint, dict) and _non_empty_string(checkpoint.get("name"))
    }


def _memory_events(trial: dict[str, Any], key: str | None = None) -> list[dict[str, Any]]:
    events = get_path(trial, "memory.events")
    if not isinstance(events, list):
        raise TypeError("memory.events must be a list")
    selected = [event for event in events if isinstance(event, dict)]
    return [event for event in selected if event.get("key") == key] if key else selected


def _successful_event(
    trial: dict[str, Any], operation: str, key: str
) -> dict[str, Any] | None:
    matches = [
        event
        for event in _memory_events(trial, key)
        if event.get("operation") == operation and event.get("status") == "passed"
    ]
    return matches[-1] if matches else None


def _parse_timestamp(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("occurred_at must be a timestamp string")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("occurred_at must include a timezone")
    return parsed


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
                passed = _json_equal(actual, expected)
                reason = (
                    "trace value matches expected evidence"
                    if passed
                    else f"trace value {actual!r} != expected {expected!r}"
                )
        elif check in SYSTEM_CHECKS:
            checkpoints = _checkpoint_map(trial)
            if check == "system_completed":
                actual = get_path(trial, "system.completed")
                expected = True
                passed = actual is True
                reason = (
                    "system reports complete"
                    if passed
                    else "system reports an incomplete workflow"
                )
            elif check in {"checkpoint_present", "final_checkpoint_reached"}:
                name = params["checkpoint"]
                actual = name in checkpoints
                expected = True
                passed = actual is True
                reason = (
                    f"checkpoint {name!r} is present"
                    if passed
                    else f"checkpoint {name!r} is absent"
                )
            elif check == "checkpoint_passed":
                name = params["checkpoint"]
                actual = checkpoints.get(name, {}).get("status")
                expected = "passed"
                passed = actual == expected
                reason = (
                    f"checkpoint {name!r} passed"
                    if passed
                    else f"checkpoint {name!r} status is {actual!r}"
                )
            elif check in {"checkpoint_order", "no_silent_loss"}:
                names = params["checkpoints"]
                actual = [name for name in names if name in checkpoints]
                if check == "checkpoint_order" and len(actual) == len(names):
                    positions = [int(checkpoints[name]["index"]) for name in names]
                    passed = positions == sorted(positions) and len(set(positions)) == len(positions)
                    actual = {name: checkpoints[name]["index"] for name in names}
                    expected = names
                    reason = (
                        "required checkpoints preserve configured order"
                        if passed
                        else f"checkpoint order does not match {names!r}"
                    )
                else:
                    missing = [name for name in names if name not in checkpoints]
                    passed = not missing
                    expected = names
                    reason = (
                        "all required checkpoints are present"
                        if passed
                        else f"missing checkpoints: {missing}"
                    )
            elif check == "identity_preserved":
                names = params["checkpoints"]
                field = params.get("field", "entity_id")
                expected = get_path(trial, "system.entity_id")
                actual = {
                    name: get_path(checkpoints[name], field)
                    for name in names
                }
                passed = all(_json_equal(value, expected) for value in actual.values())
                reason = (
                    "entity identity is preserved across checkpoints"
                    if passed
                    else f"checkpoint identity differs from {expected!r}: {actual!r}"
                )
            elif check == "state_continuity":
                names = params["checkpoints"]
                fields = params["fields"]
                actual = {
                    field: {
                        name: get_path(checkpoints[name]["state"], field)
                        for name in names
                    }
                    for field in fields
                }
                expected = {
                    field: next(iter(values.values())) for field, values in actual.items()
                }
                passed = all(
                    all(_json_equal(value, expected[field]) for value in values.values())
                    for field, values in actual.items()
                )
                reason = (
                    "configured state remains continuous across checkpoints"
                    if passed
                    else f"checkpoint state continuity failed: {actual!r}"
                )
            elif check == "first_failure_equals":
                actual = get_path(trial, "system.first_failure_stage")
                expected = get_path(case, grader["expected_path"])
                passed = _json_equal(actual, expected)
                reason = (
                    "first system failure matches expected evidence"
                    if passed
                    else f"first failure {actual!r} != expected {expected!r}"
                )
        elif check in MEMORY_CHECKS:
            key = params.get("key")
            if check in {"state_written", "state_retrieved", "state_updated", "state_deleted"}:
                operation = {
                    "state_written": "write",
                    "state_retrieved": "retrieve",
                    "state_updated": "update",
                    "state_deleted": "delete",
                }[check]
                event = _successful_event(trial, operation, key)
                actual = event.get("status") if event else None
                expected = "passed"
                passed = event is not None
                reason = (
                    f"state {operation} passed for key {key!r}"
                    if passed
                    else f"no successful {operation} evidence for key {key!r}"
                )
            elif check == "state_equals_expected":
                event = _successful_event(trial, "retrieve", key)
                actual = event.get("value") if event else None
                expected = get_path(case, grader["expected_path"])
                passed = event is not None and _json_equal(actual, expected)
                reason = (
                    "retrieved state matches expected evidence"
                    if passed
                    else f"retrieved state {actual!r} != expected {expected!r}"
                )
            elif check == "state_not_present":
                final_state = get_path(trial, "memory.final_state")
                if not isinstance(final_state, dict):
                    raise TypeError("memory.final_state must be an object")
                actual = final_state.get(key)
                expected = "absent"
                passed = key not in final_state
                reason = (
                    f"key {key!r} is absent from final state"
                    if passed
                    else f"key {key!r} remains in final state"
                )
            elif check == "state_isolated":
                checks = get_path(trial, "memory.isolation_checks")
                if not isinstance(checks, list):
                    raise TypeError("memory.isolation_checks must be a list")
                by_dimension = {
                    row.get("dimension"): row.get("passed")
                    for row in checks
                    if isinstance(row, dict)
                }
                expected = {dimension: True for dimension in params["dimensions"]}
                actual = {
                    dimension: by_dimension.get(dimension)
                    for dimension in params["dimensions"]
                }
                passed = actual == expected
                reason = (
                    "state is isolated across configured dimensions"
                    if passed
                    else f"state isolation failed: {actual!r}"
                )
            elif check == "state_not_stale":
                maximum = float(params["maximum_age_seconds"])
                reads = [
                    event
                    for event in _memory_events(trial)
                    if event.get("operation") == "retrieve" and event.get("status") == "passed"
                ]
                ages = [event.get("age_seconds") for event in reads]
                actual = ages
                expected = {"maximum_age_seconds": maximum}
                passed = bool(ages) and all(
                    _finite_non_negative(age) and float(age) <= maximum for age in ages
                )
                reason = (
                    "all retrieved state is within the staleness limit"
                    if passed
                    else f"retrieved state ages {ages!r} exceed {maximum:g} seconds"
                )
            elif check == "state_conflict_resolved":
                conflicts = get_path(trial, "memory.conflicts")
                if not isinstance(conflicts, list):
                    raise TypeError("memory.conflicts must be a list")
                matching = [
                    conflict
                    for conflict in conflicts
                    if isinstance(conflict, dict) and conflict.get("policy") == params["policy"]
                ]
                actual = [conflict.get("status") for conflict in matching]
                expected = "resolved"
                passed = bool(matching) and all(status == expected for status in actual)
                reason = (
                    "memory conflicts use the configured policy and are resolved"
                    if passed
                    else f"unresolved conflict evidence: {actual!r}"
                )
            elif check == "state_temporal_order":
                events = _memory_events(trial)
                timestamps = [_parse_timestamp(event.get("occurred_at")) for event in events]
                actual = [event.get("occurred_at") for event in events]
                expected = "strictly increasing timestamps"
                passed = all(left < right for left, right in zip(timestamps, timestamps[1:]))
                reason = (
                    "memory events preserve strict temporal order"
                    if passed
                    else "memory event timestamps are not strictly increasing"
                )
        else:
            actual = get_path(trial, grader.get("actual_path", ""))
            if check == "equals_expected":
                expected = get_path(case, grader["expected_path"])
                passed = _json_equal(actual, expected)
                reason = "value matches expected evidence" if passed else f"{actual!r} != {expected!r}"
            elif check == "equals":
                expected = params.get("value")
                passed = _json_equal(actual, expected)
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
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        reason = f"required trial evidence is absent or invalid: {exc}"

    return {
        "grader_id": grader["id"],
        "name": grader["name"],
        "scope": grader["scope"],
        "category": grader["category"],
        "kind": "deterministic",
        "gate": grader["gate"],
        "passed": passed,
        "actual": actual,
        "expected": expected,
        "reason": reason,
    }
