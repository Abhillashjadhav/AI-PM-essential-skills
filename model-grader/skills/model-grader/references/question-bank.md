# The twenty-four questions

Three parts. **Part A** makes a grader possible to write. **Part B** makes it hard to cheat. **Part C** makes its verdicts mean something. Skip Part A and there is nothing to build. Skip Part B and what you build gets walked around. Skip Part C and it produces numbers nobody can interpret.

Ask at most three per turn. Quote the spec where it already answers one.

Eight per part. A7 and A8 were added after an audit of a working grader found it consumed inputs no question asked for — the note on each says so.

---

# Part A · Shape — what a grader mechanically needs

Without these, the first line of a check cannot be written.

## A1 · Outcome and targets

**Ask:** In one sentence, what is this system for? What share of its published output must be correct? What share of valid work may be wrongly rejected? When those two pull against each other, which wins?

**Why:** these numbers set how strict every later rule should be. A grader tuned to a tight wrong-rejection ceiling is a different grader from one tuned to never let a bad record through.

**Complete answer names:** the outcome; a correctness target; a wrong-rejection target; the tradeoff direction; and explicitly, whether correctly refusing to act counts toward success. It usually should not — a system that correctly declines everything has completed no work.

**Never supply these numbers.** They are the owner's.

## A2 · Input and output shape

**Ask:** What exactly does the system receive, and what exactly must it return? Field by field, with types and nesting. What is per-item and what is per-submission?

**Why:** a grader compares a returned structure against an expected one. Undefined structure, no comparison.

**Complete answer names:** every field, its type, whether it sits on the item or the submission, and one full worked example of a correct output.

## A3 · Requirement class per field

**Ask:** For each field — always required, required only under some condition, or optional? For conditional fields, required when exactly?

**Why:** "required" is contextual. A field mandatory for a new record may be irrelevant for an update. A grader that treats one list as universal will block correct work.

**Complete answer names:** the class per field; the trigger condition for every conditional one; and what a missing optional field does (it should do nothing).

## A4 · Allowed values, units and formats

**Ask:** Which fields draw from a fixed list? Is there an alias or normalisation map? What units apply, and what conversions are permitted? What happens to a value that is not in the list — block, normalise, or pass through?

**Why:** without this the grader cannot tell a typo from a legitimate variant, and the unmapped-value path is where most silent corruption enters.

**Complete answer names:** the enums; the alias map; the unit rules with exact conversion factors; and the unmapped-value decision.

## A5 · Evidence and provenance

**Ask:** Must every output value cite where it came from? In what format? If two supplied sources assert the same value, may either be cited? What makes a citation wrong rather than merely different?

**Why:** a value can be real and still be attached to the wrong thing. Provenance is the only thing that catches it.

**Complete answer names:** whether citation is required and for which fields; the reference format; whether alternate equivalent references are acceptable; and what a citation must prove — that the value exists, or that it belongs to this item.

## A6 · Record relationships

**Ask:** Are items independent, or linked — parent and child, a sequence, a batch, a thread? What establishes a link? Which values are shared across a link and which belong to the item alone?

**Why:** every inheritance and propagation rule depends on this, and those are where the subtle failures live.

**Complete answer names:** the link types; what proves a link; the shared set; the item-only set; and whether links may be created by the system or only observed.


## A7 · Operations and record states

**Ask:** What distinct operations does this system perform — create, update, attach to something existing, correct, withdraw? Do the requirements differ per operation? And what states can an incoming item be in — new, existing, proposed, pending a correction, withdrawn — and does its state change what is required of it or what may be done with it?

**Why:** "required" is meaningless without the operation. A field mandatory when creating a record is often irrelevant when attaching to one that already exists, and demanding it blocks correct work. Separately, an item with a change in flight is neither settled nor absent, and a grader with no third state will force it into one of the two wrong ones.

**Complete answer names:** the operation list; per-operation requirement differences; the record states; and what happens to an item whose state is `pending` — does it block, pass with an annotation, or wait.

