# Gate 2 — Trigger accuracy

SHOULD FIRE:
T1. "Here's the PRD for our AI ticket summarizer — create an eval for it"
T2. "Write an eval for this feature spec: [spec]"
T3. "Help me define good for this summarization feature"
T4. "How do I test this AI feature before launch? Spec attached."
T5. "Generate a verification layer for this task description"
T6. "I need an eval rubric and an LLM judge for grading outputs of this spec"
T7. "Add quality gates to this feature — how do I measure if it works?"

SHOULD NOT FIRE:
N1. "Run my existing eval suite and tell me what failed"      (running, not creating)
N2. "Why is this test case failing?"                          (debugging)
N3. "Write unit tests for this Python function"               (non-AI QA)
N4. "Is this one output good?"                                (one-off review, no spec)
N5. "What's the difference between evals and tests?"          (knowledge question)

# Gate 3 — Functional known-answer (end-to-end)

INPUT: pm-verifier/skills/eval-engine/examples/sample-spec.md (AI ticket summarizer)

EXPECTED ARTIFACTS (reference output in examples/sample-eval/):
- 3-6 binary gates, each with a WHY-a-gate-not-a-score line and a TYPE
  (mechanical or judge); the sample yields 5 (2 field_present, 1 max_length,
  1 contains_none, 1 judge fabrication gate)
- 4-7 rubric criteria, each with feature-specific 1/5 anchors and a worked
  example; the sample yields 5; plus a self-contained judge prompt block
  ending in the exact JSON output shape
- harness scaffold: prepare.py / run.py / report.py copied from harness/
  templates, plus generated gates.json / rubric.json / judge_prompt.md

EXPECTED HARNESS BEHAVIOR (verified on the 2 included cases):
- prepare.py: validates cases/, rejects a case missing a required field with
  exit 1 and a named-field error; passes 2 valid cases
- run.py: case-002 fails mechanical gate G4 (commitment language) and is
  finalized WITHOUT rubric scoring — gates always run first; case-001 passes
  mechanical gates and, with judgments/case-001.json absent, gets a generated
  judgments/case-001.prompt.md and PENDING status; with the judgment present,
  finalizes as PASS with all 5 criterion scores
- report.py: renders report.md with a pass/fail table (mean score column,
  gate-failed cases show — not a score), a PENDING count when applicable, a
  per-criterion 1-5 histogram, and the judge-assigned-not-objective caveat line
