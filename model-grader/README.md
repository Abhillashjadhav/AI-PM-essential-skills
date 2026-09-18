# model-grader

Asks the questions needed to build a model grader, and nothing else.

Twenty-six questions derived from observed failures, one worked reference implementation you can run, and an exit test that has not yet been run on a filled contract.

It asks. It does not write graders, evals, rubrics or fixtures.

## The problem it solves

A grader needs two things most specs lack.

**Shape** — the fields, types, statuses and codes it must produce. Without these it cannot be written at all.

**Integrity** — the decisions whose absence lets a model satisfy every rule while doing the wrong thing. Without these it can be written, and cheated.

The second half is not hypothetical. In one author-run exercise, a catalog grader built against a carefully written contract caught every deliberately injected fault, then missed every real exploit tried against it. Each miss traced to a decision the contract never made:

**Five wrong answers the grader accepted.** Each is a replayable probe under `reference/catalog/attacks/`.

| Decision never made | What got through | Probe |
|---|---|---|
| what the output may add that the source did not | an invented label contradicting its own numbers | `ASTRA_A1` |
| where casing carries meaning | a rule evaded by capitalising one word | `ASTRA_A3` |
| what must be preserved when unused | supplied metadata silently dropped | `ASTRA_A4` |
| what makes a source fit to depend on | a record inherited from a blocked parent and published | `ASTRA_A5` |
| which request values may never change | currency relabelled, amounts intact | `ASTRA_A2` |

**Two right answers it rejected.** The same missing decisions cut both ways, which is why B3 carries both directions.

| Decision never made | What was wrongly rejected | Probe |
|---|---|---|
| which values compare as numbers, which as text | a correct answer rejected over `10.0` vs `10` | `FR1` |
| what counts as a valid evidence reference | a correct answer rejected over the spelling of an evidence key | `FR2` |

**Two more questions come from reasoning, not from a probe.** B2 (what binds an answer to its request) and B6 (whether the output schema is closed) have no shipped attack behind them. They are in the bank on argument, and the bank says so rather than letting them borrow the others' evidence.

Six of Part B's eight questions are those seven observed failures, generalised. The bank is mostly a failure log turned into an interview, and the two questions that are not are labelled above rather than passed off as evidence-derived.

> **On the numbers in this README.** Every figure here comes from one author-run exercise against a single grader in a single domain, and that grader is not shipped — so nothing here is independently reproducible. `VERIFICATION.md` records the method, the counts and the limitations in full. Read the eight rows above as a failure log that motivated eight questions, not as a benchmark.

## Structure

**26 questions: ten, then eight, then eight.**

- **Part A · Shape (A1–A10)** — the grader itself, reference-based or rule-based, outcome and targets, input and output shape, requirement classes, allowed values, evidence and provenance, record relationships, operations and record states, authority and resolution. A1 and A2 define the grader itself; the rest define the system it grades.
- **Part B · Integrity (B1–B8)** — addition, binding, comparison, preservation, dependency, output shape and the private envelope, fixed context, completion.
- **Part C · Verdict (C1–C8)** — statuses, issue codes, blocker vs warning, tolerances, rollup and denominator, error ranking, human judgment, verification plan.

**Four gates per rule,** never collapsed: Decision, Examples, Verification, Buildability. Writing an example is not running it; running it is not independent review.

**Exit on a buildability test, not an opinion.** Hand the contract to a reader who did not see the interview and count the questions they still need answered. Zero is the exit condition. Anything else is a logged gap.

**A trail before freeze.** Question coverage, the owner's decisions in their own words, revisions, at least one review by someone who is not the interviewer, and the dry-run. A contract with no recorded revisions and no reviews may be correct — nobody can tell, which is the same problem.

## Use

```
/model-grader path/to/spec.md
```

Outputs `CONTRACT.md`, `OPEN_DECISIONS.md` and `PROCESS_LEDGER.md`.

## Test input and expected output

**Input:** a two-line spec — *"The agent reads a supplier price sheet and writes rows into our pricing table. It should get the prices right."*

**Expected output:** states back what the system consumes and produces, classifies it as derived, and asks at most three questions in its first turn, drawn from A1–A3 in order — for example: *when the grader runs, is it handed the supplier's price sheet as well as the rows the agent wrote, or only the rows?*; *is there a known-correct set of rows to compare against, or is correctness decided by checking the rows back against the sheet?*; *what share of published rows must be correct, and what share of valid submissions may be wrongly rejected?* Each question carries one line on why it matters.

**Expected non-output:** no rubric, no eval code, no acceptance criteria written on the owner's behalf, no assumed targets, no filled-in defaults.

**Fails if:** it answers any question itself, supplies a correctness target the owner did not give, emits a contract before the buildability test, reports a rule complete on three gates, or produces grader code.

## Boundary

| Skill | Where it starts and stops |
|---|---|
| `model-grader` | asks the 26 questions; ends at a contract and open decisions |
| `eval-rubric-generator` | turns a settled contract into pass/fail criteria |
| `pm-verifier` | runs a suite against outputs and issues release evidence |

### No skill in this repository can fix the reference grader

Hard rule 6 forbids this skill from writing grader code, fixtures or scoring,
and from repairing an existing grader. That is deliberate, and it has a
consequence worth stating plainly rather than leaving someone to discover:

**`reference/catalog/` ships with known divergences from its own approved
decisions, and nothing in this repository is allowed to repair them.**
`DIVERGENCES.md` records D4 and D2. `eval-rubric-generator` starts from a
settled contract and writes criteria; `pm-verifier` runs suites and issues
release evidence. Neither modifies a grader either.

So if you routed "build a grader" here, the work stops at a contract, a list
of open decisions, and — where a grader already exists — a report saying which
approved decision it diverges from. Repairing that grader is a human's job, or
another tool's. It is not this skill's, and rule 6 means it will refuse rather
than quietly start.

That refusal is the point. A skill that both defines correctness and
implements it is grading its own homework, which is the failure the four-gate
model exists to make visible.

## Files

```
skills/model-grader/
  SKILL.md
  references/
    question-bank.md        the 26 questions, each with why it exists
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
