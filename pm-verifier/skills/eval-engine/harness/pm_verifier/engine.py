from __future__ import annotations

import math
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from .analysis import aggregate_metrics, build_slices, cluster_failures
from .graders import grade_deterministic, validate_grader
from .io import (
    EvidenceError,
    load_json,
    load_jsonl,
    rubric_hash,
    sha256_file,
    valid_sha256,
)


SCHEMA_VERSION = "1.0"
METRIC_FIELDS = ("latency_ms", "input_tokens", "output_tokens", "cost_usd", "retries")


def _blocked(errors: list[str], suite: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "suite": {
            "id": (suite or {}).get("suite_id"),
            "version": (suite or {}).get("suite_version"),
            "type": (suite or {}).get("suite_type"),
        },
        "decision": "BLOCKED",
        "evidence_errors": sorted(set(errors)),
        "failed_gate_ids": [],
        "failed_release_rules": [],
        "summary": {"case_count": 0, "trial_count": 0},
        "trials": [],
        "slices": {},
        "failure_clusters": [],
        "limitations": _limitations(),
    }


def _limitations() -> list[str]:
    return [
        "Model scores are calibrated judgments, not objective measurements.",
        "This out-of-band CI harness does not replace production monitoring, user feedback, A/B tests, or periodic human trace review.",
        "Lexical failure clustering is deterministic and dependency-free but is less semantic than an embedding-based method.",
    ]


def _is_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def _valid_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _required_mapping(
    container: dict[str, Any], key: str, label: str, errors: list[str]
) -> dict[str, Any]:
    value = container.get(key)
    if not isinstance(value, dict):
        errors.append(f"{label}.{key} must be an object")
        return {}
    return value


def _validate_provenance(
    suite_path: Path,
    suite: dict[str, Any],
    dataset: dict[str, Any],
    run: dict[str, Any],
    cases_path: Path,
) -> list[str]:
    errors: list[str] = []
    for label, document in (("suite", suite), ("dataset", dataset), ("run", run)):
        if document.get("schema_version") != SCHEMA_VERSION:
            errors.append(f"{label}.schema_version must be {SCHEMA_VERSION}")

    actual_cases_hash = sha256_file(cases_path)
    if dataset.get("source") in (None, ""):
        errors.append("dataset.source is required")
    for field in ("dataset_id", "dataset_version"):
        if dataset.get(field) in (None, ""):
            errors.append(f"dataset.{field} is required")
    if dataset.get("cases_path") != cases_path.name:
        errors.append(f"dataset.cases_path must be {cases_path.name!r}")
    run_dataset = _required_mapping(run, "dataset", "run", errors)
    for label, value in (
        ("dataset.cases_sha256", dataset.get("cases_sha256")),
        ("run.dataset.cases_sha256", run_dataset.get("cases_sha256")),
    ):
        if value != actual_cases_hash:
            errors.append(f"{label} mismatch: expected actual cases_sha256 {actual_cases_hash}")

    if run_dataset.get("id") != dataset.get("dataset_id"):
        errors.append("run.dataset.id does not match dataset.dataset_id")
    if run_dataset.get("version") != dataset.get("dataset_version"):
        errors.append("run.dataset.version does not match dataset.dataset_version")

    configuration = _required_mapping(run, "configuration", "run", errors)
    if configuration.get("id") != suite.get("suite_id"):
        errors.append("run.configuration.id does not match suite.suite_id")
    if configuration.get("version") != suite.get("suite_version"):
        errors.append("run.configuration.version does not match suite.suite_version")
    actual_suite_hash = sha256_file(suite_path)
    if configuration.get("sha256") != actual_suite_hash:
        errors.append(
            f"run.configuration.sha256 mismatch: expected actual suite hash {actual_suite_hash}"
        )

    if run.get("run_id") in (None, ""):
        errors.append("run.run_id is required")
    if not _valid_timestamp(run.get("created_at")):
        errors.append("run.created_at must be an RFC 3339 timestamp with timezone")
    candidate = _required_mapping(run, "candidate", "run", errors)
    for key in ("id", "version"):
        if candidate.get(key) in (None, ""):
            errors.append(f"run.candidate.{key} is required")

    model = _required_mapping(run, "model", "run", errors)
    for key in ("provider", "name", "version"):
        if key not in model or model[key] in (None, ""):
            errors.append(f"run.model.{key} is required")
    if not isinstance(model.get("parameters"), dict):
        errors.append("run.model.parameters must be an object")
    prompt = _required_mapping(run, "prompt", "run", errors)
    harness = _required_mapping(run, "harness", "run", errors)
    for label, value in (("prompt", prompt), ("harness", harness)):
        for key in ("id" if label == "prompt" else "name", "version", "sha256"):
            if value.get(key) in (None, ""):
                errors.append(f"run.{label}.{key} is required")
        if not valid_sha256(value.get("sha256")):
            errors.append(f"run.{label}.sha256 must be a 64-character SHA-256")
    tools = run.get("tools")
    if not isinstance(tools, list) or not tools:
        errors.append("run.tools must be a non-empty list")
    else:
        for index, tool in enumerate(tools):
            if not isinstance(tool, dict):
                errors.append(f"run.tools[{index}] must be an object")
                continue
            for key in ("name", "version", "sha256"):
                if tool.get(key) in (None, ""):
                    errors.append(f"run.tools[{index}].{key} is required")
            if not valid_sha256(tool.get("sha256")):
                errors.append(f"run.tools[{index}].sha256 must be a 64-character SHA-256")
    return errors


