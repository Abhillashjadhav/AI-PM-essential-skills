"""One explicit, public-input experiment. It cannot promote a routing prompt."""
from __future__ import annotations

import hashlib
import json
import sys
import time
import uuid
from pathlib import Path

from .classifier import ClassifierInput
from .contracts import TaskKind
from .jev import (EVALUATION_CANDIDATE, MAX_ORDINARY_CONSEQUENCES, MIN_CONFIDENCE,
                  MODEL, PROMPT_VERSION, JevClient, JevUnavailable, request_for)
from .jev_cli import CASES
from .plugin_classifier import combined_classifier
from .policy import ROLE_FLOORS, required_role

SUITE_VERSION = "approved-design-comparison-1"
VARIANTS = ("baseline", EVALUATION_CANDIDATE)
# Original prompts and expectations are untouched. These added cases are
# targeted regression probes, NOT unseen/held-out accuracy evidence.
COMPARISON_CASES = CASES + (
    ("approved ordinary design", "Implement the agreed design: sort a list of public book titles alphabetically and return a new list. The design is final.", "middle"),
    ("approved money design", "Implement the bank transfer endpoint exactly as specified by the approved architecture.", "highest"),
    ("approved privacy design", "Implement the approved export of private customer records, including home addresses and phone numbers.", "highest"),
    ("approved security design", "Implement authentication and permissions exactly as specified by the approved architecture.", "highest"),
    ("reconsider architecture", "Reconsider the approved architecture and decide whether to use a queue or synchronous requests.", "highest"),
    ("coding plus decision", "Implement the CSV export and decide the product's data retention policy.", "highest"),
)
CHECKS = ("valid_response", "expected_role", "provider_role_matches",
          "confidence_sufficient", "within_two_seconds")


