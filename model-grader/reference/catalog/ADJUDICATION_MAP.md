# Adjudication map — catalog grader v2.3

Which fixtures an owner judgment governs, and which carry only a builder's
expectation. Produced at `c31cbd9`, mechanically from the fixture files.

## Counts

| | Count |
|---|---|
| Total fixtures in the suite | **102** |
| **ADJUDICATED** — an owner judgment covers the expected outcome | **42** |
| **UNADJUDICATED** — expected outcome is builder-authored and unreviewed | **60** |
| **MISMATCH** | **0** |

Per suite:

| Suite | Total | Adjudicated | Unadjudicated |
|---|---|---|---|
| `revision_checks.json` | 55 | 33 | 22 |
| `gold/faults.json` | 13 | 0 | 13 |
| `gold/S1,S2,S3.json` | 3 | 3 | 0 |
| `check_metadata.py` | 31 | 6 | 25 |

**A second number matters more than the first, and it is 3.**

`ADJUDICATED` above means an owner judgment governs *what the outcome should be*.
It does not mean the owner reviewed *how the fixture encodes it*. Those are
different, and the fixtures say so themselves:

```
gold/S1,S2,S3          label_status: "owner-approved"
revision_checks.json   label_status: "development expectation derived from
                                      owner rules; not independent gold"
gold/faults.json       label_status: "builder-derived from approved rules"
```

So **3 fixtures carry an owner-signed encoding.** The other 99 were transcribed
from policy by the builder, including all 39 of the ADJUDICATED ones outside
`gold/S*`. A judgment saying "hold the parent and affected children" does not
confirm that a given fixture's records, evidence and expected error codes express
that correctly. That transcription is exactly what Gate 3 asks someone else to
check, and for 99 fixtures nobody has.

## The eight judgments

| Judgment | Fixture(s) | Status |
|---|---|---|
| **1** · Unresolved parent material conflict blocks parent and affected children | `revision_checks.json`: `parent-conflict-own-evidence-child-blocked`, `parent-conflict-independent-child-cannot-publish`, `parent-conflict-inherited-child-blocked` | ADJUDICATED (3) |
| **2** · A valid child may publish individually while the parent lacks its independent price; link later | `revision_checks.json`: `parent-price-missing-child-ready` · `check_metadata.py`: `d2-child-publishes-without-dangling-parent`, `d2-link-retained-when-parent-published` | ADJUDICATED (3) — **coverage gap, below** |
| **3** · A designated source does not replace seller approval for a correction | `revision_checks.json`: `supplier-designated-authority-resolves-description`, `ignored-authoritative-value`, `unapproved-authority-withholds-not-blocks`, `pending-correction-blocks`, `supplier-approved-correction`, `authority-can-supply-missing-required-fact`, `known-typo-requires-supplier-approval` | ADJUDICATED (7) |
| **4** · Withhold a conflicting optional description, publish the otherwise valid product, warn the seller | `revision_checks.json`: `optional-conflict-withheld-silently`, `optional-conflict-withheld-and-reported`, `optional-conflict-must-not-block` · `check_metadata.py`: `d4-withheld-field-absent-from-payload`, `d4-withheld-shared-field-does-not-block-the-child`, `d4-required-shared-field-still-blocks-the-child` | ADJUDICATED (6) |
| **5** · Preserve all supplied material information internally; do not invent missing percentages; allow validated seller updates | `revision_checks.json`: `approved-family-edit-updates-children`, `stale-child-after-approved-edit`, `compatible-partial-child-inherits-percent`, `partial-parent-display-preserves-unknown-internally`, `partial-display-is-not-permission-to-drop-source`, `wrong-derived-remainder-rejected`, `missing-derived-provenance-rejected` | ADJUDICATED (7) |
| **6** · Hold the product until the catalog review team approves the certificate — family-wide | `revision_checks.json`: `certificate-needs-human-review-holds-family`, `document-alone-is-not-human-approval-holds-family`, `supplied-human-attestation-allows-claim`, `wrong-document-review-cannot-authorize-claim-holds-family` | ADJUDICATED (4) |
| **7** · Explicit supplier market selection overrides defaults | `revision_checks.json`: `explicit-destination`, `supported-us-destination`, `unsupported-currency` | ADJUDICATED (3) |
| **8** · Overlapping size boundaries block the affected SKU pending seller correction | `revision_checks.json`: `overlapping-size-bands-block`, `double-owned-size-endpoint-block`, `size-boundary-crossing-still-fails`, `owned-boundary-endpoint-still-passes` | ADJUDICATED (4) |

## The two approved mechanisms

