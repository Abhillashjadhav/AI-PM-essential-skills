# T-shirt Lab Contract v1.4 — Approved Lab Baseline

**Owner:** Abhillash Jadhav · **Updated:** 18 September 2026
**Status:** Approved by Abhillash on 18 September 2026 as v1.4, including the supplier-designated flagship-parent rule. Frozen business-rule baseline for implementation. The preceding v1.3 received reviewer PASS; this does not claim a separate reviewer run on v1.4. Model choice and run count remain pending. No grader has been implemented or tested.

## Contract

**1. Outcome and scope.** Given already-fetched synthetic T-shirt facts, produce correctly mapped catalog records without manual editing. No web discovery, pagination, ASIN search, seller-offer workflow, live submission, or model training. Price is mandatory on every SKU record, including parents and children; this is a lab policy and does not add an offer-management workflow. The requested one-off public product mapping is a preparation example, not a live-retrieval requirement for the candidate agent.

**2. Inputs and outputs.** Each case supplies product facts, evidence of identity/family relationships, mandatory `record_status: existing | proposed` on every record, and a fixed destination profile containing applicable field requirements, allowed values, aliases, and units. The candidate returns structured catalog records, customer-facing composition text, per-SKU READY/BLOCKED decisions, actionable reasons, and evidence/transformation references. Account for every assigned SKU; never invent combinations or drop difficult records.

**2a. What an evidence entry is.** An evidence entry is `{sku, field, value}`
plus an optional `source_note`. Its **`value` is the exact machine value of the
field it evidences — the same shape the record carries for that field**, not
prose about the source. For a scalar field that is the scalar; for `material`
it is the full material object. The grader compares `evidence[f"{sku}.{field}"].value`
to the record's field value directly, so any difference in shape is a mismatched
fixture, not a looser match.

```json
"P1.color":    { "sku": "P1", "field": "color",    "value": "Navy" }
"P1.price":    { "sku": "P1", "field": "price",    "value": "649.00" }

"P1.material": { "sku": "P1", "field": "material",
                 "value": { "components": [ { "material": "cotton",    "percent": "60" },
                                            { "material": "polyester", "percent": "40" } ] } }
```

Not `"value": "60% cotton / 40% polyester (spec sheet A)"`. That sentence is a
description of a source, and it belongs in `source_note`:

```json
"P1.material.a": { "sku": "P1", "field": "material",
                   "value": { "components": [ { "material": "cotton",    "percent": "60" },
                                              { "material": "polyester", "percent": "40" } ] },
                   "source_note": "spec sheet A, page 4" }
"P1.material.b": { "sku": "P1", "field": "material",
                   "value": { "components": [ { "material": "cotton",    "percent": "80" },
                                              { "material": "polyester", "percent": "20" } ] },
                   "source_note": "supplier invoice, 12 Aug" }
```

`source_note` is optional and inert. The grader never compares it and never
decides anything with it; it is quoted back in supplier guidance so a seller
reads "the spec sheet says one thing, the invoice says another" instead of an
internal evidence id. Its absence never changes a verdict.

**3. Accuracy and correctness.** Abhillash approves synthetic facts and expected judgments. Accuracy checks factual agreement with the approved evidence; correctness additionally checks identity, grouping, inheritance, transformations, completeness, and readiness. Real-world source verification is outside this lab. The grader evaluates the submitted candidate; it does not repair it or trust its claimed success.

**4. Platform requirements.** For this bounded lab, Appendix A defines `LAB-TS-0.1`, using verified field names from the Amazon UK January 2021 guide where available. Its required/conditional/optional flags are lab requirements, NOT verified Amazon requirements. The companion field map and Appendix A together distinguish documented names from lab choices. This versioned profile is the sole requirement source for lab grading. Optional absence does not block. India-template retrieval moves to Later and does not block lab review, implementation, or lab completeness grading. Neither lab READY nor this historical mapping certifies current UK/India platform completeness or live Amazon acceptance. The previous `LAB-AMZ-IN-0.1` was also a lab proposal, not an Amazon schema.

