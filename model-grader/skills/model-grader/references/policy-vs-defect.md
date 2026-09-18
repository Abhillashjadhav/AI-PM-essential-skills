# Policy gap or implementation defect

When something behaves unexpectedly, it is exactly one of these. Classifying it wrongly wastes the owner's time or quietly rewrites their decision.

## The test

**Is the expected behaviour recorded and approved?**

- **No** → **policy gap.** Ask the owner. Do not infer the answer from what the code currently does. Code is evidence of what someone built, never of what was decided.
- **Yes, and the implementation does something else** → **implementation defect.** Report it: the approved decision, the observed behaviour, the smallest example showing the difference. Do not reopen the decision.

## The rule that matters

**Never reopen a settled decision to accommodate existing code.**

The pull is strong and it is always available: the code does X, X is defensible, adjusting the contract to X is one line and adjusting the code is twenty. Taking it means the contract now documents the implementation instead of governing it, and the owner's decision has been overwritten by an accident.

If the implementation reveals the decision was genuinely wrong, that is a new decision for the owner, raised explicitly as one — not a quiet edit.

## A third case: invalid fixture

Sometimes neither. The test case itself is malformed — missing evidence, contradictory setup, an expectation that contradicts its own inputs.

Mark it `SETUP_ERROR`. No model should be scored on it, and it is not evidence of anything about the implementation. Fixture defects that get scored as model failures are a quiet and common way to make a system look worse than it is.

## Reporting format

```
CLASSIFICATION: policy gap | implementation defect | invalid fixture
RULE:           <which rule>
DECISION:       <the approved decision, quoted, or "none recorded">
OBSERVED:       <what happens>
SMALLEST CASE:  <minimal input showing it>
ASK:            <the question for the owner — only when policy gap>
```
