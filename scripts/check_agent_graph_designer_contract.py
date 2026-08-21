#!/usr/bin/env python3
"""Validate agent-graph-designer's committed synthetic contract and package."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = ROOT / "agent-graph-designer"
SKILL_ROOT = PLUGIN_ROOT / "skills" / "agent-graph-designer"
EXAMPLES = SKILL_ROOT / "examples"
CONTRACT_PATH = EXAMPLES / "sample-graph-contract.json"

NODE_FIELDS = {
    "id",
    "type",
    "purpose",
    "owner",
    "inputs",
    "outputs",
    "reads_state",
    "writes_state",
    "allowed_tools",
    "permissions",
    "model_policy",
    "budget",
    "timeout_seconds",
    "max_attempts",
    "verifier",
    "on_exhaustion",
}
EDGE_FIELDS = {
    "id",
    "source",
    "target",
    "type",
    "condition",
    "evidence_required",
    "state_mapping",
    "priority",
}
EDGE_TYPES = {
    "SEQUENCE",
    "FAN_OUT",
    "FAN_IN",
    "PASS",
    "FAIL",
    "RETRY",
    "ESCALATE",
    "APPROVE",
    "REJECT",
}
NODE_TYPES = {"LOOP", "WORKER", "VERIFIER", "JOIN", "HUMAN_GATE", "TERMINAL"}


def _load_json(path: Path, failures: list[str]) -> dict[str, Any]:
    if not path.is_file():
        failures.append(f"missing required JSON file: {path.relative_to(ROOT)}")
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        failures.append(f"invalid JSON {path.relative_to(ROOT)}: {exc}")
        return {}
    if not isinstance(value, dict):
        failures.append(f"{path.relative_to(ROOT)}: root must be an object")
        return {}
    return value


def _require_files(failures: list[str]) -> None:
    paths = (
        PLUGIN_ROOT / ".claude-plugin" / "plugin.json",
        PLUGIN_ROOT / "README.md",
        SKILL_ROOT / "SKILL.md",
        SKILL_ROOT / "references" / "qualification.md",
        SKILL_ROOT / "references" / "contracts.md",
        EXAMPLES / "sample-request.md",
        EXAMPLES / "sample-graph-package.md",
        CONTRACT_PATH,
        EXAMPLES / "sample-orchestrator.py",
        ROOT / "tests" / "agent-graph-designer" / "fixtures.md",
    )
    for path in paths:
        if not path.is_file():
            failures.append(f"missing agent-graph-designer file: {path.relative_to(ROOT)}")


def _validate_nodes(contract: dict[str, Any], failures: list[str]) -> set[str]:
    nodes = contract.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        failures.append("graph contract: nodes must be a non-empty list")
        return set()
    ids: list[str] = []
    for index, raw in enumerate(nodes):
        if not isinstance(raw, dict):
            failures.append(f"graph contract: node {index} must be an object")
            continue
        missing = NODE_FIELDS - set(raw)
        if missing:
            failures.append(f"graph contract: node {index} missing {sorted(missing)}")
        node_id = raw.get("id")
        if not isinstance(node_id, str) or not node_id:
            failures.append(f"graph contract: node {index} needs a non-empty id")
            continue
        ids.append(node_id)
        if raw.get("type") not in NODE_TYPES:
            failures.append(f"graph contract: node {node_id} has invalid type {raw.get('type')!r}")
        attempts = raw.get("max_attempts")
        if not isinstance(attempts, int) or not 1 <= attempts <= 2:
            failures.append(f"graph contract: node {node_id} max_attempts must be 1..2")
        verifier = raw.get("verifier")
        if not isinstance(verifier, dict) or not verifier.get("role") or not verifier.get("gates"):
            failures.append(f"graph contract: node {node_id} needs verifier role and gates")
        permissions = raw.get("permissions")
        if not isinstance(permissions, dict) or set(permissions) != {"read", "write", "actions"}:
            failures.append(
                f"graph contract: node {node_id} permissions require read/write/actions"
            )
        budget = raw.get("budget")
        if not isinstance(budget, dict) or not {"max_seconds", "max_cost_units"} <= set(budget):
            failures.append(f"graph contract: node {node_id} needs bounded time and cost")
    if len(ids) != len(set(ids)):
        failures.append("graph contract: node ids must be unique")
    return set(ids)


def _validate_edges(
    contract: dict[str, Any],
    node_ids: set[str],
    nodes_by_id: dict[str, dict[str, Any]],
    failures: list[str],
) -> list[dict[str, Any]]:
    edges = contract.get("edges")
    if not isinstance(edges, list) or not edges:
        failures.append("graph contract: edges must be a non-empty list")
        return []
    valid: list[dict[str, Any]] = []
    edge_ids: list[str] = []
    for index, raw in enumerate(edges):
        if not isinstance(raw, dict):
            failures.append(f"graph contract: edge {index} must be an object")
            continue
        missing = EDGE_FIELDS - set(raw)
        if missing:
            failures.append(f"graph contract: edge {index} missing {sorted(missing)}")
        edge_id = raw.get("id")
        if isinstance(edge_id, str):
            edge_ids.append(edge_id)
        if raw.get("source") not in node_ids or raw.get("target") not in node_ids:
            failures.append(f"graph contract: edge {edge_id!r} references an unknown node")
        if raw.get("type") not in EDGE_TYPES:
            failures.append(f"graph contract: edge {edge_id!r} has invalid type")
        if not raw.get("condition"):
            failures.append(f"graph contract: edge {edge_id!r} needs a condition")
        evidence = raw.get("evidence_required")
        mapping = raw.get("state_mapping")
        if not isinstance(evidence, list) or not all(isinstance(item, str) for item in evidence):
            failures.append(f"graph contract: edge {edge_id!r} evidence_required must be strings")
            evidence = []
        if not isinstance(mapping, dict) or not all(
            isinstance(source, str) and isinstance(target, str)
            for source, target in mapping.items()
        ):
            failures.append(f"graph contract: edge {edge_id!r} state_mapping must map strings")
            mapping = {}
        unmapped_sources = set(mapping) - set(evidence)
        if unmapped_sources:
            failures.append(
                f"graph contract: edge {edge_id!r} maps undeclared evidence {sorted(unmapped_sources)}"
            )
        target = nodes_by_id.get(str(raw.get("target")), {})
        target_fields = set(target.get("inputs", [])) | set(target.get("reads_state", []))
        unknown_targets = set(mapping.values()) - target_fields
        if unknown_targets:
            failures.append(
                f"graph contract: edge {edge_id!r} maps unknown target inputs {sorted(unknown_targets)}"
            )
        if target.get("type") == "TERMINAL" and target.get("inputs") and not mapping:
            failures.append(
                f"graph contract: edge {edge_id!r} reaches terminal without mapping its input"
            )
        valid.append(raw)
    if len(edge_ids) != len(set(edge_ids)):
        failures.append("graph contract: edge ids must be unique")
    return valid


def _validate_topology(
    contract: dict[str, Any],
    node_ids: set[str],
    nodes_by_id: dict[str, dict[str, Any]],
    edges: list[dict[str, Any]],
    failures: list[str],
) -> None:
    start = contract.get("start_node")
    terminals = contract.get("terminal_nodes")
    if start not in node_ids:
        failures.append("graph contract: start_node must reference a declared node")
    if not isinstance(terminals, list) or not terminals or not set(terminals) <= node_ids:
        failures.append("graph contract: terminal_nodes must reference declared nodes")
        terminals = []

    outgoing = {node_id: 0 for node_id in node_ids}
    incoming = {node_id: 0 for node_id in node_ids}
    for edge in edges:
        if edge.get("source") in outgoing:
            outgoing[str(edge["source"])] += 1
        if edge.get("target") in incoming:
            incoming[str(edge["target"])] += 1
    for node_id in node_ids - set(terminals):
        if outgoing[node_id] == 0:
            failures.append(f"graph contract: non-terminal node {node_id} has no exit")
        exhaustion = nodes_by_id.get(node_id, {}).get("on_exhaustion")
        if exhaustion == "BLOCKED" and not any(
            edge.get("source") == node_id
            and edge.get("target") in set(terminals)
            and edge.get("type") in {"FAIL", "REJECT", "ESCALATE"}
            for edge in edges
        ):
            failures.append(
                f"graph contract: node {node_id} declares BLOCKED exhaustion without a terminal edge"
            )
    for node_id in node_ids - {str(start)}:
        if incoming[node_id] == 0:
            failures.append(f"graph contract: node {node_id} is orphaned")

    reachable: set[str] = set()
    frontier = [str(start)] if start in node_ids else []
    while frontier:
        node_id = frontier.pop()
        if node_id in reachable:
            continue
        reachable.add(node_id)
        frontier.extend(
            str(edge["target"])
            for edge in edges
            if edge.get("source") == node_id and edge.get("target") in node_ids
        )
    unreachable = node_ids - reachable
    if unreachable:
        failures.append(f"graph contract: unreachable nodes {sorted(unreachable)}")

    # Retry edges are the only allowed cycles in the sample. Removing them
    # must leave a DAG, otherwise a hidden unbounded control cycle exists.
    non_retry_successors: dict[str, set[str]] = {node_id: set() for node_id in node_ids}
    for edge in edges:
        if edge.get("type") != "RETRY" and edge.get("source") in node_ids:
            non_retry_successors[str(edge["source"])].add(str(edge["target"]))
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node_id: str) -> None:
        if node_id in visited:
            return
        if node_id in visiting:
            failures.append(f"graph contract: unbounded non-retry cycle reaches {node_id}")
            return
        visiting.add(node_id)
        for target in non_retry_successors[node_id]:
            visit(target)
        visiting.remove(node_id)
        visited.add(node_id)

    for node_id in sorted(node_ids):
        visit(node_id)

    joins = contract.get("joins")
    if not isinstance(joins, list) or len(joins) != 1:
        failures.append("graph contract: sample requires exactly one join contract")
        return
    join = joins[0]
    if not isinstance(join, dict):
        failures.append("graph contract: join must be an object")
        return
    required = join.get("required_branches")
    if join.get("policy") != "ALL_REQUIRED":
        failures.append("graph contract: sample join must use ALL_REQUIRED")
    if not isinstance(required, list) or len(required) < 3 or not set(required) <= node_ids:
        failures.append("graph contract: join needs at least three declared required branches")
    for field in ("artifact_schema", "timeout_seconds", "on_missing", "on_failed", "on_stale", "on_conflict"):
        if not join.get(field):
            failures.append(f"graph contract: join missing {field}")

    edge_types = {str(edge.get("type")) for edge in edges}
    for required_type in ("FAN_OUT", "FAN_IN", "RETRY", "FAIL", "PASS", "APPROVE", "REJECT"):
        if required_type not in edge_types:
            failures.append(f"graph contract: sample missing {required_type} edge")


def _validate_state_and_permissions(
    contract: dict[str, Any], node_ids: set[str], failures: list[str]
) -> None:
    state = contract.get("state")
    if not isinstance(state, dict):
        failures.append("graph contract: state must be an object")
        return
    fields = state.get("fields")
    if not isinstance(fields, list) or not fields:
        failures.append("graph contract: state fields must be a non-empty list")
        return
    by_field: dict[str, dict[str, Any]] = {}
    for raw in fields:
        if not isinstance(raw, dict) or not isinstance(raw.get("name"), str):
            failures.append("graph contract: every state field needs a name")
            continue
        name = str(raw["name"])
        if name in by_field:
            failures.append(f"graph contract: duplicate state field {name}")
        by_field[name] = raw
        for key in ("schema", "writers", "readers", "sensitivity", "freshness"):
            if key not in raw:
                failures.append(f"graph contract: state field {name} missing {key}")
        if not set(raw.get("writers", [])) <= node_ids:
            failures.append(f"graph contract: state field {name} has unknown writer")
        if not set(raw.get("readers", [])) <= node_ids:
            failures.append(f"graph contract: state field {name} has unknown reader")

    human_actions = set(contract.get("human_approval_actions", []))
    for node in contract.get("nodes", []):
        if not isinstance(node, dict) or node.get("id") not in node_ids:
            continue
        node_id = str(node["id"])
        for field in node.get("writes_state", []):
            if field not in by_field:
                failures.append(f"graph contract: node {node_id} writes undeclared state {field}")
            elif node_id not in by_field[field].get("writers", []):
                failures.append(f"graph contract: node {node_id} is not an allowed writer of {field}")
        for field in node.get("reads_state", []):
            if field not in by_field:
                failures.append(f"graph contract: node {node_id} reads undeclared state {field}")
            elif node_id not in by_field[field].get("readers", []):
                failures.append(f"graph contract: node {node_id} is not an allowed reader of {field}")
        actions = set(node.get("permissions", {}).get("actions", []))
        prohibited = actions & human_actions
        if prohibited:
            failures.append(
                f"graph contract: node {node_id} can perform human-only actions {sorted(prohibited)}"
            )
        verifier = node.get("verifier", {})
        if verifier.get("role") == node.get("owner"):
            failures.append(f"graph contract: node {node_id} verifier is not independent")


def validate_contract() -> list[str]:
    failures: list[str] = []
    _require_files(failures)
    plugin = _load_json(PLUGIN_ROOT / ".claude-plugin" / "plugin.json", failures)
    if plugin.get("name") != "agent-graph-designer":
        failures.append("agent-graph-designer plugin manifest has wrong name")
    skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    frontmatter = skill_text.split("---", 2)[1] if skill_text.startswith("---") else ""
    if "\nargument-hint:" not in f"\n{frontmatter}":
        failures.append("agent-graph-designer skill frontmatter needs argument-hint")

    contract = _load_json(CONTRACT_PATH, failures)
    if not contract:
        return failures
    if contract.get("qualification", {}).get("verdict") != "GRAPH_REQUIRED":
        failures.append("graph contract: known-answer verdict must be GRAPH_REQUIRED")
    if contract.get("max_repairs_per_node") != 2:
        failures.append("graph contract: max_repairs_per_node must be 2")
    cap = contract.get("concurrency_cap")
    if not isinstance(cap, int) or not 1 <= cap <= 3:
        failures.append("graph contract: concurrency_cap must be 1..3")
    total_budget = contract.get("total_budget")
    if not isinstance(total_budget, dict) or not {"max_seconds", "max_cost_units"} <= set(
        total_budget
    ):
        failures.append("graph contract: total_budget needs time and cost ceilings")
    approval_actions = contract.get("human_approval_actions")
    if not isinstance(approval_actions, list) or not {"deploy", "merge", "publish"} <= set(
        approval_actions
    ):
        failures.append("graph contract: consequential actions must require human approval")

    node_ids = _validate_nodes(contract, failures)
    nodes_by_id = {
        str(node["id"]): node
        for node in contract.get("nodes", [])
        if isinstance(node, dict) and isinstance(node.get("id"), str)
    }
    edges = _validate_edges(contract, node_ids, nodes_by_id, failures)
    _validate_topology(contract, node_ids, nodes_by_id, edges, failures)
    _validate_state_and_permissions(contract, node_ids, failures)

    sample_package = (EXAMPLES / "sample-graph-package.md").read_text(encoding="utf-8")
    for marker in (
        "GRAPH_REQUIRED",
        "GRAPH_CONTRACT_VALID",
        "ALL_REQUIRED",
        "AWAITING_HUMAN_APPROVAL",
        "no external actions taken",
    ):
        if marker not in sample_package:
            failures.append(f"sample graph package missing marker {marker!r}")
    return failures


def main() -> int:
    failures = validate_contract()
    if failures:
        print("AGENT GRAPH DESIGNER CONTRACT: FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("AGENT GRAPH DESIGNER CONTRACT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
