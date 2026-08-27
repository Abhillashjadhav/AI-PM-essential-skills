# Brand `pm-verifier` as AI Evals for PMs

## Approved input

Rename the product publicly to **AI Evals for PMs** and make its description
explain what the product actually represents.

## Product contract

- Public display name: **AI Evals for PMs**.
- Tagline: **Spec to evidence-backed release decision.**
- Stable technical identifier: `pm-verifier` remains the repository path,
  marketplace/plugin name, Python package, and CLI command.
- Product meaning: an evidence-first, out-of-band evaluation and release-gating
  product for AI features and agents. It converts a feature specification or
  existing evaluation into a versioned suite, runs isolated repeated trials,
  grades real outcomes and trajectories, validates calibrated model judgments,
  exposes failures, and emits auditable `PASS`, `FAIL`, or `BLOCKED` evidence
  for CI and accountable human release review.

## Guardrails

- Do not describe the product as a single score.
- Do not claim hosted monitoring, live experimentation, inline request gating,
  deployment, or release automation.
- Do not rename technical identifiers or break existing installation and CLI
  commands.
- Keep the public profile, marketplace, documentation, CLI help, and generated
  human reports consistent.
- Synchronize plugin and package versions and correct stale consolidation
  status while changing the public copy.

## Evidence required

- Packaging and branding contract tests.
- Full `pm-verifier` test suite.
- Skill lint and repository-integrity checks.
- Public-profile link and copy contract.
