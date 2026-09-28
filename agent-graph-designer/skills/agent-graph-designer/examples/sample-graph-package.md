# Sample graph package

## Graph decision

```text
Verdict: GRAPH_REQUIRED
Problem: launch evidence is fragmented across three independently verifiable domains.
Hypothesis: parallel specialist review loops with typed artifacts and an all-required join reduce decision time without weakening accountability.
Outcome North Star: percentage of evaluated release candidates that receive a correct, evidence-backed launch decision within two working days.
Leading metrics: valid branch-artifact rate; review completion time; join-block rate; repair rate.
Guardrails: no fabricated evidence; synthetic data only; verifier independence; no autonomous deployment.
Key trade-off: lower wall-clock time versus higher orchestration and token cost.
Proposed next step: run one synthetic candidate and stop at a human approval gate.
Qualification evidence: three branches can run independently, require distinct evidence and verification, and must converge before the decision.
```

## Topology

```mermaid
flowchart TD
    A["Freeze candidate"] -->|FAN_OUT| B["Product outcome loop"]
    A -->|FAN_OUT| C["Model quality loop"]
    A -->|FAN_OUT| D["Safety and privacy loop"]
    A -->|FAIL or timeout| H["BLOCKED"]
    B -->|FAN_IN| E["All-required join"]
    C -->|FAN_IN| E
    D -->|FAN_IN| E
    E -->|PASS| F["Human launch gate"]
    E -->|FAIL| H["BLOCKED"]
    F -->|APPROVE| G["Ready for release process"]
    F -->|REJECT| H
```

## Machine-readable contract

The source of truth is [`sample-graph-contract.json`](sample-graph-contract.json). It declares:

- eight bounded nodes;
- typed fan-out, retry, fan-in, failure, approval, and rejection edges;
- versioned state ownership;
- an `ALL_REQUIRED` join;
- maximum two attempts per specialist loop;
- whole-graph cost and concurrency ceilings;
- a human gate before any release process.

## Runnable skeleton

[`sample-orchestrator.py`](sample-orchestrator.py) loads the contract, freezes one synthetic candidate digest, executes the three review loops concurrently, validates their schemas and digests at the join, and stops at `AWAITING_HUMAN_APPROVAL`.

It performs no model, network, deployment, merge, send, publish, purchase, delete, or overwrite action.

## Contract checks and runtime evidence

`GRAPH_CONTRACT_VALID` describes the static contract check. The successful
synthetic run has no external actions taken; neither result proves that every
declared transition has been executed.

| Claim | Evidence / boundary |
|---|---|
| Start, edges, terminal reachability, retry caps, budgets and permissions are declared | Static contract checker |
| Three branches run concurrently and join against required IDs | Synthetic runner |
| Join rejects missing branches, mismatched schema labels/digests or non-PASS status | Runner checks; rejection raises `ValueError` |
| Run stops at `AWAITING_HUMAN_APPROVAL` without an external action | Synthetic runner |
| Independent reviewers, timeout handling, retry execution, cost metering, freshness and structured `BLOCKED` results | Not implemented by this runner |

The topology above describes the intended workflow. It is not a trace of all
transitions being executed. All review branches use the same fixture function;
its `verified_by` labels do not prove independent verification.

## Limitations

- Synthetic branch results demonstrate orchestration shape, not live-model quality.
- The runner does not integrate with product analytics, evaluation platforms, policy engines, or deployment systems.
- A production implementation still requires verified APIs, identity, permissions, durable state, monitoring, and incident controls.
