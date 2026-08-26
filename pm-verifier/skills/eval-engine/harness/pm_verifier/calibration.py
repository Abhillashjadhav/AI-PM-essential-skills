from __future__ import annotations

import math
from collections import Counter
from pathlib import Path
from typing import Any

from .io import EvidenceError, load_jsonl, rubric_hash, sha256_file


def _blocked(errors: list[str]) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "status": "BLOCKED",
        "evidence_errors": sorted(set(errors)),
    }


def _wilson_interval(successes: int, total: int) -> tuple[float, float]:
    if total <= 0:
        return 0.0, 0.0
    z = 1.959963984540054
    rate = successes / total
    denominator = 1 + (z * z / total)
    centre = rate + (z * z / (2 * total))
    margin = z * math.sqrt((rate * (1 - rate) / total) + (z * z / (4 * total * total)))
    return max(0.0, (centre - margin) / denominator), min(
        1.0, (centre + margin) / denominator
    )


def _cohens_kappa(human: list[str], judge: list[str]) -> float:
    if not human or len(human) != len(judge):
        return 0.0
    observed = sum(left == right for left, right in zip(human, judge)) / len(human)
    human_counts = Counter(human)
    judge_counts = Counter(judge)
    expected = sum(
        (human_counts[label] / len(human)) * (judge_counts[label] / len(judge))
        for label in {"PASS", "FAIL"}
    )
    if math.isclose(expected, 1.0):
        return 1.0 if math.isclose(observed, 1.0) else 0.0
    return (observed - expected) / (1 - expected)


def _thresholds(config: dict[str, Any]) -> tuple[dict[str, float | int], list[str]]:
    errors: list[str] = []
    values: dict[str, float | int] = {}
    integer_fields = ("minimum_golden_items",)
    ratio_fields = (
        "minimum_agreement",
        "minimum_kappa",
        "maximum_false_positive_rate",
    )
    for field in integer_fields:
        value = config.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            errors.append(f"suite.calibration.{field} must be an integer >= 1")
        else:
            values[field] = value
    for field in ratio_fields:
        value = config.get(field)
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            errors.append(f"suite.calibration.{field} must be a number from 0 to 1")
        elif not 0 <= float(value) <= 1:
            errors.append(f"suite.calibration.{field} must be a number from 0 to 1")
        else:
            values[field] = float(value)
    score_mae = config.get("maximum_score_mae")
    if not isinstance(score_mae, (int, float)) or isinstance(score_mae, bool) or score_mae < 0:
        errors.append("suite.calibration.maximum_score_mae must be a non-negative number")
    else:
        values["maximum_score_mae"] = float(score_mae)
    return values, errors


