# Architecture

## PM-facing workflow

`pm-verifier` exposes one product flow:

1. **Feature spec** — supply the PRD or task contract.
2. **Define good** — separate disqualifying gates from gradual rubric criteria.
3. **Create suite** — freeze capability/regression cases, graders, thresholds, and provenance.
4. **Run trials** — capture repeated outcomes, trajectories, and operational metrics.
5. **Grade** — run deterministic checks and ingest calibrated model judgments.
6. **Inspect failures** — view cases, slices, clusters, silent path failures, and invalid evidence.
7. **Release decision** — emit `PASS`, `FAIL`, or `BLOCKED` for CI and a human-readable report.

## Runtime layers

| Layer | Responsibility |
|---|---|
| Package boundary | `pyproject.toml`, semantic version, console entry point, and bundled versioned JSON schemas provide one supported installation surface. |
| Execution | `execute` starts a fresh JSON-over-stdio subprocess for every trial, with no shell interpolation and a configured timeout/output limit. Expected answers never cross this boundary. |
| Evidence boundary | Strict JSON/JSONL loading, stable IDs, hashes, schema versions, provenance, and explicit validation errors. |
| Trial model | One case can have multiple trials; every trial contains an outcome, trajectory, metrics, environment fingerprint, and unique isolation ID. |
| Grading | Deterministic outcome/trajectory/safety/privacy checks run first; each check is explicitly a release gate or diagnostic. Calibrated model judgments handle semantic checks and rubrics. |
| Calibration | Held-out human goldens separately produce binary label agreement, Cohen's kappa, a Wilson interval, class-conditional false-positive/negative rates, and ordinal-score error. |
| Analysis | Binary release results, gradual partial-quality scores, reliability metrics, capability/regression summaries, metadata slices, and deterministic lexical failure clusters. |
| Decision | Release rules combine evidence validity, disqualifying gates, reliability thresholds, and operational guardrails. |
| Reporting | `results.json` is canonical machine evidence; `report.md` is the PM/reviewer view; `inspect` joins failures back to redacted raw outcomes and trajectories. |

The harness is deliberately a local/CI process, not a distributed service.
Postgres, object storage, worker fleets, tenancy, and hosted orchestration are
not prerequisites for trustworthy release evaluation and are not present.

## Fail-closed state model

| State | Meaning | CI exit |
|---|---|---:|
| `PASS` | Evidence is valid and every release rule passed. | 0 |
| `FAIL` | Evidence is valid and at least one quality, safety, privacy, regression, or operational gate failed. | 1 |
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
├── trials.jsonl            # repeated outcome/trajectory/metric evidence
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
  tuning when used as final calibration evidence.
- Each trial must use a unique isolation ID. The environment fingerprint binds
  it to a declared clean starting environment; repeated trials with shared
  isolation are invalid evidence.
- `run.created_at` is input provenance, not wall-clock output. Consequently,
  identical evidence produces byte-identical canonical results.
- Reports and inspection redact credential assignments, bearer tokens, email
  addresses, and private-key blocks before display. Raw trial files remain
  sensitive evidence and require repository/environment access controls.
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
  "input": {},
  "metadata": {}
}
```

The expected answer is deliberately absent. The adapter returns one JSON
object with the outcome, trajectory, metrics, missing-evidence list,
environment fingerprint, isolation ID, and completion status. The harness owns
and overwrites case/trial identifiers to prevent adapter-side selection drift.
