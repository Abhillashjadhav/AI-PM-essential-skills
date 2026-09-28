# Worked loop template — daily GitHub issue triage

Manual expected output for `sample-request.md`; no scheduler or durable-state
implementation ships with this example. Review cases are in
`tests/loop-designer/fixtures.md`.

## 1. Loop spec

```text
LOOP SPEC: daily-issue-triage (acme/support-widget)
PREFLIGHT — require a host-enforced single-run lock for this repository.
            If the host cannot enforce it, stop BLOCKED. Under the lock, find
            open triage PRs, including drafts. If one is pending, return
            WAITING_FOR_MERGE with its link; create no new branch or PR.
DISCOVER  — list every open issue, with pagination. Exclude PRs. Read the
            processed issue IDs from triage/seen-log.md on main. An absent log
            on the first run means no processed IDs; an unreadable or malformed
            log is BLOCKED. Do not use run dates as discovery cutoffs.
PLAN      — deduplicate by issue ID against the log. Order survivors by
            (created_at, issue number). Select the oldest 25; count the rest
            as deferred. If discovery is incomplete, report BLOCKED, not EMPTY.
EXECUTE   — use a host-supplied run ID and branch triage/daily-<run-id>.
            Write triage/<run-id>.md with each selected issue's number, title,
            link, one-line source-backed summary and existing suggested label.
            Prepare a seen-log append for the same IDs in this branch, recording
            issue created_at separately from processed_at. These are proposed
            records; they become canonical only when the PR is merged.
VERIFY    — inspect the prepared changes before opening a PR:
            [ ] issue IDs exactly match PLAN; no duplicates or unselected IDs
            [ ] each entry has the required fields and source-backed summary
            [ ] each suggested label exists in the repository
            [ ] seen-log changes append exactly the selected IDs
            [ ] no ID was already in main's pre-run log
            Any failure: report FAILED with the branch/artifact location;
            open no PR and leave main's log unchanged.
PUBLISH   — open one PR to main only after VERIFY passes. If the API result is
            uncertain, look up the same branch's PR before retrying; never open
            a second PR. Unknown state remains BLOCKED for owner inspection.
STOP      — READY_FOR_REVIEW with PR link and deferred count; EMPTY if complete
            discovery found no survivors; WAITING_FOR_MERGE for an existing PR;
            FAILED/BLOCKED for any incomplete action. Always emit a run result.
            Release the host lock on exit. Never merge the PR automatically.
```

A checklist pass by the same model is self-review. Independent adjudication
requires a separately configured reviewer or deterministic checks.

## 2. Guardrails

1. **Work cap:** 25 issues per run. Overflow remains eligible because the next
   run scans all open issues and excludes only committed processed IDs.
2. **Budget:** one complete discovery, one branch and one PR; at most two
   retries per API operation and a 15-minute proposed run limit. Prompt text
   does not meter tokens or enforce timeouts; the host must enforce its budget.
3. **State:** `triage/seen-log.md` on main is canonical. Include the proposed
   append in the verified PR. A pending PR pauses later runs; a closed unmerged
   PR leaves its IDs eligible. A timestamp is audit data, not a cursor.
4. **Action scope:** create the run branch, add its triage artifact, append its
   proposed log entries and open one PR. Do not edit issues, comment on issues,
   close existing PRs or push to main. Preserve failed artifacts for inspection.
5. **Notification:** print a structured final status, artifact/PR link and
   deferred count to the scheduler's run output. No additional message channel
   is assumed. The owner must confirm that failed run output is visible.

## 3a. Scheduled prompt

Use the complete spec and guardrails above as the scheduled prompt. Include the
repository, host lock mechanism, run ID, budget enforcement and run-output
location in the scheduler configuration. Do not enable the schedule while any
of those host requirements is unresolved. The prompt does not install them.

## 3b. Local cron variant

Save the full prompt as `~/.claude/loops/daily-issue-triage.md`. An example daily
schedule, after host locking and timeout handling are configured:

```bash
0 7 * * * cd ~/code/support-widget && claude -p "$(cat ~/.claude/loops/daily-issue-triage.md)" >> ~/.claude/loops/daily-issue-triage.log 2>&1
```

The cron line alone provides neither locking nor budget enforcement. On macOS,
use the same prompt with a launchd job and the same host prerequisites.
Pick one scheduler. Verify failure visibility and crash recovery before using
real repository writes; this document is a template, not a deployed runner.
