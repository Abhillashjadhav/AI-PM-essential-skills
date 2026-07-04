---
name: builder-validator
description: Use this skill when the user asks to generate an artifact (document, code, post, analysis, design spec) and wants it validated, self-checked, or quality-assured before seeing it — or whenever they say "make sure it meets the requirements", "validate against the spec", "self-QA this", "check your own work", or after repeated correction rounds on the same artifact. Freezes the requirements into binary pass/fail criteria BEFORE generating, generates, then audits the output against the frozen criteria in a separate pass and reports a scorecard. Do NOT use for pure questions, brainstorming, or when the user explicitly wants a fast rough draft with no checks.
---

# Builder-Validator

Lock the spec first, build second, audit third. The builder never grades its own homework mid-flight — validation is a separate pass against criteria frozen before generation began.

## Step 1 — Freeze the spec (silent)

Extract every stated requirement into binary (yes/no) criteria. Rules:
- Each criterion must be checkable by reading the output alone (no "feels good").
- Mark each as GATE (failure = artifact rejected) or SCORE (failure = noted, tradeable).
- If a requirement is vague ("make it engaging"), convert to a proxy ("opens with a specific number or question") — record the conversion but don't narrate it to the user.
- **Never invent facts to pass a gate.** If a gate-critical criterion depends on a fact not given by the user — a date, a name, a number, a policy detail, a metric — stop and ask the user for it before drafting. Do not fabricate a plausible-sounding value to make the criterion checkable.
- Freeze the checklist silently. It cannot change during this cycle. Show only the audit result (Step 3), not the checklist itself. If the user adds requirements later, that starts a new cycle with a new frozen spec.

## Step 2 — Build

Generate the artifact. Do not reference the checklist while generating beyond following the requirements — no criterion-by-criterion writing, which produces stilted output.

## Step 3 — Validate (separate pass)

Re-read the frozen checklist, then audit the artifact criterion by criterion. Output this scorecard:

```
SPEC AUDIT — cycle N
GATES:  [PASS/FAIL] <criterion> — <one-line evidence>
SCORES: [PASS/FAIL] <criterion> — <one-line evidence>
RESULT: X/Y passed. Gates: ALL PASS | FAILED (list)
```

## Step 4 — Iterate or ship

- Any GATE failed → revise the artifact targeting only the failed criteria, re-audit. Max 3 cycles, then stop and report what's stuck and why.
- All gates pass → present the artifact + final scorecard.
- Never silently revise: every cycle's scorecard is shown.

## Limitations

- Criteria quality bounds audit quality: vague specs produce weak proxies; the checklist itself stays silent, but every proxy conversion is still recorded and available if the user asks to see the frozen spec.
- Self-audit by the same model has blind spots; for high-stakes artifacts, recommend a second-model or human review of the frozen checklist itself.
- Max 3 cycles is a cost guardrail, not a quality guarantee.
- Silence on the checklist is a presentation choice, not a secrecy rule: the user can always ask to see the frozen criteria before or after the audit.
