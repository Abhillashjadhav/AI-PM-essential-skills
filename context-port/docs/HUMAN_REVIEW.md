# Offline human review

Phase 5 turns a ready segregation plan into a deterministic, metadata-only review package and standalone HTML form. ContextPort does not open the page automatically.

## Sample selection

Every project group and the ungrouped container is represented. Each group contributes at most two conversations: first and last by validated ordinal. Empty groups remain visible.

The sample includes titles, stable IDs, ordering, message counts, role sequences, content-kind counts, and attachment-reference counts. It excludes message text and raw unknown payloads. Titles remain potentially sensitive metadata, so private review packages stay local.

## Approval contract

An approval must confirm:

- Project boundaries.
- Conversation titles and order.
- Roles and content kinds.
- Attachment and unsupported dispositions.
- Destination mappings and transformations.

The decision is bound to `review_package_sha256`. Approval fails unless every confirmation is true. Rejection never authorizes automatic repair.

## UI safety

The HTML is standalone and requires no network service. Imported metadata is HTML-escaped and inserted only as inert text. The page can download a decision JSON file after an explicit click; ContextPort itself does not launch a browser or write the decision.
