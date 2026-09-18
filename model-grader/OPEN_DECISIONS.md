# Open decisions — model-grader itself

Gaps in **this skill**, found by the build dry-run recorded as Check 5 in `VERIFICATION.md`.

Not to be confused with `skills/model-grader/templates/OPEN_DECISIONS.md`, which is the blank template the skill emits for a product owner's contract. This file is the skill's own ledger, kept beside `VERIFICATION.md` and `BAR.md`.

**None of these are answered here.** The skill's first hard rule is that the interviewer never answers on the owner's behalf, and its buildability test says a dry-run question is recorded as a gap, never filled in by the party holding the document. That applies to the skill's own release or it means nothing.

## How these were produced

A reviewer was given `templates/CONTRACT.md` and `references/question-bank.md` and nothing else — no `SKILL.md`, no `buildability-test.md`, no README, no repository context, and no indication it was being tested. It was told an owner's answers would be filled into that template and handed to it, and asked what it would still need before writing the **first check** of a grader.

That is the dry-run as `buildability-test.md` defines it. It is not independent adjudication — see the gate-3 note in `VERIFICATION.md` Check 4.

**It returned 18 questions. The exit condition is zero.**

## The structural finding

The individual questions cluster into three, and the cluster matters more than the list.

**1 · The contract never says what the grader is called with.** Both documents specify the *graded system's* inputs and outputs, never the grader's. But B2 asks for "the identifier carried from request to response, and the check comparing them", which is uncheckable unless the request is in hand, and A5's citation rules need the source documents. Whether the grader receives `(output)`, `(request, output)` or `(request, sources, output)` is undetermined, and the first check is a different program in each case.

**2 · The contract never says what the grader returns, or over what unit.** Three levels appear — per-item (A2), item-to-batch rollup (C5), and corpus-level shares (A1) — and none is designated as the verdict. Whether the grader also measures A1's targets is unstated.

**3 · Reference-based or rule-based grading is undetermined.** A2's rationale says a grader "compares a returned structure against an expected one", implying per-submission gold data. But the contract has one worked example for the whole feature and no slot for per-submission expected output, while B1 and A5 describe checking against supplied sources instead.

Under the skill's own framing these are Part A shape questions — the class it says must be answered or the grader cannot be written at all.

## The 18

### What the grader receives and returns

1. What does the grader itself receive — `(output)`, `(request, output)`, or `(request, sources, output)`? B2 and A5 both require more than the output.
2. Is there an expected output per submission, or only rules? A2's rationale implies reference-based grading; the contract has no per-submission gold slot.
3. What unit does the verdict cover — item, batch, or corpus — and is the grader responsible for measuring A1's shares?
4. Is the Rule register the complete set of checks, or a restatement of Parts A–C? Parts A–C carry enforceable rules with no ID. If a register row contradicts the Part A cell it came from, which governs?

### Contract states the implementer must act on

5. What does an implementer do with a rule that is `PROPOSED`, `OPEN`, `MISSING` or `NOT DECIDABLE` — build it, skip it, or stop? And may any check be written against a contract still marked DRAFT?
6. What verdict does an item get that is undecidable *yet*? A7 allows a `pending` third outcome; C1 asks only for end states. Must "waiting on a human" be one of them, and what does C7's "Grader records" cell range over?
7. May the grader call a model, or must every check be deterministic code? C7 exists because some rules cannot be decided by code, but neither document says whether the deliverable is code, a model-judged rubric, or a hybrid.

### Verdict mechanics

8. Evaluation order, short-circuiting, and multi-failure verdicts: do checks run to completion or halt at the first blocker, may an item carry several issue codes, and how is one C1 status chosen when two rules of different severity fail?
9. What does C6's "Error" column range over — C2 issue codes, register rule IDs, or informal categories? Does rank change any threshold or status selection at runtime, or is it only for human tradeoff discussion?
10. Do warnings draw from C2's closed code list, their own vocabulary, or free text — which C2's own rationale forbids? Does an item with only warnings end in a publishable status by definition?
11. Where does "whether an unrecognised code is itself a failure" get written? The bank requires it in a complete C2 answer; the contract's C2 table has no cell for it.
12. What status and code does a shape-level parse failure produce — unparseable, wrong type, truncated — and does it short-circuit everything else? B8 maps empty, refusal and partial, but malformed is none of those.

### Rules that collide

13. Declining is asked at A1 and again at B8 and may be answered differently. Which governs, what C1 status is B8's "third thing", and does "not success" mean counted as failure in C5's numerator or excluded — which then collides with the rule against shrinking the denominator?
14. A4 permits unit conversions; B7 may fix units as request context. May an output legitimately arrive converted? Which cell governs a unit-bearing field?
15. A4 supplies an alias map; B3 may class the same field as exact or verbatim. Normalise through the aliases before comparing, or treat any alias as a mismatch? B3's own failure record cuts both ways, so there is no safe default.
16. What does C4's "Where" range over — field, field type, rule ID, or unit? If B3 compares a field as a number and C4 assigns it a tolerance, is the tolerance part of that comparison or a separate check with its own code?

### Examples and scope

17. Are the register's must-fail and must-pass cells executable fixtures or prose to be materialised? Does "must-fail" mean any non-publishable status, or that rule's code and no other? The buildability section treats them as things that were run.
18. B6's second envelope rule — that a private envelope may never reach a publishing or acting consumer — is a property of downstream routing, not of the artifact in front of the grader. What is the grader supposed to read to decide it, or is the rule out of scope?

## What is not recorded here

Whether any of these should be closed by adding questions to the bank, by changing the contract template, or by scoping them out as the implementer's business is a product decision for the repository owner. The dry-run's job is to produce the count and the list. It has.
