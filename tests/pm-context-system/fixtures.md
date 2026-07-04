# Gate 2 — Triggers
FIRE: "set up my context system" | "make Claude remember my stakeholders" | "you keep forgetting my project every session" | "set up project memory" | "initialize my PM workspace"
NO-FIRE: "summarize this meeting" (one-off) | "audit my CLAUDE.md" (context-auditor) | "do you remember our last chat?" (conversation memory) | "what is context engineering?" (knowledge) | "add a note about Priya" when context/ already exists (ritual step, not scaffold — skill fires only its update path, not re-scaffold)

# Gate 3 — Functional known-answer
INPUT A (fresh project): expect 4 files scaffolded, user interviewed ≤5 questions, CLAUDE.md pointer added, INDEX contains read order
INPUT B (existing context/, user says "update context" after a session where a decision was made): expect a PROPOSED diff (not silent write) touching STATE + DECISIONS, DECISIONS entry has date+why+rejected alternatives, STAKEHOLDERS untouched
INPUT C (STATE.md has an item idle 45 days): expect archive proposal + user flag, not silent deletion
