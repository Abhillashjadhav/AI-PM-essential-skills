# Prompt: Document a loop-versus-graph case study

**Date:** 2026-08-19
**Scope:** Root README documentation for `loop-designer` and `agent-graph-designer`

## Input

Use one AI product case to show where a guarded loop is sufficient and where a coordinated graph becomes necessary.

## Contract

- Keep one shared feature and outcome context across both designs.
- Show the loop as a durable recurring, bounded, sequential repair-and-verification cycle for one unit of work.
- Show the graph as coordination across independently verifiable branches with an explicit join and decision gate.
- State that a graph node may itself be a guarded loop.
- Explain the decision boundary in plain language.
- Include budgets, attempt caps, verification, visible failure, and non-deployment boundaries.
- Do not present two unrelated prompt templates.
- Do not modify either skill's runtime behavior.
