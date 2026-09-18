# Process discipline

A contract is not trustworthy because it reads well. It is trustworthy because there is a record of how it was arrived at. This file defines that record and the conditions for freezing.

The model is the one every engineering team already uses to judge whether work happened: issues raised, changes proposed, reviews performed, revisions committed. A repository with one enormous commit and no reviews is not trusted no matter how good the code looks. A contract assembled in one pass with no recorded questions is the same thing.

---

## The four gates

Every rule must clear four gates. They are independent and none substitutes for another. A rule short of any gate is not finished, and the contract reports it that way rather than rounding up.

| Gate | Question it answers | Values |
|---|---|---|
| **1 · Decision** | did the owner settle this, in their words? | `OPEN` / `PROPOSED` / `APPROVED` |
| **2 · Examples** | do both sides exist — what must fail and what must pass? | `MISSING` / `ONE-SIDED` / `BOTH` |
| **3 · Verification** | was anything actually run, and by whom? | `NOT RUN` / `EXECUTED` / `INDEPENDENTLY REVIEWED` |
| **4 · Buildability** | can an implementer build this rule without asking? | `TESTED` / `UNTESTED` / `ONE-SIDED` / `NOT DECIDABLE` |

**Never report a rule as complete on three gates.** The common failure is gate 2 standing in for gate 3 — an example is written, and the rule is called tested. It is not. Writing is not running.

---

## Sequence

The interview runs **A → B → C → buildability**. The order is not decoration:

- Part B questions are unanswerable without Part A. "What may the output add?" means nothing until the output's fields are defined.
- Part C rollup and denominators depend on Part B's completion rules.
- The buildability test needs all three parts present or it tests nothing.

**Out-of-sequence is allowed and must be logged.** An owner who wants to settle the error ranking first, or who answers B3 while discussing A4, is working the way people actually work. Take the answer. Then record the deviation in the process ledger with one line on why, and return to the sequence.

What is not allowed is arriving at the buildability test with unanswered questions in an earlier part and proceeding anyway. Unanswered is fine; unrecorded is not.

---

## The trail that must exist before freeze

Five things, each recorded with a timestamp, in the process ledger.

| Signal | What it is | Minimum before freeze |
|---|---|---|
| **Questions raised** | every one of the 24 asked, or quoted from the spec as already answered | all 24 accounted for |
| **Decisions recorded** | the owner's answer in their own words, per question | one per question, or an entry in `OPEN_DECISIONS.md` |
| **Revisions** | each contract version with what changed and why | at least one revision after the first draft |
| **Review** | someone other than the interviewer read the contract and raised findings | at least one review, findings recorded |
| **Dry-run** | a reader who did not see the interview lists the questions they would still need | recorded, with the count |

**A contract with zero recorded revisions and zero reviews has not been through a process.** It may still be correct. Nobody can tell, which is the same problem.

---

## Freeze conditions

All five must hold. Report which fail; never freeze past a failure.

1. All 24 questions answered, quoted as pre-answered, or listed open.
2. Every rule shows all four gates explicitly. No blanks, no implied values.
3. No rule sits at `PROPOSED` in the contract body. Proposed decisions either become `APPROVED` or move to `OPEN_DECISIONS.md`.
4. The build dry-run has been run and its question count recorded. Zero is the exit condition; any other number means the questions are logged as gaps.
5. At least one review by someone other than the interviewer, with findings recorded and each one resolved or explicitly deferred.

A frozen contract carries a version number and a hash of its own content. Changes after freeze create a new version with a recorded reason — never a silent edit.

---

## What this prevents

In the source project, a 52-check suite reported 52 of 52 matching. Every expectation had been written by the same builder that wrote the grader. No independent adjudication, no external review, no dry-run. The number was real and meant nothing.

Gates 3 and 4, and the review and dry-run signals, exist so that a number like that arrives with its provenance attached and cannot be read as more than it is.
