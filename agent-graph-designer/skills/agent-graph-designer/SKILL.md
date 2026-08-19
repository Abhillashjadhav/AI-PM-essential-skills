---
name: agent-graph-designer
description: Use this skill when the user asks to design an agent graph, graph a multi-agent workflow, connect agents or loops, parallelize specialist agents, define agent handoffs or joins, map conditional branches and approval gates, or decide whether a workflow needs a loop or graph. It qualifies LOOP_SUFFICIENT versus GRAPH_REQUIRED, then produces outcome, node, typed-edge, shared-state, join, recovery, permission, budget, verification, and human-approval contracts plus Mermaid, machine-readable, and runnable orchestration artifacts. Do NOT use for GraphRAG, knowledge graphs, database/entity graphs, generic diagrams, org charts, one-off delegation, or one recurring task that fits loop-designer.
---

# Agent Graph Designer

Design the graph around guarded loops. Treat nodes as bounded work contracts and edges as evidence-backed product decisions.

## Step 0 — Preserve product judgment

Before choosing a topology, ask only for missing parts of the user's own:

1. problem framing;
2. hypothesis and proposed answer;
3. outcome North Star, leading metrics, guardrails, and key trade-off;
4. proposed next step.

Critique contradictions after the user answers. Never replace these decisions with a fashionable topology.

## Step 1 — Qualify the shape

Read `references/qualification.md`. Return exactly one verdict before drawing anything:

- `LOOP_SUFFICIENT`: one objective, one primary working context, sequential execution, and no meaningful fan-out/fan-in or conditional ownership boundary. Route to `loop-designer` when it is recurring.
- `GRAPH_REQUIRED`: at least one structural graph need and one coordination need are evidenced.

Structural graph needs:

- two or more independent branches can run before a deterministic join;
- evidence can route the workflow to materially different states;
- multiple bounded loops must coordinate without sharing one unbounded context.

Coordination needs:

- distinct owners, tools, permissions, budgets, or verifier independence;
- typed artifact handoffs or shared state are required;
- failure in one branch must block, degrade, compensate, or escalate differently.

Do not invent parallelism. A sequential checklist remains a loop or pipeline.

## Step 2 — Lock the graph outcome contract

Emit:

```text
GRAPH DECISION
Verdict: LOOP_SUFFICIENT | GRAPH_REQUIRED
Problem:
Hypothesis:
Outcome North Star:
Leading metrics:
Guardrails:
Key trade-off:
Proposed next step:
Qualification evidence:
```

The North Star must measure a real outcome, not graph creation, node count, agent count, or usage.

If the verdict is `LOOP_SUFFICIENT`, stop after explaining the smaller design and route to `loop-designer`. Do not emit a decorative graph.

## Step 3 — Define node contracts

For `GRAPH_REQUIRED`, define every node using the required fields in `references/contracts.md`.

Rules:

- Prefer 3–7 nodes initially; justify every additional node.
- A node may be a guarded loop, deterministic worker, independent verifier, join, human gate, or terminal.
- Every working node has typed inputs and outputs, an owner, allowed tools, explicit permissions, time/token budget, timeout, attempt cap, and verifier.
- The executor cannot be its sole verifier.
- Use the smallest capable model policy; do not hard-code current model names without verification.
- A node may write only declared state fields.

## Step 4 — Define typed edges and handoffs

Use only explicit edge types:

- `SEQUENCE`
- `FAN_OUT`
- `FAN_IN`
- `PASS`
- `FAIL`
- `RETRY`
- `ESCALATE`
- `APPROVE`
- `REJECT`

Every edge declares source, target, condition, evidence required, and state mapping. Conditional edges must be deterministic when the evidence is deterministic. If an LLM judges the edge, provide an anchored rubric, disqualifying gates, and uncertainty behavior.

Never hide routing in a coordinator prompt.

## Step 5 — Define shared state and joins

Declare:

- schema version and fields;
- allowed writers and readers per field;
- provenance and freshness metadata;
- idempotency key;
- merge and conflict policy;
- retention or redaction requirements.

For every join, declare:

- required incoming branches;
- `ALL_REQUIRED`, `THRESHOLD`, or `FIRST_VALID` policy;
- schema validation before admission;
- timeout behavior;
- missing, failed, stale, or conflicting branch behavior.

Default to `ALL_REQUIRED`. Never convert a missing branch into success.

## Step 6 — Bound execution and recovery

Always include:

```text
GRAPH GUARDRAILS
1. NODE CAP: maximum nodes per run.
2. CONCURRENCY CAP: maximum branches in flight.
3. TOTAL COST/TIME CEILING: whole-graph budget, not only per-node budgets.
4. RETRY CAP: maximum two repair attempts per failed node; then BLOCKED or ESCALATE.
5. PERMISSION BOUNDARY: explicit read/write/tool allowlists per node.
6. IDEMPOTENCY: repeated invocation cannot duplicate consequential effects.
7. NO SILENT SUCCESS: missing evidence, orphan nodes, dead ends, invalid joins, and exhausted retries are visible terminal failures.
8. HUMAN APPROVAL: merge, deploy, send, publish, purchase, delete, overwrite, or other consequential actions stop at an accountable human gate.
9. PROVENANCE: every branch output records producer, inputs, timestamp, and verification result.
10. KILL SWITCH: operator can stop new dispatch and preserve state for review.
```

## Step 7 — Emit three synchronized artifacts

Produce all three from the same contract:

1. **Mermaid topology** — short node labels, typed conditional edges, visible fan-out/fan-in and terminal states.
2. **Machine-readable contract** — JSON or YAML following `references/contracts.md`.
3. **Vendor-neutral orchestration skeleton** — code that loads the contract, schedules ready nodes, enforces concurrency/retries/joins/budgets, checkpoints state, and stops for human approval.

The skeleton must not claim deployment. Mark unavailable integrations explicitly.

## Step 8 — Verify independently

Run a separate graph-verification pass after generation:

- exactly one declared start state;
- every edge references existing nodes;
- every non-terminal node has an exit;
- every terminal is reachable;
- no orphan node;
- every cycle has a counter and hard exit;
- every fan-out has a declared join or independently justified terminal;
- every join validates required branch artifacts;
- every failure and timeout has a visible destination;
- total and per-node budgets are bounded;
- permissions follow least privilege;
- consequential actions stop for human approval;
- outcome metric and guardrails remain aligned with the problem and hypothesis.

Return `GRAPH_CONTRACT_VALID` only when every check passes. Otherwise return `GRAPH_CONTRACT_BLOCKED` with exact failed checks and required corrections.

## Limitations

- A graph contract and runner skeleton are designs, not a production deployment.
- Static checks cannot prove live-model behavior, external API compatibility, credential safety, latency, or cost.
- More agents can increase correlated errors, token cost, race conditions, and debugging effort.
- Mermaid is a view of the machine-readable contract; it is not the execution source of truth.
- GraphRAG, knowledge graphs, entity resolution, and graph databases require a different skill.
