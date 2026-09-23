# Verification report — model-grader v0.1.0

Three checks, as scoped. **All three are author-run walkthroughs, not independent adjudication.** Check 1 is a mechanical audit against a real artifact and is the only one producing hard evidence. Checks 2 and 3 are design reviews and are labelled as such.

---

## Check 1 · Coverage against a working grader *(mechanical, evidence-backed)*

**Method.** Parsed the catalog grader and extracted every distinct input it consumes from the case, profile, record, candidate, output and measurement objects, plus every issue code it emits. Mapped each against the question bank. A key with no question behind it is a gap: the contract would not have told an implementer it existed.

*Originally recorded as "410 lines, `revised-v2.1`, 47 keys, 39 issue codes". Those numbers were wrong and are corrected below — see **Re-run**.*

**Result: 3 gaps found, all now closed.**

| Grader inputs with no question behind them | Gap | Fix |
|---|---|---|
| `operation`, `record_status`, `known_corrections`, `proposed_corrections` | nothing asked what operations exist, what states a record can be in, or what happens to an item with a change in flight | **A9 · Operations and record states** (A7 at the time) |
| `authority_registry`, `approved`, `supplier_edits`, `family_wide` | nothing asked who resolves a disagreement, what makes a resolution binding, or how far it propagates | **A10 · Authority and resolution** (A8 at the time) |
| (combined) | the bank asked what makes a source *fit to depend on* (B5) but never who decides when two sources disagree | folded into A10 |

After adding the two questions this audit produced — numbered A7 and A8 at the time, A9 and A10 since Part A gained two upstream questions — **47 of 47** consumed inputs and **39 of 39** issue codes trace to at least one question. Both new questions carry a "found by audit, not by design" note in the bank, so a reader knows which questions are evidence-derived rather than reasoned.

**Re-run against `grader.py`, now that the reference ships.** The original numbers could not be reproduced and all three were wrong. `reference/catalog/coverage_audit.py` re-runs the audit; anyone can check it.

| | Originally recorded | Actual, `grader.py` |
|---|---|---|
| Lines | 410 | **427** at the time of the re-run; **507** after the D4/D2 implementation |
| Version | `revised-v2.1` | `revised-v2.1` (confirmed — `VERSION` on line 7) |
| Consumed inputs | 47 / 47 | **45 / 45** |
| Issue codes | 39 / 39 | **43 / 43** at the re-run; **44 / 44** after D4 added `WITHHELD_FIELD_PUBLISHED` |

The "410 lines" belonged to `baseline_v2.py`, a different version (`revised-v2`). The audit was run against one file and labelled with another's line count. Nothing was repointed to make the old numbers work: `grader.py` is the file the reference calls `revised-v2.1`, so it is the file audited.

**Coverage still holds, and is better than recorded** — 45 of 45 consumed inputs and 43 of 43 issue codes trace to a question. The conclusion the original audit drew survives; only its arithmetic did not.

**What the re-run additionally shows: the grader exercises 19 of the 26 questions.** Not exercised: **A1, A2, A3, C3, C5, C6, C8**. That is expected for most of them and worth stating rather than hiding:

- **A1, A2** post-date this grader — they were added by the Check 5 slot review.
- **A3** (outcome and targets) and **C5**, **C6**, **C8** are contract-level and process-level decisions that do not appear as keys or codes in grader source. Their absence here is not evidence they are unnecessary; it is evidence this audit cannot see them.
- **C3** (blocker versus warning) *is* implemented — the grader separates `err()` from `warnings` — but the distinction lives in control flow rather than in a key or a code, so the extraction does not catch it. A limitation of the method, not a gap in the bank.

**Kept current.** `coverage_audit.py` runs against `grader.py` as it is, so these numbers move when the grader does. The D4 implementation added one issue code and the audit caught it as untraced until it was mapped to A5 — which is the check working, not a defect.

**Honest limit on the numbers.** Extraction is mechanical and reproducible. The question each input maps to was decided by hand, in the mapping tables inside `coverage_audit.py`. 45/45 means every input has a question someone argued it belongs to — not that the mapping was independently adjudicated.

