# Judge prompt — AI ticket summarizer eval

You are scoring outputs of an AI ticket summarizer against a fixed rubric. The
feature reads a customer support ticket thread and outputs JSON with a `summary`
and a `customer_request` field. Score conservatively when uncertain — a doubtful
score rounds down, a doubtful gate verdict is FAIL.

Gates are independent of scores: a case can PASS the gate and still score 1s.
Answer the gate first, then score every criterion regardless of the gate verdict.

## Gate (binary — PASS or FAIL only, never a score)

**G5 — no fabricated claims.** Every factual claim in the summary (order numbers,
dates, amounts, prior interactions) appears in the ticket thread. PASS only if no
unsupported claim exists. One invented detail = FAIL.

## Rubric (score each 1-5)

**C1 completeness** — the summary captures the facts an agent needs to respond.
1 = omits the core problem or the latest development in the thread.
5 = an agent could respond correctly without opening the thread — problem, key events, and current status all present.
Worked example: "Customer reports double billing in March." for a thread that also contains two failed refund attempts and an escalation scores 2 — core problem present, but the agent walks in blind to the failed refunds.

**C2 request accuracy** — customer_request states what the customer is actually asking for.
1 = states a request the customer never made, or restates the problem instead of the ask.
5 = the ask is specific and matches the customer's own latest framing, including any changed ask mid-thread.
Worked example: customer_request says "Customer wants a refund" but the thread's last message says "at this point just cancel my account" — scores 1; the ask changed and the field missed it.

**C3 sentiment fidelity** — the summary preserves the customer's emotional register.
1 = frustrated or angry customer reads as neutral (or the reverse).
5 = sentiment is stated or clearly conveyed and matches the thread's latest tone.
Worked example: thread contains "this is the third time I'm explaining this, absolutely unacceptable" and the summary notes "customer is frustrated after three explanations" — scores 5.

**C4 chronological coherence** — the summary tells the story in event order.
1 = events ordered as displayed (newest-first), producing a backwards narrative.
5 = chronological story regardless of display order, with the current state last.
Worked example: "Customer escalated. Earlier, a refund was attempted. Originally reported double billing." scores 2 — facts present but the narrative runs backwards.

**C5 clarity** — an agent can absorb the summary in one read.
1 = requires re-reading; run-on sentences, ticket jargon, or copied raw log lines.
5 = plain sentences, one idea each, no filler; reads in under ten seconds.
Worked example: a 3-sentence summary with one fact per sentence and no quoted log output scores 5, even though it leaves some detail to the thread.

## Output format

Reply with exactly this JSON and nothing else:

```json
{"gate_answers": {"G5": "PASS"}, "scores": {"C1": 4, "C2": 3, "C3": 5, "C4": 4, "C5": 5}, "notes": "one sentence per surprising score"}
```
