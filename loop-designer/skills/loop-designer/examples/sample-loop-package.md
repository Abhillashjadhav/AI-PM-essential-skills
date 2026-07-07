# Generated loop package — daily GitHub issue triage

Known-answer output for `sample-request.md`. Used as the Gate 3 fixture in
`tests/loop-designer/fixtures.md`.

---

## 1. Loop spec

```
LOOP SPEC: daily-issue-triage (acme/support-widget)
DISCOVER  — open issues in acme/support-widget created since the timestamp in
            triage/seen-log.md (fallback: last 24h on first run). Issues only —
            not PRs, not comments.
PLAN      — dedup FIRST: read triage/seen-log.md (create if missing), drop any
            issue number already logged. Then select all survivors up to the
            iteration cap, oldest first (no ranking needed — triage wants
            completeness, not curation).
EXECUTE   — write triage/YYYY-MM-DD.md on branch triage/daily with one entry
            per issue, exactly these fields:
            - Issue: #<number> <title> (<link>)
            - Summary: <one line, from the issue body — no speculation>
            - Suggested label: <one of the repo's existing labels>
            Then open a PR from triage/daily to main titled
            "Daily triage YYYY-MM-DD — N new issues".
VERIFY    — separate checklist pass over the produced file (not the executor
            re-reading its own reasoning — inspect the artifact):
            [ ] triage/YYYY-MM-DD.md exists on the branch
            [ ] entry count == survivor count from PLAN (no drops, no padding)
            [ ] every entry has all 3 fields and a working issue link
            [ ] every suggested label exists in the repo's label list
            [ ] no entry's issue number appears in the pre-run seen-log
            Any unchecked box → run FAILED → notify (guardrail 5), do not
            merge, do not update the seen-log for unverified entries.
STOP-OR-REPEAT — stop when: all survivors processed and verified (append them
            to seen-log, notify success) | zero new issues (write the one-line
            honest entry "No new issues since last run" in the notification,
            skip the file, stop) | iteration cap or cost ceiling hit (process
            none beyond the cap; report what was left).
```

## 2. Guardrails block

```
GUARDRAILS (non-negotiable)
1. MAX ITERATIONS: 25 issues per run; if more are new, triage the oldest 25,
   list the remainder count in the notification, stop.
2. COST CEILING: one discovery pass + one file + one PR per run; no retries
   beyond 2 per API call; if the run exceeds ~15 minutes or approaches its
   token budget, stop and report progress.
3. SEEN-LOG: cross-run memory lives in triage/seen-log.md (append-only lines:
   "<issue-number> <ISO-date>"). Read before acting, create if missing, append
   after VERIFY passes — never before.
4. NO DESTRUCTIVE ACTIONS: allowlist = create files under triage/, create
   branch triage/daily, open PRs to main. Never delete or edit issues, never
   close anything, never push to main directly, never email anyone.
5. NOTIFY: end every run with one line in the PR body (or as a repo issue
   comment if no PR was made): "TRIAGE OK — N issues" | "TRIAGE EMPTY — no new
   issues" | "TRIAGE FAILED — <which check/guardrail> — <what was preserved>".
   Never end silently.
```

## 3a. Artifact — Claude Code Routine prompt (cloud scheduled)

> Register with cron `0 7 * * *` in the repo's environment.

```
You are the daily issue-triage loop for acme/support-widget. Each run is
stateless — follow every step; all memory lives in files.

DISCOVER: list open issues created since the newest timestamp in
triage/seen-log.md (first run: last 24 hours). Issues only.
PLAN: read triage/seen-log.md (create if missing). Drop any issue number
already logged. Take up to 25 survivors, oldest first.
EXECUTE: write triage/YYYY-MM-DD.md on branch triage/daily — per issue exactly:
"Issue: #<number> <title> (<link>)", "Summary: <one line from the issue body,
no speculation>", "Suggested label: <an existing repo label>". Open a PR to
main titled "Daily triage YYYY-MM-DD — N new issues".
VERIFY (separate pass — inspect the file you produced, checklist, all boxes
required): file exists on branch; entry count equals survivor count; every
entry has all 3 fields and a working link; every label exists in the repo;
no entry is in the pre-run seen-log. Any failure → report FAILED, do not
update seen-log.
STOP: on verified success append processed issue numbers + date to
triage/seen-log.md. If zero new issues, skip the file and report the empty run.

GUARDRAILS: max 25 issues/run (list remainder count if exceeded). Budget: one
discovery pass, one file, one PR; stop and report if exceeded. Allowlist:
create under triage/, branch triage/daily, PRs to main — never delete, close,
edit issues, or push to main. End EVERY run with exactly one of:
"TRIAGE OK — N issues" | "TRIAGE EMPTY — no new issues" |
"TRIAGE FAILED — <check/guardrail> — <preserved>". Never end silently.
```

## 3b. Artifact — local cron variant

Same prompt body, run by your machine instead of a cloud Routine. Save the
prompt above as `~/.claude/loops/daily-issue-triage.md`, then:

```bash
# crontab -e  (07:00 daily; adjust CLAUDE_BIN and repo path)
0 7 * * * cd ~/code/support-widget && claude -p "$(cat ~/.claude/loops/daily-issue-triage.md)" >> ~/.claude/loops/daily-issue-triage.log 2>&1
```

macOS launchd equivalent (`~/Library/LaunchAgents/com.acme.issue-triage.plist`):
`ProgramArguments = [zsh, -c, "cd ~/code/support-widget && claude -p \"$(cat ~/.claude/loops/daily-issue-triage.md)\""]`,
`StartCalendarInterval = {Hour 7, Minute 0}`.

**Pick ONE runner** (cloud Routine or local cron) — running both
double-processes the seen-log window between firings.