---

## Check 2 · A task with subjective quality *(design review, author-run)*

**Scenario.** "The agent drafts a customer apology email. It should sound appropriate."

**Walkthrough.** A1 forces the outcome and both targets before anything else. A2 exposes that the output is a single text field, which makes the shape questions cheap and pushes the weight onto Part C. C7 is where the task either becomes tractable or stops: "appropriate tone" cannot be a deterministic check, so the rule must carry a named reviewer, the evidence they need, and their criteria — or be dropped.

`human-judgment.md` governs three things that would otherwise go wrong here: no invented proxy (a similarity threshold standing in for faithfulness), no attestation that is not bound to the specific item, and a model reviewer only where the owner explicitly chose one, recorded as a model judgment with its own error rate rather than as human approval.

Hard rule 5 is what makes this hold: *never claim a judgment is deterministic when it is not.*

**Result: handled, with a caveat.** The skill routes the subjective rule correctly rather than faking a metric. But most of Part A is thin for a single-text-field task, and the interview will feel long relative to what it yields. **Not yet tested on a real subjective spec.** If it proves tedious in practice, the fix is a documented short path for single-field generative tasks — not loosening C7.

---

## Check 3 · An approved rule with a broken implementation *(design review, author-run)*

**Scenario.** The owner approved "a named blend requires that fibre to exceed 50%." The code compares the label case-sensitively, so `Cotton Blend` at exactly 50% passes. This is a real defect from the source project.

**Walkthrough.** `policy-vs-defect.md` asks one question: is the expected behaviour recorded and approved? It is. Therefore implementation defect, reported with the approved decision quoted, the observed behaviour, and the smallest case showing the difference. The decision is not reopened.

The rule that carries the weight is *never reopen a settled decision to accommodate existing code* — the pull is always available and always cheap, and taking it means the contract documents the implementation instead of governing it.

The file also covers the third case that gets misfiled most often: a malformed fixture, marked `SETUP_ERROR`, scored against nobody. Fixture defects recorded as model failures are a quiet way to make a system look worse than it is.

**Result: handled.** Design review only; the classifier has not been run against a live disputed case.

---

## What changed in this revision

| Change | Source |
|---|---|
| Renamed `contract-interviewer` → `model-grader` | owner |
| Restructured into three parts of eight: Shape / Integrity / Verdict | owner's bar — answers must be sufficient to build from, not merely catch cheats |
| Added Part A entirely (A1–A6 at the time, now A3–A8): outcome and targets, input and output shape, requirement classes, allowed values, evidence and provenance, record relationships | owner's bar |
| Added the two operations/authority questions, now A9 and A10 | **Check 1 audit** |
| Added Part C (C1–C8): statuses, issue codes, blocker vs warning, tolerances, rollup and denominator, error ranking, human judgment, verification plan | owner's bar |
| Four gates per rule, never collapsed | brief §4 |
| `policy-vs-defect.md` | brief §2 |
| Both-sided examples, complete inputs shown, model proposals tagged `UNAPPROVED` | brief §3 |
| Private envelope rules and the publication projection, in B6 | brief §5 |
| `human-judgment.md` | brief §6 |
| Three questions per turn, gaps visible, owner approval before final | brief §7 |
| `process-discipline.md` + `PROCESS_LEDGER.md`: sequence, trail, five freeze conditions | owner — the GitHub-signal requirement |
| Buildability dry-run as the exit condition | this revision |
| Added A1 (the grader itself) and A2 (reference-based or rule-based), and a per-submission expected-output slot | **Check 5 slot review** |

**Correction to the brief as given.** It specified 98% correctness and 0.5% wrong-rejection as targets in the skill. Those are one project's numbers. Hardcoding them would have had the skill supply an owner's decision — the exact failure hard rule 1 exists to prevent. They now appear only in `examples/catalog.md`, explicitly labelled as the shape of an answer rather than a default, and A1 requires the owner to state their own.

---

## Unresolved decisions

