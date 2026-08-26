# Validation evidence

This document records what this repository's checks establish and what they do not establish. It applies the evidence labels used by ContextPort: `VERIFIED` means observable repository evidence exists, `UNKNOWN` means the available evidence does not establish the claim, and `UNSUPPORTED` means the product intentionally does not perform the behavior.

## Automatically checked

`VERIFIED` by [`scripts/check_repository_integrity.py`](../scripts/check_repository_integrity.py):

- the seven marketplace plugins have registered sources, plugin manifests, and skill directories;
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
- human calibration enforces sample size, class coverage, confidence bounds,
  chance-corrected agreement, ordinal error, and biased-judge rejection;
- capability and regression thresholds, diagnostic-versus-gate behavior,
  partial quality, failure slices, lexical clustering, and migrated-data hashes
  are executable;
- subprocess adapter failures and shared trial isolation produce `BLOCKED`;
- identical evidence produces identical results and displayed evidence is
  redacted for credential/PII patterns; and
- the package installs without runtime dependencies and the production example
  executes, grades, reports, and inspects from an isolated directory.

## Manually validated material

The Markdown fixture documents under [`tests/`](../tests/) and product example directories provide reviewer prompts, known-answer cases, and expected outputs. They are **manual review material**, not automated behavioural tests: no repository command executes the Claude Code skills against those documents.

The agent-graph-designer contract checker and sample runner validate committed synthetic artifacts only. They do not invoke a hosted model or prove that the skill will produce equivalent artifacts in every live runtime.

ContextPort's evaluation notes under [`context-port/evals/`](../context-port/evals/) record expected deterministic gates and synthetic-fixture observations. Review them with the corresponding command output; do not treat the documents alone as a passing automated run.

## Recorded behavioural model evidence

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
