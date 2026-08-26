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
