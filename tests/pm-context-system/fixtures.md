# Gate 2 — Triggers
FIRE (explicit setup): "set up my context system" | "make Claude remember my stakeholders" | "you keep forgetting my project every session" | "set up project memory" | "initialize my PM workspace"
FIRE (proactive, mid-session): a decision gets made in conversation (e.g. "let's go with Postgres over Dynamo for the audit log") with no explicit memory request — expect a one-line proposal, not silence and not an interview
NO-FIRE: "summarize this meeting" (one-off) | "audit my CLAUDE.md" (context-auditor) | "do you remember our last chat?" (conversation memory) | "what is context engineering?" (knowledge) | routine conversation with no decision, stakeholder fact, or state change worth keeping (nothing proposed, stays silent)

# Gate 3 — Functional known-answer
INPUT A (fresh project, no context/ yet, a decision gets made in conversation): expect ONE proposal line ("Log to memory: ... — yes/edit/skip"), NOT a 5-question interview; on "yes", expect all 4 files scaffolded silently plus the approved entry written, CLAUDE.md pointer added, INDEX contains read order
INPUT B (existing context/, mid-session, a second decision gets made): expect another one-line proposal tied to that specific decision, not a batched interview
INPUT C (end of session, "update context", one decision was already proposed+logged inline, one state change was not): expect the sweep to propose only the unlogged state change, not re-propose the already-logged decision
INPUT D (STATE.md has an item idle 45 days): expect archive proposal + user flag, not silent deletion
