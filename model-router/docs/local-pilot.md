# Continue on your Mac (one handoff)

The cloud build environment has done everything that doesn't need your Mac or your ChatGPT account. The rest runs on your Mac. Open **Claude Code in your local clone** of this repository and paste the prompt below. That is the whole handoff.

```text
Continue the model-router task in this repo on branch claude/intelligent-johnson-rhr02b
(stacked draft PRs #68 → #69 → #70; do not merge, keep the stack).

1. git fetch origin && git checkout claude/intelligent-johnson-rhr02b && git pull --ff-only
2. Run: python3 -m unittest discover -s model-router/tests -q   (must pass on macOS)
3. Run: python3 model-router/router.py setup
   It pins my installed Codex CLI, validates the router's own ChatGPT-only profile,
   opens Codex's ChatGPT sign-in if needed (I will complete it in the browser — never ask
   me to paste credentials), discovers my account's models, and asks me to approve one
   model per role. Relay each approval question to me; do not answer them yourself.
4. If setup reports the spend boundary VERIFIED, run: python3 model-router/router.py pilot
   and then python3 model-router/tools/measure_latency.py 200 20 for Mac latency.
   If it reports BLOCKED, do not run the pilot and do not try to work around it.
5. Save content-free evidence under model-router/docs/evidence/ (setup report, doctor --json,
   pilot report if run, latency), update model-router/docs/capability-evidence.md with what was
   verified on this Mac, commit, push to the same branch, and update the PR descriptions.
6. Report: what I can use now, what was verified with real models, and at most one next action.
```

## What each step needs from you

| Step | Your part |
|---|---|
| Sign-in | Codex's normal browser login, if the router's profile isn't signed in yet |
| Model approvals | Pick a model for each of highest, middle and lowest from your account's list (Astra/Sol/Luna candidates are shown first) |
| Spend boundary | Nothing to click. It is read from OpenAI's live signals. On a personal plan it stays BLOCKED (see [capability-evidence.md](capability-evidence.md)) |

## What the pilot covers when it can run

At most 8 real turns:

1. A normal answer (lowest role).
2. An architecture chat (highest) → "Approved, implement this" → an implementation chat in the same project (middle), in a scratch git repo inside the router's data folder.
3. A human model override on the first chat.
4. A restart before a queued job, followed by automatic resume on the same pinned model.

It doesn't deliberately use up your usage; limit behaviour is covered by the simulator tests. Usage is read before and after as rounded, shared percentages, not as cost.

## Everyday use after setup

```bash
python3 model-router/router.py chat --project <name>     # auto-resume runs while this is open
python3 model-router/router.py serve                     # optional: keep queued work moving in one window
python3 model-router/router.py eval report               # weekly review (~30 minutes)
```

Nothing runs while the router is closed or the Mac is asleep. After a wake, the router reconciles uncertain sends before continuing.
