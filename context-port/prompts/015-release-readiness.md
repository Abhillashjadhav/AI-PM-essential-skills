# Phase 15 prompt: generated session memory and release readiness

## Date

2026-07-11

## Branch

`context-port/015-release-readiness`

## Public task record

Create generated canonical session artifacts (`SESSION.md` and `SESSION.json`) and a `contextport handoff` command before performing the final release-readiness audit. Derive version, phase, branch, merged commit/PR history, open PRs, blockers, tests, coverage status, repository health, resume instructions, approval gates, and unsupported capabilities from observable repository state. Make output deterministic, add stale checking and tests, and require regeneration before every phase PR. Then complete a requirement-by-requirement public release-readiness audit without selecting a license, publishing, accessing real exports, automating a browser, or writing to assistants.

## Status

Complete. All automated synthetic-MVP gates pass. Public release remains blocked by explicit human decisions for licensing and publication; no release was published and no real-data/browser/write gate was crossed.
