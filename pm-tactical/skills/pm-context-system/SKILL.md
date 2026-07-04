---
name: pm-context-system
description: Use this skill proactively during any session — observe the conversation, and the moment a decision is made or context worth keeping surfaces, propose a one-line log entry rather than interviewing the user up front. Use this skill when the user makes an explicit request too — wanting Claude to remember their work across sessions, set up persistent project context, or complaining that Claude starts from zero every time — phrasings like "set up my context system", "make Claude remember my stakeholders", "you keep forgetting my project", "set up project memory", "initialize my PM workspace". Scaffolds a four-file context structure (INDEX, STAKEHOLDERS, DECISIONS, STATE) silently on first approved log entry, with a session-start read order and maintenance rules for merging, pruning, and flagging stale entries. Do NOT use for one-off summaries, for auditing an existing CLAUDE.md (context-auditor's job), or for conversation-level memory questions.
---

# PM Context System

A maintained memory structure, not a filing cabinet. Observe the session, propose what's worth keeping in one line, scaffold silently on first yes, then a read order and pruning rules so project knowledge compounds instead of rotting.

## Step 1 — Observe and propose (no interview)

Don't front-load an interview. Instead, watch the session as it unfolds. The moment a decision gets made, a stakeholder fact surfaces, or project state changes in a way worth remembering, propose exactly one line:

```
Log to memory: "<decision or fact + why>" — yes/edit/skip
```

- yes → write it (scaffolding `context/` silently first if it doesn't exist yet — see Step 2).
- edit → take the user's correction, then write.
- skip → drop it, don't ask again about that same fact.

Never write anything without one of these three responses. Never interview the user with a batch of questions — one proposal at a time, tied to something that actually just happened.

## Step 2 — Scaffold (silent, triggered by first yes)

If `context/` doesn't exist in the project root yet, create it silently the first time a proposal is approved — no announcement, no empty templates shown up front:

```
context/
├── INDEX.md         ← read-order rules + one-line summary of each file
├── STAKEHOLDERS.md  ← per person: role, what they care about, communication style, last interaction
├── DECISIONS.md     ← append-only: date, decision, why, alternatives rejected
└── STATE.md         ← current project status: active work, blockers, next milestones
```

Write the approved entry into whichever file it belongs in. Add a pointer in the project's CLAUDE.md: "At session start, read context/INDEX.md first."

## Step 3 — Session-start read order

1. INDEX.md (cheap, routes everything)
2. STATE.md (what's live right now)
3. STAKEHOLDERS.md / DECISIONS.md only when the task touches a person or reopens a past decision — progressive disclosure, don't bulk-load.

## Step 4 — Session-end catch-all sweep

Real-time proposals (Step 1) cover most of what's worth logging as it happens. Before the session ends (or when the user says "update context"), do one final sweep for anything not already proposed and answered — propose it the same one-line way, never silently write:
- STATE.md: what changed, what's newly blocked/unblocked
- DECISIONS.md: any decision made this session not already logged (date + why + rejected alternatives)
- STAKEHOLDERS.md: only if new information about a person surfaced and wasn't already logged
User approves each, then write.

## Step 5 — Maintenance rules (run when files are touched)

- MERGE: two entries about the same thing → combine, keep the newer framing.
- PRUNE: STATE items untouched for 30+ days → move to an "archive" section, flag to user.
- STALENESS: any entry contradicted by newer information → flag `[STALE?]`, ask, never silently delete.
- SPLIT: any file over ~200 lines → propose splitting by theme, update INDEX.
- DECISIONS.md is append-only: corrections are new entries referencing the old, never edits.

## Limitations

- Files persist per project; a session must actually read them — the CLAUDE.md pointer makes this reliable in Claude Code, but nothing auto-syncs across machines except via git.
- Quality depends on the update ritual actually running; skipped sessions create gaps, not errors.
- STAKEHOLDERS.md holds professional context only — no sensitive personal data; the skill refuses entries about health, private life, or anything a stakeholder wouldn't expect written down.
