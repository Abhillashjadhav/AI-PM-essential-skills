# Three statuses, never collapsed

Every rule carries three independent statuses. Collapsing them is how a suite comes to look validated when it is not.

## Decision

| Value | Meaning |
|---|---|
| `OPEN` | the owner has not settled this |
| `PROPOSED` | a model or builder suggested an answer; the owner has not confirmed it |
| `APPROVED` | the owner decided it, in their own words |

A `PROPOSED` decision may be written into the contract so the work can continue. It may never be counted as settled, and it must be visibly marked wherever it appears.

## Examples

| Value | Meaning |
|---|---|
| `MISSING` | no example exists |
| `ONE-SIDED` | only the failing example, or only the passing one |
| `BOTH` | an incorrect example that must fail and a legitimate example that must pass, each with its expected reason and the decision behind it |

`ONE-SIDED` is the dangerous middle. A rule with only a failing example has never been checked for what it wrongly rejects — and wrongly rejecting correct work is, in most contracts, the worst error class.

## Verification

| Value | Meaning |
|---|---|
| `NOT RUN` | the example exists on paper |
| `EXECUTED` | it has been run against an implementation and the result recorded |
| `INDEPENDENTLY REVIEWED` | someone who did not build the grader or write the example has adjudicated the expected answer |

**Writing an example is not running it. Running it is not independent review.** A rule may sit at `APPROVED / BOTH / NOT RUN` indefinitely and that is an honest state. What is not honest is calling it tested.

## The combined line

Each rule in the contract shows all three:

```
R7 · child inherits from blocked parent
    decision: APPROVED  examples: BOTH  verification: EXECUTED
```

## Why this exists

In the source project a suite of 52 checks reported 52 of 52 matching expectations. The expectations had been written by the same builder that wrote the grader, and the file's own label said so. The suite was internally consistent and established nothing about correctness. Three separate statuses make that visible on every row instead of buried in a footnote.