1. **Does the interview need a short path for single-field generative tasks?** Check 2 suggests yes; there is no evidence yet. Do not add one until a real interview proves it tedious.
2. **Should A8 permit any self-resolution?** The bank recommends no and asks the owner. Left open deliberately.
3. **Is 24 the right number?** It is what one audit produced. A second audit in a different domain is the way to find out, and the honest expectation is that it adds one or two.

## Check 4 · Automated review sweep *(EXECUTED — not independent adjudication)*

**Method.** Three automated reviewers were run over the plugin before merge: a consistency sweep, a quality-bar audit against the repository's `CLAUDE.md`, and a cold read by a reviewer given only the contract template and the question bank.

**Result: real defects, found and fixed.** Among them: three decisions pre-filled in `CONTRACT.md` in the interviewer's words, violating hard rule 1 in the one artifact the owner signs; a project number surviving in A1's rationale four lines above "Never supply these numbers"; `status-model.md` defining three gates while hard rule 8 forbids stopping at three; `SKILL.md` omitting A1 from its own Part A list and mislabelling C8; and `PROCESS_LEDGER.md` shipping with no section for "Decisions recorded", a trail signal freeze requires.

**Gate status: `EXECUTED`, not `INDEPENDENTLY REVIEWED`.** Every reviewer above was spawned by the same session that made these changes, from the same context, on instructions written by the same party. That is a second sample, not a second party. Under this skill's own gate 3 — "someone who did not build the grader or write the example has adjudicated" — it does not qualify, and claiming otherwise would be the exact collapse gate 3 exists to prevent. The findings are evidence; the reviewing is not independent.

## Check 5 · Template slot coverage *(EXECUTED — not the exit test)*

**Method.** A reviewer was handed `templates/CONTRACT.md` and `references/question-bank.md` and nothing else — no `SKILL.md`, no `buildability-test.md`, no README, no repository context, and no indication it was being tested. It was told an owner's answers would be filled into that template and handed to it, and asked what it would still need before writing the **first check** of a grader.

**This is not the skill's exit test, and the earlier framing of it as one was wrong.** The reviewer was handed a *blank template*, not a contract filled in for a real product. What that measures is slot coverage: whether the template has somewhere to write every decision an implementer needs. It cannot measure buildability, because a blank form is unbuildable by construction — a reader will always have questions about cells nobody has filled.

The exit test as `buildability-test.md` defines it needs a contract completed through a real interview about a real product, handed to an implementer who did not sit through it. **That has now been run once — see Check 8 — and it failed.**

**Result: 18 questions, of which two were missing slots.** Two decisions had nowhere to be written at all — what the grader is called with and returns, and whether grading is reference-based or rule-based — and those are genuine slot-coverage failures, now closed by A1, A2 and the per-submission expected-output table. The remaining sixteen are questions a filled contract may well answer; they are logged as gaps rather than treated as defects.

The 18 are recorded in `OPEN_DECISIONS.md` at this plugin's root, unanswered, per hard rule 1 and the dry-run's own instruction that gaps are recorded rather than filled in by the party holding the document. Three clusters carry the weight, and all three are Part A shape questions by the skill's own classification — the class it says must be answered or the grader cannot be written at all:

1. **The contract never states what the grader is called with.** Both documents specify the graded system's I/O, never the grader's. B2's identifier check and A5's citation rules are uncheckable from the output alone.
2. **It never states what the grader returns, or over what unit.** Per-item, batch rollup and corpus-level shares all appear; none is designated the verdict.
3. **Reference-based versus rule-based grading is undetermined.** A2's rationale implies per-submission gold data; the contract has no slot for any.

**What this does and does not establish.** It found two real holes in the template and produced sixteen questions worth checking against a filled contract. It establishes nothing about whether the skill's exit condition is met, because it did not test that. Unresolved decision 3 below expected a second domain to add "one or two" questions to the bank; two were added, so that estimate held.

This reviewer was also spawned by the session that made these changes, so Check 4's gate-3 caveat applies here unchanged: `EXECUTED`, not `INDEPENDENTLY REVIEWED`.

## Check 6 · External review — three defects reproduced and repaired *(EXECUTED)*

