# Gate 2 — Trigger accuracy

SHOULD FIRE (direct ask → full breakdown, Step 3a):
T1. "Which model should I use to refactor my auth module?"
T2. "Am I overpaying by running Opus for these copy tweaks?"
T3. "Route this data-cleanup task to the right model"
T4. "Is fixing this CSS alignment an Opus task or can Haiku do it?"
T5. "I keep burning expensive tokens on simple edits — help"

SHOULD FIRE (plain task handoff, no model question asked → compact header, Step 3b):
T6. "Fix the typo in the README and push it"
T7. "Refactor the auth module to use the new session store"
T8. "Write unit tests for the pricing utility"
T9. "Draft a competitive analysis from these 5 docs" (attached/described, not a model question)
T10. "Design the migration plan from monolith to services"

SHOULD NOT FIRE:
N1. "Which LLM is best, Claude or GPT?"        (vendor comparison, no task)
N2. "Explain how transformers work"             (knowledge question)
N3. "What's the pricing of Opus?"               (pricing lookup only)
N4. "Switch my session to Sonnet"               (direct /model action, no classification asked)
N5. "Any update on the CSS fix?" (same task as T6/T4-equivalent, already handed off and scored this session — fires once per task, not per follow-up message)

# Gate 3 — Known-answer classification (pre-labeled)

F1. "Fix a typo in README" ......................................... LABEL: Haiku
F2. "Change button color from blue to teal across one CSS file" ..... LABEL: Haiku
F3. "Rename a variable consistently in one 200-line script" ......... LABEL: Haiku
F4. "Add pagination to an existing REST endpoint" ................... LABEL: Sonnet
F5. "Write unit tests for a known utility module" ................... LABEL: Sonnet
F6. "Draft a competitive analysis from 5 provided docs" ............. LABEL: Sonnet
F7. "Design the migration plan from monolith to services" ........... LABEL: Opus
F8. "Debug an intermittent race condition across 3 services" ........ LABEL: Opus
F9. "Architect eval pipeline for a new AI feature (prod-facing)" .... LABEL: Opus
F10. "Rewrite pricing-page copy that goes live to all customers" ..... LABEL: Sonnet (error-cost bump from Haiku)