**5. Family identity.** The parent in this lab is a concrete, purchasable flagship SKU explicitly designated by the supplier, with its own colour, size and price. Other variants link to it and retain their own colour, size and price. Page selection, search arrival and variant links do not replace supplier designation. This internal model differs from the non-buyable Amazon parent export concept; no direct export equivalence is claimed. Preserve evidenced relationships and matching brand, sub-brand/brand extension, category, subcategory (e.g. round-neck or polo), material, and design/pattern. Collection alone does not determine membership; an evidenced sub-brand does. Shared attributes alone do not prove a family. Colour, size and price require support for their own SKU, whether flagship parent or child. The parent displays its own SKU price, not a range or minimum derived from children.

**6. Material and inheritance.** Prefer all available supported detail. Under this business rule, a named blend requires that material to exceed 50%; exactly 50% does not qualify. When applicable evidence supplies percentages, retain every supplied material and percentage in the structured catalog record and check any named-blend label against them. Silently dropping known components or percentages from that structured record fails. An explicit supplier revision is handled only through the resolution gate below, with original evidence retained; it cannot erase a known numerical conflict. Customer-facing text may use the separately approved simplifications below. A supplied generic “cotton blend” is acceptable only while applicable evidence remains generic, with no contradiction or stricter destination requirement. Never invent supplier-confirmed percentages or identify an unknown fibre. A calculated display remainder is permitted only as specified below and must be distinguished from source facts.

**Parent-first validation gate — latest owner clarification:** Shared values inherit from a validated parent. A new child's more-specific composition does not validate an existing generic parent's composition or that of existing siblings. Block the proposed child's assignment until the supplier resolves the mismatch. The agent must not automatically enrich the parent from that child or propagate its percentages to siblings.

The supplier has two resolution paths: (1) confirm and update the parent specifications, with consistent family applicability, before the child inherits them; or (2) revise the proposed child to the parent's generic description. The second path requires an explicit supplier revision in the supplied evidence; the candidate cannot silently discard percentages. Preserve original facts and the revision provenance. An explicit 80/20 versus 60/40 conflict cannot be erased by relabelling both “cotton blend.” All siblings must match the validated parent; unresolved conflicts block affected assignments. Confirmed different compositions require separate families. Display simplification never changes internal family checks.

Example: existing parent = cotton blend; existing red child = cotton blend; proposed blue child = 80% cotton / 20% polyester. Without supplier resolution, blue is BLOCKED with an actionable request to resolve the parent/child specifications. Automatically changing parent and red to 80/20 is a FAIL, even with blue's citation. Existing consistent records do not become incorrect solely because this proposed addition is blocked. If supplied evidence explicitly confirms a family-wide 80/20 update, parent and applicable children can consistently use 80/20. If the supplier explicitly revises the proposed child to generic cotton blend without an unresolved numerical conflict, the generic family can pass. In the offline lab, such resolutions must be supplied facts; the candidate cannot manufacture supplier confirmation or claim an external update occurred.

**Owner-approved all-new-family verdict:** All records proposed: parent cotton blend, red cotton blend, blue 80/20. Assuming every other requirement is met, parent and red pass; blue blocks pending supplier resolution. There need not be an existing parent for the mismatch gate to apply.

This supersedes v1.2's automatic child-to-parent enrichment example. The earlier proposed attack prediction about automatic propagation is therefore not an accepted limitation of v1.3. Its scenario now tests whether the grader catches unauthorized enrichment. Real-world mistakes absent from all supplied evidence remain outside factual verification in this lab.

**7. Transformations and warnings.** Use only profile-approved aliases; an unmapped value blocks. Size labels and boundaries belong to the supplied company/brand chart, not a universal chart. Preserve supported Small/Medium/Large labels; do not infer measurements from them. Do not infer a size from a number without an applicable supplied chart.

For every converted measurement, emit its source evidence reference, source SKU, measurement type, source value, source unit, output value, and output unit. The grader first checks these source attributes against the supplied evidence for that SKU and measurement. Numerically equal source representations such as 25 and 25.0 are equivalent; another SKU's citation is not. Wrong-SKU or wrong-measurement evidence fails before any numeric tolerance, even if the final number happens to be close.

