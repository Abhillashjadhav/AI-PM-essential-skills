# The buildability test

The exit condition. Run it before emitting anything. A contract that has not passed is a draft.

## Level 1 · Per rule

**Name the case that fails if this rule is deleted.** A concrete input and a concrete wrong output that this rule, and only this rule, rejects.

- Named → `TESTED`. Record the case with the rule.
- Not named → `UNTESTED`. Do not invent the case. Do not drop the rule — a known gap is worth more than a silent one.

*Why:* in the source project, thirty development cases were built and the grader accepted all thirty. The suite contained zero instances of the rule that three contract revisions had been spent defining, and two of the thirty were the same case duplicated. "Accepted all thirty" measured almost nothing. This question catches it on day one.

**Name the legitimate answer this rule might wrongly reject.**

- Named → record it as the rule's predicted false rejection; it becomes a test case.
- Not named → push once. Still nothing → `ONE-SIDED`.

*Why:* closing eight exploits in that project introduced five new ways to reject correct work. Predicting collateral before the fix is the discipline. Finding it afterwards is luck.

## Level 2 · Per contract

1. **Can a system satisfy every rule and still do the wrong thing?** Spend real effort answering yes. Describe the cheapest way. If one exists, that gap is worth more than the rest of the document.
2. **Can a system do the work correctly and fail this contract?** Same effort, other direction. Any answer is a rank-1 problem in most error rankings.
3. **Is every rule decidable** — by deterministic check, or by a named human against named evidence? Anything else is `NOT DECIDABLE`.

## Level 3 · The build dry-run

The real test, and the only one that measures completeness rather than the interviewer's confidence.

**Hand the contract to a reader who has not seen the interview. Ask them to list every question they would need answered before writing the first check.**

- **Zero questions** → the contract is buildable. This is the exit condition.
- **Any question** → each one is a gap. Record it in `OPEN_DECISIONS.md`. Do not answer it yourself.

Reviewer questions about the *domain* ("what is a variant?") are contract gaps too — the contract must be readable by someone who does not know the business.

## Output

A table, one row per rule: rule, testing case, predicted false rejection, decision status, examples status, verification status, buildability status.

Emitted with `UNTESTED` rows, the contract is honest. Emitted without the table, it is not finished.
