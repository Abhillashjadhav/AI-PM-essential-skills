# Four gates, never collapsed

Every rule carries four independent gates. Collapsing them is how a suite comes to look validated when it is not. The authoritative table is in `process-discipline.md` §The four gates; this file explains what each value means and why the distinctions hold.

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

## Buildability

| Value | Meaning |
|---|---|
| `UNSPECIFIED` | nobody has named the case that fails if this rule is deleted |
| `ONE-SIDED` | the failing case is named but the legitimate answer this rule might wrongly reject is not |
| `SPECIFIED` | both sides named, and an implementer could write the check from this rule alone. Says nothing about whether it was run — that is Verification |
| `NOT DECIDABLE` | the rule cannot be settled from the contract as written; it is a gap, recorded not filled |

**A rule an implementer cannot build from is not finished, however settled its decision.** This gate is answered by the buildability test, not by the interviewer's confidence. See `buildability-test.md`.

## The combined line

Each rule in the contract shows all four:

```
R7 · child inherits from blocked parent
    decision: APPROVED  examples: BOTH  verification: EXECUTED  buildability: SPECIFIED
```

## Why this exists

In the source project a suite of 52 checks reported 52 of 52 matching expectations. The expectations had been written by the same builder that wrote the grader, and the file's own label said so. The suite was internally consistent and established nothing about correctness. Four separate gates make that visible on every row instead of buried in a footnote.
