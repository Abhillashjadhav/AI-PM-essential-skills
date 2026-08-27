# Repository pilot workflow

Use this workflow when an approved PMOS package must become a runnable,
repository-bound evaluation without manually reinterpreting product intent.
The current pilot intentionally starts from the synthetic customer-support
template only.

## Authority boundaries

| Owner | Supplies | Must not silently change |
|---|---|---|
| PMOS | Product identity, `GO` decision, approver, problem, scope, metrics, guardrails, stable `FR-*` and `AC-*` intent | Policies, thresholds, expected answers, unresolved questions |
| AI Evals for PMs | Eval contract, representative cases, outcome/trajectory/system/memory graders, release rules, FR/AC traceability | Product intent or engineering behavior |
| Engineering AgentOS | Candidate implementation, checkpoints, evidence adapter, state semantics | Approved requirements or eval gates |
| Runtime evidence | Actual outcomes, traces, checkpoints, memory events, metrics, fingerprints, isolation IDs | Expected answers or contract digests |

The binder accepts only `decision="GO"`, an accountable approver, no unresolved
questions, unique stable IDs, relationally correct FR/AC/case/grader
traceability, distinct safe paths, and matching product identities. A candidate
file may not alias a contract, adapter, tool, run, or evidence output, including
through a hard link. `HOLD`, `NO-GO`, ambiguity, or a digest mismatch stops the
handoff before any file is rewritten.

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

1. `contracts/pmos-contract.json`: enter approved facts, assign one product ID,
   keep stable `FR-*` and `AC-*` IDs, record the approver, and leave
   `unresolved_questions` empty only when genuinely resolved.
2. `pilot.json`: use the same product ID/version, set `synthetic_fixture` to
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

- The PMOS decision is still `GO`, and the approver and product identity are correct.
- Every `FR-*` and `AC-*` is represented in cases and deterministic or calibrated grading.
- The engineering contract implements the exact PMOS and eval digests.
- Candidate files are separate from managed artifacts, and the candidate and
  adapter match the reviewed repository head.
- Fresh evidence has a matching `SEALED` receipt, verifies, and the PM report
  explains every `FAIL` or `BLOCKED` state.

This pilot proves portable contract and evidence binding for one workflow. It
does not prove arbitrary-repository compatibility, live-product quality,
adversarial evidence integrity, production monitoring, deployment, or release.
