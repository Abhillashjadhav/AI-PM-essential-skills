---
name: eval-engine
description: Use this skill when a user supplies an AI feature spec, PRD, PMOS/task contract, existing eval suite, traces, outputs, state evidence, or release question and wants to define good, create or run evals, grade outcomes, agent trajectories, end-to-end system checkpoints, or promised memory behavior, add deterministic or model graders, calibrate an LLM judge against human goldens, compare repeated trials, inspect failures, debug evaluation evidence, or make a CI release decision. Produce one provider-neutral AI Evals for PMs suite through the stable pm-verifier runtime, with binary gates, gradual rubrics, provenance, operational metrics, JSON results, and a Markdown report. Also use for migrating pm-evals or Evals-pass-1 work. Do not use for ordinary non-AI unit testing, generating the AI application itself, a one-off opinion on one output without a quality contract, or live production monitoring.
---

# Eval Engine

This skill powers **AI Evals for PMs**. Its stable install and CLI identifier is
`pm-verifier`.

Keep the user-facing flow simple:

`product contract → define surfaces → create eval suite → run trials → grade → inspect failures → release decision`

Put framework complexity in the bundled harness, not in the PM's workflow.

## 1. Start from the claim

Read the spec or existing suite. State the decision the evaluation must support:

- **Capability:** what can the candidate do, and how often does at least one attempt succeed?
- **Regression:** can the candidate still perform previously reliable behavior consistently?
- **Safeguard:** does a safety or privacy control block forbidden behavior?

Ask for missing product facts. Never invent policies, expected fields, thresholds, reference answers, or safety boundaries.

Classify each approved claim against four surfaces:

- **Outcome:** the final user/environment state.
- **Trajectory:** the risk-critical path, tools, policies, and decisions.
- **System:** required and optional checkpoints, identity, continuity, first failure, and consequences.
- **Memory:** only when the product promises persistence; write, retrieve, update, forget, isolation, freshness, conflict, and time semantics.

Safety, privacy, reliability, quality, and operations are cross-cutting grader
categories. Capability and regression are suite lifecycle purposes.

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
- optional hash-bound PMOS and engineering contract lineage;
- repeated trial outcomes, full trajectories, enabled system/memory evidence,
  cost, latency, tokens, and retries; and
- explicit `missing_evidence` values rather than inferred defaults.

Install the bundled package from `pm-verifier/` for CI use. Keep the
compatibility wrappers only for existing suites. Do not add provider SDKs or
hidden network calls.

When an approved PMOS package must be carried into an implementation
repository, read `references/repository-pilot.md` and use the guided
customer-support pilot. Keep `create`, `bind`, and `verify` as skill-owned
onboarding operations; do not add another public CLI or infer missing product
facts. Bind only after the accountable approver has selected `GO` and every
unresolved question is closed. A real first bind returns `BOUND`; execute the
adapter, bind again to seal the full trial file, and require read-only
`VERIFIED` evidence before interpreting a release decision.

## 4. Run trials and grade

