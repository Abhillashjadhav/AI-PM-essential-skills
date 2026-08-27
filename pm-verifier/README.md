# AI Evals for PMs

**Product contract to evidence-backed release decision.**

AI Evals for PMs is an evidence-first, out-of-band evaluation and release-gating
product for AI features and agents. It turns a feature specification or
existing evaluation into a versioned suite, runs isolated repeated trials,
grades real outcomes, trajectories, end-to-end system checkpoints, and promised
memory/state behavior, validates calibrated model judgments, exposes failures,
and emits auditable `PASS`, `FAIL`, or `BLOCKED` evidence for CI and accountable
human release review.

The stable plugin, package, directory, and CLI identifier is `pm-verifier`.
Existing installation and automation commands do not change.

The product follows one workflow:

`product contract → define surfaces → create eval suite → run trials → grade → inspect failures → release decision`

The PM works through that sequence. The installable, pure-standard-library CLI
executes one fresh adapter process per trial, captures evidence, grades it,
exposes the complete failure trace, and produces a CI decision.

This is not a single-score tool. Binary release gates remain separate from
gradual quality scores, repeated-trial reliability, judge-calibration evidence,
and operational metrics.

## Install

Install the PM-facing plugin:

```bash
claude plugin marketplace add Abhillashjadhav/AI-PM-essential-skills
claude plugin install pm-verifier@ai-pm-skills
```

Install the versioned CI harness from a clean checkout:

```bash
git clone https://github.com/Abhillashjadhav/AI-PM-essential-skills.git
cd AI-PM-essential-skills
python3 -m pip install --no-deps ./pm-verifier
pm-verifier --version
```

No runtime dependencies or provider SDKs are installed.

Then paste a PRD/spec or point to an existing suite and ask:

```text
Create an eval for this feature.
Run this eval suite and explain the failures.
Calibrate this judge against our human golden set.
Can this candidate pass the release gate?
```

The same `eval-engine` skill handles creation, execution, calibration, failure
inspection, and migration. There is no second eval product.

For an approved PMOS handoff, the skill also includes a customer-support
repository pilot that binds one product identity across stable `FR/AC` intent,
the eval suite, Engineering AgentOS checkpoints, candidate files, the evidence
adapter, and a full-file evidence receipt before the runtime decision. Its
`create`, `bind`, and `verify` operations are onboarding tools; the public
`pm-verifier` CLI remains unchanged.

## What it is

This is a reusable evaluation contract and CI harness, not boilerplate that
generates an AI product. PMOS supplies the approved product claim and acceptance
contract; engineering implements the product and a small evidence adapter;
`pm-verifier` decides whether the resulting evidence supports release.

See [the complete handoff contract](docs/COMPLETE_EVAL_SUITE.md) for the exact
PMOS inputs, engineering outputs, lineage binding, and fail-closed semantics.

## What it evaluates

| Surface | Behavior |
|---|---|
| Outcome | Checks the real final state, not only what the agent claims happened. |
| Trajectory | Checks ordered tool/model/decision steps and exposes silent path failures. |
| System | Checks required/optional checkpoints, order, identity, state continuity, first failure, consequences, and final completion. |
| Memory | When promised, checks write, retrieve, update, forget, isolation, staleness, conflicts, and temporal order. |
| Execution | Runs a JSON-over-stdio adapter in a fresh subprocess for every selected trial. |
| Deterministic graders | Exact expected values, fields, regex, length, required values, and trace-step evidence. |
| Model graders | Ingests external semantic judgments only with matching judge/rubric provenance and statistically passing human calibration. |
| Repeated trials | Reports per-trial success, empirical `pass@k`, and consistency-oriented `pass^k`. |
| Suite types | Capability suites can use explicit hill-climbing thresholds; regression suites default to all-trials consistency. |
| Cross-cutting categories | Quality, safety, privacy, reliability, and operations can apply to every relevant surface. |
| Operations | Enforces cost, latency, token, and retry ceilings. |
| Failure analysis | Separates failures by surface and category, records the first system failure, slices metadata, and produces explainable lexical clusters. |
| Inspection | Opens the failing outcome, trajectory, system, memory, grader reasons, environment fingerprint, and isolation ID. |

## Evidence and decision states

Every run produces:

