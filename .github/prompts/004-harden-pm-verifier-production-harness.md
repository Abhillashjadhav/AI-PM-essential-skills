# Harden `pm-verifier` into an installable production CI harness

## Outcome

Make `pm-verifier` the one installable, versioned evaluation product in this
repository. A clean checkout must support this complete loop without a second
evaluation product:

`define suite -> execute isolated trials -> grade evidence -> inspect failures -> release decision`

## Verified starting point

PR #39 implements an evidence grader and release-decision engine. It validates
pre-recorded trials, applies deterministic and calibrated model judgments,
reports failure slices, and fails closed when evidence is invalid. It does not
yet execute a system under test, install as a package, or expose transcript
inspection through its CLI.

## Required changes

1. Add a dependency-free Python package with a `pm-verifier` console script and
   semantic version output.
2. Add versioned suite/result schemas and explicit compatibility blocking.
3. Add `inspect` so a PM can read failing trials, trajectories, outcomes,
   grader reasons, slices, and clusters.
4. Replace the combined calibration ratio with separate binary and ordinal
   statistics. Require a minimum human-golden sample, chance-corrected label
   agreement, and an agreement confidence lower bound.
5. Make trajectory and other deterministic checks explicitly gating or
   diagnostic. Exact paths must not gate by accident, while policy/safety path
   checks may remain deliberate release gates.
6. Preserve binary risk gates and add partial quality scores for capability
   hill-climbing.
7. Add a JSON-over-stdio subprocess adapter. Start a fresh process for every
   trial, never disclose expected answers to the adapter, require unique
   isolation IDs, and record an environment fingerprint.
8. Add known-answer tests for degenerate judges, insufficient calibration,
   non-gating trace checks, adapter failures, trial isolation, schema mismatch,
   deterministic outputs, and secret redaction.
9. Audit every useful public capability in `pm-evals` and `Evals-pass-1` before
   recommending repository removal.

## Explicit non-goals

- Postgres, S3, worker fleets, tenancy, or a hosted control plane
- live-traffic or inline request gating
- coupling the core to a model-provider evaluation API
- allowing gradual quality scores to bypass binary safety, privacy, or
  high-risk release gates

## Acceptance boundary

Do not call the result production-ready unless installation, execution,
inspection, calibration, fault injection, deterministic output, clean-checkout
usage, and CI behavior are covered by executable tests. Do not remove either
source repository until the destination is merged and its capability audit has
no unresolved `missing` entries.
