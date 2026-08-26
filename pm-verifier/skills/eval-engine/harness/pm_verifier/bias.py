from __future__ import annotations

from pathlib import Path
from typing import Any

from .io import EvidenceError, load_jsonl


def analyze_pairwise_bias(
    path: str | Path,
    minimum_accuracy: float = 0.8,
    minimum_position_consistency: float = 0.8,
) -> dict[str, Any]:
    """Analyze blind AB/BA swaps without claiming the sample generalizes."""
    try:
        rows = load_jsonl(path)
    except EvidenceError as exc:
        return {"status": "BLOCKED", "evidence_errors": [str(exc)]}
    if not rows:
        return {"status": "BLOCKED", "evidence_errors": ["pairwise evidence is empty"]}

    correct = 0
    consistent = 0
    verbose_picks = 0
    verbose_truth = 0
    errors: list[str] = []
    for index, row in enumerate(rows, 1):
        required = {
            "pair_id",
            "truth_original",
            "truth_swapped",
            "verbose_original",
            "verbose_swapped",
            "pick_original",
            "pick_swapped",
        }
        missing = sorted(required - set(row))
        if missing:
            errors.append(f"pairwise row {index} missing {missing}")
            continue
        for field in required - {"pair_id"}:
            if row[field] not in {"A", "B"}:
                errors.append(f"pairwise row {index} has invalid {field}")
        correct += int(row["pick_original"] == row["truth_original"])
        correct += int(row["pick_swapped"] == row["truth_swapped"])
        consistent += int(row["pick_original"] != row["pick_swapped"])
        verbose_picks += int(row["pick_original"] == row["verbose_original"])
        verbose_picks += int(row["pick_swapped"] == row["verbose_swapped"])
        verbose_truth += int(row["truth_original"] == row["verbose_original"])
        verbose_truth += int(row["truth_swapped"] == row["verbose_swapped"])
    if errors:
        return {"status": "BLOCKED", "evidence_errors": errors}

    n = len(rows)
    accuracy = correct / (2 * n)
    position_consistency = consistent / n
    verbosity_pick_rate = verbose_picks / (2 * n)
    verbosity_truth_rate = verbose_truth / (2 * n)
    status = (
        "PASS"
        if accuracy >= minimum_accuracy
        and position_consistency >= minimum_position_consistency
        else "FAIL"
    )
    return {
        "status": status,
        "n_pairs": n,
        "accuracy": accuracy,
        "position_consistency": position_consistency,
        "verbosity_pick_rate": verbosity_pick_rate,
        "verbosity_truth_rate": verbosity_truth_rate,
        "thresholds": {
            "minimum_accuracy": minimum_accuracy,
            "minimum_position_consistency": minimum_position_consistency,
        },
        "limitations": "This measures only the supplied blind swapped-order sample; it does not establish general judge impartiality.",
        "evidence_errors": [],
    }
