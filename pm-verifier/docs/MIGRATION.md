# Source capability map and archive plan

## Capability map

| Source capability | Destination | Evidence |
|---|---|---|
| `Evals-pass-1`: outcome vs trajectory, full trace, silent-failure detection | `harness/pm_verifier/engine.py`, `graders.py` | `test_known_bad_trajectory_gate_fires_on_silent_failure` |
| `Evals-pass-1`: deterministic wrong-document fault | `harness/pm_verifier/faults.py`, `production-eval/faults/specs.json` | Known-bad outcome, trajectory, safety, privacy, metrics, retry, and mixed-failure tests |
| `Evals-pass-1`: answer key and return-policy dataset | `examples/migrated/Evals-pass-1/` plus generalized `production-eval/` | Source commit and SHA-256 provenance |
| `Evals-pass-1`: verbosity and position-bias experiment | `harness/pm_verifier/bias.py`, calibration pair fixtures | Stable and biased AB/BA known-answer tests |
| `pm-evals`: JSONL traces and multi-domain datasets | `examples/migrated/pm-evals/examples/` | Lossless `.xz` source snapshots with decompressed SHA-256 and commit provenance |
| `pm-evals`: rubrics and prompt-preparation concepts | Migrated rubrics; `suite.json` grader/rubric contract; provider-neutral `judgments.jsonl` | Strict schema and model-evidence tests |
| `pm-evals`: human golden set and judge results | `examples/migrated/pm-evals/golden/`; `calibration.py` | Human/held-out validation and biased-judge rejection tests |
| `pm-evals`: failure clustering | `analysis.py` | Explainable `lexical-v1` clusters and failure-slice test |
| `pm-evals`: Markdown reports and JSON workflow | `reporting.py`, CLI `run` and `report` | Clean-copy example emits `results.json` and `report.md` |
| `pm-evals`: pairwise swapped-order workflow | `bias.py` | Accuracy, position consistency, verbosity-pick/truth rates |
| existing `pm-verifier`: spec/PRD trigger and define-good workflow | `skills/eval-engine/SKILL.md` | Trigger fixtures and skill lint |
| existing `pm-verifier`: binary gates vs gradual rubric | `suite.json`, deterministic/model gate results, rubric scores | Per-trial gating and report tests |
| existing `pm-verifier`: simple local prepare/run/report UX | Copyable pure-stdlib harness and compatibility wrappers | Clean-copy execution test |
| existing `pm-verifier`: marketplace installation | `.claude-plugin/plugin.json` and root marketplace entry | Repository-integrity check |

## Production-layer coverage

| Required capability | Destination behavior | Executable evidence |
|---|---|---|
| 1. Outcome evaluation | Deterministic gates address paths in the real `trial.outcome`. | Known-good and wrong-outcome tests |
| 2. Trajectory evaluation | Ordered `trajectory` steps are graded independently from outcome. | Silent trajectory-failure test |
| 3. Deterministic/code graders | Eight provider-neutral checks, including exact values, patterns, structure, and trace-step matching. | Outcome, trajectory, safety, privacy, and deterministic-only tests |
| 4. Calibrated model graders | External judgments require exact judge, rubric, and calibration provenance. | Model-gate and provenance tests |
| 5. Human golden calibration | Held-out human labels produce per-dimension agreement and error rates. | Good-versus-biased calibration test |
| 6. Multiple trials | Minimum trials are enforced; per-case empirical `pass@k` and `pass^k` are reported. | Repeated-trial and minimum-trial tests |
| 7. Capability and regression suites | Suite type selects explicit hill-climbing or strict consistency semantics. | Capability-versus-regression test |
| 8. Dataset/version provenance | Dataset identity, version, source, cases hash, and suite hash are validated. | Provenance-mismatch and migrated-hash tests |
| 9. Runtime/config provenance | Candidate, model, prompt, tool, harness, and configuration identities, versions, and hashes are required. | Known-good and provenance-mismatch tests |
| 10. Operational metrics | Cost, latency, input/output tokens, and retries are recorded and can gate release. | Missing-metric and retry-ceiling tests |
| 11. Safety/privacy gates | Dedicated categories default to zero tolerated failures. | Safety and privacy fault tests |
| 12. Failure slicing/clustering | Case metadata slices and disclosed deterministic lexical clusters are emitted. | Slice/cluster test |
| 13. CI release gates | Exit codes are `0=PASS`, `1=FAIL`, `2=BLOCKED`; GitHub Actions runs all checks. | Report/exit tests and `.github/workflows/pm-verifier.yml` |
| 14. Known-bad gate fixtures | Deterministic fault specs mutate outcome, trace, safety, privacy, metrics, retries, and mixed evidence. | Known-bad unit tests |
| 15. Machine and human reports | `results.json` is canonical; `report.md` renders decisions, failures, metrics, provenance, and limitations. | Report-content test and clean-copy run |
| 16. Missing/invalid evidence | Schema, release-rule, hash, provenance, calibration, judgment, and metric errors produce `BLOCKED`. | Missing/invalid-evidence, invalid-contract, and provenance tests |

## Rejected source behavior

- The `pm-evals` `claude` judge fallback to a prompt hash is not migrated. A
  missing model judgment makes the unified result `BLOCKED`.
- Hash-derived demo scores are not quality evidence and do not enter release
  metrics.
- The source pairwise sample is not described as proof of general judge
  impartiality.
- Large source datasets remain labelled synthetic; their size does not make
  them representative of a live product distribution.

## Compatibility

- `prepare.py`, `run.py`, and `report.py` remain as wrappers around the unified
  runtime.
- Existing `gates.json`/`rubric.json` users should migrate to `suite.json`; the
  product README includes the field mapping.
- `eval-rubric-generator` is retired as a triggerable skill. Its directory
  retains a migration README pointing to `pm-verifier`.

## Archive recommendation

After the destination PR is human-reviewed, CI is green, and the default branch
contains the merged commit:

1. update each source repository README with an archived notice and a link to
   `AI-PM-essential-skills/pm-verifier`;
2. archive `Abhillashjadhav/pm-evals` and `Abhillashjadhav/Evals-pass-1` in
   GitHub settings; and
3. retain them read-only for commit-history and external-link continuity.

Do not delete either repository. Before merge, the recommendation is **not yet
safe to execute** because the destination branch and CI result are not the
public default-branch state.
