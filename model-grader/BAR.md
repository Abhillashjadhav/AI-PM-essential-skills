# BAR — model-grader

Written before any file, per AGENTS.md.

**1. New or existing behaviour?**
New. `eval-rubric-generator` starts from a settled contract and turns it into criteria. `pm-verifier` runs suites and issues release evidence. Neither produces the contract. This fills that gap and stops at its boundary.

**2. Does it duplicate an official Anthropic surface?**
No. Generic planning assistance is the closest thing, and it carries no evidence-backed question bank, no four-gate status model, and no buildability exit test.

**3. Can its output be verified?**
Yes, and the verification is the exit condition rather than a claim. The build dry-run is an observable count: hand the contract to a reader who did not see the interview and count their questions. The skill asserts nothing about the world; every substantive statement in its output is the owner's decision, attributed.

**4. What are its failure guardrails?**
Nine hard rules in SKILL.md. Load-bearing ones: never answer on the owner's behalf; never mark a rule verified because an example was written; never reopen a settled decision to accommodate existing code; never claim a judgment is deterministic when it is not; never freeze without the trail.

**5. What is the smallest shippable version?**
SKILL.md, six references, three templates, one worked example. No code, no fixtures, no runner. Domain-neutral: all 22 questions are about provenance, identity, comparison, dependency, verdict and process. None is domain-specific. The one example that uses concrete numbers is explicitly labelled as shape rather than default.

**Two attempts max, then delete the branch.**
