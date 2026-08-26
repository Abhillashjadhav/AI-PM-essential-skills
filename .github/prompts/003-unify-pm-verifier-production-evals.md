# Prompt 003 — unify production evaluation in pm-verifier

## Objective

Make `pm-verifier` the single public AI PM evaluation product. Migrate the
useful capabilities from `Abhillashjadhav/pm-evals` and
`Abhillashjadhav/Evals-pass-1`; do not create another eval product.

## Required user flow

`feature spec → define good → create eval suite → run trials → grade → inspect failures → release decision`

## Evidence contract

Implement and test:

1. outcome and trajectory evaluation;
2. deterministic and calibrated model graders;
3. human golden calibration and bias checks;
4. repeated trials, capability suites, and regression suites;
5. dataset, system, prompt, tool, harness, and configuration provenance;
6. cost, latency, token, and retry metrics;
7. safety/privacy gates;
8. failure slicing and clustering;
9. CI release decisions;
10. known-bad fixtures that prove important gates fire;
11. JSON results and Markdown reports; and
12. fail-closed handling of missing or invalid evidence.

Do not describe behavior as production-grade unless executable tests establish
it. Keep the PM-facing workflow simple and put implementation complexity below
the skill. Remove the `eval-rubric-generator` trigger collision while retaining
migration guidance.

## External baseline

- Anthropic, *Demystifying evals for AI agents* (2026-01-09)
- OpenAI, *Evaluate agent workflows*
- OpenAI, *Evaluation best practices*
- OpenAI, *A shared playbook for trustworthy third party evaluations* (2026-05-29)

## Delivery workflow

Issue #38 → `feat/pm-verifier-production-evals-38` → logical commits → tests →
draft PR → documented review → CI. Repository policy requires human approval
before merge.
