# loop-designer

**Any recurring task → a guarded autonomous loop, in one pass.**

One skill that takes "summarize new GitHub issues every morning" and hands back a complete loop package: a five-part spec, five non-negotiable guardrails, and two ready-to-paste runners (Claude Code Routine or local cron). The architecture isn't invented — it's generalized from a production daily-radar loop that fires on a live schedule, plus the locked-checklist discipline of [pm-tactical](../pm-tactical/)'s prompt-optimizer-loop.

Fourth plugin in the [ai-pm-skills](../) marketplace.

## The problem

Everyone's first autonomous loop fails the same four ways: it re-processes the same items every run (no cross-run memory), it grows without bound (no caps), it breaks silently at 7am (no notification), or it ships garbage confidently (the prompt that did the work also graded the work). loop-designer makes those failure modes structurally impossible to omit.

## Install (30 seconds)

```bash
claude plugin marketplace add Abhillashjadhav/AI-PM-essential-skills
claude plugin install loop-designer@ai-pm-skills
```

## Use (60 seconds)

```
Summarize new GitHub issues in acme/support-widget every morning — turn this into a loop.
```

Also fires on: "run this on a schedule", "automate this daily", "build me a loop", "make this recurring", "design a loop for…", "loop this task". Two neighbors it routes away from: "improve this prompt" is prompt-optimizer-loop's job, and "run X every 10 minutes right now" is Claude Code's built-in `/loop` command — loop-designer *designs* durable guarded loops for Routines/cron; it doesn't run anything.

After a minimal interview (goal, inputs, destination, schedule — one message), you get:

1. **Loop spec** — Discover → Plan (dedup first) → Execute → **Verify** → Stop-or-Repeat, every part explicit. Verify is a separate checklist pass over the produced artifact — the executor never grades its own work.
2. **Guardrails block** — always all five: max-iterations cap, cost ceiling, seen-log file for cross-run dedup (runs are stateless; state lives in files), no-destructive-actions allowlist, and a notification line on completion *and* on any trip. Non-negotiable — asking to skip one gets you the failure story it prevents, and the guardrail.
3. **Two runners, pick one** — a complete Claude Code Routine prompt for cloud scheduled runs, and a local cron/launchd variant with the same prompt body.

A full worked example (request → interview → complete package) ships in `skills/loop-designer/examples/`.

## Design stance

- **Verification first.** No verifiable success condition → the skill helps define one before generating anything. An unverifiable loop is an unattended failure generator.
- **Honest empty runs.** A run that finds nothing new says "nothing new" in one line and exits. Padding is a verify failure.
- **State lives in files.** Every scheduled run starts stateless. The seen-log contract (read before acting, append after verify passes) is what separates a loop from an amnesia machine.

Full reasoning in `skills/loop-designer/references/loop-anatomy.md` and `references/guardrail-design.md`.

## Testing

Three-gate harness, same convention as the other plugins (`tests/loop-designer/fixtures.md`): manifest/lint clean; trigger fire/no-fire (including "improve this prompt" routing away); end-to-end known-answer — the sample request must produce all three artifacts with all five guardrails present and a verifier distinct from the executor.

## License

MIT, same as the repo.

---

*Built by [Abhillash Jadhav](https://github.com/Abhillashjadhav) — GenAI PM. Evals, context engineering, agentic reliability.*
