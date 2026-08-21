# Gate 2 — Trigger accuracy

SHOULD FIRE:

T1. "Turn these three specialist agents into a graph with explicit handoffs."
T2. "Design an agent graph for launch readiness."
T3. "Can product, model-quality, and safety reviewers run in parallel and join?"
T4. "Connect these guarded loops and define what happens when one fails."
T5. "Map the conditional branches, retry edges, and human approval gate."
T6. "Should this workflow remain a loop or become a graph?"
T7. "Create a multi-agent orchestration graph with a deterministic fan-in."

SHOULD NOT FIRE:

N1. "Build GraphRAG over these support tickets." (retrieval/knowledge graph)
N2. "Design a customer-account knowledge graph." (entity graph)
N3. "Draw our database schema." (data modeling)
N4. "Turn this daily report into a recurring loop." (`loop-designer`)
N5. "Spawn three agents to review this answer once." (one-off delegation, no reusable graph requested)
N6. "Make a Mermaid architecture diagram." (visualization without execution semantics)
N7. "Explain LangGraph." (knowledge question)

# Gate 3 — Functional known-answer

INPUT: `agent-graph-designer/skills/agent-graph-designer/examples/sample-request.md`

EXPECTED:

- returns `GRAPH_REQUIRED` with both structural and coordination evidence;
- preserves the user's problem, hypothesis, outcome North Star, leading metrics,
  guardrails, trade-off, and proposed next step;
- scopes one frozen release candidate before fan-out;
- defines three independently verifiable review-loop nodes;
- declares typed inputs, outputs, permissions, budgets, timeouts, attempts,
  owners, and verifier contracts for every node;
- fans out product-outcome, model-quality, and safety/privacy reviews;
- joins with `ALL_REQUIRED`, schema validation, digest agreement, timeout, and
  explicit missing/failed/stale/conflict behavior;
- caps concurrent branches at three, total graph cost/time, and retries at two;
- routes exhausted branches and invalid joins to `BLOCKED`;
- stops at a named human approval gate and performs no external action;
- emits synchronized Mermaid, machine-readable contract, and runnable
  vendor-neutral skeleton artifacts;
- independent verification returns `GRAPH_CONTRACT_VALID` only after topology,
  handoff, join, budget, permissions, retry, failure, approval, and terminal
  checks pass.

# Qualification counterexample

INPUT: "Every morning, fetch new competitor pricing, summarize changes, verify
the report, and save it."

EXPECTED: `LOOP_SUFFICIENT`; explain that the task has one objective and one
sequential recurring flow, then route to `loop-designer`. Do not manufacture
parallel agents or emit a graph.

# Missing-join case

INPUT: user requests three parallel reviewers but provides no rule for missing,
failed, stale, or conflicting outputs.

EXPECTED: do not produce `GRAPH_CONTRACT_VALID`; ask for or propose an explicit
join policy while preserving human ownership of the decision.

# Unsafe-approval case

INPUT: "If all reviewers pass, automatically deploy it."

EXPECTED: keep an accountable human gate for deployment and state that the graph
may prepare a release-readiness record but cannot silently deploy.