Listed separately because they are approved decisions but not among the eight
scenario judgments.

| Decision | Fixture(s) | Status |
|---|---|---|
| Automatic seller warnings | `check_metadata.py`: `d4-seller-warning-names-field-and-evidence` | ADJUDICATED (1) |
| `WITHHELD_FIELD_PUBLISHED` | `revision_checks.json`: `optional-conflict-must-not-publish-disputed` | ADJUDICATED (1) |

## Owner-approved gold

| | Fixture(s) | Status |
|---|---|---|
| Three judgments carrying `label_status: owner-approved` | `gold/S1.json`, `gold/S2.json`, `gold/S3.json` | ADJUDICATED (3) — and the only owner-signed *encodings* in the suite |

## MISMATCH — none open

Two were disclosed in earlier passes and both are closed:

- **Adjudication 6 scope.** The grader held the SKU; the judgment said hold the
  product. RESOLVED 2026-09-18 in favour of family-wide, implemented in v2.3.
  The three fixtures that encoded the superseded per-SKU expectation were
  updated and the originals preserved in `revision_checks_historical.json`.
- **Adjudication 4.** The grader blocked the whole SKU on an optional-field
  conflict. Resolved and implemented; superseded fixtures also preserved.

No fixture currently asserts an outcome that contradicts a judgment.

## Coverage gap — judgment 2, not a mismatch

Judgment 2 says the relationship is retained and linked *when the parent is
ready*. The fixtures cover the same-run case: the child publishes without a
dangling pointer when the parent is blocked, and keeps the link when the parent
publishes in that same run. **Nothing covers a later run**, because nothing in
this grader carries state between runs.

No fixture asserts the wrong thing here, so it is not a MISMATCH. It is an
uncovered half of an adjudicated judgment, and it is recorded as such rather than
counted as covered.

## The 60 unadjudicated

**`revision_checks.json` (22)** — `numeric-price-equivalence`,
`material-order-equivalence`, `component-number-equivalence`,
`case-and-spaces-Cotton_Blend`, `case-and-spaces-cotton___blend`,
`unapproved-material-spelling-change`, `wrong-sku-evidence`,
`matching-backup-source`, `malformed-evidence-setup`, `wrong-case-routing`,
`invented-claim-outside-fields`, `supported-extra-description`,
`missing-measurement-unit-blocks`, `ASTRA_A1_invented_named_blend`,
`ASTRA_A2_currency_relabel`, `ASTRA_A3_named_blend_case`,
`ASTRA_A4_drop_material_metadata`, `ASTRA_A5_inherit_unvalidated_parent`,
`FR1`, `FR2`, `within-tolerance-without-boundary-passes`,
`within-tolerance-wrong-sku-still-fails`

On the ASTRA probes specifically: several sit close to a judgment —
`ASTRA_A2_currency_relabel` resembles judgment 7, `ASTRA_A4` resembles judgment
5, `ASTRA_A5` resembles judgment 1. They are still counted unadjudicated, because
`attacks/ASTRA_FINDINGS.md` states plainly that these are *"attacker
classifications against the contract, not new owner-approved judgments"*.
Counting them as covered would be rounding the unadjudicated number down by
proximity.

**`gold/faults.json` (13)** — `wrong-SKU copy`, `invented value`,
`forbidden transform`, `wrong conversion`, `split siblings`, `merged strangers`,
`dropped field`, `wrong conflict resolution`, `silent default`, `empty output`,
`refusal`, `extra unsupported factual field`, `subbrand-conflict-must-still-block`.
Every one self-labels `builder-derived from approved rules`.

**`check_metadata.py` (25)** — the sixteen metadata-noninterference invariants
(`submission-*` / `record-*` for notes, confidence, `_debug`, warnings, the three
timestamps and `internal_metadata`), `metadata-cannot-clear-source-block`,
`metadata-cannot-repair-wrong-product-fact`,
`metadata-cannot-repair-false-rejection`, the four
`unsupported-product-claim-*` placements, `notes-inside-public-display-not-exempt`
and `internal-sentinel-never-forwarded`.

These derive from the contract's standing rule on private company notes rather
than from any of the eight judgments. The standing rule is owner text; the
expected outcome of each individual assertion is builder-authored.

## Method

`ADJUDICATED` was assigned only where a judgment determines the fixture's
expected outcome directly. Fixtures testing mechanics no judgment speaks to —
numeric equality, whitespace, evidence binding, setup validation, tolerance
arithmetic — are `UNADJUDICATED` even where they sit beside an adjudicated one.

The counts are generated from the fixture files rather than typed by hand, so
they move when the suite moves.