def _validate_suite(suite: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in ("suite_id", "suite_version", "name"):
        if suite.get(key) in (None, ""):
            errors.append(f"suite.{key} is required")
    if suite.get("suite_type") not in {"capability", "regression"}:
        errors.append("suite.suite_type must be capability or regression")
    minimum_trials = suite.get("minimum_trials_per_case")
    if not isinstance(minimum_trials, int) or isinstance(minimum_trials, bool) or minimum_trials < 1:
        errors.append("suite.minimum_trials_per_case must be an integer >= 1")

    deterministic = suite.get("deterministic_graders")
    if not isinstance(deterministic, list) or not deterministic:
        errors.append("suite.deterministic_graders must be a non-empty list")
        deterministic = []
    for grader in deterministic:
        if not isinstance(grader, dict):
            errors.append("every deterministic grader must be an object")
        else:
            errors.extend(validate_grader(grader))

    model_graders = suite.get("model_graders", [])
    rubric = suite.get("rubric", [])
    if not isinstance(model_graders, list) or not isinstance(rubric, list):
        errors.append("suite.model_graders and suite.rubric must be lists")
        model_graders, rubric = [], []
    for grader in model_graders:
        if not isinstance(grader, dict):
            errors.append("every model grader must be an object")
            continue
        if not isinstance(grader.get("gate"), bool):
            errors.append(f"model grader {grader.get('id')}: gate must be true or false")
        if grader.get("scope") not in {"outcome", "trajectory"}:
            errors.append(f"model grader {grader.get('id')}: invalid scope")
        if grader.get("category") not in {"quality", "safety", "privacy"}:
            errors.append(f"model grader {grader.get('id')}: invalid category")
        for field in ("id", "name", "prompt_version"):
            if not isinstance(grader.get(field), str) or not grader[field].strip():
                errors.append(
                    f"model grader {grader.get('id', '<missing>')}: {field} must be a non-empty string"
                )
    for criterion in rubric:
        if not isinstance(criterion, dict):
            errors.append("every rubric criterion must be an object")
            continue
        for field in ("id", "name", "definition", "anchor_1", "anchor_5", "worked_example"):
            if not isinstance(criterion.get(field), str) or not criterion[field].strip():
                errors.append(
                    f"rubric criterion {criterion.get('id', '<missing>')}: {field} must be a non-empty string"
                )
    identifiers = [
        item.get("id")
        for item in [*deterministic, *model_graders, *rubric]
        if isinstance(item, dict)
    ]
    missing_ids = sum(identifier in (None, "") for identifier in identifiers)
    if missing_ids:
        errors.append("every grader and rubric criterion needs an id")
    if len(identifiers) != len(set(identifiers)):
        errors.append("grader and rubric ids must be globally unique")
    calibration = suite.get("calibration")
    if model_graders or rubric:
        if not isinstance(calibration, dict):
            errors.append("suite.calibration is required when model judgments are used")
        else:
            for field in ("judge_id", "calibration_id"):
                if not isinstance(calibration.get(field), str) or not calibration[field].strip():
                    errors.append(f"suite.calibration.{field} must be a non-empty string")
            minimum_items = calibration.get("minimum_golden_items")
            if (
                not isinstance(minimum_items, int)
                or isinstance(minimum_items, bool)
                or minimum_items < 1
            ):
                errors.append(
                    "suite.calibration.minimum_golden_items must be an integer >= 1"
                )
            for field in (
                "minimum_agreement",
                "minimum_kappa",
                "maximum_false_positive_rate",
            ):
                value = calibration.get(field)
                if not _is_number(value) or not 0 <= float(value) <= 1:
                    errors.append(f"suite.calibration.{field} must be a number from 0 to 1")
            score_mae = calibration.get("maximum_score_mae")
            if not _is_number(score_mae) or float(score_mae) < 0:
                errors.append(
                    "suite.calibration.maximum_score_mae must be a non-negative number"
                )

    rules = suite.get("release_rules")
    if not isinstance(rules, dict):
        errors.append("suite.release_rules must be an object")
        return errors
    for field in ("min_case_pass_rate", "min_trial_pass_rate"):
        value = rules.get(field)
        if not _is_number(value) or not 0 <= float(value) <= 1:
            errors.append(f"suite.release_rules.{field} must be a number from 0 to 1")
    for field in ("max_safety_failures", "max_privacy_failures"):
        value = rules.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            errors.append(f"suite.release_rules.{field} must be an integer >= 0")
    if suite.get("suite_type") == "regression" and not isinstance(
        rules.get("require_all_regression_trials"), bool
    ):
        errors.append(
            "suite.release_rules.require_all_regression_trials must be boolean for regression suites"
        )
    if rubric:
        score = rules.get("min_model_score")
        if not _is_number(score) or not 1 <= float(score) <= 5:
            errors.append("suite.release_rules.min_model_score must be a number from 1 to 5")
    for field in ("max_cost_usd_per_trial", "max_latency_ms_per_trial", "max_total_tokens_per_trial"):
        if field in rules and (not _is_number(rules[field]) or float(rules[field]) < 0):
            errors.append(f"suite.release_rules.{field} must be a non-negative number")
    if "max_retries_per_trial" in rules:
        retries = rules["max_retries_per_trial"]
        if not isinstance(retries, int) or isinstance(retries, bool) or retries < 0:
            errors.append("suite.release_rules.max_retries_per_trial must be an integer >= 0")
    return errors


def _validate_cases(cases: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    if not cases:
        return ["cases.jsonl is empty"]
    identifiers = [case.get("case_id") for case in cases]
    if None in identifiers or "" in identifiers:
        errors.append("every case requires case_id")
    if len(identifiers) != len(set(identifiers)):
        errors.append("case_id values must be unique")
    for case in cases:
        if not isinstance(case.get("input"), (str, dict, list)):
            errors.append(f"case {case.get('case_id')}: input must be string/object/list")
        if not isinstance(case.get("expected"), dict):
            errors.append(f"case {case.get('case_id')}: expected must be an object")
        if not isinstance(case.get("metadata", {}), dict):
            errors.append(f"case {case.get('case_id')}: metadata must be an object")
    return errors


def _validate_trials(
    trials: list[dict[str, Any]], cases: list[dict[str, Any]], minimum: int
) -> list[str]:
    errors: list[str] = []
    if not trials:
        return ["trials.jsonl is empty"]
    case_ids = {case.get("case_id") for case in cases}
    trial_ids = [trial.get("trial_id") for trial in trials]
    if None in trial_ids or "" in trial_ids:
        errors.append("every trial requires trial_id")
    if len(trial_ids) != len(set(trial_ids)):
        errors.append("trial_id values must be unique")
    isolation_ids = [trial.get("isolation_id") for trial in trials]
    if None in isolation_ids or "" in isolation_ids:
        errors.append("every trial requires isolation_id")
    if len(isolation_ids) != len(set(isolation_ids)):
        errors.append("isolation_id values must be unique across trials")
    counts: Counter[str] = Counter()
    indexes: dict[str, set[int]] = {}
    for trial in trials:
        trial_id = trial.get("trial_id")
        case_id = trial.get("case_id")
        if case_id not in case_ids:
            errors.append(f"trial {trial_id}: unknown case_id {case_id!r}")
        counts[case_id] += 1
        index = trial.get("trial_index")
        if not isinstance(index, int) or isinstance(index, bool) or index < 1:
            errors.append(f"trial {trial_id}: trial_index must be an integer >= 1")
        elif index in indexes.setdefault(case_id, set()):
            errors.append(f"trial {trial_id}: duplicate trial_index {index} for case {case_id}")
        else:
            indexes[case_id].add(index)
        if trial.get("status") != "completed":
            errors.append(f"trial {trial_id}: status must be completed")
        if not valid_sha256(trial.get("environment_fingerprint")):
            errors.append(
                f"trial {trial_id}: environment_fingerprint must be a 64-character SHA-256"
            )
        if not isinstance(trial.get("outcome"), dict):
            errors.append(f"trial {trial_id}: outcome must be an object")
        if not isinstance(trial.get("trajectory"), list):
            errors.append(f"trial {trial_id}: trajectory must be a list")
        else:
            seen_step_indexes: set[int] = set()
            ordered_step_indexes: list[int] = []
            for step_number, step in enumerate(trial["trajectory"], 1):
                if not isinstance(step, dict):
                    errors.append(f"trial {trial_id}: trajectory step {step_number} must be an object")
                    continue
                for field in ("index", "type", "name", "attributes"):
                    if field not in step:
                        errors.append(
                            f"trial {trial_id}: trajectory step {step_number} missing {field}"
                        )
                step_index = step.get("index")
                if not isinstance(step_index, int) or isinstance(step_index, bool) or step_index < 1:
                    errors.append(
                        f"trial {trial_id}: trajectory step {step_number} index must be an integer >= 1"
                    )
                elif step_index in seen_step_indexes:
                    errors.append(f"trial {trial_id}: duplicate trajectory index {step_index}")
                else:
                    seen_step_indexes.add(step_index)
                    ordered_step_indexes.append(step_index)
                if not isinstance(step.get("attributes"), dict):
                    errors.append(
                        f"trial {trial_id}: trajectory step {step_number} attributes must be an object"
                    )
            if len(ordered_step_indexes) == len(trial["trajectory"]) and (
                ordered_step_indexes
                != list(range(1, len(ordered_step_indexes) + 1))
            ):
                errors.append(
                    f"trial {trial_id}: trajectory indexes must be contiguous and ordered from 1"
                )
        metrics = trial.get("metrics")
        if not isinstance(metrics, dict):
            errors.append(f"trial {trial_id}: metrics must be an object")
        else:
            for field in METRIC_FIELDS:
                value = metrics.get(field)
                if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
                    errors.append(f"trial {trial_id}: metrics.{field} must be a non-negative number")
        missing = trial.get("missing_evidence")
        if not isinstance(missing, list):
            errors.append(f"trial {trial_id}: missing_evidence must be a list")
        elif missing:
            errors.append(f"trial {trial_id}: explicitly missing evidence: {missing}")
    for case_id in sorted(str(value) for value in case_ids if value is not None):
        if counts[case_id] < minimum:
            errors.append(
                f"case {case_id}: requires at least {minimum} trials; found {counts[case_id]}"
            )
    return errors


def _eligible_model_trial_ids(
    suite: dict[str, Any],
    cases: list[dict[str, Any]],
    trials: list[dict[str, Any]],
) -> set[str]:
    """Return trials that cleared deterministic gates and need model grading."""
    by_case = {case["case_id"]: case for case in cases}
    eligible: set[str] = set()
    for trial in trials:
        case = by_case[trial["case_id"]]
        gate_results = [
            grade_deterministic(grader, trial, case)
            for grader in suite.get("deterministic_graders", [])
        ]
        if all(result["passed"] or not result["gate"] for result in gate_results):
            eligible.add(trial["trial_id"])
    return eligible


def _validate_model_evidence(
    suite: dict[str, Any],
    trials: list[dict[str, Any]],
    judgments: list[dict[str, Any]],
    calibration: dict[str, Any],
    eligible_trial_ids: set[str],
) -> list[str]:
    model_graders = suite.get("model_graders", [])
    rubric = suite.get("rubric", [])
    if not model_graders and not rubric:
        return []
    errors: list[str] = []
    config = suite["calibration"]
    expected_rubric_hash = rubric_hash(suite)
    if calibration.get("status") != "PASS":
        errors.append("calibration.status must be PASS before model judgments can gate release")
    if calibration.get("calibration_id") != config.get("calibration_id"):
        errors.append("calibration_id does not match suite calibration contract")
    if calibration.get("judge_id") != config.get("judge_id"):
        errors.append("calibration judge_id does not match suite calibration contract")
    if calibration.get("rubric_hash") != expected_rubric_hash:
        errors.append("calibration rubric_hash does not match current model graders/rubric")
    golden_set = calibration.get("golden_set")
    if not isinstance(golden_set, dict):
        errors.append("calibration.golden_set must be an object")
        golden_set = {}
    if golden_set.get("source") != "human" or golden_set.get("held_out") is not True:
        errors.append("calibration must reference a held-out human golden set")
    if not valid_sha256(golden_set.get("sha256")):
        errors.append("calibration golden_set.sha256 is invalid")
    golden_n = golden_set.get("n")
    if (
        not isinstance(golden_n, int)
        or isinstance(golden_n, bool)
        or golden_n < int(config["minimum_golden_items"])
    ):
        errors.append("calibration golden set is below the configured minimum")
    metrics = calibration.get("metrics")
    if not isinstance(metrics, dict):
        errors.append("calibration.metrics must be an object")
        metrics = {}
    if model_graders:
        interval = metrics.get("label_agreement_interval_95")
        if not isinstance(interval, dict):
            errors.append("calibration label agreement interval is missing")
            interval = {}
        agreement_lower = interval.get("lower")
        kappa = metrics.get("cohens_kappa")
        false_positive = metrics.get("false_positive_rate")
        if not _is_number(agreement_lower) or agreement_lower < float(
            config["minimum_agreement"]
        ):
            errors.append("calibration agreement confidence lower bound is below threshold")
        if not _is_number(kappa) or kappa < float(config["minimum_kappa"]):
            errors.append("calibration Cohen's kappa is below the suite threshold")
        if not _is_number(false_positive) or false_positive > float(
            config["maximum_false_positive_rate"]
        ):
            errors.append("calibration false-positive rate exceeds the suite threshold")
        label_dimensions = metrics.get("label_dimensions")
        if not isinstance(label_dimensions, dict):
            errors.append("calibration label_dimensions must be an object")
            label_dimensions = {}
        for grader in model_graders:
            grader_id = grader["id"]
            dimension = label_dimensions.get(grader_id)
            if not isinstance(dimension, dict):
                errors.append(f"calibration label dimension {grader_id} is missing")
                continue
            dimension_interval = dimension.get("agreement_interval_95")
            lower = (
                dimension_interval.get("lower")
                if isinstance(dimension_interval, dict)
                else None
            )
            dimension_kappa = dimension.get("cohens_kappa")
            dimension_false_positive = dimension.get("false_positive_rate")
            if not _is_number(lower) or lower < float(config["minimum_agreement"]):
                errors.append(
                    f"calibration label dimension {grader_id} agreement is below threshold"
                )
            if not _is_number(dimension_kappa) or dimension_kappa < float(
                config["minimum_kappa"]
            ):
                errors.append(
                    f"calibration label dimension {grader_id} kappa is below threshold"
                )
            if not _is_number(
                dimension_false_positive
            ) or dimension_false_positive > float(
                config["maximum_false_positive_rate"]
            ):
                errors.append(
                    f"calibration label dimension {grader_id} false-positive rate exceeds threshold"
                )
    if rubric:
        score_mae = metrics.get("score_mean_absolute_error")
        if not _is_number(score_mae) or score_mae > float(
            config["maximum_score_mae"]
        ):
            errors.append("calibration score mean absolute error exceeds the suite threshold")
        score_dimensions = metrics.get("score_dimensions")
        if not isinstance(score_dimensions, dict):
            errors.append("calibration score_dimensions must be an object")
            score_dimensions = {}
        for criterion in rubric:
            criterion_id = criterion["id"]
            dimension = score_dimensions.get(criterion_id)
            mae = (
                dimension.get("mean_absolute_error")
                if isinstance(dimension, dict)
                else None
            )
            if not _is_number(mae) or mae > float(config["maximum_score_mae"]):
                errors.append(
                    f"calibration score dimension {criterion_id} MAE exceeds threshold"
                )

    trial_ids = {trial["trial_id"] for trial in trials}
    by_trial = {row.get("trial_id"): row for row in judgments}
    if None in by_trial or len(by_trial) != len(judgments):
        errors.append("judgment trial_id values must be present and unique")
    missing = sorted(eligible_trial_ids - set(by_trial))
    extra = sorted(set(by_trial) - trial_ids, key=str)
    if missing:
        errors.append(f"missing model judgments for trials: {missing}")
    if extra:
        errors.append(f"model judgments reference unselected trials: {extra}")
    model_ids = {grader["id"] for grader in model_graders}
    rubric_ids = {criterion["id"] for criterion in rubric}
    for trial_id in sorted(eligible_trial_ids & set(by_trial)):
        judgment = by_trial[trial_id]
        if judgment.get("judge_id") != config.get("judge_id"):
            errors.append(f"judgment {trial_id}: judge_id mismatch")
        if judgment.get("calibration_id") != config.get("calibration_id"):
            errors.append(f"judgment {trial_id}: calibration_id mismatch")
        if judgment.get("rubric_hash") != expected_rubric_hash:
            errors.append(f"judgment {trial_id}: rubric_hash mismatch")
        answers = judgment.get("gate_answers")
        if not isinstance(answers, dict):
            errors.append(f"judgment {trial_id}: gate_answers must be an object")
        else:
            missing_answers = sorted(model_ids - set(answers))
            if missing_answers:
                errors.append(f"judgment {trial_id}: missing gate answers {missing_answers}")
            for grader_id in model_ids & set(answers):
                if answers[grader_id] not in {"PASS", "FAIL"}:
                    errors.append(
                        f"judgment {trial_id}: {grader_id} must be PASS or FAIL; got {answers[grader_id]!r}"
                    )
        scores = judgment.get("scores")
        if not isinstance(scores, dict):
            errors.append(f"judgment {trial_id}: scores must be an object")
        else:
            missing_scores = sorted(rubric_ids - set(scores))
            if missing_scores:
                errors.append(f"judgment {trial_id}: missing rubric scores {missing_scores}")
            for criterion_id in rubric_ids & set(scores):
                score = scores[criterion_id]
                if not isinstance(score, (int, float)) or isinstance(score, bool) or not 1 <= score <= 5:
                    errors.append(f"judgment {trial_id}: {criterion_id} score must be 1..5")
        if not isinstance(judgment.get("rationales"), dict):
            errors.append(f"judgment {trial_id}: rationales must be an object")
    return errors


def _grade_trials(
    suite: dict[str, Any],
    cases: list[dict[str, Any]],
    trials: list[dict[str, Any]],
    judgments: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_case = {case["case_id"]: case for case in cases}
    by_judgment = {row["trial_id"]: row for row in judgments}
    threshold = float(suite.get("release_rules", {}).get("min_model_score", 1))
    results: list[dict[str, Any]] = []
    for trial in trials:
        case = by_case[trial["case_id"]]
        gate_results = [
            grade_deterministic(grader, trial, case)
            for grader in suite.get("deterministic_graders", [])
        ]
        deterministic_failed = any(
            not result["passed"] and result["gate"] for result in gate_results
        )
        scores: dict[str, float] = {}
        quality_failures: list[str] = []
        if not deterministic_failed and (suite.get("model_graders") or suite.get("rubric")):
            judgment = by_judgment[trial["trial_id"]]
            for grader in suite.get("model_graders", []):
                passed = judgment["gate_answers"][grader["id"]] == "PASS"
                gate_results.append(
                    {
                        "grader_id": grader["id"],
                        "name": grader["name"],
                        "scope": grader["scope"],
                        "category": grader["category"],
                        "kind": "model",
                        "gate": grader["gate"],
                        "passed": passed,
                        "actual": judgment["gate_answers"][grader["id"]],
                        "expected": "PASS",
                        "reason": judgment["rationales"].get(
                            grader["id"], "model judgment supplied no rationale"
                        ),
                    }
                )
            scores = {
                criterion["id"]: float(judgment["scores"][criterion["id"]])
                for criterion in suite.get("rubric", [])
            }
            quality_failures = [
                f"{criterion_id} score {score:g} is below release threshold {threshold:g}"
                for criterion_id, score in scores.items()
                if score < threshold
            ]

        failed_checks = [result for result in gate_results if not result["passed"]]
        failed_gates = [result for result in failed_checks if result["gate"]]
        failed_ids = [result["grader_id"] for result in failed_gates]
        diagnostic_failure_ids = [
            result["grader_id"] for result in failed_checks if not result["gate"]
        ]
        outcome_failures = [
            result["grader_id"]
            for result in failed_gates
            if result["scope"] == "outcome"
        ]
        trajectory_failures = [
            result["grader_id"]
            for result in failed_gates
            if result["scope"] == "trajectory"
        ]
        partial_components = [
            1.0 if result["passed"] else 0.0 for result in gate_results
        ] + [(score - 1.0) / 4.0 for score in scores.values()]
        results.append(
            {
                "case_id": trial["case_id"],
                "trial_id": trial["trial_id"],
                "trial_index": trial["trial_index"],
                "passed": not failed_gates and not quality_failures,
                "failed_gate_ids": failed_ids,
                "failed_check_ids": [
                    result["grader_id"] for result in failed_checks
                ],
                "diagnostic_failure_ids": diagnostic_failure_ids,
                "outcome_gate_failures": outcome_failures,
                "trajectory_gate_failures": trajectory_failures,
                "silent_trajectory_failure": bool(trajectory_failures and not outcome_failures),
                "gate_results": gate_results,
                "rubric_scores": scores or None,
                "mean_rubric_score": (
                    sum(scores.values()) / len(scores) if scores else None
                ),
                "partial_quality_score": (
                    sum(partial_components) / len(partial_components)
                    if partial_components
                    else None
                ),
                "quality_failures": quality_failures,
                "model_grading_skipped": deterministic_failed,
                "metrics": trial["metrics"],
            }
        )
    return results


def _summarize(
    suite: dict[str, Any], cases: list[dict[str, Any]], results: list[dict[str, Any]]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    per_case: list[dict[str, Any]] = []
    for case in cases:
        rows = [result for result in results if result["case_id"] == case["case_id"]]
        passed = sum(1 for result in rows if result["passed"])
        any_pass = passed > 0
        all_pass = passed == len(rows)
        suite_pass = (
            all_pass
            if suite["suite_type"] == "regression"
            and suite["release_rules"].get("require_all_regression_trials", True)
            else any_pass
        )
        per_case.append(
            {
                "case_id": case["case_id"],
                "trials": len(rows),
                "passed_trials": passed,
                "success_rate": passed / len(rows),
                "pass_at_k": any_pass,
                "pass_power_k": all_pass,
                "suite_pass": suite_pass,
            }
        )
    passed_trials = sum(1 for result in results if result["passed"])
    safety = sum(
        1
        for result in results
        for gate in result["gate_results"]
        if not gate["passed"] and gate["gate"] and gate["category"] == "safety"
    )
    privacy = sum(
        1
        for result in results
        for gate in result["gate_results"]
        if not gate["passed"] and gate["gate"] and gate["category"] == "privacy"
    )
    quality_scores = [
        float(result["partial_quality_score"])
        for result in results
        if result["partial_quality_score"] is not None
    ]
    summary = {
        "case_count": len(cases),
        "trial_count": len(results),
        "passed_trials": passed_trials,
        "trial_pass_rate": passed_trials / len(results),
        "case_pass_rate": sum(item["suite_pass"] for item in per_case) / len(per_case),
        "pass_at_k": sum(item["pass_at_k"] for item in per_case) / len(per_case),
        "pass_power_k": sum(item["pass_power_k"] for item in per_case) / len(per_case),
        "mean_partial_quality_score": (
            sum(quality_scores) / len(quality_scores) if quality_scores else None
        ),
        "safety_failures": safety,
        "privacy_failures": privacy,
    }
    return summary, per_case


def _release_failures(
    suite: dict[str, Any],
    summary: dict[str, Any],
    results: list[dict[str, Any]],
) -> list[str]:
    rules = suite["release_rules"]
    failures: list[str] = []
    if summary["case_pass_rate"] < float(rules.get("min_case_pass_rate", 0)):
        failures.append("min_case_pass_rate")
    if summary["trial_pass_rate"] < float(rules.get("min_trial_pass_rate", 0)):
        failures.append("min_trial_pass_rate")
    if (
        suite["suite_type"] == "regression"
        and rules.get("require_all_regression_trials", True)
        and summary["trial_pass_rate"] < 1.0
    ):
        failures.append("require_all_regression_trials")
    if summary["safety_failures"] > int(rules.get("max_safety_failures", 0)):
        failures.append("max_safety_failures")
    if summary["privacy_failures"] > int(rules.get("max_privacy_failures", 0)):
        failures.append("max_privacy_failures")
    checks = (
        ("max_cost_usd_per_trial", "cost_usd"),
        ("max_latency_ms_per_trial", "latency_ms"),
        ("max_retries_per_trial", "retries"),
    )
    for rule_name, metric_name in checks:
        if rule_name in rules and any(
            float(result["metrics"][metric_name]) > float(rules[rule_name])
            for result in results
        ):
            failures.append(rule_name)
    if "max_total_tokens_per_trial" in rules and any(
        int(result["metrics"]["input_tokens"])
        + int(result["metrics"]["output_tokens"])
        > int(rules["max_total_tokens_per_trial"])
        for result in results
    ):
        failures.append("max_total_tokens_per_trial")
    return sorted(set(failures))


def evaluate_project(
    root: str | Path,
    *,
    trials_path: str | Path | None = None,
    judgments_path: str | Path | None = None,
) -> dict[str, Any]:
    """Validate evidence, grade trials, analyze failures, and decide release."""
    project = Path(root)
    suite_path = project / "suite.json"
    cases_path = project / "cases.jsonl"
    selected_trials = Path(trials_path) if trials_path else project / "trials.jsonl"
    selected_judgments = (
        Path(judgments_path) if judgments_path else project / "judgments.jsonl"
    )
    suite: dict[str, Any] = {}
    try:
        suite = load_json(suite_path)
        dataset = load_json(project / "dataset.json")
        run = load_json(project / "run.json")
        cases = load_jsonl(cases_path)
        trials = load_jsonl(selected_trials)
    except EvidenceError as exc:
        return _blocked([str(exc)], suite)

    errors: list[str] = []
    errors.extend(_validate_suite(suite))
    errors.extend(_validate_cases(cases))
    minimum = suite.get("minimum_trials_per_case", 1)
    if isinstance(minimum, int) and not isinstance(minimum, bool) and minimum >= 1:
        errors.extend(_validate_trials(trials, cases, minimum))
    errors.extend(_validate_provenance(suite_path, suite, dataset, run, cases_path))
    if errors:
        blocked = _blocked(errors, suite)
        blocked["summary"] = {
            "case_count": len(cases),
            "trial_count": len(trials),
        }
        return blocked

    uses_model_evidence = bool(suite.get("model_graders") or suite.get("rubric"))
    eligible_trial_ids = (
        _eligible_model_trial_ids(suite, cases, trials) if uses_model_evidence else set()
    )
    judgments: list[dict[str, Any]] = []
    calibration: dict[str, Any] = {}
    if eligible_trial_ids:
        try:
            judgments = load_jsonl(selected_judgments)
            calibration = load_json(project / "calibration.json")
        except EvidenceError as exc:
            blocked = _blocked([str(exc)], suite)
            blocked["summary"] = {
                "case_count": len(cases),
                "trial_count": len(trials),
            }
            return blocked
        errors.extend(
            _validate_model_evidence(
                suite,
                trials,
                judgments,
                calibration,
                eligible_trial_ids,
            )
        )
    if errors:
        blocked = _blocked(errors, suite)
        blocked["summary"] = {
            "case_count": len(cases),
            "trial_count": len(trials),
        }
        return blocked

    trial_results = _grade_trials(suite, cases, trials, judgments)
    summary, case_results = _summarize(suite, cases, trial_results)
    failed_gate_ids = sorted(
        {gate for result in trial_results for gate in result["failed_gate_ids"]}
    )
    failed_release_rules = _release_failures(suite, summary, trial_results)
    # A gate failure fails its trial. Suite-level thresholds decide whether the
    # observed trial failures fail the release; safety/privacy defaults remain 0.
    decision = "FAIL" if failed_release_rules else "PASS"
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": run["created_at"],
        "suite": {
            "id": suite["suite_id"],
            "version": suite["suite_version"],
            "type": suite["suite_type"],
            "sha256": sha256_file(suite_path),
        },
        "dataset": {
            "id": dataset["dataset_id"],
            "version": dataset["dataset_version"],
            "cases_sha256": sha256_file(cases_path),
        },
        "run_provenance": run,
        "calibration": {
            "id": calibration.get("calibration_id"),
            "judge_id": calibration.get("judge_id"),
            "rubric_hash": calibration.get("rubric_hash"),
            "status": calibration.get("status"),
            "metrics": calibration.get("metrics"),
        },
        "decision": decision,
        "evidence_errors": [],
        "failed_gate_ids": failed_gate_ids,
        "failed_release_rules": failed_release_rules,
        "summary": summary,
        "case_results": case_results,
        "metrics": aggregate_metrics(trials),
        "trials": trial_results,
        "slices": build_slices(cases, trial_results),
        "failure_clusters": cluster_failures(trial_results),
        "limitations": _limitations(),
    }
