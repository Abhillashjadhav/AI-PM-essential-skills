# Evidence contract

Read this when creating or validating a runnable suite.

All evidence uses standards-compliant JSON. Non-standard numeric constants such
as `NaN`, `Infinity`, and `-Infinity` are invalid at every JSON/JSONL boundary.

## Required files

| File | Required content |
|---|---|
| `suite.json` | Schema version, suite ID/version/type, enabled surfaces, optional system/state/lineage contracts, minimum trials, graders, rubric, calibration contract, and release rules. |
| `dataset.json` | Dataset ID/version/source, `cases.jsonl` path, and SHA-256. |
| `cases.jsonl` | Stable `case_id`, input, expected outcome/trajectory evidence, and slicing metadata. |
| `run.json` | Run/candidate ID, deterministic `created_at`, model/prompt/tool/harness/configuration/dataset provenance, plus optional hash-bound PMOS and engineering lineage. |
| `trials.jsonl` | Stable trial/case IDs, unique isolation ID, environment fingerprint, trial index, completed status, actual outcome, ordered trajectory, enabled system/memory evidence, metrics, and `missing_evidence`. |
| `judgments.jsonl` | Required only for model gates/rubrics: judge/calibration/rubric provenance, binary gate answers, 1–5 scores, and rationales. |
| `calibration.json` | Required only for model gates/rubrics: held-out human golden provenance, agreement/error metrics, thresholds, and status. |

## Trial metrics

Record non-negative `latency_ms` and `cost_usd`, plus non-negative integer
`input_tokens`, `output_tokens`, and `retries`. Token release ceilings are also
integers. When the provider does not expose one, set a named
`missing_evidence` entry and accept a `BLOCKED` result until the suite owner
explicitly changes the evidence contract. Do not silently write zero.

## Candidate and run binding

`run.json` requires an immutable `candidate.sha256`. Every trial and model
judgment requires the same `run_id` plus `run_sha256`, where `run_sha256` is the
SHA-256 of the exact `run.json` bytes. The execution harness supplies and
overwrites these fields; the adapter cannot choose them. Any candidate or run
provenance change therefore invalidates stored trials and judgments.

Schema 1.1 can require `run.contract_lineage` roles through
`suite.lineage_contract`. Each lineage item declares `role`, `id`, `version`, a
project-relative `path`, and the artifact's SHA-256. Missing, escaping, or
digest-mismatched artifacts block the evaluation.

## Four-surface contract

- `outcome` and `trajectory` retain schema 1.0 behavior.
- Enabling `system` requires `system_contract` and `trial.system`. Required
  checkpoints must be present with ordered indexes, status, identity, state,
  and reason evidence. Optional checkpoints may be absent.
- Enabling `memory` requires `state_contract.enabled=true` and `trial.memory`.
  Required operations, isolation dimensions, timestamps, read ages, final
  state, and conflict evidence must be present.
- Missing required surface evidence is `BLOCKED`. Valid evidence of incorrect
  behavior is graded and can produce `FAIL`.

## Supported deterministic checks

- `equals_expected`: compare a trial path with a case's expected path.
- `equals`: compare with a configured literal.
- `field_present`: require a non-empty value.
- `max_length`: cap serialized length.
- `regex` / `not_regex`: require or prohibit patterns.
- `contains_all`: require configured members.
- `trace_step_equals`: locate a named trajectory step and compare one field
  with case evidence.

System checks:

- `checkpoint_present`, `checkpoint_passed`, and `final_checkpoint_reached`;
- `checkpoint_order` and `no_silent_loss`;
- `identity_preserved` and `state_continuity`; and
- `first_failure_equals`.

Memory checks:

- `state_written`, `state_retrieved`, `state_updated`, and `state_deleted`;
- `state_equals_expected` and `state_not_present`;
- `state_isolated` and `state_not_stale`; and
- `state_conflict_resolved` and `state_temporal_order`.

Use a model grader instead of stretching these checks into semantic claims.
Every check explicitly declares `gate: true|false`. A non-gating failure remains
visible as a diagnostic and contributes to partial quality, but it cannot fail
the release by itself. Wrong policy/tool paths can remain gates when the
approved risk contract makes that path disqualifying.

## Release rules

The runtime supports minimum case/trial pass rates, all-trials regression
consistency, minimum rubric score, zero-tolerance safety/privacy counts, and
per-trial ceilings for cost, latency, total tokens, and retries.

`examples/production-eval/` proves schema 1.0 compatibility. The complete
schema 1.1 executable example is `examples/complete-eval/`; its named fault
specifications cover system and memory `FAIL` and `BLOCKED` paths.

## Adapter protocol

`pm-verifier execute` sends `schema_version`, case/trial IDs, trial index,
`input`, and `metadata` to one fresh subprocess per trial. It never sends the
case's `expected` object. Adapter stdout must be exactly one JSON object and is
bounded to 1 MB; stderr is bounded to 64 KB. Non-zero exit, timeout, malformed
output, unordered trace indexes, missing evidence, invalid fingerprint, or
reused isolation ID blocks the evaluation.

Use `pm-verifier fault --project <eval> --name <fixture>` to materialize a named
known-bad mutation without editing source evidence.
