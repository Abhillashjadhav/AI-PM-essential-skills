from __future__ import annotations

from pathlib import Path
from typing import Any

from .io import EvidenceError, load_jsonl, rubric_hash, sha256_file


def _blocked(errors: list[str]) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "status": "BLOCKED",
        "evidence_errors": errors,
    }


def calibrate(
    suite: dict[str, Any],
    goldens_path: str | Path,
    judge_path: str | Path,
) -> dict[str, Any]:
    """Compare one judge/rubric version with a held-out human golden set."""
    try:
        goldens = load_jsonl(goldens_path)
        judgments = load_jsonl(judge_path)
    except EvidenceError as exc:
        return _blocked([str(exc)])

    errors: list[str] = []
    config = suite.get("calibration")
    if not isinstance(config, dict):
        return _blocked(["suite.calibration must be an object"])
    expected_judge = config.get("judge_id")
    if not isinstance(expected_judge, str) or not expected_judge:
        errors.append("suite.calibration.judge_id must be a non-empty string")
    try:
        minimum = float(config["minimum_agreement"])
        maximum_fp = float(config["maximum_false_positive_rate"])
    except (KeyError, TypeError, ValueError):
        return _blocked(
            [
                "suite calibration thresholds minimum_agreement and maximum_false_positive_rate must be numbers"
            ]
        )
    if not 0 <= minimum <= 1 or not 0 <= maximum_fp <= 1:
        errors.append("suite calibration thresholds must be between 0 and 1")
    if not goldens:
        errors.append("human golden set is empty")
    if not judgments:
        errors.append("judge calibration labels are empty")
    if any(row.get("source") != "human" for row in goldens):
        errors.append("every golden label must declare source='human'")
    if any(not isinstance(row.get("reviewer_id"), str) or not row["reviewer_id"] for row in goldens):
        errors.append("every golden label requires reviewer_id provenance")
    held_out = bool(goldens) and all(row.get("split") == "test" for row in goldens)
    if not held_out:
        errors.append("golden calibration evidence must use held-out split='test'")

    by_human = {row.get("item_id"): row for row in goldens}
    by_judge = {row.get("item_id"): row for row in judgments}
    if None in by_human or len(by_human) != len(goldens):
        errors.append("golden item_id values must be present and unique")
    if None in by_judge or len(by_judge) != len(judgments):
        errors.append("judge item_id values must be present and unique")
    if set(by_human) != set(by_judge):
        errors.append("human and judge calibration item_id sets must match exactly")
    judge_ids = {row.get("judge_id") for row in judgments}
    if judge_ids != {expected_judge}:
        errors.append(
            f"judge calibration provenance mismatch: {sorted(str(x) for x in judge_ids)}"
        )

    label_ids = {
        grader.get("id")
        for grader in suite.get("model_graders", [])
        if isinstance(grader, dict) and grader.get("id")
    }
    score_ids = {
        criterion.get("id")
        for criterion in suite.get("rubric", [])
        if isinstance(criterion, dict) and criterion.get("id")
    }
    for source, rows in (("human", goldens), ("judge", judgments)):
        for row in rows:
            item_id = row.get("item_id", "<missing>")
            labels = row.get("labels")
            scores = row.get("scores")
            if not isinstance(labels, dict) or set(labels) != label_ids:
                errors.append(
                    f"{source} item {item_id}: labels must match model grader ids {sorted(label_ids)}"
                )
            elif any(value not in {"PASS", "FAIL"} for value in labels.values()):
                errors.append(f"{source} item {item_id}: labels must be PASS or FAIL")
            if not isinstance(scores, dict) or set(scores) != score_ids:
                errors.append(
                    f"{source} item {item_id}: scores must match rubric ids {sorted(score_ids)}"
                )
            elif any(
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or not 1 <= float(value) <= 5
                for value in scores.values()
            ):
                errors.append(f"{source} item {item_id}: scores must be numbers from 1 to 5")
    if errors:
        return _blocked(errors)

    total = 0
    agree = 0
    false_positive = 0
    false_negative = 0
    gate_cells = 0
    dimensions: dict[str, dict[str, int]] = {}
    for item_id in sorted(by_human):
        human = by_human[item_id]
        judge = by_judge[item_id]
        human_labels = human.get("labels", {})
        judge_labels = judge.get("labels", {})
        human_scores = human.get("scores", {})
        judge_scores = judge.get("scores", {})

        for dimension, human_value in human_labels.items():
            judge_value = judge_labels.get(dimension, "UNKNOWN")
            stats = dimensions.setdefault(
                dimension, {"n": 0, "agree": 0, "false_positive": 0, "false_negative": 0}
            )
            stats["n"] += 1
            total += 1
            gate_cells += 1
            if judge_value == human_value:
                agree += 1
                stats["agree"] += 1
            elif judge_value == "PASS" and human_value == "FAIL":
                false_positive += 1
                stats["false_positive"] += 1
            elif judge_value == "FAIL" and human_value == "PASS":
                false_negative += 1
                stats["false_negative"] += 1

        for dimension, human_value in human_scores.items():
            stats = dimensions.setdefault(
                dimension, {"n": 0, "agree": 0, "false_positive": 0, "false_negative": 0}
            )
            stats["n"] += 1
            total += 1
            try:
                judge_value = float(judge_scores[dimension])
                human_score = float(human_value)
            except (KeyError, TypeError, ValueError):
                continue
            if abs(judge_value - human_score) <= 1:
                agree += 1
                stats["agree"] += 1

    overall = agree / total if total else 0.0
    fp_rate = false_positive / gate_cells if gate_cells else 0.0
    fn_rate = false_negative / gate_cells if gate_cells else 0.0
    status = "PASS" if overall >= minimum and fp_rate <= maximum_fp else "FAIL"

    per_dimension = {
        key: {
            **value,
            "agreement": value["agree"] / value["n"] if value["n"] else 0.0,
        }
        for key, value in sorted(dimensions.items())
    }
    return {
        "schema_version": "1.0",
        "calibration_id": config.get("calibration_id"),
        "judge_id": expected_judge,
        "rubric_hash": rubric_hash(suite),
        "golden_set": {
            "id": f"{suite.get('suite_id')}-human-goldens",
            "version": suite.get("suite_version"),
            "source": "human",
            "held_out": held_out,
            "n": len(goldens),
            "sha256": sha256_file(goldens_path),
        },
        "metrics": {
            "overall_agreement": overall,
            "false_positive_rate": fp_rate,
            "false_negative_rate": fn_rate,
            "per_dimension": per_dimension,
        },
        "thresholds": {
            "minimum_agreement": minimum,
            "maximum_false_positive_rate": maximum_fp,
        },
        "status": status,
        "evidence_errors": [],
    }
