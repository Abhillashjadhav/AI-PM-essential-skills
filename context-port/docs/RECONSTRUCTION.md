# Reconstruction planning

Phase 6 generates an assistant-neutral dry-run plan after an explicit approved review. It performs no destination write.

## Guarantees

- Exact project and conversation titles are preserved.
- Roles, message order, content-block order, and text are unchanged.
- Every operation has a deterministic idempotency key.
- Dependencies enforce container → conversation → message order.
- Equivalent approved inputs produce an identical plan digest.
- `writes_performed` is always false.

Mapped projects use their approved destination container references. Ungrouped conversations use the adapter-defined `default` target. An unmapped project blocks planning; ContextPort never guesses a destination.

Destination APIs, observed effects, retries, and adapter-specific limits remain outside this phase.
