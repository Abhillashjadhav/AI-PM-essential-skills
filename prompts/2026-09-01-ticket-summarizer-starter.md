# Copyable ticket-summarizer eval starter

## Objective

Add a second, lightweight AI Evals for PMs use case that a PM can copy and
adapt to another AI feature without inheriting the four-surface customer-support
repository pilot.

## Problem and hypothesis

The completed verifier proves release evaluation, but the existing canonical
pilot is intentionally deep and customer-support-specific. A new user still
needs a short bridge from a product specification to a runnable local suite.

Hypothesis: a self-contained ticket-summarizer package with a filled eval
contract, synthetic cases, deterministic adapter, known-bad faults, and one
demo command will let a PM understand and adapt the product within ten minutes.

## Required behavior

1. Use the existing AI ticket-summarizer specification as the product claim.
2. Enable only outcome and trajectory. Do not enable system or memory when the
   feature makes no such promise.
3. Use synthetic ticket threads and pure-standard-library execution.
4. Check required output, length, grounded claims, sentiment, escalation reason,
   chronological processing, safety, and privacy with deterministic gates.
5. Include known-bad fabricated-claim, missing-escalation, and wrong-order
   mutations.
6. Provide a filled, copyable eval contract and explicit adaptation steps.
7. Provide one terminal demo that captures fresh isolated trials, shows a
   fabricated-claim `FAIL`, then shows the clean `PASS`.
8. Keep the stable `pm-verifier` CLI and schemas unchanged.

## Verification

- Clean execution returns `PASS`.
- Every named fault returns `FAIL`.
- The demo runs without modifying checked-in evidence.
- Existing eval-engine tests remain green.
- No real customer or personal data is committed.

## Product boundary

This is a synthetic adoption kit for local/CI release evaluation. It is not
live monitoring, a hosted service, or evidence of production-model quality.
