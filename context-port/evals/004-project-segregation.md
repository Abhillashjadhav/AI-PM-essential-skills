# Phase 4 project segregation evaluation

## Revision

- Branch: `context-port/004-project-segregation`
- Evaluated implementation commit: `3f091f6b9da60d8d67a393afe91510dc42d02d34`

## Input classification

- **VERIFIED synthetic:** `fixtures/segregation-contextpack.json`.
- **VERIFIED synthetic:** valid and ambiguous project mapping fixtures.
- No real export, private conversation, credential, browser, network service, or destination system was accessed.

## Gates

1. Duplicate project and conversation titles remain separate by stable ID.
2. Ungrouped conversations remain explicit and are not merged into a project.
3. Every conversation appears exactly once.
4. Message membership never crosses conversations or projects.
5. Equivalent inputs produce an identical plan and digest.
6. The plan emits message IDs and counts but no message content.
7. Multiple destination mappings for one project emit only `decision_required`.
8. Unknown source projects and invalid ContextPacks fail closed.
9. CLI ready and decision-required paths have distinct exit codes.
10. Public schema and engine versions agree.

## Completed evidence

`python3 .github/scripts/pr_required_checks.py --base main --head HEAD --head-ref context-port/004-project-segregation`

- Result: **VERIFIED PASS**
- Infrastructure tests: 4 passed.
- ContextPort tests: 21 passed.
- Compilation: 3 changed Python paths passed.
- Git diff check: passed.
- Privacy check: passed.
- Existing-skill impact: none.

`python3 context-port/contextport.py segregate context-port/fixtures/segregation-contextpack.json --mappings context-port/fixtures/project-mappings-valid.json`

- Result: **VERIFIED PASS**, exit 0.
- Project groups: 2.
- Ungrouped groups: 1.
- Conversations: 3.
- Messages: 3.
- Content emitted: false.
- Plan SHA-256: `5561ccdec52ab9bad51cc14b96289a0ee65ae6ac9749fdc9bd23e073b4a44825`.

Ambiguous mapping fixture:

- Result: **VERIFIED decision gate**, exit 3.
- Plan emitted: false.
- Conflicting destinations were sorted and reported without resolution.

## Repair history

No failed Phase 4 gate or repair attempt.

## Limitations

- **UNSUPPORTED:** real-export parsing or compatibility claims.
- **UNSUPPORTED:** human approval interface, reconstruction, destination writes, and synchronization.
- **INFERRED:** a content-free plan reduces disclosure risk; project and conversation titles remain metadata and may still be sensitive on private inputs.
- **UNKNOWN:** real source project-link semantics until approved inspection.
