# Gate 2 — Triggers
SHOULD FIRE: "improve this prompt" | "my support-bot prompt works 80% of the time" |
"optimize my system prompt" | "make this extraction prompt more reliable" | "tune this instruction"
SHOULD NOT FIRE: "write me a prompt for summarizing calls" (new, not existing) |
"why did this output fail?" (one-off debug) | "what is prompt engineering?" (knowledge) |
"improve this blog post" (artifact, not prompt) | "which model runs prompts cheapest?" (router territory)

# Gate 3 — Functional known-answer
WEAK PROMPT: "Summarize the customer feedback."
LOCKED CHECKLIST: C1 exactly-3-bullets | C2 each bullet <20 words | C3 each names a feature area | C4 nothing invented
TEST INPUTS: 2 real feedback batches
KNOWN DEFECTS: no format spec (breaks C1), no length spec (breaks C2), no grounding rule (risks C4)
EXPECTED: baseline ~2/8; one mutation per round targeting worst check; all-pass within 4 rounds; original preserved; changelog complete
