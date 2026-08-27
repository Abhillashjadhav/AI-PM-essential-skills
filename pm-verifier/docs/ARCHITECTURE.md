# Architecture

## PM-facing workflow

AI Evals for PMs, delivered through the stable `pm-verifier` package and CLI,
exposes one product flow:

1. **Product contract** — supply the PRD, PMOS decision, or task contract.
2. **Define surfaces** — select outcome, trajectory, system, and promised memory claims.
3. **Create suite** — freeze capability/regression cases, graders, thresholds, lineage, and provenance.
4. **Run trials** — capture repeated outcomes, trajectories, system/memory evidence, and operational metrics.
5. **Grade** — run deterministic checks and ingest calibrated model judgments.
6. **Inspect failures** — view cases, slices, clusters, silent path failures, and invalid evidence.
7. **Release decision** — emit `PASS`, `FAIL`, or `BLOCKED` for CI and a human-readable report.

## Runtime layers

| Layer | Responsibility |
|---|---|
| Package boundary | `pyproject.toml`, semantic version, console entry point, and bundled versioned JSON schemas provide one supported installation surface. |
| Execution | `execute` starts a fresh JSON-over-stdio subprocess for every trial, with no shell interpolation and a configured timeout/output limit. Expected answers never cross this boundary. |
| Evidence boundary | Strict JSON/JSONL loading, stable IDs, hashes, schema versions, provenance, and explicit validation errors. |
| Trial model | One case can have multiple trials; every trial contains a run binding, outcome, trajectory, enabled system/memory evidence, metrics, environment fingerprint, and unique isolation ID. |
| Grading | Deterministic checks span outcome, trajectory, system, and memory; quality, safety, privacy, reliability, and operations remain explicit categories. Each check is a release gate or diagnostic. Calibrated model judgments handle semantic checks and rubrics. |
| Calibration | Held-out human goldens separately produce binary label agreement, Cohen's kappa, a Wilson interval, class-conditional false-positive/negative rates, and ordinal-score error. |
| Analysis | Binary release results, gradual partial-quality scores, reliability metrics, capability/regression summaries, metadata slices, and deterministic lexical failure clusters. |
| Decision | Release rules combine evidence validity, disqualifying gates, reliability thresholds, and operational guardrails. |
| Reporting | `results.json` is canonical machine evidence; `report.md` is the PM/reviewer view; `inspect` joins failures back to redacted raw evidence for every enabled surface. |

The harness is deliberately a local/CI process, not a distributed service.
Postgres, object storage, worker fleets, tenancy, and hosted orchestration are
not prerequisites for trustworthy release evaluation and are not present.

## Fail-closed state model

| State | Meaning | CI exit |
|---|---|---:|
| `PASS` | Evidence is valid and every release rule passed. | 0 |
| `FAIL` | Evidence is valid and at least one quality, safety, privacy, reliability, regression, or operational rule failed. | 1 |
| `BLOCKED` | Required evidence is missing, invalid, mismatched, or uncalibrated. No quality claim is allowed. | 2 |

`BLOCKED` is not a softer `FAIL`: it says the evaluation cannot support a
release claim. Reports preserve the exact missing/invalid evidence rather than
turning absence into a default score.

## File contract

```text
eval/
├── suite.json              # graders, rubric, suite type, release rules
├── dataset.json            # dataset identity/version/source/cases hash
├── cases.jsonl             # inputs, expected evidence, slicing metadata
├── run.json                # candidate + model/prompt/tool/harness/config provenance
├── contracts/              # optional hash-bound PMOS/engineering artifacts
├── trials.jsonl            # repeated four-surface/metric evidence
├── trials.executed.jsonl   # adapter-captured evidence when `execute` is used
├── judgments.jsonl         # optional semantic gate/rubric judgments
├── calibration.json        # required when model graders are release-critical
├── results.json            # canonical machine-readable evaluation result
└── report.md               # human-readable release and failure report
```

## Trust boundaries

- Deterministic graders are valid only for checks their configuration can
  express; semantic claims are never approximated by hashes or keyword scores.
- A failing diagnostic contributes to partial quality and inspection, but only
  checks configured with `gate: true` can directly fail a release. High-risk
  tool/policy/safety paths may be deliberate gates; incidental exact sequences
  should remain diagnostic.
- Model judgments are external evidence. The runtime validates their schema,
  judge/rubric provenance, and calibration reference; it does not pretend to
  make an LLM call when no transport exists.
- Human goldens must be labelled as human, cover both PASS and FAIL classes,
  meet the configured sample floor, use stable IDs, and be held out from prompt
  tuning when used as final calibration evidence. Every label and score
  dimension must pass its threshold independently; pooled agreement cannot hide
  a weak grader dimension.
- Each trial must use a unique isolation ID. The environment fingerprint binds
  it to a declared clean starting environment; repeated trials with shared
  isolation are invalid evidence.
- `candidate.sha256` identifies immutable candidate content. Every trial and
  model judgment must match the exact `run_id` and SHA-256 of `run.json`, so a
  provenance or candidate change invalidates stored evidence.
- Schema 1.1 may require PMOS and engineering lineage roles. Every declared
  artifact must be a project-relative file whose actual SHA-256 matches
  `run.contract_lineage`; missing or escaping paths block the run.
- Required system checkpoints may fail, but they may not silently disappear.
  Missing/malformed checkpoint evidence is `BLOCKED`; present failed evidence
  is graded. The declared first failure must match the observed first failed
  required checkpoint.
- Memory evidence is mandatory only when the suite enables a state contract.
  Required operations, isolation checks, staleness, conflict, and temporal
  evidence then fail closed at the evidence boundary.
- `run.created_at` is input provenance, not wall-clock output. Consequently,
  identical evidence produces byte-identical canonical results.
- Adapter input, stdout, and stderr are bounded. Nonzero exits preserve bounded
  stderr or explicitly show its beginning, end, and truncation size.
  Trajectory indexes must be contiguous and ordered; oversized evidence and
  timeouts block the run.
- Reports and inspection redact credential-named structured values,
  credential assignments, bearer tokens, email addresses, and private-key
  blocks before display. Raw trial files remain sensitive evidence and require
  repository/environment access controls.
- Production monitoring, user feedback, A/B tests, and periodic transcript
  review remain outside this out-of-band CI harness.

## Subprocess adapter protocol

For every selected case and trial index, the harness starts a new command and
writes this request to stdin:

```json
{
  "schema_version": "1.0",
  "case_id": "case-1",
  "trial_id": "case-1-t1",
  "trial_index": 1,
  "run_id": "candidate-run-001",
  "run_sha256": "<sha256-of-run.json>",
  "input": {},
  "metadata": {}
}
```

The expected answer is deliberately absent. The adapter returns one JSON
object with the outcome, trajectory, metrics, missing-evidence list,
environment fingerprint, isolation ID, and completion status. The harness owns
and overwrites case/trial and run-binding identifiers to prevent adapter-side
selection or provenance drift.
