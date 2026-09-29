# Return-to-work note

## Current next step — 2026-09-29

Use `docs/model-router-personal-subscription`, run `router.py setup`, then `router.py pilot --routing-check`. Existing model approvals are reused; record the billing confirmation locally for the same account. [Complete instructions](personal-subscription.md). No model weights, paid API credentials or workspace upgrade are required by this mode. Do not merge or release until review and real-task validation are complete.

## Historical Jev integration note

No new product decision was needed to finish the TypeSafe integration. The approved direction has been implemented: TypeSafe enforces credits; the router has no local spending cap or daily billing check.

## Work ready for review

- Optional Jev classifier, local fallback, unchanged GPT policy and spend gate.
- First-prompt classification, fixed model for the thread, override and architecture handoff retained.
- Credit/provider-error stop, no automatic retries, durable recovery, private local key entry.
- Offline tests and repository checks passed; no live provider call, billing change or main merge.
- [Complete architecture and operating guide](jev-integration.md).

## Actions that require the Mac/account

1. Enter the TypeSafe key privately through `python3 model-router/router.py jev setup`.
2. Run `python3 model-router/router.py jev pilot` and review its six classifications and timing. This uses only Jev, never GPT or existing queued work.
3. Run the existing GPT `setup`/`doctor` locally. If the spend gate blocks, preserve it and report the exact reason. No new paid plan, paid API or billing change is approved.
4. Review real outputs before adopting the router in the daily workflow. Tests establish software behavior, not 95% routing quality.

These are activation and validation steps, not a request to redesign the product.

## Interface item left open

The desktop integrated terminal can host the router without another browser tab. Automatic routing of text typed into the normal Codex/ChatGPT composer has not been established. No documented browser model-picker hook was found, and no browser automation was added.

If the native composer remains essential after trying the integrated terminal, the open question is: **what interaction would be acceptable inside the current chat when a supported automatic model switch is unavailable?** That answer would define a separate interface experiment. This question does not block the terminal pilot, and it does not reopen the already-approved local/cloud or spending decisions.

## Exact next commands

From the full `docs/model-router-jev-guide` branch on the Mac:

```bash
python3 model-router/router.py jev setup
python3 model-router/router.py jev pilot
```

The API key belongs in the hidden terminal prompt, not in a chat message.