An external review reported three defects. Each was **reproduced before any code
changed**, with a minimal fixture under `reference/catalog/reproductions/`. The
fixtures stay as regression cases: exit 1 while the defect is present, 0 once it
is gone.

```
$ python3 reproductions/run_reproductions.py        # before any repair
Finding 1 - FAMILY_MISMATCH on a withheld optional field   RESULT: DEFECT PRESENT
Finding 2 - warning branch inconsistent with final status  RESULT: DEFECT PRESENT
Finding 3 - MISSING_ACTION on permitted issues             RESULT: DEFECT PRESENT
0 of 3 findings absent

$ python3 reproductions/run_reproductions.py        # after the three repairs
...                                                        RESULT: DEFECT ABSENT  (x3)
3 of 3 findings absent
```

| Finding | Reproduced as | Repair |
|---|---|---|
| 1 · `FAMILY_MISMATCH` on a withheld field | `C1 withholding=[SOURCE_CONFLICT subbrand]` and `C1 blocking=[FAMILY_MISMATCH subbrand]` — the same field withheld and blocked at once | The family check skips a field **this record** is withholding. Verified narrow: a sibling not withholding it still gets `FAMILY_MISMATCH`, and a required shared conflict still blocks |
| 2 · warning branch vs status | `P1 expected_status=BLOCKED`, `payload=['C1']`, warning said *"the rest of this product is published"* | `warning_branch(status, designated)` — three outcomes, status passed in from `grade()`, `branch` emitted on every warning |
| 3 · `MISSING_ACTION` on permitted | silent PASS, with-action PASS, **without-action FAIL** on identical facts | Permitted issues skip the per-issue checks entirely |

**Finding 2 did not match its description, and that is recorded rather than
quietly corrected.** The report named three branches. Before the repair only two
existed, and neither consulted the computed status — both asserted publication
unconditionally. The defect was real; its shape was not as described.

**Two fixtures were wrong on the first attempt and were fixed, not accepted.**
Finding 1's first version asserted on `errors`, where the defect does not appear —
`FAMILY_MISMATCH` is an *expected* issue, so it sets `wanted=BLOCKED` and the
honest candidate trips `FALSE_READY` instead. Finding 2's first version matched the
substring `"published"`, which also matches `"not published"`, so it would have
passed the repaired text and the broken text alike. Both were rewritten to assert
on the structure that actually carries the defect.

**Repairs 1 and 2 were each verified by re-introducing the defect**, because a test
that passes either way is not a test:

```
repair 2, status ignored  ->  mismatches = [('blocked','P1','description',
                                             'eligible_for_publication','blocked','BLOCKED')]
repair 2, repaired        ->  mismatches = none
```

**Suite counts, before and after all three repairs — identical:**

```
approved 3/3 · fault_injection 13/13 · revision 55/55 · replay 30/30 · metadata 31/31
```

No check changed its verdict. The repairs removed penalties that no fixture was
exercising, which is why the counts hold and why the reproductions had to be
written to see the defects at all.

**Withdrawn.** An earlier revision claimed the seller-warning wording could not be
checked without an LLM judge. That was wrong. The warning is a three-way template
choice over a computed status, decided in one function, and asserted directly.

## Check 7 · Adjudication 6 clarified — certification made family-wide *(EXECUTED)*

The owner resolved the mismatch Check 6 disclosed: certification is family-wide.
Reproduced first, implemented second, verified third.

**Part 1 — current behaviour, before any change (v2.2):**

```
$ python3 reproductions/finding4_certification_scope.py
P1 blocking=[('HUMAN_VALIDATION_REQUIRED', 'certification')]  C1 blocking=[]
publication_payload = ['C1']
'certification' in SHARED = False
RESULT: DEFECT PRESENT
```

**After (v2.3):**

```
C1 blocking=[('HUMAN_VALIDATION_REQUIRED', 'certification')]
publication_payload = []
RESULT: DEFECT ABSENT
```

Asserted on the payload itself — not a status field, not a substring. The payload
is what a downstream consumer receives, and the only place "no variant is
published" can be checked honestly.

