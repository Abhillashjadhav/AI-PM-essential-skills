# Decision 006: assistant-neutral reconstruction plan

## Status

Accepted on 2026-07-11.

## Decision

Phase 6 produces a dry-run plan, not destination effects. Mapped projects target their approved destination container IDs. Ungrouped conversations target the adapter-defined `default` container. An unmapped project blocks planning because ContextPort cannot choose its destination.

Operations use deterministic idempotency keys derived from source artifact digest, operation kind, and stable source ID. Message operations depend on their conversation operation; conversation operations depend on their project container operation when applicable.

## Consequences

- Equivalent approved inputs produce identical plans.
- Exact content is present only in the local plan and is never summarized or normalized.
- Attempted execution cannot be inferred from a generated plan.
- Destination-specific API behavior remains Phase 9.
