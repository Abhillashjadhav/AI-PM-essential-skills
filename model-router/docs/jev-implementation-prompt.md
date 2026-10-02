# Saved implementation brief — TypeSafe integration

This is the normalized implementation request for this phase, including the owner's final credit-policy correction. It contains no private chat export, screenshot, API key or account data.

Implement TypeSafe Jev in the existing `model-router/` application in `AI-PM-essential-skills`. Continue the existing architecture; do not rebuild the product or modify other skills. Work on feature branches and draft PRs. Do not merge `main`, buy anything, change payment settings or access private exports.

The goal is automatic, fast selection of an approved GPT tier for the first prompt in a new chat. Jev classifies; GPT executes. Highest covers architecture/product/UI decisions, consequential assessments, high-credibility writing and risky money/privacy/security coding. Middle covers ordinary implementation. Lowest covers routine text and literal extraction. Preserve conservative uncertainty handling, per-chat pins, human overrides, the structured architecture-to-implementation handoff, usage gating, crash recovery, and evaluation-before-owner-approval for new GPT mappings.

The owner authorizes the hosted TypeSafe API using existing free credits and explicitly rejects a local spending cap. Let TypeSafe enforce credit availability. Do not introduce a local dollar cap, request quota, credit-expiry timer, daily billing reconfirmation, or estimated-balance gate. Keep a manual off switch and stop on provider/transport errors without retries. Do not claim that no card proves an observed exact credit cutoff or that a local tracker sees account-wide spending. The GPT subscription spend gate is separate and remains unchanged.

Use only the Python standard library. TypeSafe's interface is `POST https://api.typesafe.ai/v1/systemone`, with a bearer key and JSON `{model, state, questions}`. Pin `jev-1.13.0`. In one request, ask a `choice` question using the existing `TaskKind` labels and a separate `noul` question about consequences. Each question includes complete independent instructions. A successful result includes the model version, typed answers, choice probabilities/confidence, and `usage.input_tokens`/`output_tokens`. Strictly validate them. Provisional thresholds are 0.80 choice confidence/probability and at most 0.20 consequences for ordinary tiers; uncertainty routes conservatively. These thresholds are not empirical proof of correctness.

Do not upload attachments, history, repository files or credentials to the classifier. Bound text without truncating; use rules when text/context is unsupported. Preserve existing risk floors. Fix the existing hook bug where a resolved UNKNOWN secondary category still forces highest.

Store the key privately on the local computer via an interactive hidden prompt. Do not put keys in argv, environment passed to Codex, Git, logs or prompt content. A key in the environment alone does not opt in. Enablement is explicit and bound to the key. Record the owner-confirmed free-credit/no-card/reload-off arrangement without inventing a billing API.

Use a fixed HTTPS destination with redirects disabled. A disposable subprocess enforces a 1.6-second total HTTP deadline including DNS/TLS/reads. The existing four-second route fence and manual choice remain. Persist a request record before network dispatch under a non-blocking cross-process lock. Keep records until owner deletion. Recover saved classifications by request ID; never resend an unknown request. No history scan or ever-growing in-memory list should add routing latency.

Expose `jev setup`, `jev status`, `jev disable`, and a six-example `jev pilot` independent of Codex, queues and GPT calls. Offline simulation/evaluation must not call external plugins even with credentials configured. Normal follow-ups and task bookkeeping must not call Jev again.

Verify actual routing roles, credit/error rejection, timeout, concurrency, crash recovery, idempotency, private key handling and offline isolation using synthetic fixtures. Test that the removed local cap/daily lease cannot silently return. Run required repository gates. Report live/account/Mac evidence separately from simulation; do not claim real-world accuracy or production readiness from unit tests.

Check official interface capabilities. Running the router in the desktop integrated terminal is acceptable to implement/document. Native browser/Codex composer interception must not be claimed without a verified extension mechanism. Record unresolved interface decisions for the owner rather than blocking other authorized work or fabricating support.

Deliver a complete architecture/operating guide, saved brief, evidence, and a short owner-follow-up note. Continue autonomously while the owner is unavailable. Use separate runtime and documentation PRs, no main merge.
