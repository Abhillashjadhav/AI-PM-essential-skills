# eval-rubric-generator migration

This standalone skill is retired to prevent an evaluation trigger collision.
It is not an independently maintained eval product.

Install and use [`pm-verifier`](../pm-verifier/) for the complete workflow:

`feature spec → define good → create eval suite → run trials → grade → inspect failures → release decision`

Existing binary rubric items map to gates in `suite.json`. Tradeable `CHECK`
items should become anchored gradual rubric criteria instead of binary checks.
Keep the original product requirement and human examples as dataset provenance
when migrating.

The directory remains only so existing repository links have a useful landing
page. Do not restore `SKILL.md`; doing so would reintroduce the duplicate trigger.
