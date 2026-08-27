# Complete AI Evals for PMs as a full evaluation suite

## Objective

Extend the existing `pm-verifier` package and CLI into a complete, fail-closed evaluation suite. Preserve the public product name **AI Evals for PMs**, the stable technical identifier `pm-verifier`, all existing commands, and all existing outcome/trajectory behavior.

Do not create a second product, repository, plugin, or CLI.

## Problem and hypothesis

The current harness can grade supplied outcomes and trajectories, but a PM cannot yet prove that a multi-step product workflow completed correctly or that promised state survived, changed, disappeared, and stayed isolated as required.

Hypothesis: one explicit contract spanning outcome, trajectory, system, and optional memory evidence will let a PM convert a product claim into an inspectable release decision without requiring a hosted evaluation service.

## Evaluation taxonomy

- Surface: `outcome`, `trajectory`, `system`, or `memory`.
- Category: `quality`, `safety`, `privacy`, `reliability`, or `operational`.
- Lifecycle purpose: suite type `capability` or `regression`.
- Safety and privacy are cross-cutting categories, not separate execution surfaces.
- Memory is evaluated only when a suite-level state contract enables it.

## Required behavior

1. Support deterministic and calibrated model graders across all four surfaces.
2. Add a suite-level system contract with required and optional checkpoints.
3. Validate checkpoint order, status, entity identity, state continuity, silent disappearance, first failure, consequences, and final completion.
4. Add an optional state contract for write, retrieve, update, delete/forget, isolation, stale reads, conflicts, and temporal behavior.
5. Treat missing, malformed, mismatched, or untrustworthy required evidence as `BLOCKED`; never convert it to a pass or crash.
6. Preserve valid, observed failures even when a later step appears successful.
7. Report per-surface results, cross-cutting safety/privacy/reliability/operations findings, first system failure, provenance, and limitations in both machine-readable and PM-readable forms.
8. Add optional project-relative lineage artifacts whose declared SHA-256 digest is verified, so PMOS and engineering contracts can be bound to the run when supplied.
9. Keep schema `1.0` projects working unchanged and introduce an explicit compatible schema for the new contracts.

## Required executable evidence

- Existing outcome/trajectory example and tests remain green.
- A deterministic complete example exercises all four surfaces.
- System fixtures: good, discovery failure, identity failure, content cross-wire, silent drop, wrong path, and missing-evidence blocked.
- Memory fixtures: write/read good, update good, forget good, forget failure, session/user/project isolation, stale failure, conflict/temporal failure, and missing-evidence blocked.
- CLI evaluate, run, inspect, report, fault injection, packaging, clean installation, repeatability, skill lint, repository integrity, and repository-wide tests pass.
- No real personal, customer, or private-source data is committed.

## Product boundary

Keep this a local/CI evaluation harness. Do not add a database, worker fleet, web service, dashboard, tenancy system, or vendor-specific production integration.

## Delivery process

Track the work in GitHub issue #42, implement on a feature branch with red-first tests and logical commits, open a draft PR, request independent review, run exact-head CI, and stop at the repository's manual merge boundary.
