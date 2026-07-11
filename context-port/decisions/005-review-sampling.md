# Decision 005: deterministic review sampling

## Status

Accepted on 2026-07-11 as a reversible Phase 5 implementation rule.

## Decision

The review package samples at most two conversations from every segregation group: the first and last by validated ordinal. A one-conversation group contributes that conversation once. Empty groups remain listed with an empty sample so their boundary is still visible.

The package includes titles, stable IDs, ordinals, role sequences, content-block kind counts, message counts, and attachment-reference counts. It excludes message text and unknown raw payloads.

## Consequences

- Every project and the ungrouped container is represented.
- Boundary cases at both ends of each group are visible without sampling the entire corpus.
- Approval is bound to the exact review-package digest and all required confirmation fields.
- Rejection records no automatic repair authorization.
