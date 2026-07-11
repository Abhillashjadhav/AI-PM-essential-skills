# ContextPort handoff

This handoff follows completion of Phase 14 implementation. Finish PR #22, then begin only the Phase 15 release-readiness audit when the roadmap resumes.

## Resume command

After confirming PR #22 is merged:

```sh
cd ~/code/AI-PM-essential-skills
git switch main
git pull --ff-only origin main
git status
```

Do not revisit or rewrite Phase 2, Phase 3, old restacks, rebases, or safety branches.

## Next Codex prompt

```text
Resume ContextPort from context-port/STATE.md and context-port/HANDOFF.md.

Verify main and confirm PR #22 is merged first. Do not touch historical Phase 2/3 branches.
Start Phase 15 only: perform a requirement-by-requirement release-readiness audit over the public standalone product. Verify tests, schemas, packaging/install artifacts, synthetic demo, docs, privacy gates, authorship, and clean public scope. Produce a saved prompt, auditable readiness report, tests/evaluation, and one independently reviewed PR. Do not select a license, publish a release, access a real export, automate a browser, or write to an assistant. Stop with explicit human decisions for licensing, publication, real Claude ZIP access, and any browser/assistant write.
```

## Real Claude ZIP gate

Do not locate, open, hash, list, extract, inspect, parse, copy, upload, or otherwise access a real Claude ZIP without fresh explicit human approval. After approval, keep it outside version control, inspect locally, emit no content values during structural inspection, and stop for any ambiguous mapping or privacy/legal uncertainty.

## Browser and assistant-write gate

Do not launch browser automation and do not write to ChatGPT or Claude without separate fresh explicit approval. API credentials, cookies, sessions, exports, and private derived reports must not enter commits, fixtures, logs, or network services.

## What is ready

The synthetic migration MVP is complete through Phase 14: validated neutral data, segregation, review, approved dry-run planning, independent reconciliation, incremental change planning, fail-closed destination capability assessment, CLI, package artifacts, local installer, revision-bound synthetic demonstration, and consolidated public operator/privacy documentation.

This does not prove real-export compatibility or live destination reconstruction. Those claims remain `UNKNOWN` and `UNSUPPORTED`, respectively.

## Remaining work

1. Phase 15 release-readiness audit.
2. Human decisions before any release: repository license and publication approval.
3. Fresh approval before real Claude ZIP access.
4. Fresh approval before browser automation or assistant writes.

The authoritative detailed snapshot, PR list, checks, gates, and unsupported inventory is in `STATE.md`.
