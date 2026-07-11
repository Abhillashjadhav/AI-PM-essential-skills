# Task title

ContextPort Phase 3: public schema and safe Claude export inspection

## Original task prompt

```text
Decision:

Do not build or design a Product Engineering OS in this project.

The distinction is:

- PM-agent-OS decides and evaluates what should be built.
- A future Product Engineering agent would implement and operate software delivery.
- ContextPort is the current priority and must be completed first.

ContextPort remains:

- Public
- Inside AI-PM-essential-skills/context-port/
- Fully standalone
- Free to install and use
- Independent of PM-agent-OS at runtime

PM-agent-OS remains private and may only be used by me as an internal evaluation and review layer.

Now proceed with ContextPort.

NEXT PHASE

1. Update the ContextPort architecture documents to record this boundary.
2. Save this exact input as the next prompt contribution.
3. Create the next feature branch.
4. Define the public ContextPort contracts and synthetic fixtures.
5. Implement the ContextPack schema and safe Claude export inspection layer.
6. Run tests and evaluations.
7. Commit, push, open a draft PR, independently review it, and merge it if every gate passes.
8. Continue to the next ContextPort phase automatically.

Do not ask me about implementation choices.

Stop only for:
- real export access
- ambiguous project mappings
- browser automation
- ChatGPT or Claude writes
- truncation or summarization
- destructive actions
- a material product behavior decision
- failed gates after two repair attempts

Do not modify PM-agent-OS.
Do not expose or copy PM-agent-OS internals.
```

## Date

2026-07-11

## Branch

`context-port/003-safe-export-inspection`

## Status

Implemented and evaluated; awaiting human review.

## Proposed PR title

`feat(context-port): add safe synthetic export inspection`

## Decisions requested

None for routine implementation. Automatic merge cannot be performed because the repository's permanent contribution rules require human review before merge and prohibit automatic merges.

## Decisions received

- Do not build or design a Product Engineering OS in this project.
- ContextPort is the current priority.
- ContextPort remains public, standalone, free to use, and contained under `context-port/`.
- Private development tooling is not a ContextPort runtime dependency and its internals must not be exposed or copied.
- Stop at the repository's existing approval gates.