**Part 4 — preservation checks.** Expected to pass against both versions; that is
what a preservation check is for, and they are reported as such rather than as
before/after evidence.

```
$ python3 reproductions/preservation_certification.py     # identical on v2.2 and v2.3
TEST 2 approval lifts the certification hold
      P1 blocking=[]  C1 blocking=[('SOURCE_CONFLICT', 'price')]
TEST 2 the unrelated blocker still blocks C1, and P1 publishes
      publication_payload=['P1']  verdict=PASS
TEST 3 a family with no certification requirement is unaffected
      blocking={'P1': [], 'C1': []}  publication_payload=['C1', 'P1']  verdict=PASS
RESULT: ALL PRESERVED
```

**Mutation checks — both preservation tests discriminate.** A test that passes
whatever the code does is not a test:

| Mutation | Result |
|---|---|
| approval wrongly clears every other blocking issue | **TEST 2 FAILS** — `the unrelated blocker still blocks C1, and P1 publishes` |
| certification hold applied to a family with no certification requirement | **TEST 3 FAILS** — `a family with no certification requirement is unaffected` |
| neither mutation present | ALL PRESERVED |

Both mutations were reverted; `grep -c MUTATION grader.py` returns 0.

**Three existing checks changed verdict, and the checks were wrong, not the
grader.** `certificate-needs-human-review`,
`document-alone-is-not-human-approval` and
`wrong-document-review-cannot-authorize-claim` each encoded the superseded
per-SKU policy — candidate `P1 BLOCKED, C1 READY`. Under the clarified
adjudication C1 is held too. Updated to hold the family and renamed; the old
expectations are in `revision_checks_historical.json`, which now preserves five
superseded checks.

```
revision 52 / 55   with the three stale checks
revision 55 / 55   after updating them
```

**Part 5 — the reproductions now run inside the standard suite.** Check 6 found
three live defects while the suite reported 55/55 green, because the only thing
that could see them was a runner nobody was obliged to invoke. `run_checks.py`
now executes every reproduction and its exit code covers them. A fixture that
can no longer reach the state it tests (exit 2) is reported as a failure, not
counted as a pass.

Verified the wiring catches a live defect, by running the suite against the v2.2
grader:

```
$ python3 run_checks.py            # v2.2 grader
revision: 52 / 55
Regressions: 4 / 5 reproduced defects still absent
REGRESSION: finding4_certification_scope -> DEFECT PRESENT
exit=1

$ python3 run_checks.py            # v2.3 grader
approved 3/3 · fault_injection 13/13 · revision 55/55
Saved candidate replay 30/30 · Internal metadata 31/31 · Regressions 5/5
exit=0
```

## Check 8 · The exit condition, measured once *(EXECUTED — it failed)*

**Method.** A party that had never seen the grader source, the 102 fixtures, the attack
findings or any execution result was given the written contract, the owner's eight judgments,
the candidate interface and a data-format guide, and asked to write nine evaluation cases with
their expected outcomes. This is the blind-author probe in
`skills/model-grader/references/blind-author-probe.md`, and it is the exit condition Check 5
could not test.

**Result: zero of nine parsed. All nine were rejected before grading.**

```
UCA-01 … UCA-09   SETUP_ERROR: material must be object
CANDIDATE GRADING    denominator 0    agreements 0 / 0
PUBLICATION          denominator 0    agreements 0 / 0
SELLER GUIDANCE      denominator 0    agreements 0 / 0
```

**The cause.** The grader required every evidence value to mirror its field's shape exactly. No
contract clause said so, no prompt said so, and `SEALED_CASES.md` did not say so. The rule
existed only in `grader.py` and in the 102 fixtures the same party had written. Full record:
`reference/catalog/EVALUATION_v2.3.md`.

**What it establishes.** The buildability dry-run passes on slot coverage while missing
undocumented *input* requirements — a contract can have a slot for every decision and still be
unbuildable by someone outside the room. Check 5 measured the template and reported two missing
slots; this measured the contract and found it was not, in the operative sense, a contract.

