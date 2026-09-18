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
| Lines | 410 | **427** |
| Version | `revised-v2.1` | `revised-v2.1` (confirmed — `VERSION` on line 7) |
| Consumed inputs | 47 / 47 | **45 / 45** |
| Issue codes | 39 / 39 | **43 / 43** |

The "410 lines" belonged to `baseline_v2.py`, a different version (`revised-v2`). The audit was run against one file and labelled with another's line count. Nothing was repointed to make the old numbers work: `grader.py` is the file the reference calls `revised-v2.1`, so it is the file audited.

**Coverage still holds, and is better than recorded** — 45 of 45 consumed inputs and 43 of 43 issue codes trace to a question. The conclusion the original audit drew survives; only its arithmetic did not.

**What the re-run additionally shows: the grader exercises 19 of the 26 questions.** Not exercised: **A1, A2, A3, C3, C5, C6, C8**. That is expected for most of them and worth stating rather than hiding:

- **A1, A2** post-date this grader — they were added by the Check 5 slot review.
- **A3** (outcome and targets) and **C5**, **C6**, **C8** are contract-level and process-level decisions that do not appear as keys or codes in grader source. Their absence here is not evidence they are unnecessary; it is evidence this audit cannot see them.
- **C3** (blocker versus warning) *is* implemented — the grader separates `err()` from `warnings` — but the distinction lives in control flow rather than in a key or a code, so the extraction does not catch it. A limitation of the method, not a gap in the bank.

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

The exit test as `buildability-test.md` defines it needs a contract completed through a real interview about a real product, handed to an implementer who did not sit through it. That has still never been run.

**Result: 18 questions, of which two were missing slots.** Two decisions had nowhere to be written at all — what the grader is called with and returns, and whether grading is reference-based or rule-based — and those are genuine slot-coverage failures, now closed by A1, A2 and the per-submission expected-output table. The remaining sixteen are questions a filled contract may well answer; they are logged as gaps rather than treated as defects.

The 18 are recorded in `OPEN_DECISIONS.md` at this plugin's root, unanswered, per hard rule 1 and the dry-run's own instruction that gaps are recorded rather than filled in by the party holding the document. Three clusters carry the weight, and all three are Part A shape questions by the skill's own classification — the class it says must be answered or the grader cannot be written at all:

1. **The contract never states what the grader is called with.** Both documents specify the graded system's I/O, never the grader's. B2's identifier check and A5's citation rules are uncheckable from the output alone.
2. **It never states what the grader returns, or over what unit.** Per-item, batch rollup and corpus-level shares all appear; none is designated the verdict.
3. **Reference-based versus rule-based grading is undetermined.** A2's rationale implies per-submission gold data; the contract has no slot for any.

**What this does and does not establish.** It found two real holes in the template and produced sixteen questions worth checking against a filled contract. It establishes nothing about whether the skill's exit condition is met, because it did not test that. Unresolved decision 3 below expected a second domain to add "one or two" questions to the bank; two were added, so that estimate held.

This reviewer was also spawned by the session that made these changes, so Check 4's gate-3 caveat applies here unchanged: `EXECUTED`, not `INDEPENDENTLY REVIEWED`.

---

## Evidence limitations

- **No independent adjudication.** Checks 1–3 were authored and run by the party that wrote the skill. Check 4 was run by automated reviewers spawned from that same session and shares its blind spots by construction — it raises the floor on defects found, and moves gate 3 not at all. Nobody outside has adjudicated any of it.
- Check 1 is mechanical and reproducible: parse the grader, enumerate its inputs, map them to questions. Checks 2 and 3 are reasoning about a design, and reasoning about a design is not evidence that it works.
- **The exit test has still never been run.** Check 5 tested the template for slot coverage, not a contract for buildability, and the two are different measurements — an earlier revision of this file conflated them. The exit test requires the full interview run on an unseen spec with a real owner, the resulting contract handed to an implementer who did not see the interview, and their questions counted. Until that happens the exit condition remains a claim this skill makes about itself with no measurement behind it, and the version stays `v0.1.0`.