The lab target is centimetres to one decimal using decimal half-up rounding and 1 inch = 2.54 cm. Compare with the correctly rounded reference: equal passes; a nonzero absolute difference up to 0.5 cm passes with a P2 warning only if it does not cross or reach a boundary assigned to a different size band; greater than 0.5 cm fails. Company-defined size boundaries are strict and override tolerance. Use exact unit conversion for boundary checks, not rounded thresholds. Apply supplied endpoint inclusivity; do not invent gaps, overlaps, or which size owns an unspecified endpoint. A fixture testing classification must supply a complete relevant chart with those definitions; otherwise it cannot establish the expected boundary verdict.

Example without a conflicting size boundary: source Medium chest 25 inches → reference 63.5 cm; candidate 63.0 cm may pass with a P2 warning only with the correct Medium source. If the supplied chart puts 63.0 cm in Small and 63.5 cm in Medium, that same candidate fails because it violates the size boundary. Using Small's 24.8-inch evidence for Medium fails regardless of the chart or tolerance. These are distinct checks: evidence identity, arithmetic tolerance, and company-specific classification. The grader reports defects without repairing the output.

Preserve material proportions and prefer descending percentage order. Wrong order alone is a non-blocking formatting issue. A 99.9% composition total is acceptable. A total above 100% and up to 101% passes with a warning; above 101% blocks pending source correction. Never reduce or rebalance supplied percentages to force 100%. These checks are separate from the centimetre tolerance.

**Structured composition versus customer text:** Preserve the original source and every currently applicable supplied component in the structured catalog record, even when the display omits a component. Keep superseded supplier submissions in the evidence history when an explicit revision is supplied under §6. Family identity, supplier-authorized updates, conflicts, composition totals, and inheritance are checked against the full structured composition. Matching display text alone cannot establish equal material composition. Thus children with 60% cotton / 5% polyester and 60% cotton / 7% polyester do not become equivalent just because both display “60% cotton.”

**General display rules (approved):**
1. Exactly two components with stated percentages, larger >50% and smaller <10%: display only the larger with its percentage.
2. Every other two-component case: display both, no “others.” Thus 60/10 and 55/45 display both; 50/50 displays both and cannot use a named-majority blend label.
3. Three or more components, each with a supplied percentage, totaling less than 100%: display all plus `N% others`, where N = 100 minus the sum. Mark N as derived, not supplier-confirmed.
4. Otherwise preserve the supplied description and known details; do not infer missing percentages or compute a remainder from an incomplete set of percentage values.

**No minimum disclosed-percentage total:** Material identity is required, but percentages and complete numerical composition are not. Generic “cotton polyester mix” is acceptable when the source identifies those materials without proportions; it asserts no majority. Known percentages must still be preserved. A bare “60” without a material or interpretable unit is not a usable material fact. Missing specificity alone is not a blocker; contradiction and unsupported interpretation remain blockers. Quantified shortfalls warn but do not block solely for their size. The >101% excess rule still applies.

Examples:

| Supplied composition | Customer-facing text | Structured record and handling |
|---|---|---|
| 80% cotton, 15% polyester | 80% cotton, 15% polyester | Keep both supplied components; no “others” text. Incomplete total is non-blocking with a warning, provided all other checks pass. |
| 60% cotton, 5% polyester | 60% cotton | Keep both supplied components internally. With two supplied materials, the larger exceeding 50% and the smaller below 10%, display only the larger with its percentage. No “others” text. Incomplete total is non-blocking with a warning. |
| 60% cotton, 25% polyester, 5% elastane | 60% cotton, 25% polyester, 5% elastane, 10% others | Keep all three supplied components. Record the 10% separately as a calculated, unconfirmed remainder; never as a supplier-confirmed material. Incomplete source composition is non-blocking with a warning. |

These decisions replace the earlier blanket addition of “others” for two-component shortfalls and the earlier blanket failure for simplified customer text. They do not permit arbitrary omission of other known materials. A display remainder never resolves conflicting evidence or proves family membership. The total and warnings are internal catalog checks; no extra sum field is required on the customer page. Applicable destination requirements still govern export validity. The model transforms; the grader checks the submitted structured record and display separately.

