# BAR — model-grader

Written before any file, per AGENTS.md.

**1. New or existing behaviour?**
New. `eval-rubric-generator` starts from a settled contract and turns it into criteria. `pm-verifier` runs suites and issues release evidence. Neither produces the contract. This fills that gap and stops at its boundary.

**2. Does it duplicate an official Anthropic surface?**
No. Generic planning assistance is the closest thing, and it carries no evidence-backed question bank, no four-gate status model, and no buildability exit test.

**3. Can its output be verified?**
Yes, and the verification is the exit condition rather than a claim. The build dry-run is an observable count: hand the contract to a reader who did not see the interview and count their questions. The skill asserts nothing about the world; every substantive statement in its output is the owner's decision, attributed.

**The exit condition has now been measured once, and it failed.** A blind author given the contract, the owner's judgments and a data-format guide could not produce a single valid input — nine of nine cases were rejected before grading, because the grader required an evidence shape that existed only in its own code and its own fixtures (`VERIFICATION.md` Check 8). The dry-run passes on slot coverage while missing undocumented input requirements, so the count alone is not sufficient. That failure is the strongest evidence the skill has that its own exit test needed a second half, and the two references added here are that half.

**4. What are its failure guardrails?**
Ten hard rules in SKILL.md. Load-bearing ones: never answer on the owner's behalf; never mark a rule verified because an example was written; never reopen a settled decision to accommodate existing code; never claim a judgment is deterministic when it is not; **never trust a pass rate until a blind author has written the cases**; never freeze without the trail.

Rule 9 is new and is the one the evidence forced. A suite written by the party that built the system can only catch what that party imagined: 102 checks reported 100% green while four defects were live, and five separate times in the source project a green number concealed a live defect, each caught by a different hand.

**5. What is the smallest shippable version?**
SKILL.md, eight references, three templates, one worked example. No code, no fixtures, no runner. Domain-neutral: all questions are about provenance, identity, comparison, dependency, verdict and process. (Written pre-audit at 22 questions; the shipped bank is 26. The coverage audit in `VERIFICATION.md` added two, now numbered A9 and A10, and the Check 5 slot-coverage review added A1 and A2.) None is domain-specific. The one example that uses concrete numbers is explicitly labelled as shape rather than default.

The two references added after the audit — `three-hand-protocol.md` and `blind-author-probe.md` — are about how to tell whether a grader's pass rate is a measurement or a mirror. They are equally domain-neutral: the protocol names three roles and what each may not see, and the probe is a one-hour test of whether a contract is a contract. The 26-question bank is unchanged by them.

**Two attempts max, then delete the branch.**
