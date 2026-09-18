# Guided source setup

Supply the source records, evidence, and destination first. Run --guide to receive affected SKU, field, evidence IDs, and the specific supplier action. Setup does not fetch any database or invent a document authority.

## Authority

For each conflicting field, the supplier identifies the source that governs it. Add its contents to evidence and register it:

```json
"authority_registry": {
  "P1.description": {
    "evidence_id": "P1.description.spec",
    "source_location": "supplier-master/spec-v2",
    "supplier_approved": true
  }
}
```

The location is a traceable label/path supplied by the operator, not proof of live retrieval. Missing authority yields a supplier-resolution action; conflicting optional descriptions do not silently pass. See examples/authority_missing.json and examples/authority_resolved.json.

## Approved edits

```json
"supplier_edits": [{
  "sku": "P1", "field": "material", "operation": "replace",
  "evidence_id": "P1.material.edit", "approved": true, "family_wide": true
}]
```

The edit evidence must exist with the matching SKU, field, and replacement value. family_wide means the supplier confirms applicability to children; it is not permission for the model to infer applicability. Raw old facts stay in the input. Only one active approved edit per field is permitted; retain earlier history in evidence, not as multiple active edits.

## Corrections

An explicitly identified correction is a record-level proposed_corrections list, for example [{"field":"description","suggested":"cotton blend"}]. Known corrections may also be provided as profile.known_corrections (field -> misspelling -> suggested spelling). No automatic fuzzy typo detection is claimed. Publication remains blocked until an approved replacement resolves it.

## Claims and human review

Put descriptions/certifications in fields with evidence. Record claims requiring human validation in the record's claims list. Example:

```json
"claims": [{
  "field": "certification", "document_ref": "supplier/doc-x",
  "human_review": {
    "status": "approved", "reviewer": "reviewer-identifier",
    "reviewed_at": "2026-09-18", "document_ref": "supplier/doc-x",
    "evidence_id": "P1.certification"
  }
}]
```

Never manufacture these entries. A missing approval blocks. Built-in certification/compliance fields require review; additional fields can be registered in profile.human_review_fields. The Python checker verifies the declared association, not the authenticity or substance of the document. Unrestricted free-text claim recognition remains a limitation.

## Source problems versus setup mistakes

Supplier omission/conflict -> BLOCKED SKU with an action. Malformed evidence envelopes, impossible identity links, or ambiguous active edit configuration -> SETUP_ERROR, not a candidate failure. Size-chart ambiguity and missing units are supplier problems and block only the affected SKU. Claims and conflict metadata are source-side declarations; candidates cannot authorize their own corrections.

## Private company metadata

Use internal_metadata at submission/record level for arbitrary company fields. notes, confidence, _debug, warnings and created_at/updated_at/processed_at at those levels are recognized as internal aliases. They may contain any JSON value and are not evaluated as product claims. The grader ignores their content and never executes or propagates it into publication_payload or guided_help.

Downstream publication must use publication_payload, and downstream supplier actions must use guided_help generated from source rules. Neither consumer should use the raw candidate's notes, suggested actions, confidence or status overrides. This package contains no publisher or action executor.
