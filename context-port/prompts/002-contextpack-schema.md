# Task title

ContextPort Phase 2: standalone ContextPack contract, synthetic fixtures, and validation

## Original task prompt

```text
Clarification:

AI-PM-essential-skills is the public repository.

PM-agent-OS is a separate private/internal repository and must remain opaque to public users.

ContextPort must:
- live inside AI-PM-essential-skills/context-port/
- be fully standalone
- have no runtime dependency on PM-agent-OS
- not copy PM-agent-OS internals
- not mention private architecture details in public docs
- be installable and usable by anyone from the public repository alone

PM-agent-OS may be used privately during development only for:
- evaluation design
- reviewer personas
- regression checks
- PR quality review

Any outputs from PM-agent-OS that are committed publicly must be:
- generic
- redacted
- non-proprietary
- understandable without access to PM-agent-OS

Update the architecture recommendation accordingly.

Then proceed with the next implementation phase in AI-PM-essential-skills only.
Do not modify PM-agent-OS.
```

## Date

2026-07-11

## Branch

`context-port/002-contextpack-schema`

## Status

In progress.

## Proposed PR title

`feat(context-port): define standalone ContextPack contract`

## Phase scope

- Define a public, assistant-neutral ContextPack contract without assuming a real export schema.
- Add entirely synthetic fixtures for valid and invalid packages.
- Add dependency-free deterministic validation and automated tests.
- Document the standalone architecture boundary and evaluation evidence.

## Exclusions

- No real Claude or ChatGPT export access.
- No source-specific parser or destination writer.
- No browser automation, network access, authentication, synchronization, or private data.
- No production dependency additions.
- No changes to existing AI-PM skills or any external repository.

## Acceptance gates

1. Public artifacts contain no private repository architecture or proprietary material.
2. Fixtures are visibly synthetic and contain no personal conversations or credentials.
3. Validation is deterministic and uses only the Python standard library.
4. Unknown content is distinguishable from empty content and never silently discarded.
5. Validation reports every detected failure instead of stopping at the first one.
6. The phase includes completed automated-test and evaluation evidence.

## Privacy classification

Public. All examples and fixtures must be synthetic and non-proprietary.

## Decisions requested

None. The user supplied the architecture boundary and authorized the next implementation phase.

## Decisions received

- ContextPort remains fully standalone under `AI-PM-essential-skills/context-port/`.
- It has no runtime dependency on private development systems.
- Private development-system internals must not be copied or exposed publicly.
- Any privately assisted review output committed here must be generic, redacted, non-proprietary, and independently understandable.
