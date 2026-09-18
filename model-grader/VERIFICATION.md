# Verification report — model-grader v0.1.0

Three checks, as scoped. **All three are author-run walkthroughs, not independent adjudication.** Check 1 is a mechanical audit against a real artifact and is the only one producing hard evidence. Checks 2 and 3 are design reviews and are labelled as such.

---

## Check 1 · Coverage against a working grader *(mechanical, evidence-backed)*

**Method.** Parsed a production T-shirt catalog grader (410 lines, `revised-v2.1`) and extracted every distinct input it consumes from the case, profile and candidate — 47 keys — plus its 39 issue codes. Mapped each against the question bank. A key with no question behind it is a gap: the contract would not have told an implementer it existed.

**Result: 3 gaps found, all now closed.**

| Grader inputs with no question behind them | Gap | Fix |
|---|---|---|
| `operation`, `record_status`, `known_corrections`, `proposed_corrections` | nothing asked what operations exist, what states a record can be in, or what happens to an item with a change in flight | **A7 · Operations and record states** |
| `authority_registry`, `approved`, `supplier_edits`, `family_wide` | nothing asked who resolves a disagreement, what makes a resolution binding, or how far it propagates | **A8 · Authority and resolution** |
| (combined) | the bank asked what makes a source *fit to depend on* (B5) but never who decides when two sources disagree | folded into A8 |

After adding A7 and A8, **47 of 47** consumed inputs and **39 of 39** issue codes trace to at least one question. Both new questions carry a "found by audit, not by design" note in the bank, so a reader knows which questions are evidence-derived rather than reasoned.

**Limitation.** Coverage against one grader in one domain. It shows the bank is sufficient for a task of this shape. It does not establish sufficiency for tasks of other shapes, and a second audit against a different domain would likely find more.

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
| Added Part A entirely (A1–A6): outcome and targets, output shape, requirement classes, allowed values, evidence format, record relationships | owner's bar |
| Added A7 and A8 | **Check 1 audit** |
| Added Part C (C1–C8): statuses, issue codes, blocker vs warning, tolerances, rollup and denominator, error ranking, human judgment, verification plan | owner's bar |
| Four gates per rule, never collapsed | brief §4 |
| `policy-vs-defect.md` | brief §2 |
| Both-sided examples, complete inputs shown, model proposals tagged `UNAPPROVED` | brief §3 |
| Private envelope rules and the publication projection, in B6 | brief §5 |
| `human-judgment.md` | brief §6 |
| Three questions per turn, gaps visible, owner approval before final | brief §7 |
| `process-discipline.md` + `PROCESS_LEDGER.md`: sequence, trail, five freeze conditions | owner — the GitHub-signal requirement |
| Buildability dry-run as the exit condition | this revision |

**Correction to the brief as given.** It specified 98% correctness and 0.5% wrong-rejection as targets in the skill. Those are one project's numbers. Hardcoding them would have had the skill supply an owner's decision — the exact failure hard rule 1 exists to prevent. They now appear only in `examples/catalog.md`, explicitly labelled as the shape of an answer rather than a default, and A1 requires the owner to state their own.

---

## Unresolved decisions

1. **Does the interview need a short path for single-field generative tasks?** Check 2 suggests yes; there is no evidence yet. Do not add one until a real interview proves it tedious.
2. **Should A8 permit any self-resolution?** The bank recommends no and asks the owner. Left open deliberately.
3. **Is 24 the right number?** It is what one audit produced. A second audit in a different domain is the way to find out, and the honest expectation is that it adds one or two.

## Evidence limitations

- No fresh model run. No independent adjudication. Every check above was authored and run by the same party that wrote the skill — the same weakness this skill's own gate 3 exists to make visible.
- Check 1 is mechanical and reproducible: parse the grader, enumerate its inputs, map them to questions. Checks 2 and 3 are reasoning about a design, and reasoning about a design is not evidence that it works.
- **The real test has not been run:** give the skill a spec it has never seen, run the full interview with a real owner, hand the resulting contract to an implementer who did not see the interview, and count the questions they ask. That number is the only measure of whether this works. Until then, `v0.1.0`.
