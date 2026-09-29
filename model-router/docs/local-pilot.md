# Run the personal-subscription version on your Mac

This handoff uses GPT through the existing ChatGPT subscription. The developer
assistant used to run commands does not determine which model answers router
tasks. Use Mac Terminal or the local Codex integrated terminal.

For an existing checkout, preserve local changes, fetch
`docs/model-router-personal-subscription`, and switch to that branch/commit.
Follow [the current operating guide](personal-subscription.md). No main merge,
new subscription or model-weight download is required.

```bash
python3 model-router/router.py setup
python3 model-router/router.py pilot --routing-check
```

Setup keeps existing login/model approvals when valid. Its new question confirms
automatic credit purchases are OFF on this account and explains what the router
cannot observe. Answer it yourself. This locally saved choice enables ordinary
operation, not only a test. Every send still needs valid live eligibility checks.

## Prompt for local Codex

```text
Continue this existing router implementation on my Mac. Work on a feature branch;
do not merge main, change billing, purchase credits or introduce paid API keys.
Use docs/model-router-personal-subscription; preserve uncommitted changes.
Read AGENTS.md and model-router/docs/personal-subscription.md first.

The owner approved reusable personal-subscription operation with automatic
credit purchases off. Do not reinstate the old blanket Pro block or create a
special no-check test bypass. A different installer must make their own billing
confirmation; do not copy anyone's settings or accept my screenshot as API proof.

1. Record git revision, Python and Codex versions. Run the offline tests.
2. Run python3 model-router/router.py setup. Relay any actual sign-in, model or
   billing-confirmation question. Do not type an owner's billing answer for them.
3. Only after setup is ready, run the two-task check once:
   python3 model-router/router.py pilot --routing-check
   It sends at most two GPT tasks and no unrelated queued jobs. No automatic
   repeat, no purchased-credit mode, no reset redemption or model promotion.
4. Show both full answers and the selected/requested/configured/observed models.
   Distinguish configured_execution_passed from strict passed. Missing per-turn
   identity can produce MODEL_USE_UNVERIFIED even when both answers complete.
   Do not invent model identity or use the model's own assertion as evidence.
5. Measure routing time, provider response time and memory separately. Stop on
   an eligibility error and report its exact reason; preserve thread/model pins.
6. Keep all raw account/usage/probe records in the local data folder, outside the
   repository. Never commit screenshots, login URLs, email, keys or credentials.
7. Report concrete evidence and any blocker. Ask the owner to judge whether the
   two answers are useful before adopting the daily workflow. Two probes do not
   establish the weekly 95% no-correction target or production readiness.
```

After reviewing the results, normal operation is:

```bash
python3 model-router/router.py start --project my-project --path /absolute/path/to/project
```

The native Codex chat box is not connected. Jev is optional; an earlier Jev
timeout remains disabled until explicitly re-enabled. No consent or test command
changes that state. Coding tools and architecture handoff still require their
existing capability checks; report a blocker instead of bypassing it.