**Found by audit, not by design.** A working grader consumed `operation`, `record_status`, `known_corrections` and `proposed_corrections`. The original bank asked for none of them and the contract would have been unbuildable.

## A8 · Authority and resolution

**Ask:** When two supplied sources disagree, who or what decides? What makes a resolution binding — a designated authoritative source, a named person's approval, a recorded supplier confirmation? May the system ever resolve a disagreement itself? And when a resolution arrives, what does it change — this item only, or everything in its family?

**Why:** a conflict with no resolution path has only two outcomes, and both are bad: it blocks forever, or something quietly picks a side. Naming the authority converts an unresolvable state into a routed one.

**Complete answer names:** the resolution authority per conflict type; what evidence makes a resolution binding; whether the system may self-resolve (usually no); the scope a resolution applies to; and what is retained of the original disagreement after it is settled.

**Found by audit.** The same grader consumed `authority_registry`, `approved`, `supplier_edits` and `family_wide`. None of it was asked for.

---

# Part B · Integrity — what stops it being cheated

Each family exists because its absence let something wrong pass a real grader. State the failure when you ask. Source: a catalog grader that caught 12 of 12 injected faults and missed 8 of 8 real exploits.

## B1 · Addition — what may appear that the source did not

**Ask:** Which values must trace to something supplied, and which may be derived or composed? How does a reader tell a derived value from a supplied one?

**Failure:** a record invented a product label contradicting its own supplied numbers and passed — the check compared the numbers and never read the label.

**Complete answer names:** the must-trace set; permitted derivations and their inputs; how derived values are marked; what happens when a derivation's inputs are incomplete.

## B2 · Binding — what ties an answer to its request

**Ask:** If the system returned a well-formed answer to a *different* request, what in your checks would notice?

**Failure:** one saved answer passed as the correct answer to four different cases. Sixteen wrong-case pairs passed. Nothing bound answer to question.

**Complete answer names:** the identifier carried from request to response, and the check comparing them.

**Weight:** under optimisation pressure this is the cheapest strategy available — one canned answer for a family of prompts, reward collected every time. The highest-value question in the bank.

## B3 · Comparison — what counts as the same value

**Ask:** Field by field: compared as a number, as exact text, or as normalised text? Is `10` the same as `10.0`? Is `Cotton Blend` the same as `cotton blend`? Where does casing carry meaning?

**Failure:** twice, in opposite directions. A correct answer rejected because `"10.0"` was string-compared against `"10"`. And a rule evaded by capitalising one word, because that check alone was case-sensitive.

**Complete answer names:** per field or per type — numeric, exact, or normalised — and which fields are reproduced verbatim.

## B4 · Preservation — what must survive unused

**Ask:** What supplied information must appear in the output even if nothing downstream consumes it? What may be dropped?

**Failure:** a record silently dropped supplied supplier metadata and passed, because the comparison only looked at fields it knew about.

**Complete answer names:** the preserved set explicitly, including what the current consumer ignores; and whether preservation means unchanged or merely present.

## B5 · Dependency — what makes a source fit to depend on

**Ask:** When one item depends on another, what must be true of the thing it depends on? What happens to the dependent when its source is disputed, pending, or itself blocked?

**Failure:** a child inherited a value from a parent blocked on an unresolved conflict, and was published as ready. The dependency was mechanical; nothing checked fitness.

**Complete answer names:** the states a source can occupy; which permit dependency; the dependent's status in each.

## B6 · Shape — closed or open, and where private data lives

**Ask:** May the output carry keys you did not specify? If yes, which, and may they carry claims about the subject? Where do notes, confidence, debug and timestamps legitimately live?

**Failure:** claims parked outside the expected structure passed unchecked. The repair then over-reached and began rejecting harmless internal keys — the worse of the two errors.

**Complete answer names:** closed or open; the permitted private envelope if open; and the two rules that make an envelope safe — it may never carry a claim about the subject, and it may never reach a publishing or acting consumer. Systems that publish or act consume an explicit projection of checked data, never the raw submission.

