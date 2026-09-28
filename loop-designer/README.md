# loop-designer

**Any recurring task → a guarded autonomous loop, in one pass.**

One skill that takes "summarize new GitHub issues every morning" and hands back a complete loop package: a five-part spec, five non-negotiable guardrails, and two ready-to-paste runners (Claude Code Routine or local cron). The architecture isn't invented — it's generalized from a production daily-radar loop that fires on a live schedule, plus the locked-checklist discipline of [pm-tactical](../pm-tactical/)'s prompt-optimizer-loop.

Fourth plugin in the [ai-pm-skills](../) marketplace.

## The problem

Recurring jobs can repeat work, lose backlog, exceed their budget or fail without
notification. This skill asks for explicit handling of those cases. Enforcement
still belongs to the scheduler, runtime and configured permissions.

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

1. **Loop spec** — Discover → Plan (dedup first) → Execute → **Verify** → Stop-or-Repeat, every part explicit. Verify is a separate checklist pass over the produced artifact. In a single-model run this is self-review; independence requires a separate reviewer or deterministic checks.
2. **Guardrails block** — always all five: max-iterations cap, cost ceiling, seen-log file for cross-run dedup (runs are stateless; state lives in files), no-destructive-actions allowlist, and a notification line on completion *and* on any trip. Non-negotiable — asking to skip one gets you the failure story it prevents, and the guardrail.
3. **Two runners, pick one** — a complete Claude Code Routine prompt for cloud scheduled runs, and a local cron/launchd variant with the same prompt body.

A full worked example (request → interview → complete package) ships in `skills/loop-designer/examples/`.

## Design stance

- **Verification first.** No verifiable success condition → the skill helps define one before generating anything. An unverifiable loop cannot establish whether a run succeeded.
- **Honest empty runs.** A run that finds nothing new says "nothing new" in one line and exits. Padding is a verify failure.
- **State lives in files.** Every scheduled run starts stateless. Define where verified progress becomes durable and how pending work survives a crash or a run cap.

Full reasoning in `skills/loop-designer/references/loop-anatomy.md` and `references/guardrail-design.md`.

## Testing

Manual review cases in `tests/loop-designer/fixtures.md` cover triggering,
artifact shape and failure scenarios. Metadata and manifest checks are automated;
no command executes the skill against those prompts. The worked sample pauses
while a triage PR is pending, verifies before opening a PR, and retains overflow
without a run-date cursor. Its host lock and budget are requirements to implement,
not runtime capabilities supplied by this plugin.

## License

MIT, same as the repo.

---

*Built by [Abhillash Jadhav](https://github.com/Abhillashjadhav) — GenAI PM. Evals, context engineering, agentic reliability.*
