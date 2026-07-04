# Gate 2 — Triggers
SHOULD FIRE:
T1. "Write the launch email and make sure it meets all my requirements"
T2. "Validate this PRD draft against the spec before showing me"
T3. "Self-QA the landing page copy"
T4. "Check your own work before you give me the report"
T5. (3rd correction round on same artifact) "again, the CTA is missing"
SHOULD NOT FIRE:
N1. "What makes a good launch email?"           (question)
N2. "Brainstorm 10 taglines"                    (divergent, no spec)
N3. "Quick rough draft, don't polish"           (explicit no-checks)
N4. "Review this competitor's email"            (external artifact, no build)
N5. "How does builder-validator work?"          (meta question)

# Gate 3 — Functional known-answer test
INPUT SPEC: "LinkedIn post: max 1300 chars, hook contains a specific number
in first 8 words, no hashtags, ends with a question, article link in first
comment not body."
EXPECTED FREEZE: 5 binary criteria; char-limit + no-hashtags + link-placement = GATES;
number-hook + question-close = SCORE or GATE (either defensible).
PLANTED VIOLATION: artifact includes "#AIPM" hashtag and link in body.
EXPECTED AUDIT: both violations caught as GATE failures, revision cycle triggered.
