"""Optional external classifier hook (e.g. a local model such as Kev).

Off by default: the router's deterministic rules are the classifier. A plugin
is loaded only when the owner sets ``MODEL_ROUTER_CLASSIFIER=module:function``.
It never affects subscription access or spend; it can only change which role
a *new* chat starts on, within these limits:

* Hard floors from the rules (credibility writing, money/privacy/security
  coding, consequential or destructive operations) are never lowered.
* A plugin may raise a role, or classify a task the rules could not recognise.
* Any plugin error or malformed answer falls back to the rules, visibly.

Plugin contract: ``function(text: str) -> {"task_kind": <TaskKind value>, "reason": str}``.
"""

from __future__ import annotations

import importlib
import os
from typing import Any, Callable

from .classifier import ClassifierInput, classify
from .contracts import TaskAssessment, TaskKind
from .policy import ROLE_FLOORS

HARD_FLOOR_KINDS = frozenset(
    {TaskKind.HIGH_RISK_CODING, TaskKind.CONSEQUENTIAL_ASSESSMENT, TaskKind.HIGH_CREDIBILITY_WRITING}
)
ENV_VAR = "MODEL_ROUTER_CLASSIFIER"


def load_plugin(spec: str | None = None) -> Callable[[str], Any] | None:
    spec = spec if spec is not None else os.environ.get(ENV_VAR)
    if not spec:
        return None
    module_name, _, attr = spec.partition(":")
    if not module_name or not attr:
        raise ValueError(f"{ENV_VAR} must look like 'package.module:function', got {spec!r}")
    return getattr(importlib.import_module(module_name), attr)


def combined_classifier(plugin: Callable[[str], Any]) -> Callable[[ClassifierInput], TaskAssessment]:
    def classify_with_plugin(item: ClassifierInput) -> TaskAssessment:
        rules = classify(item)
        try:
            answer = plugin(item.text)
            kind = TaskKind(answer["task_kind"])
            reason = str(answer.get("reason", ""))[:200]
        except Exception as exc:  # fall back to the rules, visibly
            rules.reason_codes.append(f"PLUGIN_FAILED:{type(exc).__name__}")
            return rules
        rules.reason_codes.append(f"PLUGIN_SAID:{kind.value}")
        if rules.task_kind in HARD_FLOOR_KINDS or rules.risk_flags:
            return rules  # never lower a hard floor
        rules_role = ROLE_FLOORS[rules.task_kind][0]
        plugin_role = ROLE_FLOORS[kind][0]
        has_data = any(code.endswith("TREATED_AS_DATA") or code.startswith("PASTED") for code in rules.reason_codes)
        # Resolving an unknown task may not drop it to the lowest role when the
        # prompt carries pasted/quoted material the rules did not interpret.
        may_resolve_unknown = rules.task_kind is TaskKind.UNKNOWN and (plugin_role.rank >= 1 or not has_data)
        if may_resolve_unknown or plugin_role.rank > rules_role.rank:
            rules.secondary_kinds = [k for k in [rules.task_kind, *rules.secondary_kinds] if k is not kind]
            rules.task_kind = kind
            rules.reason_codes.append("PLUGIN_CLASSIFICATION_USED")
            if reason:
                rules.evidence.append(f"plugin: {reason}")
            if kind is not TaskKind.UNKNOWN:
                rules.ambiguous = False
                rules.uncertainty = [u for u in rules.uncertainty if "not recognised" not in u]
        return rules

    return classify_with_plugin
