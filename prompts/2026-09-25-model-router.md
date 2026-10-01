# Build prompt: model router

The complete build prompt (owner-approved specification, version 1.0, 25 September 2026) is saved word for word at [`model-router/docs/implementation-prompt.md`](../model-router/docs/implementation-prompt.md). The only change: three Markdown hard line breaks written as trailing double spaces became backslash line breaks, so `git diff --check` passes.

- Uploaded original sha256: `fb8b3e7b558c286c7d1bac8262a567771852d068737720e2dc495a1426786f4a`
- PRD: [`prds/2026-09-25-model-router.md`](../prds/2026-09-25-model-router.md)

## Build summary

Implement `model-router/`, a Python 3.11 standard-library terminal router that uses SQLite state and a pinned Codex App Server stdio adapter. It needs:

- task and consequence role floors;
- a per-thread model pin with human override;
- an automatic architecture → implementation handoff with the narrow capacity-based downgrade;
- durable queueing and recovery;
- model discovery and owner approval;
- an evaluation foundation.

Additional spend must be ₹0: live dispatch stays blocked unless enforceable included-only execution is proven. Don't modify existing skills, the marketplace, or ContextPort. Work on feature branches, keep PRs in draft, and don't merge.
