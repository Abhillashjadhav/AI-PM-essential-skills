from __future__ import annotations

import copy
from typing import Any

from .io import EvidenceError


def _parent_for_path(value: Any, path: str) -> tuple[Any, str]:
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
    by_id = {trial.get("trial_id"): trial for trial in mutated}
    for spec in specs:
        trial_id = spec.get("trial_id")
        if trial_id not in by_id:
            raise EvidenceError(f"fault references unknown trial_id: {trial_id!r}")
        parent, leaf = _parent_for_path(by_id[trial_id], str(spec.get("path", "")))
        operation = spec.get("operation")
        if isinstance(parent, list) and leaf.isdigit():
            key: Any = int(leaf)
            if key >= len(parent):
                raise EvidenceError(f"fault list index is out of range: {leaf}")
        else:
            key = leaf
        if operation == "set":
            parent[key] = copy.deepcopy(spec.get("value"))
        elif operation == "delete":
            if isinstance(parent, dict) and key not in parent:
                raise EvidenceError(f"fault delete path does not exist: {spec['path']}")
            del parent[key]
        else:
            raise EvidenceError(f"unsupported fault operation: {operation!r}")
    return mutated
