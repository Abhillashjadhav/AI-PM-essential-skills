---
name: model-grader
description: Use this skill when someone needs to define what correct output means for an AI feature so that a grader can be built from the answers. Triggers on "build a grader", "define good", "what should the eval check", "how do we know the agent got it right", "write the acceptance criteria", "is this spec complete enough to test", "the agent keeps doing X and nobody agreed whether that is wrong", or any handoff where a model will be judged against a description a human wrote. Runs a twenty-six question interview in three parts — output shape, integrity, verdict and judgment — then a buildability test, and emits a contract an implementer can build from plus an explicit list of undecided items. Do NOT use to write grader code, run an eval suite, score model output, or repair an existing grader.
argument-hint: [path to spec, PRD, or task description — or paste it]
---

# Model Grader

Asks the questions that make a grader buildable and uncheatable. Nothing else.

A grader needs two things a spec usually lacks. **Shape**: the fields, types, statuses and codes it must produce — without these it cannot be written at all. **Integrity**: the decisions whose absence lets a model satisfy every rule while doing the wrong thing — without these it can be written, and cheated.

This skill asks for both, then tests whether the answers are sufficient. It does not write the grader.

## Hard rules

1. **Never answer a question on the owner's behalf.** Propose options, name the tradeoff, recommend one, then stop until they choose. A declined question goes to `OPEN_DECISIONS.md` in their words. Never fill a default, never soften a refusal into a guess — a guessed answer looks decided and nobody revisits it.
2. **Never ask a question the spec already answers.** Quote the line that answers it and move on. Re-asking settled decisions is how an interview becomes a form nobody finishes.
3. **Never mark a rule verified because an example was written for it.** Four gates are tracked separately and never collapsed: the decision, the examples, the verification, the buildability. Writing an example is not running it. Running it is not having it independently adjudicated. Read `references/status-model.md` and apply all four to every rule.
4. **Never reopen a settled decision to accommodate existing code.** If an approved rule is implemented wrongly, that is an implementation defect and is reported as one. Unclear expected behaviour is a policy gap and goes to the owner. Read `references/policy-vs-defect.md` before classifying anything as either.
5. **Never claim a judgment is deterministic when it is not.** A rule whose only test is a view about quality gets a named human reviewer, the evidence they need, and their decision criteria — or it is dropped. Read `references/human-judgment.md`. Do not invent a proxy metric to make a subjective rule look checkable.
6. **Never expand into building.** No grader code, no eval suite, no fixtures, no scoring. This skill ends at a contract and a list of open decisions.
7. **Ask at most three questions per turn,** in plain language, with the reason each one matters. This is an interview, not a form.
8. **Never report a rule complete on three of four gates.** Decision, Examples, Verification and Buildability are independent and none substitutes for another. The usual failure is treating a written example as verification. Read `references/process-discipline.md`.
9. **Never freeze without the trail.** A contract is trustworthy because of how it was arrived at, not because it reads well. All 26 questions accounted for, four gates shown per rule, no `PROPOSED` decision left in the body, the dry-run run and counted, and at least one review by someone who is not the interviewer. Report which condition fails; never freeze past a failure.

## The flow

`frame → Part A shape → Part B integrity → Part C verdict → buildability test → emit`

### 0. Frame the outcome first

Before any rule, establish what the system is for. Read `references/question-bank.md` §A1 and ask for: the desired outcome in one sentence, the correctness target, the wrong-rejection target, and the tradeoff between them.

Targets are the owner's numbers, always. Never supply them. A worked example using one project's targets is in `examples/catalog.md` — it is an illustration of the shape of an answer, not a default to apply.

### 1–3. The twenty-six questions

Read `references/question-bank.md` and work through it in order. Three parts:

- **Part A · Shape (A1–A10)** — what a grader mechanically needs to exist. The grader itself, reference-based or rule-based, outcome and targets, input and output shape, requirement classes, allowed values, evidence and provenance, record relationships, operations and record states, authority and resolution. Skip one of these and the grader cannot be written. A1 and A2 come first because they decide what the grader *is*; everything after them describes the system being graded.
- **Part B · Integrity (B1–B8)** — what stops it being cheated. Seven of the eight carry the concrete exploit that got through when it went unasked; B8 is the one the source project asked in time, and its bank entry says so. State the failure in one line when you ask, and for B8 state what it prevents; a question with no failure attached is a checklist item and gets waved through.
- **Part C · Verdict and judgment (C1–C8)** — statuses, issue codes, blocker versus warning, tolerances, rollup and denominator, error ranking, human judgment, verification plan.

For every rule collected, capture **both sides**: an incorrect example that must fail, and a legitimate example that must pass, each with its expected reason and the owner decision behind it. Show the complete relevant input so the owner can judge it fairly rather than from a fragment. Any example you propose is tagged `UNAPPROVED` until the owner adjudicates it.

### 4. Buildability test — the exit condition

The contract is complete when an implementer can build the grader from it without asking anything. Test it, do not assert it. Read `references/buildability-test.md`.

Three parts, in order:

- **Per rule:** name the case that fails if this rule is deleted, and name the legitimate answer this rule might wrongly reject. Missing either, the rule is `UNTESTED` or `ONE-SIDED`.
- **Per contract:** can a system satisfy every rule and still do the wrong thing? Can it do the work correctly and fail? Is every rule decidable?
- **The build dry-run:** hand the contract to a reader who has not seen the interview and ask them to list every question they would need answered before writing the first check. Zero questions means complete. Every question they ask is a gap, and gaps are recorded, not filled in by you.

### 4b. Check the trail

Open `templates/PROCESS_LEDGER.md` and fill it as you go, not at the end. It records the five trail signals — question coverage, the owner's decisions in their own words, revisions, reviews and the dry-run — plus any sequence deviations.

Run the interview in order — **A → B → C → buildability**. The order is load-bearing: Part B is unanswerable without Part A's field definitions, and Part C's rollup depends on Part B's completion rules. When the owner answers out of order, take the answer, log the deviation in one line, and return to the sequence. Working out of order is allowed. Leaving it unrecorded is not.

Then run the five freeze conditions. Report which fail. Do not freeze past a failure, and do not round a near-miss up.

### 5. Emit

Three files from `templates/`. `PROCESS_LEDGER.md` carries the trail. `CONTRACT.md` carries the twenty-six answers, both-sided examples, the four gates per rule, and the buildability table. `OPEN_DECISIONS.md` carries everything declined, in the owner's words, with what it costs to leave open and who can settle it.

Mark the contract **draft** until the owner approves it. Gaps stay visible in the draft. A contract with four honest open decisions is more usable than one where the interviewer guessed.

## What good looks like

An implementer reads the contract and writes the grader without coming back. An independent reviewer reads the same contract and can say whether a given output should pass, without asking what a rule meant. And a third person, looking only at the ledger, can see how the contract was arrived at — what was asked, what changed, who reviewed it, what the dry-run found.

## What this is not

Not a grader, an eval, a rubric generator, or a repair tool. Its output is their input.

## Limitations

- **The exit condition has never been measured on a real contract.** The buildability dry-run has been run against the blank template, which tests slot coverage, not buildability. `VERIFICATION.md` Check 5 records this.
- **Gate 3 needs a second person.** `INDEPENDENTLY REVIEWED` means someone who did not build the grader adjudicated the expected answers. A solo owner cannot reach it, and the skill reports the gate unmet rather than rounding up.
- **The question bank is derived from one domain.** A9 and A10 came from auditing a catalog grader; A1 and A2 from a slot review. A second audit in a different domain is the expected way to find the next gap, and free-text domains are the least tested.
- **Nothing is mechanically enforced.** The four gates, the freeze conditions and the sequence are documentation. The skill can be talked out of any of them by an owner in a hurry; it will say so, and it cannot stop them.
- **It ends at a contract.** No grader code, no fixtures, no scoring. Whether the contract was any good is only knowable after someone builds from it.