def calibrate(
    suite: dict[str, Any],
    goldens_path: str | Path,
    judge_path: str | Path,
) -> dict[str, Any]:
    """Calibrate one judge version against a held-out human golden set."""
    try:
        goldens = load_jsonl(goldens_path)
        judgments = load_jsonl(judge_path)
    except EvidenceError as exc:
        return _blocked([str(exc)])

    config = suite.get("calibration")
    if not isinstance(config, dict):
        return _blocked(["suite.calibration must be an object"])
    thresholds, errors = _thresholds(config)
    expected_judge = config.get("judge_id")
    if not isinstance(expected_judge, str) or not expected_judge:
        errors.append("suite.calibration.judge_id must be a non-empty string")
    if len(goldens) < int(thresholds.get("minimum_golden_items", 1)):
        errors.append(
            "human golden set is below the configured minimum: "
            f"found {len(goldens)}, requires {thresholds.get('minimum_golden_items', '<invalid>')}"
        )
    if not judgments:
        errors.append("judge calibration labels are empty")
    if any(row.get("source") != "human" for row in goldens):
        errors.append("every golden label must declare source='human'")
    if any(
        not isinstance(row.get("reviewer_id"), str) or not row["reviewer_id"]
        for row in goldens
    ):
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

    for dimension in sorted(label_ids):
        observed = {
            row.get("labels", {}).get(dimension) for row in goldens if isinstance(row, dict)
        }
        if observed != {"PASS", "FAIL"}:
            errors.append(
                f"human golden labels for {dimension} must contain both PASS and FAIL examples"
            )
    if errors:
        return _blocked(errors)

    human_labels: list[str] = []
    judge_labels: list[str] = []
    false_positive = 0
    human_negative = 0
    false_negative = 0
    human_positive = 0
    label_dimensions: dict[str, dict[str, Any]] = {}
    score_differences: list[float] = []
    score_dimensions: dict[str, dict[str, Any]] = {}

    for dimension in sorted(label_ids):
        dimension_human: list[str] = []
        dimension_judge: list[str] = []
        dimension_false_positive = 0
        dimension_human_negative = 0
        dimension_false_negative = 0
        dimension_human_positive = 0
        for item_id in sorted(by_human):
            human_value = by_human[item_id]["labels"][dimension]
            judge_value = by_judge[item_id]["labels"][dimension]
            dimension_human.append(human_value)
            dimension_judge.append(judge_value)
            human_labels.append(human_value)
            judge_labels.append(judge_value)
            if human_value == "FAIL":
                human_negative += 1
                dimension_human_negative += 1
                false_positive += judge_value == "PASS"
                dimension_false_positive += judge_value == "PASS"
            else:
                human_positive += 1
                dimension_human_positive += 1
                false_negative += judge_value == "FAIL"
                dimension_false_negative += judge_value == "FAIL"
        agrees = sum(
            left == right for left, right in zip(dimension_human, dimension_judge)
        )
        lower, upper = _wilson_interval(agrees, len(dimension_human))
        label_dimensions[dimension] = {
            "n": len(dimension_human),
            "agreement": agrees / len(dimension_human),
            "agreement_interval_95": {"lower": lower, "upper": upper},
            "cohens_kappa": _cohens_kappa(dimension_human, dimension_judge),
            "false_positive_rate": (
                dimension_false_positive / dimension_human_negative
            ),
            "false_negative_rate": (
                dimension_false_negative / dimension_human_positive
            ),
        }

    for dimension in sorted(score_ids):
        differences: list[float] = []
        within_one = 0
        exact = 0
        for item_id in sorted(by_human):
            human_score = float(by_human[item_id]["scores"][dimension])
            judge_score = float(by_judge[item_id]["scores"][dimension])
            difference = abs(judge_score - human_score)
            differences.append(difference)
            score_differences.append(difference)
            within_one += difference <= 1
            exact += math.isclose(difference, 0.0)
        score_dimensions[dimension] = {
            "n": len(differences),
            "mean_absolute_error": sum(differences) / len(differences),
            "within_one_rate": within_one / len(differences),
            "exact_agreement": exact / len(differences),
        }

    label_agree = sum(left == right for left, right in zip(human_labels, judge_labels))
    label_lower, label_upper = _wilson_interval(label_agree, len(human_labels))
    label_agreement = label_agree / len(human_labels) if human_labels else 0.0
    kappa = _cohens_kappa(human_labels, judge_labels)
    false_positive_rate = false_positive / human_negative if human_negative else 0.0
    false_negative_rate = false_negative / human_positive if human_positive else 0.0
    score_mae = (
        sum(score_differences) / len(score_differences) if score_differences else 0.0
    )
    label_passes = not label_ids or (
        label_lower >= float(thresholds["minimum_agreement"])
        and kappa >= float(thresholds["minimum_kappa"])
        and false_positive_rate
        <= float(thresholds["maximum_false_positive_rate"])
        and all(
            dimension["agreement_interval_95"]["lower"]
            >= float(thresholds["minimum_agreement"])
            and dimension["cohens_kappa"] >= float(thresholds["minimum_kappa"])
            and dimension["false_positive_rate"]
            <= float(thresholds["maximum_false_positive_rate"])
            for dimension in label_dimensions.values()
        )
    )
    score_passes = not score_ids or (
        score_mae <= float(thresholds["maximum_score_mae"])
        and all(
            dimension["mean_absolute_error"]
            <= float(thresholds["maximum_score_mae"])
            for dimension in score_dimensions.values()
        )
    )
    status = "PASS" if label_passes and score_passes else "FAIL"

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
            "overall_agreement": label_agreement,
            "label_agreement": label_agreement,
            "label_agreement_interval_95": {
                "lower": label_lower,
                "upper": label_upper,
            },
            "cohens_kappa": kappa,
            "false_positive_rate": false_positive_rate,
            "false_negative_rate": false_negative_rate,
            "score_mean_absolute_error": score_mae,
            "label_dimensions": label_dimensions,
            "score_dimensions": score_dimensions,
        },
        "thresholds": thresholds,
        "status": status,
        "evidence_errors": [],
    }
