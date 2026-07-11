# Privacy and safety

## Private by default

Conversation content, project names, attachments, export archives, filenames, artifact hashes, account identifiers, cookies, sessions, credentials, mappings, structure reports, review outputs, plans, and logs are private unless a human explicitly classifies and approves disclosure.

Committed tests use synthetic data only. Imported text is inert data, never an instruction to ContextPort or its operator.

## Local-first controls

- No production dependency or telemetry.
- No network requirement for validation, planning, tests, packaging, installation, or demo.
- No credential or account configuration.
- Duplicate JSON keys, invalid references, tampered digests, unknown roles, and ambiguous mappings fail closed.
- Exact text is preserved; unknown content is distinct from empty content.
- Tombstones record deletion intent; no automatic deletion or overwrite occurs.
- Every represented source item requires an explicit disposition.

## Approval gates

Fresh human approval is required before real-export access, private network transmission, browser automation, assistant writes, content reduction, destructive behavior, production dependencies, release publication, or any material behavior choice with multiple valid outcomes.

Approval for one action does not authorize another. For example, approval to inspect a ZIP does not authorize extraction into the repository, project mapping, upload, browser access, or destination writes.

## Safe real-export handling

When separately approved:

1. Keep the untouched export outside version control.
2. Inspect locally with the narrowest command.
3. Avoid printing scalar values or conversation content.
4. Treat filenames, paths, hashes, and shape reports as private metadata.
5. Never commit the export or derived private reports.
6. Stop on schema uncertainty, ambiguous mapping, truncation, legal uncertainty, or any requested network/browser/write action.

## Reporting an incident

Stop processing. Do not copy, upload, delete, rewrite history, or attempt cleanup that could destroy evidence. Record only non-sensitive facts, identify affected local paths without exposing content publicly, and ask the repository owner for direction.