Run at least the suite's `minimum_trials_per_case`. Prefer `pm-verifier
execute` with a JSON-over-stdio adapter so each trial starts in a fresh process.
Never send expected answers to the adapter. Require a unique `isolation_id` and
an `environment_fingerprint` for every trial. Capture the actual final
environment state as `outcome`; do not substitute the agent's claim about what
happened. Capture ordered tool/model/decision steps as `trajectory`.

For schema 1.1, capture `system.checkpoints` for every required workflow stage.
Missing required checkpoints block the evaluation; a present failed checkpoint
is valid failure evidence. Require `system.first_failure_stage` to match the
first observed failed required checkpoint so later success cannot erase it.

Capture `memory` only when `state_contract.enabled=true`. Require the declared
operations, isolation dimensions, staleness evidence, conflict evidence, and
temporal fields. If the product makes no memory promise, omit the memory surface
and state contract rather than fabricating state tests.

Run deterministic gates first. Skip model scoring for a trial that already failed a deterministic gate. For semantic gates or gradual rubrics:

1. prepare a self-contained judgment request;
2. save the external response in `judgments.jsonl` with judge and rubric provenance;
3. require a passing `calibration.json` for that exact judge/rubric hash; and
4. return `BLOCKED` for missing, invalid, mismatched, or `UNKNOWN` evidence.

Never replace a missing judge with a random, hash-based, or synthetic score.

## 5. Calibrate model graders

Use held-out human goldens. Keep prompt-tuning examples separate from final
calibration cases. Require the configured sample floor and both PASS/FAIL
classes. Compute binary agreement, a Wilson confidence interval, Cohen's kappa,
class-conditional false-positive/negative rates, and separate ordinal score
error. Use blind AB/BA swaps when pairwise position bias is relevant.

Read `references/rubric-calibration.md` before making a model grader release-critical. Small exploratory sets can improve a rubric; they do not justify a broad trust claim.

## 6. Inspect failures

Show:

- outcome failures separately from trajectory failures;
- system and memory failures separately from outcome/trajectory failures;
- first failed system checkpoint and user/operational consequences;
- silent path failures where the final outcome passed but the trajectory did not;
- per-case trial success, empirical `pass@k`, and empirical consistency `pass^k`;
- safety/privacy failures;
- operational guardrail failures;
- metadata slices; and
- failure clusters with the clustering method disclosed.

Keep the failing trace, grader reason, and provenance available for review.
Use `pm-verifier inspect`; reports and inspection must redact credential and
personal-data patterns before display.

## 7. Make the release decision

Emit exactly one state:

- `PASS`: evidence is valid and every release rule passed;
- `FAIL`: evidence is valid and a quality, reliability, safety, privacy, regression, or operational rule failed;
- `BLOCKED`: required evidence is missing, invalid, mismatched, or uncalibrated.

Write canonical machine evidence to `results.json` and the PM/reviewer view to `report.md`.

Run from an installed clean checkout:

```bash
python3 -m pip install --no-deps ./pm-verifier
pm-verifier execute --project eval -- python3 eval/adapter.py
pm-verifier run --project eval --trials eval/trials.executed.jsonl
pm-verifier inspect --results eval/results.json --trials eval/trials.executed.jsonl
pm-verifier report --results eval/results.json --out eval/report.md
```

The compatibility wrappers `prepare.py`, `run.py`, and `report.py` run the same commands. Exit codes are `0=PASS`, `1=FAIL`, and `2=BLOCKED`.

## Hard rules

- Grade the real outcome and the recorded trajectory independently.
- Grade the full system and promised memory independently when enabled.
- Treat missing required system/memory evidence as `BLOCKED`, not a failing score.
- Bind declared PMOS and engineering contracts by project-relative path and SHA-256.
- Require stable `FR-*` and `AC-*` IDs and preserve their PMOS relationships through cases and graders.
- Reject aliases among managed paths or candidate files before writing a repository pilot.
- Require a canonical receipt that seals the complete trial file before returning `VERIFIED`.
- Never create or bind an engineering handoff from `HOLD`, `NO-GO`, or unresolved PMOS intent.
- Treat safety and privacy defaults as zero tolerated failures unless the approved suite says otherwise.
- Version and hash datasets, rubrics, prompts, tools, harnesses, and configurations.
- Keep capability and regression thresholds separate; a capability failure is data, while a regression failure usually blocks release.
- Require known-bad fixtures for every important deterministic or release gate.
- Label synthetic data and deterministic demos; never present them as live-product quality evidence.
- Do not claim general judge impartiality from one bias sample.
- Do not describe a behavior as production-grade unless an executable test covers it.

## Limitations

- This is an out-of-band production CI/release harness, not hosted production observability, live experimentation, or an inline request gate.
- Model judgments remain probabilistic after calibration and need periodic human review.
- Empirical `pass@k` and `pass^k` describe recorded trials, not population guarantees.
- Dependency-free lexical clustering is explainable and reproducible but less semantic than embedding-based clustering.
- Marketplace installation supplies the PM workflow; the packaged CLI executes a product-specific adapter that must expose real trial evidence.
- The guided repository pilot is customer-support-specific until it is validated against additional repositories; it is not a general project generator.
