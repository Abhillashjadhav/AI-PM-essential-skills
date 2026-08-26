---
name: eval-engine
description: Use this skill when a user supplies an AI feature spec, PRD, task contract, existing eval suite, traces, outputs, or release question and wants to define good, create or run evals, grade outcomes or agent trajectories, add deterministic or model graders, calibrate an LLM judge against human goldens, compare repeated trials, inspect failure clusters, debug evaluation evidence, or make a CI release decision. Produce one provider-neutral pm-verifier suite with binary gates, gradual rubrics, provenance, operational metrics, JSON results, and a Markdown report. Also use for migrating pm-evals or Evals-pass-1 work. Do not use for ordinary non-AI unit testing, a one-off opinion on one output without a quality contract, or live production monitoring.
---

# Eval Engine

Keep the user-facing flow simple:

`feature spec → define good → create eval suite → run trials → grade → inspect failures → release decision`

Put framework complexity in the bundled harness, not in the PM's workflow.

## 1. Start from the claim

Read the spec or existing suite. State the decision the evaluation must support:

- **Capability:** what can the candidate do, and how often does at least one attempt succeed?
- **Regression:** can the candidate still perform previously reliable behavior consistently?
- **Safeguard:** does a safety or privacy control block forbidden behavior?

Ask for missing product facts. Never invent policies, expected fields, thresholds, reference answers, or safety boundaries.

## 2. Define good

Separate:

- **Gates:** binary, disqualifying checks on one trial. Prefer deterministic code checks for objective facts, outcome state, tool calls, required structure, safety, and privacy.
- **Rubric criteria:** gradual 1–5 judgments for useful differences among gate-clearing outputs. Use feature-specific anchors and a worked example.

Use the smallest complete set. Do not add weak gates to satisfy a fixed count. Read `references/gate-design.md` when a check could be either a gate or a score.

## 3. Create the suite

Create the files in `references/evidence-contract.md`. Record:

- suite type, version, graders, rubric, and release thresholds;
- versioned dataset and case metadata for slicing;
- candidate, model, prompt, tool, harness, and configuration provenance;
- repeated trial outcomes, full trajectories, cost, latency, tokens, and retries; and
- explicit `missing_evidence` values rather than inferred defaults.

Copy the bundled `harness/pm_verifier/` package plus `prepare.py`, `run.py`, and `report.py` into the eval folder. Do not add provider SDKs or hidden network calls.

## 4. Run trials and grade

Run at least the suite's `minimum_trials_per_case`. Capture the actual final environment state as `outcome`; do not substitute the agent's claim about what happened. Capture ordered tool/model/decision steps as `trajectory`.

Run deterministic gates first. Skip model scoring for a trial that already failed a deterministic gate. For semantic gates or gradual rubrics:

1. prepare a self-contained judgment request;
2. save the external response in `judgments.jsonl` with judge and rubric provenance;
3. require a passing `calibration.json` for that exact judge/rubric hash; and
4. return `BLOCKED` for missing, invalid, mismatched, or `UNKNOWN` evidence.

Never replace a missing judge with a random, hash-based, or synthetic score.

## 5. Calibrate model graders

Use held-out human goldens. Keep prompt-tuning examples separate from final calibration cases. Compute per-dimension agreement plus false-positive and false-negative rates. Use blind AB/BA swaps when pairwise position bias is relevant.

Read `references/rubric-calibration.md` before making a model grader release-critical. Small exploratory sets can improve a rubric; they do not justify a broad trust claim.

## 6. Inspect failures

Show:

- outcome failures separately from trajectory failures;
- silent path failures where the final outcome passed but the trajectory did not;
- per-case trial success, empirical `pass@k`, and empirical consistency `pass^k`;
- safety/privacy failures;
- operational guardrail failures;
- metadata slices; and
- failure clusters with the clustering method disclosed.

Keep the failing trace, grader reason, and provenance available for review.

## 7. Make the release decision

Emit exactly one state:

- `PASS`: evidence is valid and every release rule passed;
- `FAIL`: evidence is valid and a quality, reliability, safety, privacy, regression, or operational rule failed;
- `BLOCKED`: required evidence is missing, invalid, mismatched, or uncalibrated.

Write canonical machine evidence to `results.json` and the PM/reviewer view to `report.md`.

Run locally from the eval folder:

```bash
python3 -m pm_verifier prepare
python3 -m pm_verifier run
python3 -m pm_verifier report
```

The compatibility wrappers `prepare.py`, `run.py`, and `report.py` run the same commands. Exit codes are `0=PASS`, `1=FAIL`, and `2=BLOCKED`.

## Hard rules

- Grade the real outcome and the recorded trajectory independently.
- Treat safety and privacy defaults as zero tolerated failures unless the approved suite says otherwise.
- Version and hash datasets, rubrics, prompts, tools, harnesses, and configurations.
- Keep capability and regression thresholds separate; a capability failure is data, while a regression failure usually blocks release.
- Require known-bad fixtures for every important deterministic or release gate.
- Label synthetic data and deterministic demos; never present them as live-product quality evidence.
- Do not claim general judge impartiality from one bias sample.
- Do not describe a behavior as production-grade unless an executable test covers it.

## Limitations

- This is a local pre-release evaluation harness, not production observability.
- Model judgments remain probabilistic after calibration and need periodic human review.
- Empirical `pass@k` and `pass^k` describe recorded trials, not population guarantees.
- Dependency-free lexical clustering is explainable and reproducible but less semantic than embedding-based clustering.
- Marketplace installation supplies the skill and harness; the user's system-under-test must still produce real trial evidence.
