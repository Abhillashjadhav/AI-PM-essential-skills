# Astra development attack findings

Grader: `baseline-v1`. Offline development attack only; no held-out access. No grader, source fixture, Sol candidate, or gold file was edited. All synthetic cases retain consistent source/evidence pairs and are explicitly identified below. No fixes were made; owner prediction is required before any change.

Executed **14 grade calls**: one approved baseline, five adversarial candidates, two legitimate-output probes, and six controls. All five adversarial candidates returned **PASS with zero errors**. Both legitimate-output probes returned **FAIL**. These are attacker classifications against the contract, not new owner-approved judgments. Full observed results are in `ASTRA_run_log.json`.

## Reproducible false accepts

Each `ASTRA_A*.json` contains the complete input, attacked candidate, claim, and expected `FAIL`. Replay with `grader.grade(payload['input'], payload['candidate'])`.

| File | Input | Contract violation | Actual |
|---|---|---|---|
| ASTRA_A1_invented_named_blend.json | Original D01, unchanged | Adds unsupported `polyester blend` label to P1 despite its 20% polyester. Material equality ignores labels when components exist; named-blend checks inspect only source material. | PASS; 2 publishable |
| ASTRA_A2_currency_relabel.json | Original D01, unchanged | Adds candidate catalog US/USD while preserving unsupported relabeled 1490/990 amounts from IN/INR. Explicit output catalog configuration is ignored. | PASS; 2 publishable |
| ASTRA_A3_named_blend_case.json | Explicit synthetic D30 variant | Source and candidate say `Cotton Blend` with 50% cotton; both records claim READY. Merely capitalizing the label bypasses the source named-majority check. | PASS; 2 publishable |
| ASTRA_A4_drop_material_metadata.json | Explicit synthetic D01 variant | Source material on each record additionally has supplier-supported `recycled_percent: "50"`; candidate omits it. The prompt specifically requires retaining recycled metadata. Component equality discards other material attributes. | PASS; 2 publishable |
| ASTRA_A5_inherit_unvalidated_parent.json | Explicit synthetic D29 variant | Parent has an explicit unresolved 80/20 versus 60/40 material conflict, retaining both source evidence entries. Parent correctly BLOCKED; child inherits 80/20 and is READY despite the validated-parent gate. | PASS; 1 publishable, 1 incomplete |

A1/A2 modify only original-fixture candidates. A3 changes source label capitalization with matching evidence. A4 adds an ordinary supported metadata fact with matching evidence. A5 uses the grader's existing `conflicts` structure and adds an alternative supplier evidence record. None relies on invalid arithmetic, chart gaps, missing flagship designation, or corrupt source identity.

## False-rejection probes

Both full inputs and candidates, expected judgments, and observed results are preserved in `ASTRA_false_rejections.json`. These are the same probes already counted above, not additional grade calls.

1. **Numerically identical derived remainder rejected.** Load D09 and its Sol candidate, change only P1 `display.derived_remainder` from `"10"` to `"10.0"`. Actual **FAIL**, sole error `REMAINDER_PROVENANCE`. Both are valid decimal strings for the same calculated remainder, with identical correct display and source components. The checker compares string spelling rather than numeric equality.
2. **Equivalent evidence reference rejected.** Synthetic D01 adds `P1.material.supplier-confirmation` as a second evidence ID with the exact same `{sku: "P1", field: "material", value: ...}` as `P1.material`. Candidate cites this added ID for P1 material. Actual **FAIL**, sole error `WRONG_EVIDENCE`. This is a real same-SKU/same-field source citation; checker assumes a fixed evidence-ID spelling. If canonical IDs are intended as an output requirement, that additional restriction must be stated explicitly; the contract currently requires valid references, not this spelling.

## Controls and measurement boundaries

| Probe | Actual outcome |
|---|---|
| Approved sanity S1 unchanged | PASS |
| D24 P1 conversion 63.5 -> 63.0, crossing into M | FAIL: SIZE_BOUNDARY; CONVERSION_P2 warning also emitted |
| D24 P1 conversion 63.5 -> 63.2, endpoint explicitly owned by L | PASS with CONVERSION_P2 |
| D23 P1 conversion 63.5 -> 63.0, no bands | PASS with CONVERSION_P2 |
| D23 P1 cites C1's 24.8-inch measurement and outputs 63.0 | FAIL: MEASUREMENT_SOURCE |
| D05 automatically enrichs generic parent with child's 80/20 and citation | FAIL: WRONG_VALUE, WRONG_EVIDENCE, DISPLAY_VALUE |
| D07 removes known 5% polyester internally, retaining simplified display | FAIL: WRONG_VALUE |

No measurement-boundary exploit was found in these targeted probes. Parent enrichment and omission of known component proportions were correctly detected.

## Proposed changes for owner prediction, not implemented

| Area | Smallest proposed rule change | False-rejection risk to predict |
|---|---|---|
| Material preservation and unsupported claims | Compare labels and ancillary supplied attributes separately from order-insensitive/numerically normalized component identity; reject unsupported added factual claims. | Raw dict equality would reject legitimate component order, numeric spelling, or display simplifications. Do not force a display label to match structured composition verbatim. |
| Explicit catalog overrides | When candidate catalog context is present, require supported country/currency; preserve inheritance when omitted. | Requiring repeated per-SKU currency would reject explicitly permitted inherited context; hard-coding INR would reject valid US/USD fixtures. |
| Named blends | Normalize label case/spacing before recognizing named-blend claims, then enforce known majority consistently. | Do not impose invented percentages on genuinely generic evidence or misclassify generic multi-material descriptions. |
| Inherited parent conflict | Propagate unresolved conflict in an inherited shared attribute to the affected proposed assignment until supplied resolution validates the parent. | Do not blanket-block existing consistent siblings or children for unrelated parent price/color issues. Do not block a family whose supplied resolution is valid. A specific actionable issue code/schema may need clarification. |
| Derived remainder | Compare finite decimal values and provenance independently, accepting 10 and 10.0 as equal. | Numeric equality alone must not erase the derived-versus-supplier-confirmed distinction or permit a wrong value. |
| Evidence IDs | Resolve the cited entry and validate its source SKU, field, value, and applicability instead of requiring a constructed key. | Do not accept a sibling citation just because its value happens to match; explicitly authorized parent inheritance remains distinct. |

These probes do not measure production reliability or held-out performance. They establish concrete reproducible failures of the present deterministic checker.

A5's observed PASS is exact; its contract classification should receive owner judgment on dependency scope. It concerns a **known-invalid shared material** inherited from an unresolved parent, not a rule that any parent blocker automatically blocks every child. No broader parent-status dependency was assumed.
