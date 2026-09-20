# The three-hand protocol

A grader's pass rate is only evidence if the hand that wrote the tests is not the hand that
wrote the system. Three roles, none of which may see another's working material.

| Role | Does | Must not |
|---|---|---|
| **Owner** | Decides what correct means. Rules every policy question. Approves every expected outcome before it is run. | Write the grader. Write the cases. |
| **Builder** | Writes the grader, the harness, the fixtures. Repairs what a run exposes. | Decide a policy question. Author the evaluation cases. Adjudicate its own expectations. |
| **Blind author** | Writes evaluation cases from the written contract alone. | See the code, the existing fixtures, attack findings, or any execution result. |

## The escalation rule

Every disagreement between the grader and a case goes to the owner as a ruling. It is never
settled by the builder ("the case is invalid") or by the author ("the grader must be wrong").
Classify, then escalate:

- **IMPLEMENTATION DEFECT** — the grader contradicts a settled clause. Name the clause.
- **POLICY AMBIGUITY** — the contract does not settle it. State the owner's question.
- **INVALID CASE** — the case is malformed or its expectation does not follow. Say precisely why.

Never default to INVALID CASE when the grader disagrees with the case. That is the builder
marking its own work by another route.

## Why, with evidence

In the source project every defect was found at a seam between two parties who could not see
each other's work, and none by the party doing the work:

- 102 checks reported 100% green while four defects were live. Same party wrote grader and tests.
- A repair that passed code review and a fully green suite still left half the bug in place.
- The harness measuring all of it reported "1 of 1, zero errors" while suppressing a real wrong
  rejection of its own.
- A final review found `hits[0]` — "take the first one found" — inside the harness measuring two
  owner rulings that had just condemned taking the first one found.

Five separate times a green number concealed a live defect. Each was caught by a different hand.

## Owner adjudication costs independence — count it

When the owner overrules the blind author, that case stops being independent evidence. Report
both numbers and never merge them:

> The grader's verdict was correct on all nine cases. Eight of nine were confirmed by an
> independent author who never saw the code; on the ninth the author's expectation was
> overruled by owner ruling.

## Practical setup

The blind author works in a fresh session with no repository access. It receives the contract,
the owner's decisions, the candidate interface and a data-format guide — nothing else. If it has
seen grader source, execution results or existing fixtures, it is no longer blind and must say so
and stop.

Do not tell the blind author how its earlier cases performed. That is a channel back from the
implementation into the expectations.
