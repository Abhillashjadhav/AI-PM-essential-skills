# Validation evidence

This document records what this repository's checks establish and what they do not establish. It applies the evidence labels used by ContextPort: `VERIFIED` means observable repository evidence exists, `UNKNOWN` means the available evidence does not establish the claim, and `UNSUPPORTED` means the product intentionally does not perform the behavior.

## Automatically checked

`VERIFIED` by [`scripts/check_repository_integrity.py`](../scripts/check_repository_integrity.py):

- the catalogue's **8 installable plugins** have registered sources, plugin manifests, and skill directories;
- counts in README, CLAUDE and this document agree with the catalogue; the job table lists every plugin exactly once and every plugin has a README;
- the three public standalone skill directories exist: `token-cost-estimator`, `context-auditor`, and `concise-rewriter`;
- the retired `eval-rubric-generator` directory has no triggerable `SKILL.md`;
- each of those directories contains `SKILL.md`;
- each local Markdown link in every repository `README*.md` resolves to an existing file or directory, and local README anchors resolve to a heading;
- every fixture path mentioned in a README exists; and
- the ContextPort quick-start entry points and synthetic validation fixture exist.

`VERIFIED` by [`scripts/check_agent_graph_designer_contract.py`](../scripts/check_agent_graph_designer_contract.py):

- the committed synthetic graph contract contains complete node and typed-edge contracts;
- edge endpoints, non-terminal exits, orphan checks, fan-out/fan-in, bounded retry, failure, approval, and rejection paths are structurally valid;
- the sample uses an `ALL_REQUIRED` join with explicit missing, failed, stale, and conflict behavior;
- per-node and whole-graph budgets, permission shapes, attempt caps, and human-approval actions are declared; and
- the sample package and deterministic local runner are present.

`VERIFIED` by ContextPort's Python unit-test suite: deterministic local behavior exercised by [`context-port/tests/`](../context-port/tests/) against committed synthetic fixtures in [`context-port/fixtures/`](../context-port/fixtures/). These tests do not call a hosted model, inspect real exports, access an account, or perform destination writes.

`VERIFIED` by the pm-verifier unit-test suite in [`tests/eval-engine/`](../tests/eval-engine/):

- known-good repeated trials produce a `PASS` result and both report formats;
- deterministic outcome, trajectory, safety, privacy, metric, retry, and model-gate faults fire;
- missing, malformed, or mismatched evidence produces `BLOCKED`, never inferred success;
- human calibration enforces sample size, class coverage, per-dimension
  confidence bounds, chance-corrected agreement, false-positive rates, ordinal
  error, consistent per-dimension sample counts, and biased-judge rejection
  without pooled-metric masking;
- capability and regression thresholds, diagnostic-versus-gate behavior,
  partial quality, failure slices, lexical clustering, and migrated-data hashes
  are executable;
- subprocess adapter failures, oversized or inherited streams, finite timeout
  enforcement, unordered trajectories, non-finite metrics, malformed IDs, and
  duplicate declared trial isolation IDs produce `BLOCKED`;
- identical evidence produces identical results and displayed evidence is
  redacted for credential/PII patterns; and
- the package installs without runtime dependencies and the production example
  executes, grades, reports, and inspects from an isolated directory.
- the customer-support repository pilot refuses overwrites and path escapes,
  requires approved stable FR/AC traceability, binds PMOS/eval/engineering,
  candidate, adapter, automation, run, and trial artifacts by digest, rejects
  boundary tampering, and supports a pre-evidence `BOUND` state followed by
  structurally verified real-adapter evidence. PMOS approval is declared, not
  authenticated. Re-binding computes a new digest from current files; it is not
  proof that the prior approver approved those new contents.

Fresh adapter processes can still share files, environment variables, databases
and remote services. The adapter is trusted to reset application state and
report it honestly. IDs and fingerprints alone do not prove state isolation.

## Evidence by product

These columns describe the evidence present, not a blanket readiness rating.
Static checks inspect stored artifacts; deterministic runtime checks execute
code; recorded model runs concern specific saved outputs; human evidence must
name the scope reviewed. No plugin has a verified fresh-install test here.

| Product | Static / manual material | Deterministic runtime | Recorded model evidence | Human evidence / limits |
|---|---|---|---|---|
| pm-verifier | Manifest, skill, synthetic suites | Execute/grade/report/inspect and known-bad tests | Synthetic judge evidence; no live model-quality result | Product-specific calibration required |
| pm-tactical | Five skills, trigger and known-answer review cases | No shipped general runtime | One bounded local-skill agent exercise; broader quality unknown | Generated decisions need owner review |
| loop-designer | Trigger cases and worked loop template | No scheduler/state runtime shipped | One bounded local-skill agent exercise; broader quality unknown | Prompt budgets and checklist passes are not independent enforcement |
| agent-graph-designer | Contract topology checker and review cases | Synthetic fan-out, join and fail-closed example | No live reviewers in the sample | Retries, budgets and structured BLOCKED are contract requirements, not runner behavior |
| mcp-migration-auditor | Source-cited rules and sample audit | No live server compatibility test | Live skill quality unknown | Config-only evidence leaves some capabilities unconfirmed |
| pm-human-writer | Checker compares stored examples and required text | No live rewrite execution | Editing quality unknown | Author must review voice and factual preservation |
| ai-feature-kill-criteria | Skill, README example, manual trigger cases | No evaluation runtime | Live skill quality unknown | Owner supplies thresholds and investment decision |
| model-grader | Interview, template audit and author-run walkthroughs | Catalog replay and payload regressions; D4/D2 repaired | Saved catalog candidate outputs; not an interview-quality test | Filled-contract exit test and independent adjudication remain open |
| ContextPort (toolkit) | Schemas and synthetic fixtures | Local validation and migration tests | No hosted model required | Real export migration and destination writes unverified |
| Three standalone skills | Metadata and acceptance examples | No model or tokenizer runtime | No recorded live runs | Token, price and context claims require task-specific evidence |

