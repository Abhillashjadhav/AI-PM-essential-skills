# Build prompt: agent-graph-designer

## Goal

Add `agent-graph-designer` as the seventh installable plugin in the AI PM Skills Marketplace.

## Product boundary

- Preserve `loop-designer` unchanged: it turns one recurring task into one guarded autonomous loop.
- Use `agent-graph-designer` when multiple specialist loops or agents must branch, exchange typed artifacts, converge, and route through evidence-backed decisions.
- Do not treat a sequential checklist, knowledge graph, or GraphRAG request as an agent-orchestration graph.
- Reject unnecessary graph complexity with a `LOOP_SUFFICIENT` verdict.

## Required output contract

The plugin must produce:

1. A `LOOP_SUFFICIENT` or `GRAPH_REQUIRED` qualification with evidence.
2. The user's problem framing, hypothesis, outcome metric, leading metrics, guardrails, trade-offs, and proposed next step.
3. Node contracts covering inputs, outputs, tools, permissions, budget, attempts, ownership, and independent verification.
4. Typed edge contracts covering sequence, fan-out, fan-in, pass, fail, retry, escalation, approval, and rejection.
5. Versioned shared state and deterministic merge/join rules.
6. A Mermaid graph, machine-readable graph contract, and vendor-neutral runnable orchestration skeleton.
7. Bounded retries, cost and concurrency ceilings, idempotency, no silent success, and human approval for consequential actions.
8. An execution-verification checklist that proves topology, handoffs, joins, failure paths, budgets, permissions, and terminal states.

## Known-answer case

Use a synthetic AI feature launch-readiness workflow:

- scope evidence once;
- run product-outcome, model-quality, and safety/privacy review loops independently;
- join only after all required reviews return schema-valid artifacts;
- synthesize evidence without allowing any reviewer to approve its own work;
- stop at a human launch gate;
- never deploy, send, merge, or claim launch success.

## Repository requirements

- Add the plugin manifest and marketplace registration.
- Add a concise skill with progressive references.
- Add fire/no-fire fixtures and known-answer evidence.
- Add deterministic contract validation without a new production dependency.
- Update repository documentation and public integrity checks.
- Run repository integrity, skill lint, the synthetic runner, ContextPort tests, compile checks, and `git diff --check`.
- Work on a feature branch, create logical commits, push, and open a draft PR linked to issue #36. Do not merge.
