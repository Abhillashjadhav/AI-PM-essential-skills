# Infrastructure task: deterministic PR gates with optional external review

## Date

2026-07-11

## Branch

`infra/optional-claude-review`

## Public task record

Repair the pull-request workflow in a separate infrastructure change. Required tests, compilation, diff, privacy, and existing-skill-impact checks must be deterministic, free, and runnable without credentials. External AI review must be labeled optional, run only when its repository secret is available, and skip successfully otherwise. Document private maintainer opt-in without adding or exposing any secret, paid dependency, or private development-system requirement.

## Privacy note

This is a redacted public task record. A private development-system name from the original instruction was intentionally omitted because it is irrelevant to implementation and prohibited from public architecture.

## Status

In progress.
