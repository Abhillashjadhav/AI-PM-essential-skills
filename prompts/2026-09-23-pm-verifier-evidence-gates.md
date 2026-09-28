# Bounded executable evidence-gate review

Review the current main snapshot of the `pm-verifier` executable harness for
reproducible false PASS or invalid-evidence behavior. Use offline synthetic
fixtures only, with no live model, network, or paid calls.

Preserve schemas, release policy, thresholds, and golden fixtures unless a
mechanical correction is demonstrably necessary. Do not modify `model-grader`
or its pending PRs. Reproduce each defect before implementing a narrow repair,
include positive controls, and allow at most two repair attempts after a failed
gate. Keep one concern per PR and save observable test evidence.

Base: upstream main `60b61efb1294c10045f6af11ff07ce5aea5bb03b`, verified tree
`1d579fe26ffdb15545a368ba9af91dd09abc55ea`, local snapshot
`6a8c0d3910e20eb46fac7c9d0172db2730bdac7d`.

This phase is authorized for local review, tests, repairs, and commits only.
Publication and merging remain outside its scope.

## Verified finding and bounded correction

The full synthetic regression evaluator returned `PASS` when a `contains_all`
safety gate required `[{"approved": true}]` but every actual outcome contained
`[{"approved": 1}]`. Python membership treated the boolean and number as equal.
The harness already has recursive JSON equality that distinguishes these types.

Reuse that equality for array membership. Preserve numeric equivalence between
JSON numbers, exact nested JSON matches, string substring membership, object-key
membership, and existing release policy. Add a full-evaluator regression and
direct positive/negative controls before implementation.
