# Gate 2 — Trigger accuracy

SHOULD FIRE:
T1. "Here's the PRD for our AI ticket summarizer — create an eval for it"
T2. "Write an eval for this feature spec: [spec]"
T3. "Help me define good for this summarization feature"
T4. "How do I test this AI feature before launch? Spec attached."
T5. "Generate a verification layer for this task description"
T6. "I need an eval rubric and an LLM judge for grading outputs of this spec"
T7. "Add quality gates to this feature — how do I measure if it works?"
T8. "Run my existing eval suite and tell me what failed"
T9. "Why is this trajectory test case failing?"
T10. "Calibrate this judge against our human golden set"
T11. "Can this candidate pass the release gate?"

SHOULD NOT FIRE:
N1. "Write unit tests for this Python function"               (non-AI QA)
N2. "Is this one output good?"                                (one-off opinion, no quality contract)
N3. "What's the difference between evals and tests?"          (knowledge question)

# Gate 3 — Functional known-answer (end-to-end)

INPUT: pm-verifier/skills/eval-engine/examples/sample-spec.md (AI ticket summarizer)

EXPECTED ARTIFACTS:
- one provider-neutral `suite.json` with the smallest complete set of binary
  gates, anchored gradual rubric criteria, suite type, calibration contract,
  and explicit release thresholds;
- versioned `dataset.json` plus `cases.jsonl` with slicing metadata;
- repeated `trials.jsonl` records containing real outcome, ordered trajectory,
  cost, latency, token, retry, and provenance evidence;
- external `judgments.jsonl` and passing held-out `calibration.json` only when
  model grading is used; and
- canonical `results.json` plus human-readable `report.md`.

EXPECTED HARNESS BEHAVIOR:
- the runnable synthetic example under `examples/production-eval/` returns
  `PASS` with exit code 0;
- known-bad mutations in `production-eval/faults/specs.json` make the matching
  outcome, trajectory, safety, privacy, metric, retry, and model gates fire;
- missing or mismatched evidence returns `BLOCKED` with exit code 2; and
- all behavior claims above are executed by `tests/eval-engine/test_pm_verifier.py`.
