# pm-verifier

**One public product for AI PM evaluation work: spec in, evidence-backed release decision out.**

`pm-verifier` turns a feature spec or existing eval into one workflow:

`feature spec → define good → create eval suite → run trials → grade → inspect failures → release decision`

The PM works through that sequence. The installable, pure-standard-library CLI
executes one fresh adapter process per trial, captures evidence, grades it,
exposes the complete failure trace, and produces a CI decision.

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

## What it evaluates

| Surface | Behavior |
|---|---|
| Outcome | Checks the real final state, not only what the agent claims happened. |
| Trajectory | Checks ordered tool/model/decision steps and exposes silent path failures. |
| Execution | Runs a JSON-over-stdio adapter in a fresh subprocess for every selected trial. |
| Deterministic graders | Exact expected values, fields, regex, length, required values, and trace-step evidence. |
| Model graders | Ingests external semantic judgments only with matching judge/rubric provenance and statistically passing human calibration. |
| Repeated trials | Reports per-trial success, empirical `pass@k`, and consistency-oriented `pass^k`. |
| Suite types | Capability suites can use explicit hill-climbing thresholds; regression suites default to all-trials consistency. |
| Safety/privacy | Binary categories with zero tolerated failures by default. |
| Operations | Enforces cost, latency, token, and retry ceilings. |
| Failure analysis | Separates outcome/trajectory failures, slices metadata, and produces explainable lexical clusters. |
| Inspection | Opens the failing outcome, trajectory, grader reasons, environment fingerprint, and isolation ID. |

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

## Adapter contract

`execute` starts the configured command once per trial and sends one JSON
object to stdin. The request contains the case input and metadata but never the
expected answer. The adapter must return one JSON object on stdout containing:

- `status="completed"`;
- the harness-owned `run_id` and `run_sha256` binding;
- `outcome` and ordered `trajectory`;
- cost, latency, input/output token, and retry `metrics`;
- `missing_evidence`;
- a SHA-256 `environment_fingerprint`; and
- a unique `isolation_id`.

Non-zero exits, finite-deadline timeouts (including inherited child streams),
malformed output, stdout above 1 MB, stderr above 64 KB, non-finite metrics,
shared isolation IDs, unordered trace indexes, or missing fields produce
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
├── trials.jsonl           # supplied evidence, or
├── trials.executed.jsonl  # evidence captured by `execute`
├── judgments.jsonl       # when model graders are used
├── calibration.json      # when model graders are release-critical
├── results.json
└── report.md
```

See [`references/evidence-contract.md`](skills/eval-engine/references/evidence-contract.md)
for fields and supported deterministic checks. The runnable
[`production-eval`](skills/eval-engine/examples/production-eval/) includes two
cases × two trials, outcome and trajectory gates, a calibrated model gate,
operational metrics, and deterministic known-bad fault specifications.

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
- safety and privacy faults;
- release-critical model-gate failure;
- missing judgment/metric evidence;
- invalid release-rule and calibration contracts;
- provenance mismatch;
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

## Design evidence

- [`docs/AUTHORITY_GAP_ANALYSIS.md`](docs/AUTHORITY_GAP_ANALYSIS.md) — Anthropic/OpenAI triangulation and inherited conflicts
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — layers, states, files, and trust boundaries
- [`docs/MIGRATION.md`](docs/MIGRATION.md) — source-to-destination capability map and consolidation plan

## Production boundary and limitations

- This is a production CI/release-evaluation harness, not a hosted monitoring service, live-traffic experiment system, or inline request gate.
- Model judgments remain probabilistic and require periodic human review.
- Empirical repeated-trial metrics do not guarantee population reliability.
- Lexical clustering is reproducible and explainable but less semantic than an embedding system.
- A product-specific adapter must expose real outcomes, trajectories, metrics, environment fingerprints, and isolation IDs.
- Run hashes detect stale/mismatched evidence; they do not replace trusted CI
  storage or signing when evidence producers are adversarial.

MIT licensed.
