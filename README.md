# AI Product Management Building-Blocks Lab

This repository is a verified laboratory of reusable AI Product Management building blocks: small, inspectable tools that turn recurring AI PM work into reusable, testable mechanisms.

“Verified” describes the repository's evidence boundaries, not every component's behavior. The four standalone skills are inspectable instruction files without recorded behavioral model runs. ContextPort has deterministic local tests and one recorded real-export observation. The plugin and historical directories have mixed evidence. These are separate products and experiments that share a laboratory, not one product with one maturity level.

## Public surface

| Surface | What it contains | Maturity and evidence |
|---|---|---|
| [AI PM Skills](#ai-pm-skills) | Four small, standalone Claude Code skill instructions. | Structure is checked. Live invocation and output behavior are not recorded or automatically tested in this repository. |
| [ContextPort](#contextport) | A standalone, local-first Python toolkit for representing, reviewing, and planning movement of conversational context. | Deterministic behavior is unit-tested on synthetic fixtures. One approved real-export conversion is recorded but not publicly reproducible. Destination writes are unsupported. |
| [Experimental or archived components](#experimental-or-archived-components) | Plugin prototypes, manual fixtures, examples, prompts, reviews, and historical working documents. | Evidence varies by directory. Their presence does not promote them to the maturity of ContextPort or make them part of the four-skill set. |

The portfolio map explains [why these components coexist](docs/PORTFOLIO_MAP.md). The evidence model uses five explicit levels:

- `STRUCTURAL`: files, manifests, paths, and links exist and pass deterministic inspection.
- `VERIFIED`: a committed, repeatable check establishes the stated behavior on its declared inputs.
- `RECORDED`: a public record describes an observation, but the private input or output needed to reproduce it is intentionally absent.
- `UNKNOWN`: available evidence does not establish the claim.
- `UNSUPPORTED`: the component intentionally does not perform the behavior.

## AI PM Skills

These four directories are the standalone skill surface. Each is deliberately small enough to inspect as an instruction mechanism. None has a recorded behavioral model-run suite in this repository.

### token-cost-estimator

| Field | Definition |
|---|---|
| Problem | A model choice can be made without comparing the likely cost and latency of the prompt. |
| Decision mechanism | Estimate input and output tokens, apply documented model pricing, compare trade-offs, and recommend one candidate. |
| Input | A prompt, candidate models, and an optional expected output length. |
| Output | A cost-and-latency comparison, recommendation, and variability flags. |
| Evidence status | `STRUCTURAL`: [`SKILL.md`](token-cost-estimator/SKILL.md) exists and is integrity-checked. No recorded behavioral run or pinned tokenizer/pricing test is committed. |
| Limitation | Pricing and model availability change; token counts and latency labels are not guaranteed exact and must be verified before a production decision. |

### eval-rubric-generator

| Field | Definition |
|---|---|
| Problem | A feature requirement can reach review without a concrete pass/fail definition of acceptable output. |
| Decision mechanism | Extract stated requirements, turn them into binary criteria, and separate ship-blocking gates from tradeable checks. |
| Input | A feature specification, PRD section, user story, or plain-language requirement. |
| Output | A labeled binary rubric, passing threshold, and missing-information flags. |
| Evidence status | `STRUCTURAL`: [`SKILL.md`](eval-rubric-generator/SKILL.md) exists and is integrity-checked. No recorded behavioral run or reviewer-agreement study is committed. |
| Limitation | The rubric cannot be stronger than the source specification, and criterion quality still depends on model judgment. |

### context-auditor

| Field | Definition |
|---|---|
| Problem | An assembled context file can contain stale claims, irrelevant material, overload, or conflicting instructions before a model sees it. |
| Decision mechanism | Classify cited passages against four failure modes—poisoning, distraction, confusion, and clash—and assign a severity. |
| Input | A `CLAUDE.md`, system prompt, agent instruction file, or other assembled context. |
| Output | A severity-rated diagnostic with citations and concrete fixes for critical findings. |
| Evidence status | `STRUCTURAL`: [`SKILL.md`](context-auditor/SKILL.md) exists and is integrity-checked. No recorded behavioral run or calibrated severity study is committed. |
| Limitation | Token counts are approximate, thresholds are not empirically calibrated here, and the skill diagnoses rather than repairs context. |

### concise-rewriter

| Field | Definition |
|---|---|
| Problem | Verbose text can hide decisions and consume unnecessary reading and token budget. |
| Decision mechanism | Remove named bloat patterns while requiring every fact, claim, and decision to remain. |
| Input | Text to compress without summarizing. |
| Output | A shorter rewrite, before/after token counts, reduction percentage, and removed-pattern report. |
| Evidence status | `STRUCTURAL`: [`SKILL.md`](concise-rewriter/SKILL.md) exists and is integrity-checked. No recorded behavioral run, semantic-equivalence test, or pinned tokenizer is committed. |
| Limitation | Meaning preservation and token counts are not automatically verified; exact counts depend on the tokenizer used. |

### Install the four standalone skills

```bash
git clone https://github.com/Abhillashjadhav/AI-PM-essential-skills.git
cd AI-PM-essential-skills

mkdir -p ~/.claude/skills
cp -r token-cost-estimator ~/.claude/skills/
cp -r eval-rubric-generator ~/.claude/skills/
cp -r context-auditor ~/.claude/skills/
cp -r concise-rewriter ~/.claude/skills/
```

This copies only the four standalone skills. Claude Code discovery, invocation, hot reload, current model names, and current pricing remain `UNKNOWN` until verified in the target environment.

## ContextPort

ContextPort is a standalone toolkit inside this repository. It is not a skill and is not installed by the four-skill copy commands.

### Problem solved

Conversational context needs a local, reviewable representation before any migration plan can preserve project boundaries, ordering, content, provenance, and unsupported items without silently guessing or discarding data.

### Architecture

1. Source inspection and adapters read approved local artifacts or committed synthetic fixtures.
2. ContextPack `0.1` provides the versioned, assistant-neutral representation.
3. Segregation and offline review preserve project membership and require explicit human decisions for ambiguity.
4. Reconstruction produces a deterministic dry-run plan with no destination writes.
5. Independent reconciliation and incremental sync account for omissions, changes, conflicts, and tombstones.
6. Destination adapters must verify support and fail closed; the ChatGPT adapter currently reports every write as unsupported.

See the [ContextPort architecture](context-port/docs/ARCHITECTURE.md), [capability matrix](context-port/docs/CAPABILITIES.md), and [operator guide](context-port/docs/OPERATOR_GUIDE.md).

### Deterministic evidence

`VERIFIED` evidence comes from committed Python tests and synthetic fixtures. The suite checks validation, segregation, review artifacts, dry-run reconstruction, independent reconciliation, incremental planning, packaging, installation, the CLI, the demo, and converter invariants. It does not call a hosted model, inspect an account, or write to an assistant.

### Real-export evidence

Merged [PR #24](https://github.com/Abhillashjadhav/AI-PM-essential-skills/pull/24) records one approved local conversion of a private Claude export:

- 43 source projects were preserved, with one additional generated `Unmapped Conversations` project;
- 1,434 conversations were preserved;
- 36,264 messages were preserved; and
- 7,538 attachment records were preserved.

This is `RECORDED` evidence. The aggregate counts were published in the merged PR and are public-safe; the private export and generated migration package were not committed. The checkout can therefore verify the converter's deterministic count and loss invariants on synthetic inputs, but it cannot independently reproduce those private counts or establish compatibility with every export shape. Attachment evidence covers exported attachment records, not a destination upload of binary payloads. See the [validation boundary](docs/VALIDATION.md#recorded-real-export-observation).

### Unsupported write boundary

Consumer ChatGPT project, chat, and historical-message writes are `UNSUPPORTED`. ContextPort implements no browser automation, credential path, or assistant write. Reconstruction stops at an approved plan and a fail-closed capability report.

### Quick start

Requirements: Python 3.11 or newer and a public checkout. No production dependency is required.

```bash
python3 context-port/contextport.py --version
python3 context-port/contextport.py capabilities
python3 context-port/contextport.py validate context-port/fixtures/contextpack-valid.json
python3 context-port/demo.py
python3 -m unittest discover -s context-port/tests -q
```

See [`context-port/README.md`](context-port/README.md) before handling any non-synthetic artifact.

## Experimental or archived components

The repository also retains four plugin directories:

- [`pm-tactical/`](pm-tactical/) contains five workflow skills and three executor-agent instructions.
- [`pm-verifier/`](pm-verifier/) contains an eval-design skill, examples, and a standard-library harness.
- [`mcp-migration-auditor/`](mcp-migration-auditor/) contains a dated MCP migration-audit skill and cited reference material.
- [`loop-designer/`](loop-designer/) contains a recurring-work design skill, references, and examples.

These are separate plugin experiments, not extensions of ContextPort and not members of the four standalone-skill set. Their Markdown fixtures under [`tests/`](tests/) describe trigger and expected-output checks, but the public CI does not execute model behavior against those fixtures. Manifests, examples, and runnable scripts provide different kinds of evidence and must be evaluated per component.

Historical and operational material—including [`prds/`](prds/), [`reviews/`](reviews/), [`LESSONS.md`](LESSONS.md), saved prompts, and repository review commands—records how work was shaped or checked. It is not a product surface.

## Validation and decisions

- [`docs/VALIDATION.md`](docs/VALIDATION.md) defines the evidence boundaries and reviewer commands.
- [`docs/PORTFOLIO_MAP.md`](docs/PORTFOLIO_MAP.md) explains why the products and experiments coexist.
- [`docs/PRODUCT_DECISIONS.md`](docs/PRODUCT_DECISIONS.md) records the current product decisions and rejected alternatives.
- [`docs/WHAT_I_LEARNED.md`](docs/WHAT_I_LEARNED.md) contains evidence-backed reflection prompts that require human authorship review.
- [`docs/decisions/001-contextport-repository-separation.md`](docs/decisions/001-contextport-repository-separation.md) evaluates a future ContextPort repository split without moving it now.

Run the public checks from the repository root:

```bash
python3 scripts/check_repository_integrity.py
python3 -m unittest discover -s .github/tests -q
python3 -m unittest discover -s context-port/tests -q
python3 -m compileall -q scripts context-port
git diff --check
```

## Contributing

Review [`AGENTS.md`](AGENTS.md) before contributing. Do not modify the four standalone skills as part of ContextPort work without explicit approval. Keep one evidence claim tied to one observable check, and do not merge a pull request without human review.

## License status

No repository license file is currently committed. License selection remains a human decision before release or package publication.
