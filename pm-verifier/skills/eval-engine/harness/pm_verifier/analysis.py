from __future__ import annotations

import math
from collections import Counter
from typing import Any


_STOPWORDS = {
    "actual",
    "answer",
    "configured",
    "evidence",
    "expected",
    "failed",
    "failure",
    "gate",
    "required",
    "the",
    "this",
    "trace",
    "trial",
    "value",
    "with",
}


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, math.ceil(fraction * len(ordered)) - 1)
    return float(ordered[index])


def aggregate_metrics(trials: list[dict[str, Any]]) -> dict[str, Any]:
    metrics = [trial["metrics"] for trial in trials]
    latencies = [float(item["latency_ms"]) for item in metrics]
    total_tokens = [int(item["input_tokens"]) + int(item["output_tokens"]) for item in metrics]
    return {
        "total_cost_usd": round(sum(float(item["cost_usd"]) for item in metrics), 8),
        "mean_cost_usd_per_trial": round(
            sum(float(item["cost_usd"]) for item in metrics) / len(metrics), 8
        ),
        "mean_latency_ms": round(sum(latencies) / len(latencies), 3),
        "p95_latency_ms": percentile(latencies, 0.95),
        "input_tokens": sum(int(item["input_tokens"]) for item in metrics),
        "output_tokens": sum(int(item["output_tokens"]) for item in metrics),
        "total_tokens": sum(total_tokens),
        "retries": sum(int(item["retries"]) for item in metrics),
    }


def build_slices(
    cases: list[dict[str, Any]], trial_results: list[dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    metadata = {case["case_id"]: case.get("metadata", {}) for case in cases}
    buckets: dict[str, list[dict[str, Any]]] = {}
    for result in trial_results:
        for key, value in sorted(metadata.get(result["case_id"], {}).items()):
            buckets.setdefault(f"{key}={value}", []).append(result)
    output: dict[str, dict[str, Any]] = {}
    for name, rows in sorted(buckets.items()):
        passed = sum(1 for row in rows if row["passed"])
        output[name] = {
            "trials": len(rows),
            "passed": passed,
            "pass_rate": passed / len(rows),
            "failed_gate_ids": sorted(
                {gate for row in rows for gate in row["failed_gate_ids"]}
            ),
        }
    return output


def _tokens(text: str) -> list[str]:
    cleaned = "".join(character.lower() if character.isalnum() else " " for character in text)
    return [
        token
        for token in cleaned.split()
        if len(token) > 3 and token not in _STOPWORDS
    ]


def cluster_failures(trial_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Dependency-free lexical clustering with the method disclosed in output."""
    failures: list[tuple[str, str]] = []
    for result in trial_results:
        for gate in result["gate_results"]:
            if not gate["passed"]:
                failures.append((result["trial_id"], f"{gate['name']}: {gate['reason']}"))
        for reason in result.get("quality_failures", []):
            failures.append((result["trial_id"], reason))
    buckets: dict[str, list[tuple[str, str]]] = {}
    for trial_id, rationale in failures:
        tokens = _tokens(rationale)
        key = tokens[0] if tokens else "other"
        buckets.setdefault(key, []).append((trial_id, rationale))
    clusters: list[dict[str, Any]] = []
    for key, members in buckets.items():
        words = Counter(token for _, text in members for token in _tokens(text))
        label = " ".join(word for word, _ in words.most_common(3)).title() or key.title()
        clusters.append(
            {
                "cluster_id": key,
                "label": label,
                "method": "lexical-v1",
                "size": len(members),
                "trial_ids": sorted({trial_id for trial_id, _ in members}),
                "representative": members[0][1],
            }
        )
    return sorted(clusters, key=lambda item: (-item["size"], item["cluster_id"]))