**8. Verdicts and reporting.** Missing required facts, genuine conflicts, invented/misattributed values, incorrect identity/grouping, inconsistent structured parent/child compositions, composition totals above 101%, and conversions outside the accepted tolerance prevent READY. Approved display simplification and permitted incomplete totals are not failures by themselves. For a nonempty assignment, an assigned SKU absent from the output, an empty output, or refusal text instead of the required records is a handling FAIL; missing SKUs count as omissions (rank 4). Correctly blocking an unsupported SKU is correct handling but incomplete work. Blocking a fully supported SKU is a major failure. The grader must establish the cited defect in the supplied evidence; a plausible reason such as “awaiting supplier resolution” is not sufficient when no mismatch exists. Report “10 correctly handled; 8 publishable; 2 incomplete” where applicable. All blocking rules must pass; severity rankings cannot excuse a false READY. Report grader false accepts and false rejects against user-approved judgments separately from catalog completion.

**9. Learning and evidence.** Retain the bounded lab: one preparation hour and two work sessions, ₹0 incremental spend, existing subscriptions, no API keys. Use 30 development cases and 10 complete sealed examples (input, candidate, user verdict, reason) outside builder/attacker access. Build a deterministic v1, challenge it, and classify discoveries as grader bugs, contract ambiguities, or legitimate alternatives. Before each fix, Abhillash predicts the rule change and possible false rejection. Freeze v1/v2 and compare on the same held-out set without tuning to it. Finish with three fresh cases explaining a wrong verdict, a fix, and a possible false rejection.

## Error priorities and reasons

All blocking rules apply regardless of rank; no weighted score is authorized. Rank 1 is explicitly the owner's choice.

| Rank | Error | Reason |
|---|---|---|
| 1 | Reject correct work | Wastes completed effort, withholds an earned outcome, and damages agent credibility. |
| 2 | Silently resolve conflicts | Conceals a decision that needs supplier clarification. |
| 3, tied | Merge unrelated variants / split genuine variants | Misrepresents the product family in either direction. |
| 4 | Omit required facts or assigned records | Leaves work incomplete while concealing what was not handled. |
| 5 | Copy a wrong-SKU fact | Attaches real evidence to the wrong product. |
| 6 | Invent unsupported values | Creates facts that the supplied evidence cannot substantiate; still fails. |
| Separate P2 | Conversion error | Small permitted arithmetic deviations warn; wrong evidence, size-boundary violations, or errors beyond tolerance fail. No ordinal tie or numeric penalty was approved. |

Rank 1's rationale is the owner's stated reason; the remaining short reasons explain the retained error categories without changing their order.

## Appendix A — Lab requirement profile: LAB-TS-0.1

**Updated from the owner’s voice decisions after reviewer PASS.** These flags make the offline grader's requirement source explicit. They are not Amazon mandatory/optional flags. Verified field names below come from the historical UK guide; internal fields have no claimed Amazon export mapping. This contract is self-contained for review; the companion map provides provenance details.