`scripts/lint_all_skills.py` runs the metadata linter over every Git-tracked
`SKILL.md`, including internal skills. Public smoke runs this and the verifier
unit suite on every PR without product path filters. These are metadata and
deterministic runtime gates; they do not invoke every skill on a live model.

## Manual review material

The Markdown fixture documents under [`tests/`](../tests/) and product example directories provide reviewer prompts, known-answer cases, and expected outputs. They are **manual review material**, not automated behavioural tests: no repository command executes the Claude Code skills against those documents.

The agent-graph-designer contract checker and sample runner validate committed synthetic artifacts only. The runner uses one fixture-producing function for all branches and raises `ValueError` on a failed join. It does not execute the contract's timeout, retry, budget or `BLOCKED` transitions, and does not establish reviewer independence.

ContextPort's evaluation notes under [`context-port/evals/`](../context-port/evals/) record expected deterministic gates and synthetic-fixture observations. Review them with the corresponding command output; do not treat the documents alone as a passing automated run.

## Recorded behavioural model evidence

Two [bounded skill exercises](../reviews/2026-09-28-skill-exercises.md) used fresh
agent contexts with supplied fictional tasks and local skill text. They are
author-orchestrated samples, not installed-plugin runs or independent review.

No recorded external-model behavioural runs are present for the three standalone skills. The repository therefore makes no evidence-backed claim about their live invocation, output quality, token counting accuracy, pricing accuracy, or interoperability with other Claude Code runtimes.

pm-verifier's committed evidence is synthetic and local. It verifies the
harness behavior and known-bad gates, not the quality of an untested external
model or system under test.

ContextPort's recorded evidence is local and synthetic. Its [release-readiness report](../context-port/reports/RELEASE_READINESS.md) distinguishes completed automated checks from `UNKNOWN` and `UNSUPPORTED` capabilities. It is not evidence of a real Claude export migration or a consumer ChatGPT reconstruction write.

## Unverified and unsupported behavior

- `UNKNOWN`: compatibility with real Claude or ChatGPT exports, unless separately approved and inspected under the repository rules.
- `UNKNOWN`: current model names, availability, and prices. Any example must be treated as illustrative and checked against current official pricing.
- `UNKNOWN`: whether external or official skill libraries cover equivalent functionality; this is not continuously monitored.
- `UNKNOWN`: invocation, installation, hot-reload, and cross-runtime behavior of the three standalone Claude Code skills.
- `UNKNOWN`: live-model trigger accuracy and model-judge quality for `pm-verifier`; release-critical model judgments require product-specific human calibration.
- `UNSUPPORTED`: live production monitoring, online experimentation, or autonomous deployment by `pm-verifier`.
- `UNKNOWN`: live-model trigger accuracy and output quality for `agent-graph-designer`.
- `UNSUPPORTED`: autonomous deployment, merge, publish, send, purchase, delete, or overwrite by the agent-graph-designer synthetic runner.
- `UNSUPPORTED`: ContextPort consumer ChatGPT reconstruction writes, browser automation, and unapproved real-export handling, as documented in [`context-port/docs/CAPABILITIES.md`](../context-port/docs/CAPABILITIES.md).
- `UNKNOWN`: line coverage. No coverage instrumentation is configured; no percentage is claimed.

## Reviewer commands

Run these commands from the repository root after cloning:

```bash
python3 scripts/check_repository_integrity.py
python3 scripts/lint_all_skills.py
python3 -m pip install --no-deps --no-build-isolation ./pm-verifier
pm-verifier --version
python3 -m unittest discover -s tests/eval-engine -p 'test_*.py' -v
python3 tests/lint_skill.py pm-verifier/skills/eval-engine/SKILL.md
python3 scripts/check_agent_graph_designer_contract.py
python3 tests/lint_skill.py agent-graph-designer/skills/agent-graph-designer/SKILL.md
python3 agent-graph-designer/skills/agent-graph-designer/examples/sample-orchestrator.py
python3 -m unittest discover -s context-port/tests -q
python3 -m compileall -q scripts context-port
git diff --check
```

To verify the documented clone path without using the current working tree, run:

```bash
tmpdir="$(mktemp -d)"
git clone "$(pwd)" "$tmpdir/AI-PM-essential-skills"
cd "$tmpdir/AI-PM-essential-skills"
python3 scripts/check_repository_integrity.py
python3 -m unittest discover -s context-port/tests -q
```

The local clone command verifies the repository layout and commands. It does not prove GitHub network availability or external Claude Code behavior.