It also retires a number. The 102 checks that had reported 100% green were never a measurement
of correctness: they passed because one party wrote both halves. The moment an outsider supplied
one half, nothing ran.

**What happened next**, recorded because the repair is part of the evidence and not a footnote:
the format was documented (contract clause 2a, `SEALED_CASES.md`), `source_note` was added so a
source's own words had somewhere to go, the cases were re-encoded with **every expectation
frozen and hash-verified across all three encodings**, and the run was repeated. On the third run
all nine parsed and the grader's verdict was correct on all nine. See Check 9 below and
`reference/catalog/EVALUATION_v2.6.md`.

**The disclosure that goes with that number**, per the probe's own instruction: the format was
documented *after* these cases failed against it. Re-encoding an input to match a newly written
rule is legitimate; changing an expectation would not have been, and none was changed.

This probe was run by a party outside the building session, but its results were interpreted by
the builder. It is `EXECUTED`; it is not independent adjudication of the fixtures, and it does
not close Gate 3.

## Check 9 · Nine blind-authored cases, third encoding *(EXECUTED)*

All nine parsed. Full report: `reference/catalog/EVALUATION_v2.6.md`.

| Measurement | Denominator | Agreements | Excluded |
|---|---|---|---|
| Candidate grading | 9 | 8 / 9 | 0 |
| Publication correctness | 9 | 8 / 9 raw · 9 / 9 after the (f) ruling | 0 |
| Seller guidance | 6 | 6 / 6 | 3 (assert no guidance) |

Incorrect approvals **0**; incorrect rejections **0** after two owner rulings overruled two of
the author's expectations (UCA-02's verdict, UCA-06's `withheld_fields`). Neither case was
edited.

**Stated as the arithmetic supports, and not rounded up:** the grader's verdict was correct on
all nine cases; eight of nine were confirmed by an independent author who never saw the code; on
the ninth the author's expectation was overruled by owner ruling. Nine cases do not establish the
production accuracy targets, which remain unmeasured.

**Each overruled case stops being independent evidence.** Two of the nine are now owner-settled
rather than author-confirmed, and that is why the two numbers are reported separately and never
merged.

## Gate 3 status at `frozen-v2.3` — NOT MET (nine sealed cases run, none scored)

Gate 3 means: **someone other than the builder has checked that the test
expectations are correct.** Not that the tests pass. Not that the policy behind
them was approved. That the expectation encoded in each fixture is the right one,
checked by someone who did not write it.

Measured at `c31cbd9`. Full map in `reference/catalog/ADJUDICATION_MAP.md`.

### Which fixtures have that evidence

| | Count |
|---|---|
| Total fixtures | **102** |
| An owner judgment governs the expected outcome | 42 |
| Expected outcome builder-authored and unreviewed | 60 |
| **Fixtures whose *encoding* an owner signed off** | **3** |

**Three.** `gold/S1.json`, `gold/S2.json`, `gold/S3.json`, each carrying
`label_status: "owner-approved"`.

The 42 and the 3 measure different things, and only the 3 is Gate 3 evidence. A
judgment saying "hold the parent and affected children" settles the policy; it
does not confirm that a particular fixture's records, evidence and expected error
codes express that policy correctly. That transcription was builder work for 99
of the 102, and the fixtures say so in their own labels:

```
gold/S1,S2,S3          "owner-approved"
revision_checks.json   "development expectation derived from owner rules;
                        not independent gold"
gold/faults.json       "builder-derived from approved rules"
```

So: **3 fixtures have Gate 3 evidence. 99 do not.**

### Independent adjudication is in progress elsewhere

Steps 2 and 3 of the validation plan are being carried out by someone who is not
the builder. Their results are **not reflected in this file** and nothing here
anticipates them. When they land, the numbers above change; until then they
stand as written.

The builder cannot supply this evidence for the builder's own fixtures, and has
not attempted to.

### Sealed cases: run three times. Gate 3 is not closed by any run.

Nine cases, UCA-01 to UCA-09, were authored by someone who is not the builder
and who had **no sight of the grader**, and were **owner-approved before
execution** (`owner_approval: "APPROVED"` on all nine). The builder read them
only to run them and edited nothing in any case file. The cases are not
committed to this repository. Full report:
`reference/catalog/EVALUATION_v2.3.md`.

