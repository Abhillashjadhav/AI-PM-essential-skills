# Capability evidence (as of 2026-09-25)

Status labels: **VERIFIED**, **FAILED**, **BLOCKED**, **NOT_RUN**. Evidence levels: *upstream source* (the public openai/codex repository), *synthetic* (the simulator and fake App Server), and *live* (your Mac and account). There is no live evidence yet.

## Build environment

- Linux container, Python 3.11.15. No Codex CLI, no ChatGPT account, and no `pdftotext`.
- `learn.chatgpt.com` and `developers.openai.com` were **blocked by the network egress proxy**, so the official documentation pages listed in the prompt could not be read.
- `github.com/openai/codex` (public, Apache-2.0) was readable. The adapter was built against its generated JSON Schema: commit `bd3d4d1436bb41b94fd38ba9bdd34d74524e7a9f` (2026-09-25), path `codex-rs/app-server-protocol/schema/json/`.

## Gates

| Gate | Status | Evidence | Limitation |
|---|---|---|---|
| Offline vertical slice (routing, pins, handoff, queue, recovery) | VERIFIED (synthetic) | `python3 -m unittest discover -s model-router/tests -q` → 159 tests OK, including 9 regression tests for defects found by an independent code review (each fails on the pre-fix code) | Simulator only |
| Offline routing-policy evaluation | VERIFIED (synthetic) | [evidence/offline-eval-2026-09-25.json](evidence/offline-eval-2026-09-25.json): 33/33, judge self-check usable | Policy conformance only; says nothing about answer quality on real prompts |
| Protocol method and field names | VERIFIED (upstream source) | [evidence/upstream-schema-compat-2026-09-25.json](evidence/upstream-schema-compat-2026-09-25.json): no compatibility problems; bundle digest recorded | Not the installed binary. `doctor` must check the pinned install's own schema |
| Stdio framing (JSON per line, no `jsonrpc` field) | VERIFIED (upstream source) | Upstream test client `test_app_server.rs` writes JSON + `\n`; `JSONRPCRequest` schema has no `jsonrpc` | Not yet observed against an installed binary |
| Adapter behaviour (events, approvals, malformed lines, crashes, drift) | VERIFIED (synthetic) | `tests/test_codex_stdio.py` against the `tests/fakes/fake_codex.py` subprocess | The fake is written from the schema, not from a recording of the real server |
| Installed Codex CLI: version, checksum, schema digest, pin | BLOCKED | No Codex CLI in the build environment | Run `doctor`, then `adapter pin` on your Mac |
| ChatGPT sign-in, plan, `forced_login_method`, provider override | BLOCKED | Needs your account | `doctor` checks these read-only |
| Model discovery and reasoning settings | BLOCKED | Needs your account | Default config has no executable model IDs |
| Usage signals (single and multi-bucket, resets, credits) | BLOCKED (parser VERIFIED, synthetic) | Parser tests for both forms; absent fields stay unknown | Unit of `resetsAt` is INFERRED as epoch seconds (milliseconds if implausibly large) |
| **Enforceable included-only execution (₹0 added spend)** | **BLOCKED** | No documented control was found that stops purchased-credit use on this path. The schema exposes `ordinaryUsageAllowed`, `spendControlReached`, `credits{hasCredits, unlimited, balance}`, `rateLimitReachedType`; these are **supporting** signals only | Live dispatch stays blocked. `decide_spend` returns UNKNOWN |
| Per-turn provider model attestation | UNKNOWN | Only `model/rerouted` is documented. `observed_model` is null ("not reported") unless a reroute is reported | Undisclosed substitution can't be detected; this is an observability limit |
| Reconciliation after a lost `turn/start` acknowledgement | PARTIAL (synthetic) | Matched by `clientUserMessageId` in `thread/read` items (`userMessage.clientId`). If there's no match, you're asked | Whether the provider echoes this field is unverified |
| ChatGPT browser / Codex desktop integration | UNSUPPORTED | No supported integration found. The router doesn't scrape cookies, click in the browser, or call undocumented endpoints | Routing works in the terminal client only |
| Routing latency | VERIFIED (build container, simulator) | [evidence/latency-build-container-2026-09-25.json](evidence/latency-build-container-2026-09-25.json): warm p50 1.5 ms, p99 3.1 ms; cold (after process ready) p50 3.0 ms, max 7.3 ms; cold process wall time including the interpreter, p50 114 ms; none over 1 s | **Not** your Mac, and doesn't include live startup or eligibility waits. The 1 s / 2 s targets aren't claimed for live use |
| Text PDF extraction | BLOCKED here | `pdftotext` not installed; code path tested with a stub | Install poppler-utils locally |
| Memory on your Mac | NOT_RUN | `status` and `doctor` report peak process memory (23 MiB for a doctor run here) | Pilot measurement is still needed |
| Answer quality, and the 95% / ≤5% goals | NOT_RUN | Needs real use | Not claimed |

## What would unblock live sends

Any **one** of the following, recorded as a `live` enforcement entry in the adapter pin (`adapter-pin.json` → `enforcement`), bound to the pin digest and account, with an expiry, a documentation link and observable per-dispatch conditions:

1. A documented provider or account control that guarantees no purchased-credit use when included usage runs out on this path (for example, a documented workspace spend control of 0 for Codex), confirmed by observation on your account.
2. Documentation that plans without purchasable credits can't consume credits on this path, plus live evidence that the account is such a plan.

The owner hasn't agreed to accept residual paid-credit risk, so a screenshot, zero balance, or auto-reload being off is **not** enough on its own.

## Protocol notes checked against the upstream schema

- The client requests used are `initialize`, `thread/start`, `thread/resume`, `thread/read`, `turn/start`, `turn/interrupt`, `model/list`, `account/read`, `account/rateLimits/read`, and `config/read`. Other requests the server offers but the router **never calls**: `account/rateLimitResetCredit/consume`, `account/sendAddCreditsNudgeEmail`, login/logout, config writes, and feedback upload.
- Server requests handled: `item/commandExecution/requestApproval` and `item/fileChange/requestApproval` (decisions `accept`, `decline`, `cancel`; never `acceptForSession`). Every other server request is answered with a JSON-RPC error and shown as a warning.
- Notifications used: `item/agentMessage/delta`, `error` (with `willRetry` and `codexErrorInfo`), `turn/completed` (status `completed`, `failed`, `interrupted`, `inProgress`), `model/rerouted`, `account/rateLimits/updated`, `account/updated`, `warning`, and `item/completed`.
- `account/usage/read` exists, but it reports token activity, not remaining balance, so V1 doesn't use it for capacity.
