# Two-task execution check

Implement the owner's clarified acceptance demonstration: one simple task on
the approved lowest model and one difficult task on the approved highest model.
Each must be a fresh chat, show selection, perform the task, and report evidence
for the model used. Model names are discovered/approved, never hard-coded.

Use `pilot --routing-check`. Keep the existing spending boundary intact. Check
it before any classifier or GPT task; use at most one explicit dispatch per
case. Never resume other queued work, retry an uncertain send, or approve models.
Create evaluation threads/jobs atomically so they are excluded from weekly
adoption metrics and cannot later be resumed as user work by a background process.
Keep the two tasks in a fresh isolated folder, with read-only task execution.

Save complete answers and evidence locally. Separate the requested model, the
model in the provider's thread configuration, and observed per-turn model
evidence. A matching configured model, an answer saying "I am model X", and a
synthetic result are insufficient for a live PASS. Missing per-turn evidence
must produce MODEL_USE_UNVERIFIED. Fail incorrect routing, incomplete answers,
failed turns, model mismatches and identical model mappings.

VERIFIED from current source: normal successful Codex turns do not populate
`dispatches.observed_model`; only a reported reroute populates it, and that turn
is stopped. Thus this change alone does not make a real PASS possible with the
current adapter. It exposes the missing evidence instead of manufacturing it.
The personal-plan spending restriction is also unchanged. Both remain open
under issue #80 and the independent review.

Run meaningful offline tests for the two fresh threads, automatic classification,
evidence grading, no unrelated queue execution, evaluation isolation, failed
spending preflight, different model bindings, and no false simulator/label PASS.
Publish a draft PR; do not merge main or claim a live demonstration happened.

## Run after setup

```bash
python3 model-router/router.py pilot --routing-check
```

`BLOCKED` means no permitted live test could complete. `MODEL_USE_UNVERIFIED`
means the requested models produced responses but the per-turn model evidence
is missing. `PASS` requires matching per-turn evidence for both correct routes
and complete nonempty answers. Answer quality still needs the owner's review.
`SIMULATED` never counts as a live pass. A run is at most two explicit GPT
dispatch attempts; the durable pre-send marker gives a conservative count,
including uncertain execution, and is not a bill. Jev, when enabled, can also
classify each of the two public first prompts. When Jev is off, local rules run.
