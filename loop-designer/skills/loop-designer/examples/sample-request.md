# Sample request

> "Summarize new GitHub issues every morning — turn this into a loop.
> Repo is acme/support-widget. Post the summary as a markdown file in
> triage/ in that repo. Around 7am my time is fine."

What the interview still needed (goal was underspecified — Step 0):

- **Verifiable success condition** (agreed with user): a file
  `triage/YYYY-MM-DD.md` exists containing one entry per new issue, each with
  number, title, one-line summary, suggested label, and a link — or the
  honest empty line if no new issues.
- **Sources**: `acme/support-widget` open issues, created since the last run.
- **Destination**: `triage/YYYY-MM-DD.md` on a `triage/daily` branch, PR'd to main.
- **Schedule**: daily 07:00 local (`0 7 * * *`).

The generated package for this request is in `sample-loop-package.md`.
