# Independent review — token measurement guidance

Reviewed the uncommitted changes to `token-cost-estimator/SKILL.md` and
`concise-rewriter/SKILL.md` against `.claude/commands/pr-review.md`, the source
task, and repository instructions. Scope is the existing skills' measurement
and evidence guidance, with no new capability or deployment.

```text
PR REVIEW: token-cost-estimator and concise-rewriter measurement guidance

SPEC COMPLIANCE    PASS
→ Both retain valid names, descriptions, triggers and argument hints. Each
  changed SKILL.md passed all nine repository lint checks before this verdict.

NOVELTY            PASS
→ The diff preserves the two existing skills and introduces no duplicate or
  new skill surface. This is a review of the change, not a fresh survey of
  external skill catalogs.

HARD RULES         PASS
→ Measured, estimated and unknown counts remain distinct. Counts identify
  tokenizer/method and scope; raw text counts are not billed usage. Pricing
  requires dated official sources or explicit supplied/hypothetical labels.
  Latency and quality claims require evidence. Compression preserves facts,
  position, meaningful uncertainty and conditions, with guarded arithmetic.

TESTABILITY        PASS
→ README acceptance examples cover unavailable measurement/rates, hypothetical
  arithmetic, attributed supplied counts, preserved uncertainty and empty text.
  The cost example calculates 0.002 + 0.004 = 0.006; 200→150 is a 25% reduction.
  These are checked expectations, not live model results.

BLOAT              PASS
→ Additions address the measurement failure modes directly. Unsupported sample
  speed/accuracy claims are removed without extending either skill's purpose.

VERDICT: APPROVE
Required changes before merge:
- None from this review. Owner merge approval remains required.
```

No material regression or blocking contradiction found in the proposed diff.
This verdict covers source instructions, structural lint and deterministic
example arithmetic. It does not establish trigger accuracy, token-estimation
quality, semantic-preservation reliability, model quality, or latency in live
use. No model call or external action was made.
