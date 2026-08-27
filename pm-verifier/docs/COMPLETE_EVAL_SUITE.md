# Complete eval suite contract

AI Evals for PMs is not boilerplate for generating an AI product. It is the
verification contract that sits between a product decision and an engineering
implementation:

`PMOS decision → versioned eval contract → engineering evidence adapter → repeated trials → release decision`

The application remains product-specific. `pm-verifier` supplies the reusable
evidence, grading, inspection, and release-decision structure.

## End-to-end handoff

| Stage | Required input | Stable output |
|---|---|---|
| PMOS | User/workflow, product claim, expected outcome, risk boundaries, acceptance criteria, required checkpoints, and any memory promise | Approved product contract with ID, version, and SHA-256 |
| AI Evals for PMs | Approved contract plus representative cases, graders, thresholds, and provenance | `suite.json`, `cases.jsonl`, and the adapter evidence contract |
| Engineering AgentOS | Frozen suite and adapter protocol | Candidate implementation that emits outcome, trajectory, system, memory when enabled, metrics, and provenance-bound trial evidence |
| AI Evals for PMs | Repeated candidate trials | Machine `results.json`, PM `report.md`, failure inspection, and `PASS`, `FAIL`, or `BLOCKED` |

When available, place the PMOS and engineering contracts inside the evaluation
project and declare them in `run.contract_lineage`. A schema 1.1 suite can make
the `pmos` and `engineering` roles mandatory. The runtime verifies the paths
and SHA-256 digests before it accepts any trial.

## Evaluation surfaces

| Surface | Question | Required evidence |
|---|---|---|
| Outcome | Did the user or environment end in the correct state? | `trial.outcome` |
| Trajectory | Did the candidate use the required or forbidden path correctly? | Ordered `trial.trajectory` |
| System | Did the complete workflow preserve identity and state across every critical boundary? | `trial.system` checkpoints, first failure, completion, and consequences |
| Memory | Did promised state write, retrieve, update, forget, isolate, stay fresh, resolve conflicts, and preserve time order? | `trial.memory`; required only when `state_contract.enabled=true` |

Safety, privacy, reliability, quality, and operations are grader categories
that can apply across these surfaces. Capability and regression are suite
lifecycle purposes, not evidence surfaces.

## Fail-closed semantics

- Missing or malformed required evidence produces `BLOCKED`.
- Valid evidence showing incorrect behavior produces `FAIL` when the approved
  release rules reject it.
- Valid evidence satisfying all release rules produces `PASS`.
- A later successful checkpoint cannot erase an earlier recorded critical
  failure. `system.first_failure_stage` must match the observed first failed
  required checkpoint.
- Optional checkpoints may be absent. Required checkpoints may not disappear
  silently.
- Memory is not required when the product makes no persistence promise.

## Schema 1.1

Schema 1.1 adds:

- `suite.surfaces`;
- `suite.system_contract`;
- optional `suite.state_contract`;
- optional `suite.lineage_contract` and `run.contract_lineage`;
- `system` and `memory` grader scopes;
- `reliability` and `operational` grader categories; and
- per-surface summaries and raw inspection evidence.

Schema 1.0 outcome/trajectory projects remain executable without edits.
Use schema 1.1 only when adopting the explicit surface contracts.

## Runnable proof

[`examples/complete-eval`](../skills/eval-engine/examples/complete-eval/) is a
synthetic support workflow with two cases, two isolated trials per case, PMOS
and engineering lineage, all four surfaces, and 13 named fault fixtures. It
contains no real user or customer data.

```bash
pm-verifier execute --project complete-eval \
  --trials-out trials.executed.jsonl --results-out results.json \
  -- python3 complete-eval/reference_adapter.py

pm-verifier fault --project complete-eval \
  --name system-discovery-fail --out trials.faulted.jsonl

pm-verifier run --project complete-eval \
  --trials complete-eval/trials.faulted.jsonl \
  --out complete-eval/fault-results.json
```

The first command must return `PASS`. The discovery mutation returns `FAIL`.
The `system-silent-drop` and missing-evidence mutations return `BLOCKED`.

## Production boundary

This suite is production-capable for local and CI pre-release evaluation when
the adapter exposes real product evidence. It is not a hosted monitoring
service, live-traffic experiment platform, application generator, or proof
that an untested product is production-ready.
