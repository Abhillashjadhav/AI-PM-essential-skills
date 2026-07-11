# ContextPort handoff

This handoff follows completion of Phase 13 implementation. Finish the current PR lifecycle, then pause before starting Phase 14 unless a human explicitly resumes the roadmap.

## Resume command

After confirming PR #21 is merged:

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

Verify main and PR #21 first. Do not touch historical Phase 2/3 branches.
Start Phase 14 only: consolidate public documentation, operator guidance, navigation, capability/status labels, privacy boundaries, and synthetic-demo instructions. Keep ContextPort standalone under context-port/, add no production dependency, access no real export, and perform no browser or assistant write. Follow one saved prompt, one feature branch, tests/evaluation, one independently reviewed PR, and stop at any explicit gate.
```

## Real Claude ZIP gate

Do not locate, open, hash, list, extract, inspect, parse, copy, upload, or otherwise access a real Claude ZIP without fresh explicit human approval. After approval, keep it outside version control, inspect locally, emit no content values during structural inspection, and stop for any ambiguous mapping or privacy/legal uncertainty.

## Browser and assistant-write gate

Do not launch browser automation and do not write to ChatGPT or Claude without separate fresh explicit approval. API credentials, cookies, sessions, exports, and private derived reports must not enter commits, fixtures, logs, or network services.

## What is ready

The synthetic migration MVP is complete through Phase 13: validated neutral data, segregation, review, approved dry-run planning, independent reconciliation, incremental change planning, fail-closed destination capability assessment, CLI, package artifacts, local installer, and a revision-bound synthetic demonstration.

This does not prove real-export compatibility or live destination reconstruction. Those claims remain `UNKNOWN` and `UNSUPPORTED`, respectively.

## Remaining work

1. Phase 14 documentation consolidation.
2. Phase 15 release-readiness audit.
3. Human decisions before any release: repository license and publication approval.
4. Fresh approval before real Claude ZIP access.
5. Fresh approval before browser automation or assistant writes.

The authoritative detailed snapshot, PR list, checks, gates, and unsupported inventory is in `STATE.md`.
