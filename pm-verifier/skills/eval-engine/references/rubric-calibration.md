# Rubric Calibration

Deep guidance for Steps 3 and 5 of eval-engine. Read this when writing 1/5 anchors, when the judge and a human disagree, or when scores cluster uselessly around 3-4.

## Anchor design

An anchor is a concrete, feature-specific description of what a score looks like — not an adjective.

Bad (adjective anchors):
```
1 = poor accuracy
5 = excellent accuracy
```

Good (feature-specific anchors, for a support-ticket summarizer):
```
1 = summary contradicts the ticket or states a resolution that didn't happen
5 = every claim in the summary is traceable to a specific line in the ticket,
    and the customer's actual request is stated in the first sentence
```

Rules of thumb:
- Write the 1 and the 5 first; 2-4 are interpolation. If you can't describe a concrete 1, the criterion is probably redundant with another one.
- Anchors reference observable properties of the output ("states", "contains", "traceable to"), never reader feelings ("compelling", "confusing").
- One worked example per criterion is mandatory: a short output fragment, the score it earns, and one sentence of why. The worked example is what teaches the judge model your scale — anchors alone under-constrain it.

## The judge prompt

The judge prompt block must be self-contained — a person (or model) with no other context can apply it. Include:

1. Role framing: "You are scoring outputs of <feature> against a fixed rubric. Score conservatively when uncertain."
2. The judge gates, each demanding a binary PASS/FAIL — never a score.
3. Every rubric criterion with its 1-anchor, 5-anchor, and worked example.
4. The exact JSON output shape:
```json
{"gate_answers": {"G3": "PASS"}, "scores": {"C1": 4, "C2": 3}, "notes": "one sentence per surprising score"}
```
5. An instruction that gates are independent of scores: a case can PASS all gates and still score 1s, or fail a gate while the (unused) scores would have been 5s.

## Disagreement is calibration signal, not failure

When a human hand-score and the judge disagree, the rubric — not the judge, not the human — is usually what's broken. The gap tells you which anchor is vague.

The calibration loop:

1. **Hand-score first.** The PM scores 3-5 real cases without seeing judge output (blind, to avoid anchoring on the judge).
2. **Run the judge** on the same cases via the harness.
3. **Diff per criterion.** Agreement within ±1 point → criterion is calibrated, leave it alone.
4. **Gap ≥2 on any criterion → rewrite that anchor**, usually by moving whatever distinction the human was using into the anchor text or the worked example. Do not "prompt-engineer the judge harder" — fix the rubric so any judge lands closer.
5. **Re-run only the disagreeing criterion.** One anchor change per iteration, like any good optimization loop — batch changes hide which fix worked.
6. **Stop when all criteria agree within ±1** on the calibration set. Record the calibration set IDs in the eval folder so future rubric edits re-run against the same baseline.

## Score-distribution smells

- **Everything scores 3-4**: anchors describe the extremes but real outputs live in the middle. Sharpen the 3 by adding a mid-anchor, or admit the criterion doesn't discriminate and cut it.
- **A criterion always scores 5**: it's a gate in disguise (outputs either nail it or would have failed a gate) or it's not testing anything. Apply the gate test from `gate-design.md`.
- **Two criteria always move together**: they're one criterion. Merge, keep the clearer anchors.
- **Scores swing between identical runs**: the anchors under-constrain the judge; add the worked example (or a second one) before doubting the model.