- `results.json` — canonical machine-readable evidence;
- `report.md` — human-readable release review; and
- exit code `0=PASS`, `1=FAIL`, or `2=BLOCKED`.

`BLOCKED` means the available evidence cannot support a quality claim: a file is
missing, a schema/hash does not match, a metric is absent, a judgment is
invalid, or the judge is uncalibrated. Missing evidence is never converted into
success.

Release evidence is commit-bound: required CI must pass on the exact candidate
head after every code, configuration, dataset, prompt, tool, or harness change.

## Run the production example

The reference adapter is synthetic, deterministic, and makes no model call. It
demonstrates the same subprocess contract a real application implements:

```bash
cp -R pm-verifier/skills/eval-engine/examples/production-eval /tmp/my-eval

pm-verifier validate --project /tmp/my-eval --out /tmp/my-eval/validation.json
pm-verifier execute --project /tmp/my-eval \
  -- python3 /tmp/my-eval/reference_adapter.py
pm-verifier report \
  --results /tmp/my-eval/results.json \
  --out /tmp/my-eval/report.md
pm-verifier inspect \
  --results /tmp/my-eval/results.json \
  --trials /tmp/my-eval/trials.executed.jsonl \
  --trial A400-t1
```

Calibrate and inspect swapped-order bias:

```bash
pm-verifier calibrate \
  --suite suite.json \
  --goldens calibration/human-goldens.jsonl \
  --judgments calibration/judge-labels.jsonl

pm-verifier bias \
  --pairs calibration/pairwise-stable.jsonl
```

The compatibility commands `python3 prepare.py`, `python3 run.py`, and
`python3 report.py` remain available during migration.

Create, verify, and run the complete four-surface repository pilot:

```bash
python3 pm-verifier/skills/eval-engine/examples/complete-eval/tools/repository_pilot.py \
  create --destination /tmp/complete-eval

python3 /tmp/complete-eval/tools/repository_pilot.py \
  verify --project /tmp/complete-eval

pm-verifier execute --project /tmp/complete-eval \
  --trials-out trials.executed.jsonl --results-out results.json \
  -- python3 /tmp/complete-eval/reference_adapter.py

pm-verifier fault --project /tmp/complete-eval \
  --trials trials.executed.jsonl \
  --name system-discovery-fail \
  --out trials.faulted.jsonl
```

The known-good execution returns `PASS`; named fixtures demonstrate both
observed-behavior `FAIL` and missing-evidence `BLOCKED` paths.
See the [repository pilot workflow](skills/eval-engine/references/repository-pilot.md)
for the PMOS input, real-repository adaptation, first binding, evidence capture,
and CI handoff.

## Adapter contract

`execute` starts the configured command once per trial and sends one JSON
object to stdin. The request contains the case input and metadata but never the
expected answer. The adapter must return one JSON object on stdout containing:

- `status="completed"`;
- the harness-owned `run_id` and `run_sha256` binding;
- `outcome` and ordered `trajectory`;
- `system` checkpoints when the system surface is enabled;
- `memory` events and isolation evidence when the state contract is enabled;
- cost, latency, input/output token, and retry `metrics`;
- `missing_evidence`;
- a SHA-256 `environment_fingerprint`; and
- a unique `isolation_id`.

Non-zero exits, finite-deadline timeouts (including inherited child streams),
malformed output, stdout above 1 MB, stderr above 64 KB, non-finite metrics,
non-standard JSON constants (`NaN`/`Infinity`), shared isolation IDs, unordered
trace indexes, or missing fields produce
`BLOCKED`, never `PASS`.

Stored trials and model judgments must carry the exact `run_id` and SHA-256 of
`run.json`; `run.json` must carry an immutable candidate SHA-256. Changing the
candidate or any declared run provenance invalidates earlier evidence.

## File contract

```text
eval/
├── suite.json
├── dataset.json
├── cases.jsonl
├── run.json
├── contracts/             # optional hash-bound PMOS/engineering artifacts
├── trials.jsonl           # supplied evidence, or
├── trials.executed.jsonl  # evidence captured by `execute`
├── judgments.jsonl       # when model graders are used
├── calibration.json      # when model graders are release-critical
├── results.json
└── report.md
```

