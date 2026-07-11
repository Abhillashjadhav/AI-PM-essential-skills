# Safe synthetic export inspection evaluation

## Revision

Branch: `context-port/003-safe-export-inspection`

Evaluated implementation commit: `6b580059cd9e16e7508f27d21e1e52aca3dd9d66`.

## Input classification

- **VERIFIED synthetic:** `fixtures/synthetic-claude-export-shape.json`.
- The fixture uses deliberately synthetic field names and fictional scalar content.
- No real export, account, credential, private conversation, browser, network service, or destination system was accessed.

## Gates

1. The public ContextPack schema parses as JSON and declares the same format/version as the executable validator.
2. Structural inspection emits paths, types, and counts but no scalar values.
3. Schema interpretation remains `UNKNOWN` rather than claiming source compatibility.
4. CLI inspection requires an explicit `synthetic` or `approved-private` classification.
5. The existing ContextPack validation regression suite continues to pass.
6. Public documentation states that filenames and field names can remain sensitive metadata.
7. Inspector paths use escaped, unambiguous object-key segments.

## Completed evidence

`python3 -m unittest discover -s context-port/tests -v`

- Result: **VERIFIED PASS**
- Tests completed: 12
- Failures: 0
- Errors: 0

`python3 context-port/contextport.py validate context-port/fixtures/contextpack-valid.json`

- Result: **VERIFIED PASS**

`python3 context-port/contextport.py inspect context-port/fixtures/synthetic-claude-export-shape.json --classification synthetic`

- Result: **VERIFIED PASS**
- Artifact bytes: 823
- Artifact SHA-256: `48f99ae9f46ff573ae337f8c34ece12411ff4eba282fdfaccae273295c524d3e`
- Report stated `values_emitted: false` and `schema_interpretation: UNKNOWN`.

`python3 -m py_compile context-port/contextport.py context-port/tests/test_contextport.py`

- Result: **VERIFIED PASS**

`git diff --check`

- Result: **VERIFIED PASS**

## Repair history

No failed gate or repair attempt in this phase as of this evaluation.

## Limitations

- **UNSUPPORTED:** real-export compatibility claims or real-export access without approval.
- **UNSUPPORTED:** source-field interpretation, parsing, normalization, project mapping, or reconstruction.
- **VERIFIED:** scalar values are omitted from reports produced by the tested inspector.
- **INFERRED:** field names may contain sensitive metadata even when scalar values are omitted.
- **UNKNOWN:** actual Claude export paths and types until an approved real artifact is inspected.