## B7 · Context — what the output may never change

**Ask:** Which values are fixed by the request — currency, locale, units, tenant, environment, date basis? Which may the output vary, and on what evidence?

**Failure:** a response relabelled the assignment's country and currency while keeping the original amounts, and passed — nothing ever read the response's context block.

**Complete answer names:** the fixed set; the variable set with its evidence requirement; the check comparing response context to request context.

## B8 · Completion — what nothing counts as

**Ask:** What does an empty output mean? A refusal? A partial answer? Is correctly declining the whole task success, failure, or a third thing? What is the denominator when only part of the work was attempted?

**Failure:** not observed as an exploit in the source project, because it was asked early — which is why it is here. Without it, "I did nothing, carefully" scores as success.

**Complete answer names:** empty, refusal and partial each mapped to an outcome; the separation between handled correctly and work completed; and a rule that the system may not shrink its own denominator.

---

# Part C · Verdict and judgment — what the grader returns

## C1 · Status vocabulary

**Ask:** What states can an item end in? What does each mean to the person downstream? Which permit publication or action?

**Complete answer names:** the closed list of statuses, one plain sentence each, and which are publishable.

## C2 · Issue codes

**Ask:** When the grader rejects something, what is the closed list of reasons it may give? What must each carry — the field, the evidence, a corrective action?

**Why:** free prose cannot be checked, compared across runs, or routed to whoever fixes it.

**Complete answer names:** the code list; the payload each code carries; and whether an unrecognised code is itself a failure.

## C3 · Blocker versus warning

**Ask:** Which findings stop an item from being published, and which only annotate it? What makes something a warning rather than a blocker?

**Complete answer names:** the split; and the rule that a warning may never be reported as a blocker or the reverse.

## C4 · Tolerances

**Ask:** Where is a small deviation acceptable, how small, and what overrides the tolerance entirely?

**Why:** tolerance without an override is a hiding place. A value can land within tolerance and still be read from the wrong source, or cross a threshold that changes the answer.

**Complete answer names:** the tolerance, its unit, and every condition that voids it — wrong source, wrong unit, or crossing a defined boundary.

## C5 · Rollup and denominator

**Ask:** How do item verdicts become a batch verdict? What does "the task succeeded" mean? What is the denominator, and can the system influence it?

**Failure it prevents:** a system that quietly narrows its own scope and reports a high pass rate on what is left.

**Complete answer names:** the rollup rule; the definition of overall success; the denominator; and the rule preventing the system from shrinking it.

## C6 · Error ranking

**Ask:** Rank the error types this contract can produce, worst first, one line of reasoning each.

**Why:** unranked errors cannot be traded off, and the ranking is what tells a grader how strict to be. Push back once if a ranking looks unconsidered; accept the second answer.

**Complete answer names:** the ordered list with reasons; and the rule that ranking informs strictness but never licenses trading a lower-ranked error for completion.

## C7 · Human judgment

**Ask:** Which rules here cannot be decided by code? For each — who decides, what evidence do they need in front of them, and what are their criteria?

**Why:** pretending a subjective rule is deterministic produces a proxy metric that is confidently wrong. Read `human-judgment.md`.

**Complete answer names:** per non-deterministic rule — the named reviewer or role, the required evidence, the decision criteria, and what the grader records rather than decides.

## C8 · Verification plan

**Ask:** For each rule, who will confirm the expected answers are right, and how? Which examples has the owner personally adjudicated, and which were proposed by a model or a builder?

**Why:** a grader validated only against its author's expectations tells you the author was consistent, not that the author was right.

**Complete answer names:** which examples are owner-approved; which are proposed and pending; and the plan for an independent set prepared outside the building thread.

---

## Coverage check before leaving the bank

Twenty-four questions. Every one is either answered, quoted from the spec, or listed in `OPEN_DECISIONS.md`. None is silently skipped, and none is filled in by the interviewer.
