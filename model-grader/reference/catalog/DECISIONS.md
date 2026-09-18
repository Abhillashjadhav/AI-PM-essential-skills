# Owner-approved decisions

Settled by Abhillash Jadhav across two review sessions. These supersede earlier
conflicting interpretations. Do not reopen them to accommodate existing code —
an approved rule implemented wrongly is an implementation defect, reported as one.

## The eight business judgments

| # | Scenario | Required behaviour | Implemented? |
|---|---|---|---|
| 1 | Parent has conflicting material composition | Hold the parent and affected children. A child's own matching evidence does not resolve the parent's conflict in a shared material attribute. | ✅ verified |
| 2 | Parent lacks its own price; shared attributes validated | An otherwise complete child may publish as an individual product. It does not become a parent. Retain the intended relationship internally and link when the parent is ready. | ⚠️ partial |
| 3 | Conflicting descriptions, unapproved authoritative source | Recommend a correction to the seller. A database designation does not substitute for seller approval. | ✅ verified |
| 4 | Only an optional description conflicts | Withhold the disputed description, publish the otherwise valid product, warn the seller. Do not block the whole product. | ❌ not implemented |
| 5 | "60% cotton, polyester" with no polyester percentage | Preserve both internally, mark polyester's percentage not supplied, never infer 40%. Display "60% cotton". | ✅ verified |
| 6 | Certification document uploaded, not approved | Hold the entire product. An attachment alone is insufficient. | ✅ verified (per-SKU; see open question a) |
| 7 | Supplier explicitly chooses US/USD | Use the selected market and currency. India/INR defaults must not override. No invented FX, no relabelling. | ✅ verified |
| 8 | Size chart assigns one measurement to two sizes | Hold the affected SKU and ask the seller to resolve. Never choose automatically. | ✅ verified |

**Standing rule.** Private company notes may exist without failing a correct
catalog, but must not alter public facts, grading, or automated actions.
Publication and action-taking consume an explicit projection of checked data,
never the raw submission.

## Accuracy targets

**Primary outcome:** correct published SKU records ÷ all published SKU records **> 98%**

**Guardrail:** incorrectly blocked valid submissions ÷ all valid submissions **< 0.5%**

Different denominators. Do not combine them into 97.5%. Correctly blocking an
incomplete product is correct handling but is not successful publication. These
are evaluation targets, not permission to knowingly publish incorrect products.

**Neither is measured.** See `VERIFICATION.md`.

## Error ranking

| Rank | Error | Why it sits here |
|---|---|---|
| 1 | Reject correct work | Wastes completed effort, withholds an earned outcome, damages credibility |
| 2 | Silently resolve a conflict | Conceals a decision that needs supplier clarification |
| 3= | Merge unrelated products / split genuine variants | Misrepresents the family in either direction |
| 4 | Omit a required fact or an assigned record | Leaves work incomplete while concealing what was not handled |
| 5 | Copy a fact from the wrong SKU | Attaches real evidence to the wrong product |
| 6 | Invent an unsupported value | Creates facts the evidence cannot substantiate |
| P2 | Conversion error | Small permitted deviations warn; wrong evidence, boundary violations or errors beyond tolerance fail |

All blocking rules apply regardless of rank. Ranking informs strictness; it never
licenses trading a lower-ranked error for completion.

## Grader architecture

- **Interface:** Python `grade(case, candidate)`
- **Inputs:** supplier source records, evidence, relationships, destination config, candidate catalog output
- **Method:** deterministic rules checked against supplied evidence. Not exact-match to one gold answer. Not an LLM judge.
- **Outputs:** overall verdict, per-SKU handling, errors, warnings, supplier guidance, publication payload, completion counts
- **Distinction:** correctly handling a blocked product may pass evaluation while that product remains unpublished

Each evaluation case needs an independently approved **expected grading result**
and **publication outcome**. Both are recorded in the completed contract.
