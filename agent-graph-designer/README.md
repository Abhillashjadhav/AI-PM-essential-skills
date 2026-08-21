# agent-graph-designer

**One complex AI workflow → a bounded, executable graph of guarded loops.**

`agent-graph-designer` first decides whether a graph is justified. If one loop is enough, it returns `LOOP_SUFFICIENT` and routes the job to [`loop-designer`](../loop-designer/). If coordination is the problem, it returns `GRAPH_REQUIRED` and produces explicit node, edge, state, handoff, join, recovery, and approval contracts.

Seventh plugin in the [AI PM Skills Marketplace](../).

## The problem

Individual agents are easy to describe. Connecting them safely is harder:

- two agents silently assume different handoff formats;
- parallel reviewers finish, but nobody defines what a valid join means;
- retry edges create unbounded cost;
- one agent executes and approves its own work;
- consequential actions happen without an accountable human decision;
- orchestration logic remains buried inside a coordinator prompt.

The plugin makes those coordination decisions inspectable before producing runnable scaffolding.

## Install

```bash
claude plugin marketplace add Abhillashjadhav/AI-PM-essential-skills
claude plugin install agent-graph-designer@ai-pm-skills
```

## Use

```text
Design an agent graph for AI feature launch readiness. Run product-outcome,
model-quality, and safety/privacy reviews independently, then converge at a
human launch decision.
```

It also fires on requests such as:

- "Turn these agents into a graph."
- "Connect these specialist loops with explicit handoffs."
- "Parallelize this multi-agent workflow and define the join."
- "Map the branches and approval gates in this agent workflow."

It does not fire for GraphRAG, knowledge graphs, database schemas, org charts, diagrams without execution semantics, or one recurring task that fits a single guarded loop.

## What it returns

1. **Qualification** — `LOOP_SUFFICIENT` or `GRAPH_REQUIRED`, with structural evidence rather than trend-driven complexity.
2. **Outcome contract** — problem, hypothesis, outcome North Star, leading metrics, guardrails, trade-offs, and the user's proposed next step.
3. **Node contracts** — purpose, typed inputs/outputs, tools, permissions, owner, budget, timeout, attempts, and independent verifier.
4. **Typed edges** — sequence, fan-out, fan-in, pass, fail, retry, escalation, approval, and rejection conditions.
5. **Shared-state and join contract** — versioned fields, allowed writers/readers, merge policy, missing-branch behavior, and conflict handling.
6. **Three artifacts** — Mermaid topology, machine-readable JSON/YAML, and a vendor-neutral orchestration skeleton.
7. **Verification report** — topology, schema, permissions, budget, retry, join, failure, approval, and terminal-state checks.

## Design stance

- **Keep the loop; engineer the graph around it.** A graph node may contain a complete guarded loop. The graph owns coordination between loops.
- **Edges carry product decisions.** Every conditional edge names the evidence and threshold that permits it to fire.
- **Graph complexity must earn its cost.** Parallelism can reduce wall-clock time while increasing tokens, state, and debugging burden.
- **Joins are contracts, not waiting rooms.** No branch may disappear silently, and partial success requires an explicit policy.
- **Human judgment remains accountable.** The graph may prepare evidence and recommendations; it may not silently merge, deploy, send, purchase, publish, or approve a consequential outcome.

## Verified example

[`examples/sample-request.md`](skills/agent-graph-designer/examples/sample-request.md) is transformed into:

- [`sample-graph-package.md`](skills/agent-graph-designer/examples/sample-graph-package.md)
- [`sample-graph-contract.json`](skills/agent-graph-designer/examples/sample-graph-contract.json)
- [`sample-orchestrator.py`](skills/agent-graph-designer/examples/sample-orchestrator.py)

The sample uses synthetic evidence, runs three independent review loops concurrently, joins deterministically, and stops at `AWAITING_HUMAN_APPROVAL`. It never claims to launch anything.

```bash
python3 agent-graph-designer/skills/agent-graph-designer/examples/sample-orchestrator.py
```

## Limitations

- The plugin designs and validates orchestration artifacts; it does not deploy them.
- The sample runner proves local topology and state behavior with synthetic inputs, not live-model quality or production safety.
- Generated tool integrations remain proposals until their real APIs, credentials, permissions, and failure behavior are verified.
- Parallel branches may reduce latency but increase token and operational cost; measure cost per verified outcome.

## Testing

```bash
python3 scripts/check_agent_graph_designer_contract.py
python3 tests/lint_skill.py agent-graph-designer/skills/agent-graph-designer/SKILL.md
python3 agent-graph-designer/skills/agent-graph-designer/examples/sample-orchestrator.py
```

The trigger and known-answer contract lives in [`tests/agent-graph-designer/fixtures.md`](../tests/agent-graph-designer/fixtures.md).

## License

MIT, same as the repository.
