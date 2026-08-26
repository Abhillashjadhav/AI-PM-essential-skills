# Evidence contract

Read this when creating or validating a runnable suite.

## Required files

| File | Required content |
|---|---|
| `suite.json` | Schema version, suite ID/version/type, minimum trials, deterministic/model graders, rubric, calibration contract, and release rules. |
| `dataset.json` | Dataset ID/version/source, `cases.jsonl` path, and SHA-256. |
| `cases.jsonl` | Stable `case_id`, input, expected outcome/trajectory evidence, and slicing metadata. |
| `run.json` | Run/candidate ID, deterministic `created_at`, plus model, prompt, tool, harness, configuration, and dataset provenance. |
| `trials.jsonl` | Stable trial/case IDs, unique isolation ID, environment fingerprint, trial index, completed status, actual outcome, ordered trajectory, metrics, and `missing_evidence`. |
| `judgments.jsonl` | Required only for model gates/rubrics: judge/calibration/rubric provenance, binary gate answers, 1–5 scores, and rationales. |
| `calibration.json` | Required only for model gates/rubrics: held-out human golden provenance, agreement/error metrics, thresholds, and status. |

## Trial metrics

Record non-negative `latency_ms`, `input_tokens`, `output_tokens`, `cost_usd`,
and `retries`. When the provider does not expose one, set a named
`missing_evidence` entry and accept a `BLOCKED` result until the suite owner
explicitly changes the evidence contract. Do not silently write zero.

## Supported deterministic checks

- `equals_expected`: compare a trial path with a case's expected path.
- `equals`: compare with a configured literal.
- `field_present`: require a non-empty value.
- `max_length`: cap serialized length.
- `regex` / `not_regex`: require or prohibit patterns.
- `contains_all`: require configured members.
- `trace_step_equals`: locate a named trajectory step and compare one field
  with case evidence.

Use a model grader instead of stretching these checks into semantic claims.
Every check explicitly declares `gate: true|false`. A non-gating failure remains
visible as a diagnostic and contributes to partial quality, but it cannot fail
the release by itself. Wrong policy/tool paths can remain gates when the
approved risk contract makes that path disqualifying.

## Release rules

The runtime supports minimum case/trial pass rates, all-trials regression
consistency, minimum rubric score, zero-tolerance safety/privacy counts, and
per-trial ceilings for cost, latency, total tokens, and retries.

The complete executable schema is the synthetic
`examples/production-eval/` directory. Its `faults/specs.json` contains
deterministic known-bad mutations for outcome, trajectory, safety, privacy,
missing metrics, retries, and mixed failures.

## Adapter protocol

`pm-verifier execute` sends `schema_version`, case/trial IDs, trial index,
`input`, and `metadata` to one fresh subprocess per trial. It never sends the
case's `expected` object. Adapter stdout must be exactly one JSON object and is
bounded to 1 MB. Non-zero exit, timeout, malformed output, missing evidence,
invalid fingerprint, or reused isolation ID blocks the evaluation.
