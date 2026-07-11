# Phase 15 evaluation: generated session memory and release readiness

## Expected classification

- Synthetic migration MVP: `ready` when every automated gate passes.
- Public release: `blocked_human_decisions` until a license is selected and publication is explicitly approved.
- Real Claude ZIP compatibility: `UNKNOWN` until separately approved inspection.
- Consumer ChatGPT reconstruction writes: `UNSUPPORTED`.

## Evidence requirements

- `SESSION.md` and `SESSION.json` regenerate deterministically and pass `handoff --check`.
- Repository state changes update generated session content.
- Full tests, syntax, schema, packaging, synthetic demo, scope, authorship, privacy, and dependency gates pass.
- Release artifacts are reproducible but are not published.
- Final reports enumerate every failed automated check and human blocker.