| Concept / representation | Lab requirement | Scope / condition |
|---|---|---|
| Internal SKU ID and record role | Required | Every assigned record; unique identity; parent or child; additionally `record_status: existing | proposed`. |
| `brand_name` | Required | Parent and children; validated parent inheritance allowed. |
| Internal sub-brand | Conditional | Required when supplied/applicable to the family; fixture must explicitly mark not applicable otherwise. No invented Amazon column. |
| Internal category and subcategory | Required | T-shirts plus supported type, e.g. polo/round-neck; consistent family identity. |
| Internal design identity and `pattern_type` | Required | Supported design/pattern; a broad pattern alone cannot prove identical design. |
| `outer_material_type` / `material_composition` | Required material description | Generic description is sufficient; preserve all supplied detail. Percentages are optional, but cannot be silently dropped when supplied. |
| `parent_sku`, `relationship_type`, `variation_theme` | Conditional | Required for a proposed/accepted child assignment; a blocked proposal retains the requested link as unresolved. Parent has no parent SKU. Theme supplied by the fixture. |
| `color_name`, `size_name` | Required for every SKU | Includes the supplier-designated flagship parent; supported for each SKU separately. |
| `color_map`, `size_map` | Conditional | Only when the case's fixed lab mapping table supplies/requires normalization; unmapped required normalization blocks. |
| Internal price | Required for every SKU | Includes parents and children. Preserve supported price on its own record. This parent-price requirement is a lab choice, not an Amazon requirement. |
| Destination country and currency | Required catalog configuration | Default India / INR. Records inherit this explicit catalog context; no repeated currency field is required on each SKU. |
| `recommended_browse_nodes` | Optional for baseline lab | Preserve if supplied with an evidenced mapping; no external lookup or invented browse ID. |
| `neck_style`, `collar_style`, `style_name` | Conditional | Preserve/map when supplied and applicable; do not demand all three to represent the internal subcategory. |
| Internal garment measurements | Optional to supply; conditional preservation | If supplied, preserve for the correct SKU; conversions require §7 evidence fields. No packaging-dimension substitution. |
| Collection | Optional | Does not independently define family; retain when supplied. |
| Status, reasons, evidence references, customer material text | Required output | Every SKU receives READY/BLOCKED; blockers/warnings actionable; cite used facts and transformations. |

Each fixture carries the frozen profile version, the relevant finite allowed values/alias mappings, and any applicable company chart including endpoint ownership. These are explicit synthetic test inputs, not invented Amazon-wide lists. A missing or contradictory fixture profile is a setup defect, not grounds to label otherwise correct candidate work wrong. Absent optional fields do not block, but supplied facts required by the contract must not be silently omitted. ASIN, GTIN, images, listing restrictions, and live offer eligibility are outside this lab completeness profile.

## Later and review status

- Retrieve a real destination-specific India template/schema and its version before any India-completeness claim. This no longer blocks the bounded lab.
- The UK January 2021 source establishes documented field names, not a complete current requirement profile. Source: [Amazon UK clothing guide](https://images-na.ssl-images-amazon.com/images/G/02/rainier/help/Clothing_Style_Guide_UK_jh.pdf).
- Business decisions incorporated: supplier-resolved parent-first gate, strict company size boundaries, source binding before conversion tolerance, general display rules, generic material acceptance without a percentage floor, and retained error ordering.
- Latest owner amendments: parent price is mandatory too; India/INR is configured once; country/currency configuration must remain flexible (e.g. US/USD). Changing the destination currency does not supply an exchange rate or a destination selling price. Cross-country repricing rules and FX execution remain outside this India case; never merely relabel an INR amount as USD.
- Day 2 prediction to test: does the grader catch unauthorized enrichment even when the candidate cites a real child fact? Include the rank-1 fault injection of a spurious supplier-resolution block.
- Completed: grading research, business-rule discussion, and this draft. Not completed: full dataset/gold approval beyond the first three conversational judgments, grader code, attack runs, held-out comparison, or expertise test.

## Prompt for JudgeLLM

Review this contract for a bounded learning lab. Do not expand it into a production Amazon agent or rewrite the owner's business choices.

Give:
1. A verdict: ready to freeze, or changes needed.
2. At most five material issues, each with a concrete false-pass or false-rejection example, the affected clause, and the smallest fix.
3. Any proposed fix's risk of rejecting legitimate work.
4. Assess Appendix A explicitly: distinguish lab requirements from verified Amazon field names. Identify only material requirement choices needing owner approval. India-template retrieval is Later; do not reinstate it as a lab prerequisite.

Use v1.4 as the current contract: v1.2 automatic enrichment is superseded. Check the supplier-revision path, exact source binding, and strict size boundaries with concrete examples. Distinguish accepted decisions, lab flags, missing evidence, and genuinely ambiguous rules. Treat the >50% blend threshold as this lab's policy, not an asserted legal/Amazon requirement. Do not invent numeric penalties, claim tests were run, or infer grader quality from the quality of this document. End with only the decisions Abhillash must make before freezing.
