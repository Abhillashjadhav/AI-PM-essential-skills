# Decision 004: segregation contract

## Status

Accepted on 2026-07-11 from the permanent ContextPort reliability rules.

## Decision

Project segregation operates only on a valid ContextPack. It groups conversations by stable `project_id`, places `project_id: null` conversations in one explicit ungrouped container, preserves titles without using them as identities, and orders conversations and messages by validated ordinals.

Destination mappings are optional inputs. Zero mappings means `unmapped`; one distinct destination means `mapped`; more than one distinct destination for the same source project produces `decision_required` and no executable segregation plan.

## Consequences

- Duplicate project and conversation titles remain valid.
- Every conversation appears exactly once in a ready plan.
- Message content is not emitted by the segregation plan.
- Unknown mapping targets are validation failures.
- Ambiguous mappings are never resolved automatically.
