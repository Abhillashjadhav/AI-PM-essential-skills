# Continue on your Mac (one prompt for Codex)

The cloud build environment has done everything that doesn't need your Mac or your ChatGPT account. The rest must run on your Mac. Open **Codex in your local clone** of this repository and paste the prompt below. That is the whole handoff.

Running this handoff in Codex uses your own Codex allowance. If your account holds purchased credits, Codex itself could draw them after your included usage. That is outside the router's control.

```text
You are continuing the model-router work in this repository on my Mac. Do not restart the design.
Branch: claude/intelligent-johnson-rhr02b (it contains the whole stack: draft PRs #68 -> #69 -> #70).
Do not merge anything into main, do not force-push, and keep the stack.

Hard rules:
- Never ask me to paste a password, token, cookie or API key. Sign-in is Codex's own browser login.
- Do not buy credits, buy a reset, change billing or reload settings, or call any purchase or reset method.
- Do not edit model-router/model_router/spend.py, and do not create files that claim spend enforcement. If the
  spend boundary is not ALLOWED_INCLUDED_ONLY, the live pilot stays blocked. Report that; do not work around it.
- Commands that start the Codex App Server need network access. Ask me to approve running them outside your sandbox.

Steps:
1. git fetch origin && git checkout claude/intelligent-johnson-rhr02b && git pull --ff-only
   Record: git rev-parse HEAD, sw_vers, uname -m, python3 --version (needs 3.11+), codex --version.
2. python3 -m unittest discover -s model-router/tests -q        (must pass on macOS; fix only real macOS issues)
3. python3 model-router/tools/measure_latency.py 200 20         (routing latency on this Mac)
4. python3 model-router/router.py setup
   It pins my installed Codex CLI and validates the router's own ChatGPT-only profile. If needed, it opens Codex's
   browser sign-in for that profile, and I complete it. It discovers my account's models and asks me to approve
   one model per role. Relay every question to me word for word and wait for my answer.
5. /usr/bin/time -l python3 model-router/router.py doctor --json > /tmp/router-doctor.json
   (keep the "maximum resident set size" line: that is peak memory)
6. From setup and doctor, record the spend decision exactly as reported:
   - its status;
   - the "verified:" facts (balance, hasCredits, included usage allowed);
   - the "not satisfied:" items;
   - the missing guarantees.
   On a personal plan this is expected to be UNKNOWN ("no verified included-only mechanism").
7. Only if the spend status is ALLOWED_INCLUDED_ONLY: python3 model-router/router.py pilot
   The pilot sends at most 8 turns: a normal answer, an architecture -> implementation handoff, a manual override,
   and a restart followed by automatic same-model resume. It never runs my other queued work.
   It saves a JSON report with each response, per-turn latency, account signals before and after, and memory.
   If the status is anything else, skip this step and say why.
8. Save evidence with no email, account id or token, under model-router/docs/evidence/:
   - mac-setup-<date>.json (setup report);
   - mac-doctor-<date>.json;
   - mac-latency-<date>.json;
   - the pilot report, if one ran.
   Update the "live account" parts of model-router/docs/capability-evidence.md with what was verified on this Mac.
   Commit to the same branch with a clear message and push (no force).
   If you can edit GitHub PRs, add the new evidence to the descriptions of #68, #69 and #70; otherwise tell me.
9. Report in four groups: implemented; tested offline; tested with real models; blocked (with the exact reason).
   Then give at most one next action for me.
```

## What each step needs from you

| Step | Your part |
|---|---|
| Sign-in | Codex's normal browser login for the router's own profile, if it isn't signed in yet |
| Model approvals | Pick a model for each of highest, middle and lowest from your account's list (Astra/Sol/Luna candidates are shown first) |
| Sandbox approvals | Allow Codex to run `setup`, `doctor` and `pilot` with network access |
| Spend boundary | Nothing to click. It is read from OpenAI's live signals. On a personal plan it is expected to stay UNKNOWN (see [capability-evidence.md](capability-evidence.md)) |

## What the pilot covers when it can run

At most 8 real turns, all inside a scratch project in the router's data folder:

1. A normal answer (lowest role).
2. An architecture chat (highest) → "Approved, implement this" → an implementation chat in the same project (middle).
3. A manual model override on the first chat.
4. A restart before a queued job, then **automatic** resume through the auto-resumer on the same pinned model. The resumer is limited to the pilot's project, and the pilot fails if any other queued job changed state.

The report records each response (first 4,000 characters), per-turn latency, account signals before and after (plan, credits, included-usage flag, spend controls, usage windows), the router's peak memory and the App Server's memory. The pilot doesn't deliberately use up your usage; limit behaviour is covered by the simulator tests.

## Everyday use after setup (once sends are allowed)

```bash
python3 model-router/router.py chat --project <name>     # auto-resume runs while this is open
python3 model-router/router.py serve                     # optional: keep queued work moving in one window
python3 model-router/router.py eval report               # weekly review (~30 minutes)
```

Nothing runs while the router is closed or the Mac is asleep. After a wake, the router reconciles uncertain sends before continuing.
