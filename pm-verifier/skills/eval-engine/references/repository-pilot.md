# Repository pilot workflow

Use this workflow when an approved PMOS package must become a runnable,
repository-bound evaluation without manually reinterpreting product intent.
The current pilot intentionally starts from the synthetic customer-support
template only.

## Authority boundaries

| Owner | Supplies | Must not silently change |
|---|---|---|
| PMOS | PDC identity/version, `APPROVED` status, approver, problem, scope, metrics, guardrails, requirement and acceptance IDs | Policies, thresholds, expected answers, unresolved questions |
| AI Evals for PMs | Eval contract, representative cases, outcome/trajectory/system/memory graders, release rules, FR/AC traceability | Product intent or engineering behavior |
| Engineering AgentOS | Candidate implementation, checkpoints, evidence adapter, state semantics | Approved requirements or eval gates |
| Runtime evidence | Actual outcomes, traces, checkpoints, memory events, metrics, fingerprints, isolation IDs | Expected answers or contract digests |

The binder accepts the actual ProductDecisionContract v1 shape:
`contract_version=1`, `contract_status="APPROVED"`, named `approved_by` and
`approved_at`, `functional_requirements[].id`, and
`acceptance_criteria[].{id,requirement,criterion}`. It validates required field
shapes, unique IDs, exact AC-to-FR links, and coverage of every requirement.
Unresolved product-critical questions block binding. The source document is
never rewritten, and its entire byte digest is bound through the evidence chain.

The configured `pilot.product.id` identifies the engineering candidate; it is
separate from the source's `product_name` and `contract_id`. The package and
summary expose `source_contract` with the source dialect, native contract
version, approval status, and upstream source digest. Existing run provenance
retains string versions, so native PDC version `1` is represented there as `"1"`.

`source_digest` is carried, not verified. The adapter requires exactly `sha256:`
followed by 64 lowercase hexadecimal characters and reports
`source_digest_verification="FORMAT_ONLY"`. It does not recompute this upstream
metadata from source material or authenticate its provenance. This field is
distinct from `contracts.pmos.sha256` in `product-package.json`, which the
binder computes over the complete raw contract file and checks during `verify`.
The two digests identify different inputs and must not be equated.

`approval_status` is publisher-declared. Both PDC and legacy source identities
report `approval_verified=false`; `APPROVED` or `GO` does not authenticate an
approver or approval receipt. `BOUND` and `VERIFIED` describe contract/evidence
binding, not authenticated product approval. A well-formed, self-declared digest
and approval therefore remain explicitly unverified after a successful bind.

The bundled support example retains the explicitly labeled
`legacy-synthetic-pilot-v1` dialect (`schema_version="1.0"`, `decision="GO"`,
`requirements`, and AC `requirement_ids`). Its original approval and product-ID
checks remain enforced. Mixed dialects, unsupported PDC versions, duplicate JSON
keys, malformed shapes, and incorrect FR/AC/case/grader relationships fail closed.
A candidate file may not alias a contract, adapter, tool, run, or evidence output,
including through a hard link.

Optional gate `acceptance_criterion_refs` must be a nonempty unique list of known
AC IDs. Binding a PDC does not compile or execute its release gates, interpret
gate descriptions, verify a PMOS approval receipt, or grant release authority.
PEOS owns executable acceptance and release-gate enforcement. The standalone
`pm-verifier` CLI continues to accept projects without a PMOS contract.

## 1. Create a working copy

From a checkout of this repository:

```bash
python3 pm-verifier/skills/eval-engine/examples/complete-eval/tools/repository_pilot.py \
  create --destination /path/to/target-repository/eval/customer-support
```

`create` never overwrites an existing path. Keep the copied tool inside the
pilot; `product-package.json` binds its exact bytes.

## 2. Adapt product intent before engineering

Edit the copy in this order:

1. `contracts/pmos-contract.json`: copy the approved PDC unchanged. Preserve its
   contract identity, requirement IDs, acceptance IDs, and approval metadata.
   Product-intent changes must go through the upstream approval workflow.
