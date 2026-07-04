---
name: pm-context-system
description: Use this skill when the user wants Claude to remember their work across sessions, set up persistent project context, or complains that Claude starts from zero every time — phrasings like "set up my context system", "make Claude remember my stakeholders", "you keep forgetting my project", "set up project memory", "initialize my PM workspace". Scaffolds a four-file context structure (INDEX, STAKEHOLDERS, DECISIONS, STATE) with a session-start read order and a session-end update ritual, plus maintenance rules for merging, pruning, and flagging stale entries. Do NOT use for one-off summaries, for auditing an existing CLAUDE.md (context-auditor's job), or for conversation-level memory questions.
---

# PM Context System

A maintained memory structure, not a filing cabinet. Four files, a read order, an update ritual, and pruning rules — so project knowledge compounds instead of rotting.

## Step 1 — Scaffold (first run only)

Check whether `context/` exists in the project root. If not, create:

```
context/
├── INDEX.md         ← read-order rules + one-line summary of each file
├── STAKEHOLDERS.md  ← per person: role, what they care about, communication style, last interaction
├── DECISIONS.md     ← append-only: date, decision, why, alternatives rejected
└── STATE.md         ← current project status: active work, blockers, next milestones
```

Populate by interviewing the user briefly (max 5 questions) — never scaffold empty templates and stop. Add a pointer in the project's CLAUDE.md: "At session start, read context/INDEX.md first."

## Step 2 — Session-start read order

1. INDEX.md (cheap, routes everything)
2. STATE.md (what's live right now)
3. STAKEHOLDERS.md / DECISIONS.md only when the task touches a person or reopens a past decision — progressive disclosure, don't bulk-load.

## Step 3 — Session-end update ritual

Before the session ends (or when the user says "update context"), propose — never silently write — a diff:
- STATE.md: what changed, what's newly blocked/unblocked
- DECISIONS.md: any decision made this session (date + why + rejected alternatives)
- STAKEHOLDERS.md: only if new information about a person surfaced
User approves, then write.

## Step 4 — Maintenance rules (run when files are touched)

- MERGE: two entries about the same thing → combine, keep the newer framing.
- PRUNE: STATE items untouched for 30+ days → move to an "archive" section, flag to user.
- STALENESS: any entry contradicted by newer information → flag `[STALE?]`, ask, never silently delete.
- SPLIT: any file over ~200 lines → propose splitting by theme, update INDEX.
- DECISIONS.md is append-only: corrections are new entries referencing the old, never edits.

## Limitations

- Files persist per project; a session must actually read them — the CLAUDE.md pointer makes this reliable in Claude Code, but nothing auto-syncs across machines except via git.
- Quality depends on the update ritual actually running; skipped sessions create gaps, not errors.
- STAKEHOLDERS.md holds professional context only — no sensitive personal data; the skill refuses entries about health, private life, or anything a stakeholder wouldn't expect written down.
