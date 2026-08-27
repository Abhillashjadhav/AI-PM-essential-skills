# Customer-support repository pilot kit

## Objective

Create the first guided repository-onboarding kit for **AI Evals for PMs**.
Use the existing synthetic customer-support workflow as the only template for
this proof of concept. Preserve the stable `pm-verifier` CLI and do not add a
second public `init` product.

The workflow must bind one product identity across:

`PMOS product package → AI Evals contract → Engineering AgentOS contract → candidate evidence → release decision`

## Approved product input

PMOS receives a product-decision brief containing the customer problem, target
user, product hypothesis, proposed AI workflow, evidence, assumptions, outcome
and leading metrics, quality/safety/privacy guardrails, cost and latency limits,
trade-offs, scope, representative cases, policies, expected outcome and
trajectory, escalation point, approver, and unresolved questions.

PMOS must return a `GO`, `HOLD`, or `NO-GO` decision, stable `FR-*` and `AC-*`
identifiers, an eval design traced to those identifiers, and explicit missing
evidence. It must not create an engineering contract before explicit approval.

## Required behavior

1. Add a skill-owned repository-pilot script with `create`, `bind`, and
   `verify` operations. This is an implementation tool used by the skill, not a
   public `pm-verifier` command.
2. `create` copies the customer-support pilot into a new destination and
   refuses to overwrite any existing path.
3. `bind` is deterministic and idempotent. It validates the approved PMOS
   decision, stable IDs, traceability, and project-relative paths before it
   writes hashes.
4. Bind the PMOS contract, eval contract, suite, cases, dataset, engineering
   contract, candidate files, evidence adapter, portable product package, and
   runtime `run.json` into one verifiable SHA-256 chain.
5. The engineering contract must name the exact PMOS and eval-contract digests
   it implements. The eval contract must name the exact PMOS, suite, dataset,
   and case digests it evaluates.
6. `verify` is read-only and fails closed on a missing file, path escape,
   malformed contract, unresolved PMOS decision, unknown/duplicate `FR-*` or
   `AC-*` ID, incomplete case/grader traceability, or any digest mismatch.
7. The generated pilot must still execute twice deterministically and produce
   the expected four-surface `PASS`. Existing named `FAIL` and `BLOCKED` faults
   must remain effective.
8. Add a reusable CI example that runs package validation, pilot-chain
   verification, isolated execution, reporting, and evidence upload.
9. Document the handoff fields, the adaptation sequence for a second
   repository, and the boundary between product intent, eval design,
   engineering implementation, and observed evidence.

## Success contract

- North Star outcome: time from an approved PMOS package to the first valid
  `PASS` or `FAIL` decision in a new repository, with no reinterpretation of
  product intent.
- Leading indicators: complete `FR/AC` traceability, successful deterministic
  binding, successful preflight verification, and two isolated trials per
  representative case.
- Guardrails: zero fabricated product facts, zero silent overwrites, zero
  unbound contract/candidate inputs, and no `PASS` when required evidence is
  missing or mismatched.
- Trade-off: the first kit is intentionally customer-support-specific; broader
  templates wait until this end-to-end path is proven.

## Delivery process

Implement on a feature branch with a saved issue, logical commits, synthetic
fixtures, repository-wide tests, a draft pull request, and independent review.
Stop at the manual merge boundary.
