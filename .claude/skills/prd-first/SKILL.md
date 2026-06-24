---
name: prd-first
description: Forces a written PRD before any code generation. Use this skill the moment the user says "build", "create app", "make me a", "vibe code", "let's build", "I want an app that", "spin up a", "prototype a", "ship a", or any phrasing that signals they want code generated from a high-level idea. Also use when the user references an existing project but the conversation has no PRD context (no /prds/ file referenced, no clear success metric). The skill blocks code generation until a 5-field PRD exists as a markdown file in the repo. Do NOT use when the user is asking factual questions, debugging existing code, editing a specific file they've named, or working in a repo where a PRD for this feature already exists at /prds/. Skip when user explicitly says "skip the PRD" or "just code it" — but flag the risk once before proceeding.
---

# PRD-First Discipline

The user (Abhillash) vibe-codes 10-15 apps and loses track of what each app is actually doing because Claude generates code from high-level intent without a written contract. This skill forces a 10-minute thinking pass before any code generation. The PRD is the contract; the code must satisfy it; future-Abhillash can read the file three months from now and remember why.

## The hard rule

**No PRD, no code.** When the trigger fires, refuse to generate code or vibe-code prompts until a PRD exists as a markdown file in the repo at /prds/YYYY-MM-DD-<slug>.md. This is non-negotiable except when the user explicitly overrides with "skip the PRD" — in which case flag the risk once, then proceed.

## The 5-question protocol

Ask **one question at a time.** Wait for the answer. Do not batch. This matches the user's learning style (theory → quiz → build, one question at a time).

Each question has a quality bar. If the answer is vague, ask one follow-up. Then move on — don't gold-plate.

**Question 1 — Problem:**
> What hurts today, and for whom?

Quality bar: a specific pain, not a feature wish. "I want a dashboard" is a feature; "I'm losing 30 minutes a day reconciling Stripe payouts against orders" is a problem. If they answer with a feature, ask: "What's the underlying pain that makes you want that?"

**Question 2 — User:**
> Who specifically uses this, and what's their current alternative?

Quality bar: a real person (you, your team, a known segment) and a named alternative ("I do it in a spreadsheet now", "we use Notion but it doesn't sync"). If "everyone" — push back: "Pick the one user whose problem we're solving first."

**Question 3 — Success:**
> One metric, one number, one timeframe — when do we know this worked?

Quality bar: measurable. "Faster reconciliation" fails. "Reconcile a day's payouts in under 3 minutes by end of week 2" passes. If they can't name a number, accept a binary: "Does the thing I described in Q1 still happen on Friday? Yes/No."

**Question 4 — Scope cuts:**
> What are we explicitly NOT building in v1?

Quality bar: at least 3 things named. This is the most important question. If they say "nothing, build it all", push back hard: "Name three things you're cutting. Vibe-coded apps die from scope creep, not from missing features."

**Question 5 — Non-goals:**
> What would make us call this a failure even if it ships?

Quality bar: at least one named failure mode. Examples: "if it costs more than $5/month to run", "if I have to maintain it manually every week", "if non-technical users can't open it without help". This catches the class of bugs where you build the right thing correctly but it's still useless.

## What to do with the answers

After all 5 questions answered, write the PRD to /prds/YYYY-MM-DD-<slug>.md using this exact template (indented with 4 spaces, since the file itself is markdown):

    # PRD: <one-line name>

    **Date:** YYYY-MM-DD
    **Status:** Draft | Approved | Built | Shipped | Killed

    ## Problem
    <Q1 answer, 1-3 sentences>

    ## User
    <Q2 answer, 1-2 sentences. Name the user, name their alternative.>

    ## Success metric
    <Q3 answer. One sentence. Must contain a number or a binary yes/no.>

    ## Scope (v1)
    - <thing 1>
    - <thing 2>
    - <thing 3>

    ## Out of scope (cut from v1)
    - <cut 1>
    - <cut 2>
    - <cut 3>

    ## Non-goals (failure modes)
    - <failure mode 1>
    - <failure mode 2 if applicable>

    ## Decisions log
    (Append one line per architectural choice as we build. Format: "Chose X over Y because Z.")

Show the user the PRD. Ask: "Approve, edit, or kill?" Wait for explicit approval before generating any code or vibe-code prompts.

## After approval

When the user approves the PRD, do three things:

1. **Reference the PRD path in every subsequent code prompt.** The vibe-code prompt's first line must be: "Implement /prds/YYYY-MM-DD-<slug>.md. Code must satisfy the success metric and respect the scope cuts."

2. **Create or update /DECISIONS.md in the repo root.** This is the running architectural log. Every meaningful choice (framework, library, schema, auth pattern, deployment target) gets one line appended. Format: "2026-05-24: Chose Supabase over Firebase because — auth + Postgres in one, free tier covers v1 user count."

3. **At end of each coding session, ask the user one question:** "Anything we decided today that should go in DECISIONS.md?" Append what they say. This is how context compounds across sessions instead of evaporating.

## Edge cases

- **Existing repo, no /prds/ folder:** create it. Don't ask permission for the folder, ask permission for the PRD content.
- **User says "I already know what I want, just build it":** push back ONCE. Say: "I'll build it, but you'll forget why we made these choices in a month. 10 minutes now saves 2 hours of re-reading code later. Want me to ask the 5 questions?" If they still refuse, proceed and flag in DECISIONS.md: "Skipped PRD per user request — risk: future debugging context loss."
- **Tiny features (one-line tweak, bug fix):** PRD not required. Skill applies to *new things being built*, not edits to existing things.
- **User answers vaguely on purpose:** don't fight them. Capture what they said, mark the PRD status as "Draft", proceed. The PRD is a living doc; vague v1 is better than no v1.
- **Retrofitting a PRD for an existing vibe-coded app:** valid use case. Skip Question 4 (scope is already set) and Question 3 (success metric is "does it currently work" — binary yes). Focus on Q1, Q2, Q5 to recover lost context.

## What this skill is NOT

- Not a replacement for the user's judgment. The PRD is *their* document — Claude is a scribe, not the author.
- Not a corporate PRD template with stakeholders, timelines, and OKRs. This is a personal thinking artifact.
- Not enforced on every chat message. Only when the trigger words appear *and* code generation is the next likely step.
- Not a research exercise. If the user can't answer Q3 because they genuinely don't know the metric yet, accept "I'll figure this out after I see it working" and mark the field as "TBD — define after first prototype."

## The self-check before generating any code

Before writing a single line of code or vibe-code prompt after the trigger fires, scan:

1. Does a PRD file exist at /prds/YYYY-MM-DD-<slug>.md? If no → ask the 5 questions.
2. Has the user explicitly approved it? If no → show the PRD, ask for approval.
3. Does the prompt I'm about to write reference the PRD path? If no → add it as the first line.
4. Is there a /DECISIONS.md in the repo root? If no → create it with a header.

If all four pass, proceed. If not, stop and fix the gap.
