# Gate Design

Deep guidance for Step 2 of eval-engine. Read this when deciding whether a check is a gate or a rubric criterion, or when a spec produces too many/too few gates.

## The gate test

A check is a gate only if ALL three hold:

1. **Partial credit is meaningless.** "Slightly fabricated" is fabricated. "Mostly contains the required disclaimer" doesn't contain it. If you can imagine accepting 80% compliance, it's a rubric criterion.
2. **Failure is disqualifying regardless of everything else.** A 5/5 on every rubric criterion cannot buy back a gate failure. If stakeholders would ever say "ship it anyway, the rest is great," it's not a gate.
3. **Passing is invisible.** A passed gate earns nothing — no points, no praise, no line in the report beyond a checkmark. Gates define the floor, not the ladder.

## The three canonical gate families

Almost every unshippable failure in an AI feature falls into one of these:

- **Fabrication** — the output asserts something not grounded in its input or in verified facts: invented ticket numbers, made-up policy terms, hallucinated names or dates. Usually a judge gate ("does the summary contain any claim not present in the source ticket? PASS only if none").
- **Missing required structure** — a field, section, disclaimer, or format element the spec says must always be present. Usually mechanical (field-presence or regex).
- **Safety/policy violation** — content the org must never emit: PII leakage, medical/legal advice where forbidden, off-policy commitments ("we guarantee a refund"). Mechanical where a denylist works, judge where it needs reading.

If a proposed gate fits none of these families, apply the gate test extra skeptically — it's usually a score wearing a gate costume.

## Gate smells

- **The averaged gate.** Any scheme where gates contribute points to a total. Gates are a boolean AND, never terms in a sum.
- **The quality gate.** "Output must be well-written" — partial credit is obviously meaningful, so it's a rubric criterion. The word "well" in a gate is a smell by itself.
- **The threshold-on-a-score gate.** "Average rubric score ≥ 3.5" is a shipping decision, not a gate. Gates apply per-case, before scoring.
- **The unfalsifiable gate.** If neither code nor a judge given the case contents can answer PASS/FAIL, it can't be a gate. Rewrite until binary or move to the rubric.
- **The invented-fact gate.** A gate that hardcodes a policy value, field list, or threshold the spec never stated. Never fill these by guessing — ask the user. A gate checking the wrong policy window fails correct outputs and passes wrong ones.

## Deterministic vs model gates

Prefer deterministic checks — they are fast, reproducible, and easy to debug. Use a model gate only when the check requires semantic judgment (fabrication, tone boundaries, or context-dependent policy violations). Model gates return binary `PASS`/`FAIL`, never a score, and require held-out human calibration for the exact judge/rubric version.

Every deterministic gate uses a supported check in `references/evidence-contract.md`. If the check cannot express the claim faithfully, use a calibrated model grader instead of a brittle proxy.

Trajectory checks are not automatically gates. Exact step/order expectations
should normally be diagnostic because multiple valid paths can reach the right
outcome. They become gates only when the path itself is risk-critical—for
example, consulting the wrong policy document, skipping identity verification,
or calling a forbidden tool—even if the final answer happens to be correct.

## Count discipline

Use the smallest complete set. A fixed minimum encourages invented gates; a fixed maximum can hide real safety or contract boundaries. Re-read the spec asking "what output would get this feature turned off?" and retain only checks that pass the three-part gate test.

## Suite-level interpretation

A failed gate fails one trial. The suite's approved release rules decide whether
the observed trial failure blocks the candidate. Regression suites normally
require all previously reliable trials to pass. Capability suites may use a
measured threshold while the team is hill-climbing. Safety/privacy defaults
remain zero tolerated failures unless an accountable owner explicitly changes
the contract.
