# Known-answer fixture

## Input

```text
An AI feature is a product system, not just a model. A model demo can pass while the full product workflow still fails.

Our evaluation must cover inputs, tool calls, failure handling, latency, cost, and whether the user reaches the intended outcome.
```

## Required findings

- binary contrast
- repetitive use of “product system” and “product workflow”
- longer setup than the product judgment requires

## Required preserved facts

- a model demo can pass while the product workflow fails
- inputs
- tool calls
- failure handling
- latency
- cost
- whether the user reaches the intended outcome

## Acceptable output

```text
An AI feature can pass a model demo and still fail across the product workflow.

Evaluate the inputs, tool calls, failure handling, latency, cost, and whether the user reaches the intended outcome.
```

The exact wording may vary. Every mechanism in the output must come from the input, every required fact must remain, and no metric, result, or evaluation dimension may be invented.
