from __future__ import annotations

import json
from typing import Any

from .redaction import redact_text, redact_value


def _percent(value: Any) -> str:
    return f"{float(value):.1%}" if isinstance(value, (int, float)) else "—"


def render_markdown(result: dict[str, Any]) -> str:
    decision = result.get("decision", "BLOCKED")
    lines = ["# pm-verifier evaluation report", "", f"## Release decision: {decision}", ""]
    if decision == "BLOCKED":
        lines.extend(
            [
                "The evaluation cannot support a release claim because required evidence is missing, invalid, mismatched, or uncalibrated.",
                "",
                "### Evidence errors",
                "",
            ]
        )
        lines.extend(f"- {error}" for error in result.get("evidence_errors", []))
        lines.extend(["", "No missing evidence was converted into a passing score.", ""])
    else:
        summary = result["summary"]
        lines.extend(
            [
                f"- Suite: `{result['suite']['id']}` `{result['suite']['version']}` ({result['suite']['type']})",
                f"- Cases: {summary['case_count']} · trials: {summary['trial_count']}",
                f"- Trial pass rate: {_percent(summary['trial_pass_rate'])}",
                f"- Case release pass rate: {_percent(summary['case_pass_rate'])}",
                f"- Empirical pass@k: {_percent(summary['pass_at_k'])}",
                f"- Empirical pass^k: {_percent(summary['pass_power_k'])}",
                f"- Safety failures: {summary['safety_failures']} · privacy failures: {summary['privacy_failures']}",
                "",
                "`pass@k` means at least one observed trial passed for a case; `pass^k` means every observed trial passed. These are empirical results for the recorded trials, not population guarantees.",
                "",
                "## Outcome vs trajectory",
                "",
                "| Case / trial | Verdict | Outcome gates | Trajectory gates | Diagnostics | Partial quality | Mean rubric |",
                "|---|---|---|---|---|---:|---:|",
            ]
        )
        for trial in result["trials"]:
            outcome = ", ".join(trial["outcome_gate_failures"]) or "—"
            trajectory = ", ".join(trial["trajectory_gate_failures"]) or "—"
            mean = (
                f"{trial['mean_rubric_score']:.2f}"
                if trial["mean_rubric_score"] is not None
                else "—"
            )
            partial = (
                f"{trial['partial_quality_score']:.1%}"
                if trial.get("partial_quality_score") is not None
                else "—"
            )
            lines.append(
                f"| {trial['case_id']} / {trial['trial_id']} | "
                f"{'PASS' if trial['passed'] else 'FAIL'} | {outcome} | {trajectory} | "
                f"{', '.join(trial.get('diagnostic_failure_ids', [])) or '—'} | "
                f"{partial} | {mean} |"
            )
        metrics = result["metrics"]
        lines.extend(
            [
                "",
                "## Operational metrics",
                "",
                f"- Total cost: ${metrics['total_cost_usd']:.6f}",
                f"- Mean / p95 latency: {metrics['mean_latency_ms']:.1f} / {metrics['p95_latency_ms']:.1f} ms",
                f"- Input / output / total tokens: {metrics['input_tokens']} / {metrics['output_tokens']} / {metrics['total_tokens']}",
                f"- Retries: {metrics['retries']}",
                "",
                "## Release failures",
                "",
            ]
        )
        failures = [
            *(f"gate `{gate}`" for gate in result.get("failed_gate_ids", [])),
            *(f"release rule `{rule}`" for rule in result.get("failed_release_rules", [])),
        ]
        lines.extend([f"- {failure}" for failure in failures] or ["- None"])
        lines.extend(["", "## Failure slices", ""])
        if result.get("slices"):
            lines.extend(["| Slice | Trials | Pass rate | Failed gates |", "|---|---:|---:|---|"])
            for name, data in result["slices"].items():
                lines.append(
                    f"| {name} | {data['trials']} | {_percent(data['pass_rate'])} | "
                    f"{', '.join(data['failed_gate_ids']) or '—'} |"
                )
        else:
            lines.append("- No case metadata was available for slicing.")
        lines.extend(["", "## Failure clusters", ""])
        if result.get("failure_clusters"):
            for cluster in result["failure_clusters"]:
                lines.append(
                    f"- **{cluster['label']}** — {cluster['size']} failure(s), "
                    f"method `{cluster['method']}`; representative: {cluster['representative']}"
                )
        else:
            lines.append("- No failures to cluster.")
        calibration = result.get("calibration", {})
        lines.extend(
            [
                "",
                "## Judge calibration",
                "",
                f"- Judge: `{calibration.get('judge_id')}`",
                f"- Calibration: `{calibration.get('id')}` ({calibration.get('status')})",
                f"- Agreement: {_percent((calibration.get('metrics') or {}).get('overall_agreement'))}",
                f"- Agreement 95% lower bound: {_percent(((calibration.get('metrics') or {}).get('label_agreement_interval_95') or {}).get('lower'))}",
                f"- Cohen's kappa: {(calibration.get('metrics') or {}).get('cohens_kappa', '—')}",
                "",
                "Rubric scores are calibrated judgments, not objective measurements.",
                "",
            ]
        )

    lines.extend(["## Provenance and limitations", ""])
    if result.get("run_provenance"):
        provenance = result["run_provenance"]
        lines.extend(
            [
                f"- Candidate: `{provenance['candidate']['id']}` `{provenance['candidate']['version']}`",
                f"- Model: `{provenance['model']['provider']}/{provenance['model']['name']}` `{provenance['model']['version']}`",
                f"- Prompt: `{provenance['prompt']['id']}` `{provenance['prompt']['version']}`",
                f"- Harness: `{provenance['harness']['name']}` `{provenance['harness']['version']}`",
            ]
        )
    lines.extend(f"- {limitation}" for limitation in result.get("limitations", []))
    lines.append("")
    return redact_text("\n".join(lines))


