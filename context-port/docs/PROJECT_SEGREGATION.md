# Project segregation

The Phase 4 engine converts a valid ContextPack into a deterministic, content-free membership plan. It does not parse exports or write to an assistant.

## Invariants

- Stable IDs determine membership; titles never do.
- Original project and conversation titles are preserved exactly.
- Duplicate titles remain separate records.
- Conversations with `project_id: null` enter one explicit ungrouped container.
- Conversations and messages retain validated ordinal order.
- Every conversation appears exactly once.
- Messages never move between conversations or projects.
- The plan contains message IDs and counts, not message content.

## Optional destination mappings

Mappings use version `0.1`:

```json
{
  "mapping_version": "0.1",
  "project_mappings": [
    {
      "source_project_id": "project-a",
      "destination_container_id": "destination-a"
    }
  ]
}
```

Repeated identical rows are idempotent. Multiple distinct destination IDs for one source project produce `status: decision_required`, list the conflicting destinations, and emit no plan. An unknown source project is an input error. ContextPort never chooses a destination automatically.

## Determinism

Equivalent validated inputs and mappings produce an identical plan and `plan_sha256`. The digest covers the complete plan before the digest field is added. No timestamp is generated.

The public result contract is `schemas/segregation-plan-0.1.schema.json`. Ready plans and decision-required artifacts are distinct schema branches.

## Current boundary

Human review of the plan is Phase 5. Real exports, reconstruction, browser automation, destination writes, truncation, summarization, deletion, and synchronization remain unsupported.
