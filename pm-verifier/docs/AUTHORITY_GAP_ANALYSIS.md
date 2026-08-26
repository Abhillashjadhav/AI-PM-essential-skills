# External-authority gap analysis

Checked on 2026-08-26 against current primary guidance:

- [Anthropic — Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)
- [OpenAI — Evaluate agent workflows](https://developers.openai.com/api/docs/guides/agent-evals)
- [OpenAI — Evaluation best practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices)
- [OpenAI — Graders](https://developers.openai.com/api/docs/guides/graders)
- [OpenAI — Building resilient prompts using an evaluation flywheel](https://developers.openai.com/cookbook/examples/evaluation/building_resilient_prompts_using_an_evaluation_flywheel)
- [OpenAI — A shared playbook for trustworthy third party evaluations](https://openai.com/index/trustworthy-third-party-evaluations-foundations/)

## What the sources require

| Authority principle | Required implementation consequence |
|---|---|
| Separate the final outcome from the transcript/trajectory | Grade `outcome` and `trajectory` independently and expose silent path failures. |
| Combine code, model, and human graders | Prefer deterministic checks; require model-judge evidence only for semantic checks; calibrate it against human goldens. |
| Agent behavior varies between attempts | Record multiple trials and report per-trial success, empirical `pass@k`, and consistency-oriented `pass^k`. |
| Capability and regression suites answer different questions | Store suite type and apply a stricter default release rule to regression suites. |
| Traces, datasets, and repeatable runs create an improvement loop | Version data, capture traces, retain failing evidence, and emit repeatable JSON. |
| Graders should be narrow, explicit, and validated | Use code graders for objective claims; constrain model graders to binary gates or anchored dimensions with a fixed schema. |
| Harness choices affect measured performance | Record model, prompt, tool, harness, configuration, retries, token budget, time, and cost. |
| Evaluation claims need validity checks | Fail closed on missing evidence and surface broken cases, invalid judgments, and possible bias. |
| Model judges are probabilistic and bias-prone | Use held-out human calibration, per-dimension agreement, false-positive/negative counts, and swapped-order pairwise checks. |
| CI is a pre-launch layer, not the whole truth | Produce a release decision for CI while stating that production monitoring and periodic human review remain necessary. |

## Post-review corrections implemented

An independent architecture review correctly identified that the first PR
implemented only the evidence/grading/decision portion of an end-to-end eval
harness. The following gaps are now closed by executable code and tests:

| Gap | Resolution |
|---|---|
| No system-under-test execution | A bounded JSON-over-stdio adapter starts one fresh process per trial and withholds expected answers. |
| Trial independence was assumed | Every trial requires a unique isolation ID and an environment fingerprint; shared isolation blocks the run. |
| Raw agreement could approve a degenerate judge | Calibration now requires both human classes, a sample floor, Cohen's kappa, and a Wilson agreement lower bound. Binary and ordinal measures have separate denominators. |
| Exact trajectory checks were implicitly mandatory gates | Every deterministic/model check now declares `gate: true|false`; risk-critical paths can gate while incidental sequences remain diagnostic. |
| Capability results were only binary | Partial quality is reported for hill-climbing, but cannot override a failed binary release gate. |
| Failures were computed but not inspectable | `inspect` joins graded failures to redacted raw outcomes, trajectories, environment fingerprints, and isolation IDs. |
| The runtime was copied rather than shipped | `pm-verifier` is an installable, semantically versioned package with a console entry point and bundled schemas. |

## Existing-repository findings

| Capability | `Evals-pass-1` | `pm-evals` | existing `pm-verifier` | Finding |
|---|---|---|---|---|
| Outcome vs trajectory | Strong deterministic example and silent-failure proof | Stores output traces but does not grade an agent path separately | Outcome-oriented gates only | Preserve and generalize the `Evals-pass-1` distinction. |
| Trace capture | Explicit step trace in one synthetic domain | JSONL interaction traces | Case input/output only | Add a versioned generic trace schema. |
| Deterministic graders | Exact answer/path checks | Deterministic hash stub is a demo, not a quality grader | Four mechanical checks | Keep real code checks; never treat a hash as quality evidence. |
| Model graders | Real API experiment in `part2`, not integrated | Prompt preparation plus a `claude` path that silently falls back to the stub | Manual judgment files | Preserve provider-neutral judgment ingestion; reject missing or uncalibrated evidence. |
| Human goldens | Small structural answer keys | Human-labelled golden set and agreement report | Tells the PM to hand-score 3–5 cases | Version goldens and make calibration executable. |
| Bias experiments | Swapped position and verbosity experiment | Swapped-order pairwise comparison | None | Preserve blind AB/BA consistency; do not overgeneralize six synthetic items. |
| Multiple trials | Mentioned only as a limitation | Missing | Missing | Add first-class repeated trials and reliability metrics. |
| Capability/regression suites | Regression illustration | Missing | Missing | Add explicit suite types and separate thresholds. |
| Provenance | Missing | Some model metadata inside traces | Missing | Add run-level and dataset-level provenance with hashes. |
| Cost/latency/tokens/retries | Missing | Some latency/model metadata; no release accounting | Missing | Require metric fields or an explicit missing-evidence record. |
| Safety/privacy gates | Domain examples only | Rubric bullets for safety/PII | Possible generated gates | Make safety/privacy gate categories fail closed. |
| Failure slicing/clustering | Failure location only | Useful clustering and report concepts | Score histograms only | Add deterministic slicing and dependency-free clustering with method disclosure. |
| CI release gates | Clean deterministic example only | Smoke test; no real release contract | Manual fixture only | Add executable known-good/known-bad suites and exit codes. |
| Invalid evidence | Mostly ordinary Python errors | `claude` silently falls back to stub | Missing judge answers default to failure, but malformed judgments are weakly validated | Make `BLOCKED` distinct from quality `FAIL`; never convert missing evidence into success. |

## Conflicts that must not migrate

1. `pm-evals.scorer.claude_judge()` prints a prompt and then returns a hash-based
   stub verdict. That is a silent substitution of non-evidence for evidence.
2. `pm-evals` documentation calls the Claude path a production judge while its
   implementation is unwired.
3. Existing `pm-verifier` asks the judge to score rubric criteria even when a
   judge gate fails, while its runner discards those scores. This wastes budget
   and makes the evidence contract ambiguous.
4. Existing `pm-verifier` has descriptive fixture text but no executable tests
   for its claimed gate behavior.
5. A universal fixed count of 3–6 gates is a UX heuristic, not an evaluation
   validity rule. The unified skill should prefer the smallest complete set and
   explain missing evidence rather than invent gates to reach a quota.

## Deliberate boundary

The unified runtime remains provider-neutral and does not depend on OpenAI's
legacy Evals/Graders APIs. OpenAI's current documentation marks those legacy
surfaces for retirement in 2026. `pm-verifier` therefore consumes explicit
trial and judgment evidence and records provider/model provenance without
binding the public product to a retiring API.

The word “production” is intentionally bounded to an installable out-of-band
CI/release harness. It does not claim hosted-service uptime, live-traffic
monitoring, experimentation, or inline request enforcement.
