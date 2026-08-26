# Source-repository capability audit

Audited source commits:

- `Abhillashjadhav/pm-evals@a9adae024bfc9ace166152ffe19f7110fa1619d0`
- `Abhillashjadhav/Evals-pass-1@459ca222dae35839749964f4d26dd1862aaa19ce`

Disposition vocabulary:

- **MIGRATED** — supported by the destination product and executable evidence.
- **SUPERSEDED** — the same user outcome has a stricter destination contract.
- **DROPPED** — intentionally excluded because it is unsafe, misleading, or
  outside the single-product boundary.

There are no unresolved `MISSING` entries in this audit. Repository removal is
still blocked until the destination branch is reviewed, merged, and rerun from
a clean checkout on the public default branch.

## `pm-evals` public surface

| Source module / public symbols | Disposition | Destination / reason |
|---|---|---|
| `cli`: `version_callback`, `main`, `init`, `score`, `report`, `cluster`, `demo`, `validate_judge` | MIGRATED / SUPERSEDED | Installable `pm-verifier` CLI exposes version, validate, execute, run, inspect, report, calibrate, and bias. The PM skill creates suites from specs instead of a second `init` product. |
| `loader`: `TraceLoadError`, `iter_traces`, `load_traces` | SUPERSEDED | `io.py` uses strict JSON/JSONL evidence loading and produces `BLOCKED` rather than partial iteration over malformed evidence. |
| `models`: `Trace`, `Criterion`, `Score`, `EvalResult`, `ClusterResult`, `CriterionAggregate`, `Report` | SUPERSEDED | Versioned JSON schemas plus runtime validation replace a Pydantic-only Python API and keep the package dependency-free. |
| `rubric_parser`: `parse_rubric_text`, `parse_rubric` | SUPERSEDED | The PM-facing skill converts PRD/spec text into anchored `suite.json`; the runtime refuses ambiguous unanchored rubric bullets. Migrated source rubrics remain as examples. |
| `scorer`: `build_prompt`, `stub_judge`, `claude_judge`, `get_judge`, `score_trace`, `score_traces`, `results_to_jsonable` | DROPPED / SUPERSEDED | The `claude` path never called an SDK and silently returned hash-stub scores. The destination accepts explicit, provenance-bound judgments and blocks missing evidence; it never substitutes a fake judge. |
| `prepare`: `build_judge_prompt`, `write_judge_prompt` | SUPERSEDED | The eval skill generates provider-neutral rubric requests; versioned judgment/calibration files bind the returned evidence to judge and rubric hashes. |
| `validation`: `ValidationError`, `CriterionStats`, `DisagreementCase`, `ValidationReport`, `load_golden`, `load_judge_results`, `compute_validation`, `render_validation_markdown`, `run_validation` | MIGRATED | `calibration.py` adds held-out/source validation, minimum sample size, class coverage, Cohen's kappa, Wilson interval, class-conditional FP/FN rates, ordinal MAE, provenance hashes, and PASS/FAIL/BLOCKED. |
| `clustering`: `heuristic_namer`, `cluster_failures` | MIGRATED | `analysis.py` provides disclosed, deterministic `lexical-v1` clustering and metadata slices. |
| `clustering`: `embed_texts` and optional HDBSCAN/KMeans path | DROPPED | Heavy runtime/model downloads undermine the dependency-free, deterministic CI contract. The report explicitly discloses reduced lexical fidelity. |
| `reporter`: `build_report`, `render_markdown` | MIGRATED | `reporting.py` emits canonical release reporting plus redacted failure inspection. |
| `pairwise`: `PairLoadError`, `PairCase`, `OrientationVerdict`, `PairJudgeResult`, `PairSummary`, `PairwiseReport`, `load_pairs`, `build_pairwise_prompt`, `write_pairwise_prompt`, `load_pairwise_results`, `summarize_pairwise_results`, `render_pairwise_markdown` | SUPERSEDED | `bias.py` preserves the valid blind AB/BA experiment: accuracy, order consistency, verbosity selection, thresholds, and limitations. Source pair data/rubrics are retained as migrated examples; general preference reporting is not a release gate. |
| `pairwise_cli`: `prepare`, `report` | SUPERSEDED | The single `pm-verifier bias` workflow replaces the second console product. |
| Example generators: coding-assistant, customer-support, and summarization failure-mode builders | MIGRATED | The generators, rubrics, source data, and compressed traces are retained verbatim under `examples/migrated/pm-evals/examples/`; their hashes are covered by migration tests. |
| Datasets, rubrics, human goldens, reports, docs | MIGRATED | Lossless `.xz` snapshots and human-golden assets live under `examples/migrated/pm-evals/`; decompressed hashes are tested. |
| `CITATION.cff`, package metadata, MIT license | MIGRATED / SUPERSEDED | Destination now has installable package metadata and inherits the repository MIT license. Source commit identity is recorded above and in provenance files. |

## `Evals-pass-1` public surface

| Source module / public symbols | Disposition | Destination / reason |
|---|---|---|
| `agent.run_agent`, `part3.agent_v1.run`, `part3.agent_v2.run` | MIGRATED AS FIXTURE | The return-policy behavior is represented by the production example and its subprocess reference adapter; it is not exposed as a second product. |
| `prepare.truth` | SUPERSEDED | Expected evidence belongs in versioned cases and is never sent to the system-under-test adapter. |
| `report.grade`, `report.print_traces` | MIGRATED | Outcome/trajectory graders, silent-path detection, Markdown reporting, and `inspect` preserve the behavior with explicit schemas. |
| `part2.answer_key.flipped_key`, `part2.items.swapped`, `part2.judge.build_prompt`, `part2.judge.llm_judge`, `part2.judge.run_all` | MIGRATED / SUPERSEDED | Blind swapped-order bias analysis is implemented in `bias.py`; unwired model calls are not presented as evidence. |
| `part3.score.grade` | MIGRATED | Capability/regression suite rules and per-trial grading replace the one-off scorer. |
| `test_gate_fires.py` | MIGRATED | `test_known_bad_trajectory_gate_fires_on_silent_failure` proves a right answer reached through the wrong policy document fails when configured as a risk-critical gate. |
| `eval_set.json`, stores, answer keys, verdicts | MIGRATED | Versioned source snapshots and SHA-256 checks live under `examples/migrated/Evals-pass-1/`; the generalized production suite preserves the valid cases. |

## Removal gate

Both old repositories may be removed only when all statements below are true:

1. the destination PR has independent review, green required CI on the exact
   merge candidate, and is merged;
2. `pip install --no-deps ./pm-verifier` succeeds from a clean default-branch checkout;
3. the reference adapter produces repeated isolated trials and a PASS decision;
4. every known-bad outcome, trajectory, safety, privacy, calibration, adapter,
   provenance, schema, and metric fixture fires its intended gate;
5. the public README and GitHub profile link only to the canonical product; and
6. final source commit IDs and this audit remain in the destination history.