def request_digest(request: dict) -> str:
    return hashlib.sha256(json.dumps(request, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def score_result(prompt: str, expected: str, answer: dict, seconds: float) -> dict:
    diagnostics = answer["diagnostics"]
    role = required_role(combined_classifier(lambda _: answer)(ClassifierInput(text=prompt))).role.value
    choice = diagnostics["provider_choice"]
    checks = {
        "valid_response": True,  # JevClient already validated the full response
        "expected_role": role == expected,
        # Prevent a rules-level risk floor from hiding a bad provider downgrade.
        "provider_role_matches": choice != "unknown" and ROLE_FLOORS[TaskKind(choice)][0].value == expected,
        "confidence_sufficient": diagnostics["checks"]["confidence_sufficient"] and diagnostics["checks"]["highest_probability_sufficient"],
        "within_two_seconds": seconds <= 2.0,
    }
    return {"role": role, "seconds": round(seconds, 4), "checks": checks,
            "jev_diagnostics": diagnostics}


def summarize(rows: list[dict], *, complete: bool) -> dict:
    scores = {variant: sum(sum(row["results"].get(variant, {}).get("checks", {}).values()) for row in rows)
              for variant in VARIANTS}
    regressions = []
    for row in rows:
        results = row["results"]
        if all(v in results for v in VARIANTS):
            for check in CHECKS:
                if results["baseline"]["checks"][check] and not results[EVALUATION_CANDIDATE]["checks"][check]:
                    regressions.append({"case": row["case"], "check": check})
    total = len(COMPARISON_CASES) * len(CHECKS)
    if not complete:
        verdict = "incomplete_no_promotion"
    elif regressions:
        verdict = "regression_keep_active_prompt"
    elif scores[EVALUATION_CANDIDATE] <= scores["baseline"]:
        verdict = "no_improvement_keep_active_prompt"
    elif scores[EVALUATION_CANDIDATE] < total:
        verdict = "improved_but_checks_still_fail_keep_active_prompt"
    else:
        verdict = "ready_for_owner_review_not_promoted"
    return {"scores": scores, "checks_per_variant": total, "regressions": regressions,
            "verdict": verdict, "promoted": False}


def run_comparison(client: JevClient) -> int:
    """At most two calls per public case; stop on first error, never retry.

    State/version stay on the active prompt. Requests share the existing durable
    journal and credit-error stop mechanism, but are marked as evaluation work.
    A unique run records both full public requests before any dispatch. Partial
    results survive interruption. Running this command again starts a NEW run.
    """
    status = client.status()
    if not status.get("enabled"):
        print(json.dumps({"jev_calls": 0, "gpt_calls": 0, "blocked": status.get("reason"),
                          "next": "router.py jev setup", "promoted": False}))
        return 1
    run_id = uuid.uuid4().hex
    path = client.path / "evaluations" / (run_id + ".json")
    rows = []
    for index, (case, prompt, expected) in enumerate(COMPARISON_CASES):
        requests = {variant: request_for(prompt, evaluation_variant=variant) for variant in VARIANTS}
        rows.append({"case": case, "expected": expected, "requests": requests,
                     "request_digests": {v: request_digest(r) for v, r in requests.items()},
                     "order": list(VARIANTS if index % 2 == 0 else reversed(VARIANTS)), "results": {}})
    evidence = {
        "run_id": run_id, "suite_version": SUITE_VERSION, "model": MODEL,
        "active_prompt_version": PROMPT_VERSION, "candidate": EVALUATION_CANDIDATE,
        "status": "running", "started_at": client.clock(), "maximum_jev_calls": 2 * len(rows),
        "attempted_calls": 0, "completed_calls": 0, "gpt_calls": 0, "promoted": False,
        "thresholds": {"minimum_confidence": MIN_CONFIDENCE, "minimum_choice_probability": MIN_CONFIDENCE,
                       "maximum_ordinary_consequences": MAX_ORDINARY_CONSEQUENCES},
        "locked_checks": list(CHECKS), "cases": rows,
        "code_sha256": {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                        for name in ("jev.py", "jev_compare.py", "classifier.py", "plugin_classifier.py", "policy.py")},
        "note": "One sample per prompt and variant. Public targeted regression probes; not a blind accuracy evaluation or proof of 95% routing suitability.",
    }
    client._write_json(path, evidence)  # failure here prevents any network calls
    print(f"Comparing {len(rows)} public cases (at most {2 * len(rows)} Jev requests, zero GPT requests). Active prompt stays unchanged.", file=sys.stderr)
    try:
        for index, row in enumerate(rows):
            for variant in row["order"]:
                request_id = f"comparison:{run_id}:{index}:{variant}"
                row.setdefault("request_ids", {})[variant] = request_id
                evidence["attempted_calls"] += 1
                client._write_json(path, evidence)
                started = time.monotonic()
                answer = client(row["requests"][variant]["state"]["task_text"],
                                request_id=request_id, evaluation_variant=variant)
                row["results"][variant] = score_result(row["requests"][variant]["state"]["task_text"],
                                                       row["expected"], answer, time.monotonic() - started)
                evidence["completed_calls"] += 1
                client._write_json(path, evidence)
        evidence["status"] = "completed"
    except (JevUnavailable, OSError, KeyboardInterrupt) as exc:
        evidence["status"] = "stopped"
        evidence["stop_reason"] = str(exc) if isinstance(exc, JevUnavailable) else (
            "interrupted" if isinstance(exc, KeyboardInterrupt) else "local_storage_error")
    evidence["summary"] = summarize(rows, complete=evidence["status"] == "completed")
    client._write_json(path, evidence)
    # Compact stdout; full public requests/scores/order remain in local evidence.
    print(json.dumps({
        "status": evidence["status"], "stop_reason": evidence.get("stop_reason"),
        "attempted_calls": evidence["attempted_calls"], "completed_calls": evidence["completed_calls"],
        "gpt_calls": 0, **evidence["summary"], "evidence_file": str(path),
        "cases": ["{}: expected {}; {}".format(row["case"], row["expected"], "; ".join(
            f"{'baseline' if v == 'baseline' else 'candidate'}={result['role']} "
            f"(consequence {result['jev_diagnostics']['consequences']}, "
            f"failed checks: {','.join(k for k, ok in result['checks'].items() if not ok) or 'none'})"
            for v in VARIANTS if (result := row["results"].get(v)) is not None)) for row in rows],
        "note": evidence["note"] + " No prompt, model mapping or thread pin was promoted. Share this summary, never the API key.",
    }, indent=2))
    return 0 if evidence["summary"]["verdict"] == "ready_for_owner_review_not_promoted" else 1