**What the run showed.** All nine were rejected before grading with
`SETUP_ERROR: material must be object`. Nothing was scored:

| Measurement | Denominator | Agreements |
|---|---|---|
| Candidate grading | **0** | 0 / 0 |
| Publication correctness | **0** | 0 / 0 |
| Seller guidance | **0** | 0 / 0 |

**Both error directions:** incorrect approvals **0**, incorrect rejections
**0**. Both zeros mean *not measured*, not *no errors found*. No case reached
the verdict stage, so neither direction was exercised at all.

The `checked` column is empty for all nine rows. A `SETUP_ERROR` returns no
`publication_payload`, so there is nothing to compare on any axis.

The cause is a grader-enforced input format that is written nowhere — recorded
as open decision (e). One implementation defect was confirmed behind it
(`MALFORMED_RECORD` attributed to a well-formed candidate record,
`EVALUATION_v2.3.md` F3), reproduced from a shipped fixture. `frozen-v2.3` was
preserved unchanged; the defect is reported, not repaired.

**Nine cases do not establish the targets.** The primary outcome (**> 98%** of
published SKU records correct) and the guardrail (**< 0.5%** of valid
submissions wrongly rejected) are not measurable from nine cases even had all
nine run. Zero of nine ran. Nothing here moves either number off "unmeasured".

### Second run, against `frozen-v2.4` (2026-09-20)

The nine cases were re-run after rulings 1 and 2 documented the input format.
Full report: `reference/catalog/EVALUATION_v2.4.md`.

**The format was documented after the cases first failed against it.** That is a
real weakness in this evidence. What did *not* change is any expectation:
`expected_verdict`, `expected_publication` and `expected_seller_guidance` are
byte-identical to round one across all nine, as is every candidate. Only four
inputs were reformatted.

| Measurement | Denominator | Agreements |
|---|---|---|
| Candidate grading | **3** | **2 / 3** |
| Publication correctness | **3** | **3 / 3** |
| Seller guidance | **0** | 0 / 0 |

Incorrect approvals **0**; incorrect rejections **1**
(`UCA-02-PARENT-CONFLICT-BLOCK`). Six cases still returned `SETUP_ERROR`:
their `material` evidence values were not converted to the documented object
form. Three reached the grader, where round one had none.

One implementation defect was confirmed in `frozen-v2.4` and reported, not
repaired: `source_ref` at `grader.py:190` still reads
`values[parent][field]` where the parent supplies the field only as a declared
conflict, producing a false `MALFORMED_RECORD` against a well-formed child. The
v2.4 repair narrowed that class; it did not eliminate it.

Three cases measure nothing about the targets.

### Third run, against `frozen-v2.6` (2026-09-20)

Full report: `reference/catalog/EVALUATION_v2.6.md`.

**All nine cases reached the grader. None was excluded by the harness or the
fixture format** — the previous run excluded six, four of which expected SKUs to
publish.

| Measurement | Denominator | Agreements | Excluded |
|---|---|---|---|
| Candidate grading | **9** | **8 / 9** | 0 |
| Publication correctness | **9** | **8 / 9** raw · **9 / 9** after the (f) ruling | 0 |
| Seller guidance | **6** | **6 / 6** | 3 (assert no guidance) |

Incorrect approvals **0**. Incorrect rejections **0** — the runner tallies one
(`UCA-02-PARENT-CONFLICT-BLOCK`) against the case's `expected_verdict`, and that
expectation is overruled by the 2026-09-20 ruling that a record reports every
blocking problem present on it. The case was not edited.

Seller guidance is 6/6. The four disagreements in the first run of these cases
were the harness reading one channel; owner ruling 2026-09-20 settled that it
reads both and names which carried each pair. All eight asserted sku+field pairs
are carried by the grader. Open decision (g) closed.

UCA-06's `withheld_fields: {}` is likewise overruled by owner ruling — the
report names the field that caused the failure. Open decision (f) closed. Neither
case was edited.