def render_inspection(
    result: dict[str, Any],
    raw_trials: list[dict[str, Any]],
    *,
    case_id: str | None = None,
    trial_id: str | None = None,
) -> str:
    """Render selected failures with their raw outcome and trajectory evidence."""
    selected = [
        trial
        for trial in result.get("trials", [])
        if (case_id is None or trial.get("case_id") == case_id)
        and (trial_id is None or trial.get("trial_id") == trial_id)
        and (
            trial_id is not None
            or not trial.get("passed", False)
            or bool(trial.get("diagnostic_failure_ids"))
        )
    ]
    by_trial = {trial.get("trial_id"): trial for trial in raw_trials}
    lines = [
        "# pm-verifier failure inspection",
        "",
        f"Release decision: **{result.get('decision', 'BLOCKED')}**",
        "",
    ]
    if not selected:
        lines.append("No matching failing or diagnostic trials were found.")
    for graded in selected:
        identifier = graded.get("trial_id", "<unknown>")
        lines.extend(
            [
                f"## {graded.get('case_id', '<unknown>')} / {identifier}",
                "",
                f"- Verdict: {'PASS' if graded.get('passed') else 'FAIL'}",
                f"- Release gates: {', '.join(graded.get('failed_gate_ids', [])) or 'none'}",
                f"- Diagnostics: {', '.join(graded.get('diagnostic_failure_ids', [])) or 'none'}",
                f"- Partial quality: {_percent(graded.get('partial_quality_score'))}",
                "",
                "### Grader evidence",
                "",
            ]
        )
        for gate in graded.get("gate_results", []):
            if not gate.get("passed"):
                role = "release gate" if gate.get("gate") else "diagnostic"
                lines.append(
                    f"- `{gate.get('grader_id')}` ({role}): {gate.get('reason', 'no reason')}"
                )
        raw = by_trial.get(identifier)
        if raw is None:
            lines.extend(
                [
                    "",
                    "Raw trial evidence is unavailable. Supply the source trials JSONL to inspect the trajectory.",
                ]
            )
            continue
        safe = redact_value(raw)
        lines.extend(
            [
                "",
                "### Raw outcome",
                "",
                "```json",
                json.dumps(safe.get("outcome"), indent=2, sort_keys=True),
                "```",
                "",
                "### Raw trajectory",
                "",
                "```json",
                json.dumps(safe.get("trajectory"), indent=2, sort_keys=True),
                "```",
                "",
                f"Environment fingerprint: `{safe.get('environment_fingerprint', 'missing')}`",
                f"Isolation ID: `{safe.get('isolation_id', 'missing')}`",
                "",
            ]
        )
    return redact_text("\n".join(lines))