2. `pilot.json`: assign the candidate product ID/version, set `synthetic_fixture` to
   `false`, list implementation files relative to the selected repository root,
   and choose the final evidence and receipt filenames in `paths.trials` and
   `paths.evidence_receipt` before binding. Every `paths` value must resolve to
   a distinct file, and candidate files must be distinct from all of them.
   Keep the harness-owned `suite.json`, `dataset.json`, `cases.jsonl`, and
   `run.json` filenames unchanged.
3. `cases.jsonl`, `dataset.json`, and `suite.json`: replace synthetic policies,
   expected outcomes, thresholds, and cases only with approved evidence.
4. `contracts/eval-contract.json`: preserve each PMOS AC-to-FR relationship,
   trace it to cases carrying that same relationship, and trace every
   deterministic grader. Do not leave an untested requirement.
5. `contracts/engineering-contract.json`: describe checkpoints and evidence
   outputs the implementation will expose. The binder writes the exact PMOS and
   eval digests plus the approved FR/AC lists.
6. Replace `synthetic_candidate.py` with the real candidate files listed from
   the repository root. Replace `reference_adapter.py` with a JSON-over-stdio
   adapter that observes those files. The adapter is evidence plumbing, not the
   candidate, and it must not receive expected answers.

If `paths.trials` or `paths.evidence_receipt` names a new file, its parent
directory must already exist. Both files may be absent at the first bind.

## 3. Bind the approved package

From the target repository root:

```bash
PILOT=eval/customer-support
python3 "$PILOT/tools/repository_pilot.py" bind \
  --project "$PILOT" --repository-root .
```

For a real candidate, a successful first bind returns `status="BOUND"`. It
does not relabel copied synthetic trials as real evidence and writes a
`PENDING` evidence receipt. Binding is idempotent: rerunning it without an
input change produces identical bytes.

Any approved input change requires a new bind and invalidates prior evidence.
This includes a synthetic candidate or adapter change: the binder never edits
old trial provenance to make it look current. Review the resulting
`product-package.json` and `run.json` before execution.

## 4. Capture the first candidate evidence

Use the evidence filename already declared in `pilot.json`. Because
`--trials-out` is project-relative, pass only its filename when the file is at
the pilot root:

```bash
pm-verifier execute --project "$PILOT" \
  --trials-out trials.candidate.jsonl \
  --results-out results.json \
  -- python3 "$PILOT/reference_adapter.py"

python3 "$PILOT/tools/repository_pilot.py" bind \
  --project "$PILOT" --repository-root .

python3 "$PILOT/tools/repository_pilot.py" verify \
  --project "$PILOT" --repository-root .

pm-verifier report --results "$PILOT/results.json" \
  --out "$PILOT/report.md"
```

The second bind never relabels stale evidence. If every trial names the exact
run, it writes a canonical `SEALED` receipt containing the SHA-256 digest of
the complete JSONL bytes. Read-only `verify` requires that receipt and rejects
any later semantic or formatting change, even when `run_id` and `run_sha256`
remain untouched. `pm-verifier` independently validates and grades the
evidence. The only release states are `PASS`, `FAIL`, and `BLOCKED`.

## 5. Install CI after the first verified run

Copy `ci/github-actions.yml` to the target repository's `.github/workflows/`
directory and adapt `EVAL_PROJECT`, the adapter command, and the pinned harness
commit. Keep chain verification before execution, execute twice from fresh
processes, compare repeatable outputs, write the PM report, and upload the
evidence artifact.

The checked-in workflow uses current official major versions of GitHub's
checkout, Python setup, and artifact-upload actions. Pin action commit SHAs too
when the repository's supply-chain policy requires immutable third-party
actions.

## Review checkpoint

Before release, the accountable reviewer should be able to answer yes to all
of these:

- The PDC is still `APPROVED`, and its approver and source identity are correct
  (the legacy synthetic example instead retains its explicit `GO` decision).
- Every `FR-*` and `AC-*` is represented in cases and deterministic or calibrated grading.
- The engineering contract implements the exact PMOS and eval digests.
- Candidate files are separate from managed artifacts, and the candidate and
  adapter match the reviewed repository head.
- Fresh evidence has a matching `SEALED` receipt, verifies, and the PM report
  explains every `FAIL` or `BLOCKED` state.

This pilot proves portable contract and evidence binding for one workflow. It
does not prove arbitrary-repository compatibility, live-product quality,
adversarial evidence integrity, production monitoring, deployment, or release.
