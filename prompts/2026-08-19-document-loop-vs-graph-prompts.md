# Prompt: Document loop-versus-graph usage

**Date:** 2026-08-19
**Scope:** Root README documentation for `loop-designer` and `agent-graph-designer`

## Input

Update the repository README with one copy-pasteable loop prompt, one copy-pasteable graph prompt, and a plain-language explanation of why each shape is appropriate.

## Contract

- Keep the two plugins distinct: a loop repeats one bounded sequence; a graph coordinates independently bounded branches or loops.
- Use concrete AI product-management examples.
- Include verification, budgets, stop conditions, and non-destructive boundaries in the loop prompt.
- Include typed contracts, permissions, independent verification, retries, failure routing, an explicit join, and an approval boundary in the graph prompt.
- State that a graph may contain guarded loops as nodes.
- Do not modify either skill's runtime behavior.
