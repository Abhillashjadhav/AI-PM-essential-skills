# Loop or graph qualification

Use the smallest execution shape that preserves the required outcome and controls.

## Decision table

| Question | Loop signal | Graph signal |
|---|---|---|
| Objective | One bounded objective | Several independently verifiable contributions to one outcome |
| Work order | Primarily sequential | Fan-out/fan-in or materially different conditional paths |
| Context | One bounded working context | Separate contexts reduce interference or permission exposure |
| Ownership | One executor/verifier pair | Different owners, agents, tools, permissions, or budgets |
| Handoff | In-memory step result | Typed artifact contract across boundaries |
| Failure | Retry or stop the same loop | Branch-specific block, degrade, compensate, or escalate behavior |
| Completion | One stop condition | Join policy plus graph-level terminal condition |

## Qualification rule

Return `GRAPH_REQUIRED` only when both are true:

1. At least one structural need exists: meaningful fan-out/fan-in, conditional routing, or coordination of multiple bounded loops.
2. At least one coordination need exists: typed handoffs/shared state, separate permission or ownership boundaries, independent verification, or branch-specific failure policy.

Otherwise return `LOOP_SUFFICIENT`.

## Common false positives

- A long checklist is not automatically a graph.
- Three prompts run sequentially are not automatically three agents.
- A Mermaid diagram does not create execution semantics.
- A knowledge graph or GraphRAG index is not an orchestration graph.
- Parallel calls without a deterministic join are uncontrolled fan-out, not a reliable graph.
- Adding reviewers that read identical evidence through identical prompts may increase correlated confidence rather than independent evidence.

## Trade-off check

Challenge graph adoption when expected latency improvement or decision quality does not justify:

- higher token and tool cost;
- shared-state and checkpoint complexity;
- race and merge handling;
- wider permissions;
- more failure modes and observability work.

Measure cost per verified outcome, not cost per node or apparent parallel speed.
