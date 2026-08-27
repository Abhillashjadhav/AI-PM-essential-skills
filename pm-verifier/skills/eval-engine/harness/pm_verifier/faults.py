from __future__ import annotations

import copy
from typing import Any

from .io import EvidenceError


def _parent_for_path(value: Any, path: str) -> tuple[Any, str]:
    if not isinstance(path, str) or not path:
        raise EvidenceError("fault path must be a non-empty string")
    parts = path.split(".")
    if not parts or any(part == "" for part in parts):
        raise EvidenceError(f"invalid fault path: {path!r}")
    current = value
    for part in parts[:-1]:
        if isinstance(current, dict) and part in current:
            current = current[part]
        elif isinstance(current, list) and part.isdigit() and int(part) < len(current):
            current = current[int(part)]
        else:
            raise EvidenceError(f"fault path does not exist: {path}")
    return current, parts[-1]


def apply_faults(
    trials: list[dict[str, Any]], specs: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Apply explicit deterministic set/delete operations to trial evidence."""
    mutated = copy.deepcopy(trials)
    by_id: dict[str, dict[str, Any]] = {}
    for index, trial in enumerate(mutated):
        if not isinstance(trial, dict):
            raise EvidenceError(f"trial at index {index} must be an object")
        trial_id = trial.get("trial_id")
        if not isinstance(trial_id, str) or not trial_id.strip():
            raise EvidenceError(f"trial at index {index} needs a non-empty string trial_id")
        if trial_id in by_id:
            raise EvidenceError(f"duplicate trial_id in fault source: {trial_id!r}")
        by_id[trial_id] = trial
    for index, spec in enumerate(specs):
        if not isinstance(spec, dict):
            raise EvidenceError(f"fault specification at index {index} must be an object")
        trial_id = spec.get("trial_id")
        if not isinstance(trial_id, str) or not trial_id.strip():
            raise EvidenceError(
                f"fault specification at index {index} needs a non-empty string trial_id"
            )
        if trial_id not in by_id:
            raise EvidenceError(f"fault references unknown trial_id: {trial_id!r}")
        path = spec.get("path")
        if not isinstance(path, str) or not path:
            raise EvidenceError(
                f"fault specification at index {index} needs a non-empty string path"
            )
        parent, leaf = _parent_for_path(by_id[trial_id], path)
        operation = spec.get("operation")
        if isinstance(parent, list):
            if not leaf.isdigit():
                raise EvidenceError(f"fault list index must be an integer: {leaf!r}")
            key: Any = int(leaf)
            if key >= len(parent):
                raise EvidenceError(f"fault list index is out of range: {leaf}")
        elif isinstance(parent, dict):
            key = leaf
        else:
            raise EvidenceError(f"fault path parent is not a container: {path}")
        if operation == "set":
            parent[key] = copy.deepcopy(spec.get("value"))
        elif operation == "delete":
            if isinstance(parent, dict) and key not in parent:
                raise EvidenceError(f"fault delete path does not exist: {spec['path']}")
            del parent[key]
        else:
            raise EvidenceError(f"unsupported fault operation: {operation!r}")
    return mutated
