# <Feature> — grader contract

Owner: <name> · Date: <date> · Status: **DRAFT** until owner approves
Interview: model-grader v0.1.0 · Contract version: <n>

> Every rule below carries four gates. `decision` is the owner's; `PROPOSED` means a model suggested it and it is not settled. `examples` is whether both sides exist. `verification` is whether anything was actually run. `buildability` is whether an implementer could write the check from the rule alone. These are never collapsed.

---

## Part A · Shape

### A1 Outcome and targets
- Outcome: <one sentence>
- Correctness target: <owner's number> · Wrong-rejection target: <owner's number>
- When they conflict: <which wins, and why>
- Does correctly declining count as success? <answer>

### A2 Input and output shape
<field list with types; per-item vs per-submission; one full worked example of a correct output>

### A3 Requirement class per field
| Field | Required / Conditional / Optional | Condition |
|---|---|---|

### A4 Allowed values, units, formats
| Field | Allowed values | Aliases | Units and conversion | Unmapped value → |
|---|---|---|---|---|

### A5 Evidence and provenance
<citation required for which fields; reference format; alternate equivalent references; what a citation must prove>

### A6 Record relationships
| Link type | What proves it | Shared values | Item-only values | May the system create it? |
|---|---|---|---|---|

### A7 Operations and record states
| Operation | Requirements that differ | |
|---|---|---|

| Record state | What is required | What may be done with it |
|---|---|---|

### A8 Authority and resolution
| Conflict type | Who resolves | What makes it binding | Scope of the resolution | What is retained of the original |
|---|---|---|---|---|

May the system self-resolve a disagreement? <answer>

## Part B · Integrity

| # | Question | Decision |
|---|---|---|
| B1 | what may appear that the source did not | |
| B2 | what ties an answer to its request | |
| B3 | what counts as the same value | |
| B4 | what must survive unused | |
| B5 | what makes a source fit to depend on | |
| B6 | closed or open output; where private data lives | |
| B7 | what the output may never change | |
| B8 | what nothing counts as | |

**B6 envelope rules (if output is open):** <the owner's two rules — what a private envelope may never carry, and which consumers it may never reach. See question-bank.md §B6 for what a complete answer names; do not fill this from it.>

## Part C · Verdict and judgment

### C1 Statuses
| Status | Means | Publishable? |
|---|---|---|

### C2 Issue codes
| Code | Carries | Used when |
|---|---|---|

### C3 Blocker vs warning
<the split, and the rule that one is never reported as the other>

### C4 Tolerances
| Where | Tolerance | What voids it |
|---|---|---|

### C5 Rollup and denominator
<item → batch; what "succeeded" means; the denominator; the rule preventing the system shrinking it>

### C6 Error ranking
| Rank | Error | Why it sits here |
|---|---|---|
| 1 | | |

**What ranking does and does not license:** <the owner's rule. See question-bank.md §C6 for what a complete answer names; do not fill this from it.>

### C7 Human judgment
| Rule | Reviewer | Required evidence | Criteria | Grader records |
|---|---|---|---|---|

### C8 Verification plan
<which examples are owner-adjudicated; which are proposed and pending; the plan for an independent set prepared outside the building thread>

---

## Rule register

| ID | Rule | Must-fail example | Must-pass example | Decision | Examples | Verification | Buildability |
|---|---|---|---|---|---|---|---|
| R1 | | | | APPROVED / PROPOSED / OPEN | BOTH / ONE-SIDED / MISSING | NOT RUN / EXECUTED / INDEPENDENTLY REVIEWED | TESTED / UNTESTED / ONE-SIDED / NOT DECIDABLE |

## Buildability test result

- Rules `UNTESTED`: <list>
- Rules `ONE-SIDED`: <list>
- Rules `NOT DECIDABLE`: <list>
- Can a system satisfy every rule and still do the wrong thing? <answer, or the cheapest way>
- Can a system do the work correctly and fail? <answer>
- **Build dry-run:** reader <who>, questions raised: <n>. <List them. Zero is the exit condition.>

## Approval

- [ ] Owner has read every `PROPOSED` decision and approved or changed it
- [ ] Owner has approved the error ranking
- [ ] Build dry-run has been run, its question count recorded, and every question it raised logged in `OPEN_DECISIONS.md`

Contract is **DRAFT** until all three are checked.