See [`references/evidence-contract.md`](skills/eval-engine/references/evidence-contract.md)
for fields and supported deterministic checks. The legacy-compatible
[`production-eval`](skills/eval-engine/examples/production-eval/) proves schema
1.0 outcome/trajectory behavior. The
[`complete-eval`](skills/eval-engine/examples/complete-eval/) proves schema 1.1
system, memory, PMOS/eval/engineering digest binding, stable FR/AC traceability,
candidate/adapter binding, and repository-pilot behavior.

## Verification

From the repository root:

```bash
python3 -m unittest discover -s tests/eval-engine -p 'test_*.py' -v
python3 tests/lint_skill.py pm-verifier/skills/eval-engine/SKILL.md
python3 scripts/check_repository_integrity.py
```

The executable tests cover:

- known-good repeated trials;
- outcome and silent trajectory faults;
- system checkpoint, order, identity, continuity, silent-loss, and first-failure faults;
- memory write/retrieve/update/forget, isolation, staleness, conflict, and temporal faults;
- safety and privacy faults;
- release-critical model-gate failure;
- missing judgment/metric evidence;
- invalid release-rule and calibration contracts;
- provenance mismatch;
- PMOS/eval/engineering/candidate digest-chain tampering, unsafe repository paths, and incomplete FR/AC traceability;
- minimum trial counts and retry ceilings;
- capability vs regression semantics;
- deterministic-only suites;
- deterministic failures that correctly skip unneeded model grading;
- human calibration and biased-judge rejection;
- minimum calibration size plus per-dimension Cohen's kappa, Wilson agreement
  bounds, false-positive rates, and ordinal error;
- explicit release gates versus diagnostic trajectory checks;
- partial capability-quality scores that cannot bypass binary gates;
- fresh-process stdio execution and adapter failure blocking;
- unique trial isolation and environment fingerprints;
- deterministic results from identical evidence;
- report/inspection secret redaction;
- installable package, console entry point, and versioned schemas;
- backward compatibility for schema 1.0 plus explicit schema 1.1 contracts;
- swapped-order position bias;
- failure slicing/clustering;
- migrated source-data hashes; and
- JSON/Markdown reports and stated limitations.

## Migration

Useful data and capabilities from `pm-evals` and `Evals-pass-1` are mapped in
[`docs/MIGRATION.md`](docs/MIGRATION.md). Versioned source snapshots live under
`skills/eval-engine/examples/migrated/` with source commits and hashes. Large
JSONL snapshots use lossless `.xz`; tests verify the decompressed migration
hash, and provenance records one credential-shaped synthetic-token redaction.

Existing `gates.json` and `rubric.json` users should combine those files into
`suite.json`; existing cases become `cases.jsonl`, and actual repeated outputs
and traces become `trials.jsonl`. The old `pm-evals` hash stub is intentionally
not supported.

Existing schema 1.0 suites remain supported unchanged. Move a suite to schema
1.1 when it needs explicit `surfaces`, `system_contract`, optional
`state_contract`, or hash-bound contract lineage. Do not enable memory unless
the product explicitly promises persistent state.

## Design evidence

- [`docs/AUTHORITY_GAP_ANALYSIS.md`](docs/AUTHORITY_GAP_ANALYSIS.md) — Anthropic/OpenAI triangulation and inherited conflicts
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — layers, states, files, and trust boundaries
- [`docs/COMPLETE_EVAL_SUITE.md`](docs/COMPLETE_EVAL_SUITE.md) — PMOS-to-engineering handoff and four-surface contract
- [`docs/MIGRATION.md`](docs/MIGRATION.md) — source-to-destination capability map and consolidation plan

## Production boundary and limitations

- This is a production CI/release-evaluation harness, not a hosted monitoring service, live-traffic experiment system, or inline request gate.
- Model judgments remain probabilistic and require periodic human review.
- Empirical repeated-trial metrics do not guarantee population reliability.
- Lexical clustering is reproducible and explainable but less semantic than an embedding system.
- A product-specific adapter must expose real outcomes, trajectories, enabled system/memory evidence, metrics, environment fingerprints, and isolation IDs.
- Run hashes detect stale/mismatched evidence; they do not replace trusted CI
  storage or signing when evidence producers are adversarial.

MIT licensed.
