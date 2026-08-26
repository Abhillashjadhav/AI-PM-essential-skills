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

1. **Split first.** Keep prompt-tuning examples, validation cases, and a held-out test set separate. A few cases can improve anchors, but a release-critical trust claim needs a representative held-out set sized for the decision risk.
2. **Hand-score blind.** Domain experts score without seeing judge output, record reviewer/source provenance, and reconcile material inter-rater disagreements.
3. **Run the judge** on the same cases with model, prompt, and rubric versions frozen.
4. **Diff per dimension.** Keep binary labels and ordinal scores separate. For
   labels, report raw agreement, a confidence interval, chance-corrected
   agreement, and class-conditional false positives/negatives. For 1–5 scores,
   report absolute error and within-1 agreement as an explicit convention, not
   objective truth.
5. **Fix the rubric on train/validation evidence.** A gap ≥2 usually means an anchor or example is under-specified. Change one distinction at a time.
6. **Evaluate once on the held-out test set.** Do not tune on its misses and still call it held out.
7. **Version the result.** Store judge ID, rubric hash, golden-set hash, thresholds, and status. Any judge/rubric change invalidates the old calibration.

The release gate uses the 95% agreement lower bound, not only the point
estimate. It also enforces `minimum_golden_items`, `minimum_kappa`,
`maximum_false_positive_rate`, and `maximum_score_mae`. A golden label
dimension containing only PASS or only FAIL is invalid calibration evidence.

## Score-distribution smells

- **Everything scores 3-4**: anchors describe the extremes but real outputs live in the middle. Sharpen the 3 by adding a mid-anchor, or admit the criterion doesn't discriminate and cut it.
- **A criterion always scores 5**: it's a gate in disguise (outputs either nail it or would have failed a gate) or it's not testing anything. Apply the gate test from `gate-design.md`.
- **Two criteria always move together**: they're one criterion. Merge, keep the clearer anchors.
- **Scores swing between identical runs**: the anchors under-constrain the judge; add the worked example (or a second one) before doubting the model.
