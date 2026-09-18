# model-grader

Asks the complete set of questions needed to build a model grader, and nothing else.

It asks. It does not write graders, evals, rubrics or fixtures.

## The problem it solves

A grader needs two things most specs lack.

**Shape** — the fields, types, statuses and codes it must produce. Without these it cannot be written at all.

**Integrity** — the decisions whose absence lets a model satisfy every rule while doing the wrong thing. Without these it can be written, and cheated.

The second half is not hypothetical. In one author-run exercise, a catalog grader built against a carefully written contract caught every deliberately injected fault, then missed every real exploit tried against it. Each miss traced to a decision the contract never made:

| Decision never made | What got through |
|---|---|
| what the output may add that the source did not | an invented label contradicting its own numbers |
| what binds an answer to its request | one answer passed as the answer to four different cases |
| which values compare as numbers, which as text | a correct answer rejected over `10.0` vs `10` |
| where casing carries meaning | a rule evaded by capitalising one word |
| what must be preserved when unused | supplied metadata silently dropped |
| what makes a source fit to depend on | a record inherited from a blocked parent and published |
| whether the output schema is closed | claims parked outside the expected structure |
| which request values may never change | currency relabelled, amounts intact |

Part B of the question bank is those eight failures, generalised. The bank is a failure log turned into an interview, not a checklist someone invented.

> **On the numbers in this README.** Every figure here comes from one author-run exercise against a single grader in a single domain, and that grader is not shipped — so nothing here is independently reproducible. `VERIFICATION.md` records the method, the counts and the limitations in full. Read the eight rows above as a failure log that motivated eight questions, not as a benchmark.

## Structure

**24 questions, three parts of eight.**

- **Part A · Shape (A1–A8)** — outcome and targets, input/output shape, requirement classes, allowed values and units, evidence format, record relationships, operations and record states, authority and resolution.
- **Part B · Integrity (B1–B8)** — addition, binding, comparison, preservation, dependency, output shape and the private envelope, fixed context, completion.
- **Part C · Verdict (C1–C8)** — statuses, issue codes, blocker vs warning, tolerances, rollup and denominator, error ranking, human judgment, verification plan.

**Four gates per rule,** never collapsed: Decision, Examples, Verification, Buildability. Writing an example is not running it; running it is not independent review.

**Exit on a buildability test, not an opinion.** Hand the contract to a reader who did not see the interview and count the questions they still need answered. Zero is the exit condition. Anything else is a logged gap.

**A trail before freeze.** Question coverage, sequence deviations, revisions, at least one review by someone who is not the interviewer, and the dry-run. A contract with no recorded revisions and no reviews may be correct — nobody can tell, which is the same problem.

## Use

```
/model-grader path/to/spec.md
```

Outputs `CONTRACT.md`, `OPEN_DECISIONS.md` and `PROCESS_LEDGER.md`.

## Test input and expected output

**Input:** a two-line spec — *"The agent reads a supplier price sheet and writes rows into our pricing table. It should get the prices right."*

**Expected output:** states back what the system consumes and produces, classifies it as derived, and asks at most three questions in its first turn, drawn from A1 and A2 — for example: *what share of published rows must be correct, and what share of valid submissions may be wrongly rejected?*; *field by field, what does a row contain?*; *does correctly refusing to write a row count as success?* Each question carries one line on why it matters.

**Expected non-output:** no rubric, no eval code, no acceptance criteria written on the owner's behalf, no assumed targets, no filled-in defaults.

**Fails if:** it answers any question itself, supplies a correctness target the owner did not give, emits a contract before the buildability test, reports a rule complete on three gates, or produces grader code.

## Boundary

| Skill | Where it starts and stops |
|---|---|
| `model-grader` | asks the 24 questions; ends at a contract and open decisions |
| `eval-rubric-generator` | turns a settled contract into pass/fail criteria |
| `pm-verifier` | runs a suite against outputs and issues release evidence |

## Files

```
skills/model-grader/
  SKILL.md
  references/
    question-bank.md        the 24 questions, each with why it exists
    status-model.md         the four gates and why they never collapse
    policy-vs-defect.md     policy gap vs implementation defect vs invalid fixture
    human-judgment.md       when a rule cannot be code
    buildability-test.md    the exit condition
    process-discipline.md   sequence, the trail, freeze conditions
  templates/
    CONTRACT.md
    OPEN_DECISIONS.md
    PROCESS_LEDGER.md
  examples/
    catalog.md              one project's answers, as shape not default
```