**The grader's verdict was correct on all nine cases. Eight of the nine were
confirmed by an independent author who never saw the code; on the ninth the
author's expectation was overruled by owner ruling.**

**No expectation has ever been changed.** Across all three encodings,
`expected_verdict`, `expected_publication`, `expected_seller_guidance`, `reason`
and `candidate` hash identically on all nine cases; only `input` moved. The
input format was documented after the first run rejected every case against it,
which weakens the evidence and is stated in the report rather than softened.

Nine cases measure nothing about the targets.

**Gate 3 remains NOT MET.** The recorded 102-fixture adjudication map has only
3 owner-signed encodings, leaving 99 without that evidence. Its separate count
of 60 wholly builder-authored expectations must not be mistaken for evidence
that the other 42 encodings were independently checked. Running nine cases
against the grader does not adjudicate those 102 expectations.

### Scope, recorded so it is not mistaken for a gap

- **Durable storage is outside scope.** No requirement in this contract asks
  the grader to persist anything between runs.
- **Grouping a child SKU under a parent is a manual supplier action**, performed
  after both SKUs exist as independently published SKUs. It is not a grader
  obligation. Owner scope ruling 2026-09-18; see `DECISIONS.md`, Mismatch A.

### The harness

`reference/catalog/run_sealed_cases.py` and `SEALED_CASES.md` are the harness and
the format, built before the cases existed so neither side saw the other's work.
The harness was proved on six self-authored throwaway inputs that were then
deleted; those carry no validation weight and are labelled as such in
`SEALED_CASES.md`.

An earlier run exposed a harness defect: `compare_guidance()` checked only
`seller_warnings` and missed guidance emitted through `guided_help`. Owner ruling
(g), now settled, authorized checking both channels. The v2.6 report records the
corrected guidance result as 6/6. This records that repair; it does not certify
every other harness path or treat the throwaway cases as independent evidence.

### The accuracy targets remain unmeasured

The primary outcome — **more than 98%** of published SKU records correct — and the
guardrail — **fewer than 0.5%** of valid submissions wrongly rejected — have never
been measured. Nothing currently in this repository can measure either.

**Nine cases are an initial independent check, not proof of either target.**
A clean sealed-case run would say the grader agreed with an independent judgment
on nine cases. It does not establish a rate. Reporting one from nine cases would
be the same error as calling 52/52 self-consistency an accuracy score. The first
v2.3 run scored none of the nine. The later v2.6 report scored all nine and kept
raw verdict agreement (8/9), raw publication agreement (8/9), and guidance (6/6)
separate from the two owner-overruled expectations. Neither result establishes
the production targets.

The runner reports incorrect approvals and incorrect rejections separately and
never combines them, because the two targets have different denominators and a
single figure hides which direction is failing.

### Outside what this grader demonstrates

Two capabilities are not in scope for anything measured here, and no result from
this grader should be read as evidence about either:

- **Durable storage.** The grader is a pure function over one case. It holds no
  state between runs and nothing here exercises persistence, recovery or
  migration.
- **Later parent linking.** The owner's 2026-09-18 scope ruling makes grouping
  a manual supplier action after both SKUs exist. Later-run relinking is outside
  this grader's contract, rather than an outstanding grader requirement.

---

## Evidence limitations

- **Author-run checks do not close Gate 3.** Checks 1–3 were authored and run by the party that wrote the skill. Check 4 used reviewers from the same session and shares that limitation. The separately recorded blind-author and nine-case work in Checks 8–9 does not independently adjudicate the development fixture encodings.
- Check 1 is mechanical and reproducible: parse the grader, enumerate its inputs, map them to questions. Checks 2 and 3 are reasoning about a design, and reasoning about a design is not evidence that it works.
- **The exit condition was measured once and failed.** Check 5 measured template slot coverage. Check 8 records the distinct blind-author probe: all nine cases were rejected before grading because required input details were undocumented. Later documentation and re-encoding allowed the reported v2.6 run; they do not reverse the original failed probe or establish that the probe is sufficient in other domains.
