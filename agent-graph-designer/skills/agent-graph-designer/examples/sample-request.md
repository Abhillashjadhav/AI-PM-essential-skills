# Sample request

Design an agent graph that helps an AI product manager decide whether a support-ticket summarization feature is ready for launch.

My framing: launch risk is fragmented across product value, model quality, and safety/privacy reviews. Each review can run independently, but all three must use the same frozen release candidate and return comparable evidence before I make the decision.

My hypothesis: parallel specialist review loops with typed outputs and an all-required join will reduce decision time without weakening accountability.

North Star: percentage of evaluated release candidates that receive a correct, evidence-backed launch decision within two working days.

Leading metrics: valid branch-artifact rate, time to complete all reviews, join-block rate, and repair rate.

Guardrails: no fabricated evidence, no live customer data, no reviewer approves its own work, no autonomous deployment, and total review cost capped per candidate.

Trade-off: lower wall-clock time versus higher orchestration and token cost.

Proposed next step: validate the graph using synthetic evidence for one release candidate and stop at a human approval gate.
