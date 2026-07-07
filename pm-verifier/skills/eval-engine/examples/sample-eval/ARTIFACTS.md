# eval-engine output for examples/sample-spec.md

This is the full three-artifact output the skill produces for the ticket-summarizer
spec, exactly as it appears in chat. The machine-readable versions live next to
this file (`gates.json`, `rubric.json`, `judge_prompt.md`).

---

## Artifact 1 — Binary gates

```
GATE G1: summary field present
CHECK: output JSON contains a non-empty "summary" field
WHY A GATE, NOT A SCORE: the sidebar renders this field; without it the feature shipped nothing — there is no partially-present field
TYPE: mechanical (field_present)

GATE G2: customer_request field present
CHECK: output JSON contains a non-empty "customer_request" field
WHY A GATE, NOT A SCORE: agents triage on this field; a missing ask is a broken contract with the UI, not a quality shortfall
TYPE: mechanical (field_present)

GATE G3: summary fits the panel
CHECK: len(output.summary) <= 600 characters
WHY A GATE, NOT A SCORE: the sidebar truncates at 600 chars — a 601-char summary displays cut off mid-sentence; "mostly fits" is meaningless
TYPE: mechanical (max_length, field=summary)

GATE G4: no resolution commitments
CHECK: summary matches none of: "we guarantee", "you will receive a refund", "we promise"
WHY A GATE, NOT A SCORE: the spec forbids the model making commitments — one implied promise creates a customer-facing liability no amount of summary quality buys back
TYPE: mechanical (contains_none)

GATE G5: no fabricated claims
CHECK: every factual claim in the summary (order numbers, dates, amounts, prior interactions) appears in the ticket thread — binary PASS/FAIL
WHY A GATE, NOT A SCORE: an agent acting on one invented refund amount damages a real customer; "only slightly fabricated" is fabricated
TYPE: judge
```

## Artifact 2 — Calibrated LLM-judge rubric

```
C1: completeness — the summary captures the facts an agent needs to respond
  1 = omits the core problem or the latest development in the thread
  5 = an agent could respond correctly without opening the thread — problem, key events, and current status all present
  WORKED EXAMPLE: "Customer reports double billing in March." for a thread that also
  contains two failed refund attempts and an escalation → scores 2: core problem is
  there, but the agent would walk in blind to the failed refunds.

C2: request accuracy — customer_request states what the customer is actually asking for
  1 = states a request the customer never made, or restates the problem instead of the ask
  5 = the ask is specific and matches the customer's own latest framing, including any changed ask mid-thread
  WORKED EXAMPLE: customer_request says "Customer wants a refund" but the thread's
  last message says "at this point just cancel my account" → scores 1: the ask
  changed and the field missed it.

C3: sentiment fidelity — the summary preserves the customer's emotional register
  1 = frustrated or angry customer reads as neutral (or the reverse)
  5 = sentiment is stated or clearly conveyed and matches the thread's latest tone
  WORKED EXAMPLE: thread contains "this is the third time I'm explaining this, absolutely
  unacceptable" and the summary notes "customer is frustrated after three explanations"
  → scores 5: register preserved, grounded in the thread.

C4: chronological coherence — the summary tells the story in event order
  1 = events are ordered as displayed (newest-first), producing a backwards narrative
  5 = chronological story regardless of display order, with the current state last
  WORKED EXAMPLE: "Customer escalated. Earlier, a refund was attempted. Originally
  reported double billing." → scores 2: all facts present but the narrative runs
  backwards; an agent must mentally reverse it.

C5: clarity — an agent can absorb the summary in one read
  1 = requires re-reading; run-on sentences, ticket jargon, or copied raw log lines
  5 = plain sentences, one idea each, no filler; reads in under ten seconds
  WORKED EXAMPLE: a 3-sentence summary with one fact per sentence and no quoted log
  output → scores 5, even though it leaves some detail to the thread.
```

**Note on scores:** rubric scores are calibrated judgments from an LLM judge, not
objective measurements. Hand-score 3-5 cases blind and run the calibration loop in
`references/rubric-calibration.md` before trusting them; a ≥2-point human-judge gap
means an anchor needs rewriting, not that the judge failed.

## Artifact 3 — Runnable harness

Scaffolded next to this file: `prepare.py`, `run.py`, `report.py` (copied from the
skill's `harness/` templates), the three config files above, plus `cases/` and
`judgments/`. Flow: `prepare.py` validates cases → `run.py` applies gates first
(any failure = automatic FAIL, rubric skipped) and writes one judge prompt per
surviving case into `judgments/` → you paste each into your own Claude session and
save the JSON reply alongside → re-run `run.py` → `report.py` renders `report.md`.
