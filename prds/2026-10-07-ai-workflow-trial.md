# PRD: AI Workflow Trial Kit

**Date:** 2026-10-07
**Status:** Approved for local implementation by the October 6 task handoff

## Problem

A faster AI draft can hide review, recovery, follow-up or worse outcomes. PMs
need a reusable way to freeze a small trial and account for every assigned task
without deleting failed work or presenting a descriptive ratio as a causal result.

## User

An AI PM planning a bounded workflow trial; current alternative is a spreadsheet
that can silently drop unfinished tasks or confuse draft time with human effort.

## Success metric

The 32-task fictional demo reproducibly freezes balanced assignments, reports
both unfavorable and favorable cases from the same assignments, refuses a data
gap, and passes deterministic tests and independent review before delivery.

## Scope (v1)

- Stdlib Python plan/audit CLI and a new skill within existing pm-tactical.
- Fixed parallel unit design, frozen eligibility/strata, seed and input hashes.
- All assigned rows, common horizon, explicit measured/omitted effort scope,
  success denominators, status/deviation counts and outcomes per measured hour.
- Transparent synthetic CSVs, ordinary tests, UAT and a real cloud Linux PTY
  demo rendered at 1.5x with reading pauses, 35–55 seconds final.

## Out of scope (cut from v1)

- Significance tests, p-values, causal-validity badges, ROI and ship/kill verdicts.
- Cluster, adaptive, crossover or known/unknown interference designs.
- Account access, model/provider calls, telemetry and hosted UI.
- Push, PR creation, merge, deployment and publication.

## Non-goals (failure modes)

- Calling declarations or hashes proof of validity or honest measurement.
- Excluding unfinished/crossover work, filling missing effort with zero, hiding
  success counts when a ratio improves, or calling measured scope all work.
- Fabricating live AI output, Mac footage or measured productivity evidence.

## Decisions log

- Integrate into pm-tactical because this is workflow measurement; pm-verifier
  remains the separate product for calibrated model/evaluation release gates.
- Support one narrow even-stratum design; other designs require external review.
- Retain original assignment and observed effort through one fixed horizon.
- Use versioned SHA-256 ranking for reproducible within-stratum assignments;
  the declared seed and manifests do not establish pre-registration or validity.
- Use explicit measured-scope and omission declarations. Person-time is allocated
  once per person across tasks/stages; elapsed model waiting is not automatically labor.
