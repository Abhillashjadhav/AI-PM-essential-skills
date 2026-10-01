# PRD: Model Router

**Date:** 2026-09-25
**Status:** Approved by the owner (requirements supplied in the implementation prompt; no interview repeated)
**Source prompt:** [model-router/docs/implementation-prompt.md](../model-router/docs/implementation-prompt.md)

## Problem
The owner picks models by hand and usually defaults to the strongest, newest one. That's quick, but it spends included subscription usage on work a less demanding model could finish. The router should choose a suitable model automatically, keep one conversation on one model, and save the strongest reasoning for work where it matters.

This is a workflow and quality product, not an API billing optimiser. Using usage included in an existing subscription is fine. **Additional spend must be ₹0.**

## User
The primary user is Abhillash, who works in ChatGPT in the browser, sometimes in Codex, and in the Mac terminal for engineering. Today he picks the model by hand for every chat. Later, other people should be able to fork the public repository, use their own accounts, and contribute through issues and PRs.

## Success metric
- **North-star guardrail:** the owner changes the model in no more than 5 of every 100 eligible chat threads, measured weekly by thread-start cohort, with the real sample size shown.
- Routing finishes in under 1 second in most cases, stays within 2 seconds where possible, and falls back to manual model selection at 4 seconds.
- There are no silent model changes inside a thread, no lost architecture handoffs, and no duplicate model work after a crash.
- Wrong answers, unfinished tasks, and overrides show up in evaluation records.
- The owner's evaluation work fits within 30 minutes a week.
- **Release condition:** zero added spend. A simulator, or a live adapter that is permanently blocked, is development output, not a finished live product.

## Scope (v1)
- A local terminal client (`python3 model-router/router.py`) that takes a prompt, shows a short explanation of the model choice, and streams the answer in the same session.
- An automatic first model choice based on the task, its consequences, the explicit owner priority, and relevant project context.
- A persistent model choice per thread, with human override.
- An automatic handoff from architecture to implementation: a new thread in the same router project, carrying a complete, versioned handoff package.
- A subscription-capacity check when the implementation thread is created, with the narrow conditional downgrade (TIGHT + CLEAR_AND_SIMPLE + LOW_RISK + an approved, capable lowest model).
- Text prompts, local TXT/MD/DOCX/text-PDF attachments, collection of specified public web resources, and scoped coding-project work.
- Queueing, checkpointing, restart recovery, visible errors, and protection against duplicate sends.
- Model discovery, approved role mappings, evaluation comparisons, and human approval of new mappings.
- Durable local history and evaluation records, with CLI, Markdown, and JSON reports.
- A synthetic demo and an offline test suite that need no account and make no model call.

## Out of scope (cut from v1)
- An evaluation dashboard UI, native desktop UI, mobile UI, or a new browser chat UI.
- Automatic promotion of new models, and automatic rollback of pinned conversations.
- A mandatory local inference model or a hosted routing classifier.
- Paid APIs, paid hosting, fallback to purchased credits, and automatic purchases or resets.
- Assumed access to all ChatGPT history, native ChatGPT Projects, memory, connectors, or attachments.
- Public telemetry or central collection of users' conversations.
- Controlling the ChatGPT browser or the Codex desktop app. Automatic routing works through the terminal client only.

## Non-goals (failure modes)
- **Silent spend:** a model turn starts while the spend boundary is UNKNOWN, or it relies on purchased credits.
- **Silent switch:** a thread's model changes because usage, the registry, or the wording changed.
- **Lost or lossy handoff:** the architecture is summarised away, attached to the wrong repository, or duplicated.
- **False confidence:** a made-up confidence score, a claimed 95% accuracy, or a fabricated capacity balance.
- **Blind resend:** a crashed dispatch is sent again without reconciliation.

## Unresolved provider capabilities (UNKNOWN, not product approvals)
| Capability | Status |
|---|---|
| Enforceable included-only execution (no purchased-credit consumption) on the Codex App Server path | UNKNOWN. No documented control found; live dispatch stays blocked. |
| Models, reasoning settings, and usage buckets visible to the owner's account | UNKNOWN until `doctor` runs on the owner's Mac |
| Per-turn provider attestation of the model used | UNKNOWN. Only `model/rerouted` is documented. |
| Reliable reconciliation after a lost `turn/start` acknowledgement | UNKNOWN. `clientUserMessageId` is in the schema, but its echo semantics aren't verified. |
| Supported integration with ChatGPT in the browser or the Codex desktop app | UNSUPPORTED in V1. None has been proven. |
| Mac memory and latency under real use | UNKNOWN until the local pilot |

## Decisions log
- 2026-09-25: Retired the 80/20 priority-and-usage formula. The only automatic usage-driven coding downgrade is the implementation-thread exception. Source: owner.
- 2026-09-25: The local terminal is the permitted V1 interface. There's no browser UI and no dashboard UI in V1. Source: owner.
- 2026-09-25: Role floors come from the task's consequences (architecture, high-credibility writing, and money, privacy, or security coding → highest). Source: owner.
- 2026-09-25: The model is pinned per thread, with human override and an optional reason (unknown when left blank). Source: owner.
- 2026-09-25: New models need human approval, bound to the exact model, settings, and evaluation version. There's no automatic promotion. Source: owner.
- 2026-09-25: The routing timeout is 4 seconds, after which manual model selection takes over, with late callbacks fenced off. Source: owner.
- 2026-09-25: Local records are kept indefinitely. A dashboard UI comes later. Source: owner.
- 2026-09-25: Technical choices (recorded in `model-router/docs/decisions.md`): Python 3.11 standard library, SQLite, and Codex App Server over stdio. The coordinator runs in-process, with a SQLite lease for cross-process safety.
