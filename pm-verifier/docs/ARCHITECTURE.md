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
| Evidence boundary | Strict JSON/JSONL loading, stable IDs, hashes, schema versions, provenance, and explicit validation errors. |
| Trial model | One case can have multiple trials; every trial contains an outcome, trajectory, metrics, and candidate provenance. |
| Grading | Deterministic outcome/trajectory/safety/privacy gates run first; calibrated model judgments handle semantic gates and rubrics. |
| Calibration | Human goldens produce per-dimension agreement and false-positive/negative evidence for a specific judge and rubric hash. |
| Analysis | Reliability metrics, capability/regression summaries, metadata slices, and deterministic lexical failure clusters. |
| Decision | Release rules combine evidence validity, disqualifying gates, reliability thresholds, and operational guardrails. |
| Reporting | `results.json` is canonical machine evidence; `report.md` is the PM/reviewer view. |

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
├── judgments.jsonl         # optional semantic gate/rubric judgments
├── calibration.json        # required when model graders are release-critical
├── results.json            # canonical machine-readable evaluation result
└── report.md               # human-readable release and failure report
```

## Trust boundaries

- Deterministic graders are valid only for checks their configuration can
  express; semantic claims are never approximated by hashes or keyword scores.
- Model judgments are external evidence. The runtime validates their schema,
  judge/rubric provenance, and calibration reference; it does not pretend to
  make an LLM call when no transport exists.
- Human goldens must be labelled as human, use stable case/trial IDs, and be
  held out from prompt tuning when used as final calibration evidence.
- Production monitoring, user feedback, and periodic transcript review remain
  outside this local pre-release harness and are called out as limitations.
