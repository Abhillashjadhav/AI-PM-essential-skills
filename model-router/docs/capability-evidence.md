# Capability evidence (as of 2026-09-25)

Evidence levels:

- **upstream source:** the public openai/codex repository.
- **real binary:** the released Codex CLI 0.157.0, run in the build container without sign-in.
- **synthetic:** the simulator and a fake App Server.
- **live account:** your Mac and ChatGPT account. There is no live-account evidence yet.

## Status at a glance

| Area | Implemented | Tested with simulation | Tested against the real Codex binary | Tested with real models | Blocked on |
|---|---|---|---|---|---|
| Routing, pins, overrides, handoff, queue, recovery | yes | yes (188 tests) | — | no | the spend boundary |
| Automatic resume while running (`chat`, `serve`) | yes | yes | — | no | the spend boundary |
| Codex App Server adapter (stdio, pin, profile) | yes | yes (fake subprocess) | **yes**: initialize, account/read, config/read, model/list, schema compatibility, pin | no | sign-in (owner) |
| Spend boundary (`spend.py`) | yes | yes, including fabricated-evidence tests | partly: before sign-in it correctly stays BLOCKED | no | **provider capability** (see below) |
| Guided setup (`setup`) | yes | yes | yes, up to the sign-in step | — | sign-in (owner) |
| Bounded live pilot (`pilot`) | yes | yes (all 4 scenarios) | — | **no** | the spend boundary |
| Routing suitability (95% goal) | rules rev. 3 | yes, on 420 synthetic prompts | — | no | real prompts (owner) |

## 1. Zero added spend: what the provider actually supports

The owner's requirement splits into three separate questions. None of them answers another.

| Question | Answer | How it is enforced or known |
|---|---|---|
| **(a)** Can the router use paid API credentials or fall back to a paid API? | **No.** Enforced by the router. | API-key auth is refused (`account.type` must be `chatgpt`). The dedicated profile sets `forced_login_method = "chatgpt"`, which `config/read` validates on the real binary. API-key variables are never passed to Codex. No paid API is called anywhere. |
| **(b)** Can the router buy credits, turn on reload, or redeem resets? | **No.** Enforced by the router. | `account/rateLimitResetCredit/consume`, `account/sendAddCreditsNudgeEmail`, login/logout and config writes are hard-blocked in the JSON-RPC client. **Whether your account has automatic reload switched on is not exposed** to Codex clients: there is no such field in the App Server protocol or the backend models (checked in upstream source). |
| **(c)** Can a request consume credits you have *already purchased*? | **Personal plans (Plus/Pro/…): yes, and nothing can prevent it.** **Business/Enterprise/Edu workspaces: preventable** with a member credit limit of 0. | See below. |

### Evidence for (c)

- **Personal plans.** OpenAI's help-centre text (quoted in search results; the site itself is blocked from this container) says purchased credits "apply to eligible activity on the same account after your included usage is used". It documents automatic reload, but no switch to stop credits being used. The Codex feature request *"Add a toggle to prevent automatic use of purchased Codex credits"* ([openai/codex#28382](https://github.com/openai/codex/issues/28382), opened 15 June 2026) is still **open**, with no maintainer reply.
- **Mid-task roll-over.** The same request describes a task that "may begin using the included allowance and then automatically consume purchased credits". Checking `ordinaryUsageAllowed` or usage percentages before a send therefore cannot guarantee zero spend for the whole turn.
- **Workspace plans.** The help article *"Managing credits and spend controls in ChatGPT Business"* says owners and admins set monthly credit limits per seat type and per member, and that when a member reaches the limit, Codex usage pauses. The provider reports this to clients as `rateLimits.individualLimit {limit, used, remainingPercent, resetsAt}` and `spendControlReached`, which come from `SpendControlStatusDetails` in openai/codex `backend-client` (verified in upstream source at commit `d9275a6`).

### What the router does

- `spend.py` holds a code-defined registry of mechanisms. The only entry is `workspace_member_zero_credit_limit`. It returns ALLOWED_INCLUDED_ONLY only when **all** of these hold:
  - the plan is a workspace plan;
  - every usage snapshot where credits can apply reports a member credit limit of exactly 0;
  - credits are not unlimited;
  - the signals are live, not synthetic, and belong to this account;
  - the adapter pin is valid.

  It is re-checked before every send. A limit or credit notification during a turn triggers a re-check, and the turn stops if sends are no longer allowed.
- Nothing else can allow a send. Hand-written "enforcement" records in the pin file are ignored. `decide_spend` has no file or record input at all. Usage percentages, zero balances, owner attestations and screenshots are *supporting* observations only. Tests fabricate each of these, and every one stays UNKNOWN (`tests/test_spend.py`).

### Missing capability (why live sends are blocked on a personal plan)

> OpenAI provides no control that stops purchased credits being applied after included usage on personal ChatGPT plans, and the automatic-reload setting is not exposed to Codex clients.

It would unblock if either of these happens: OpenAI ships the requested toggle (the router would then add it as a second mechanism), or you use Codex through a ChatGPT workspace where your member credit limit is set to 0.

## 2. Codex App Server: real-binary evidence

[evidence/real-codex-0.157.0-2026-09-25.json](evidence/real-codex-0.157.0-2026-09-25.json): `npm @openai/codex@0.157.0` (linux-x64, the same release as the macOS build), unauthenticated, no model turn.

- **VERIFIED:**
  - stdio JSON Lines framing;
  - `initialize`/`initialized`, `account/read` (returns `account: null`, `requiresOpenaiAuth: true`), and `config/read`;
  - the dedicated profile's `forced_login_method=chatgpt`, with no provider override;
  - the installed schema has every method and field the adapter needs (schema digest `1bf42c6f…`);
  - the pin (binary sha256 `1a822376…`).
- **`model/list` before sign-in** returns the CLI's bundled catalogue: `gpt-6-astra`, `gpt-6-sol`, `gpt-6-luna`, `gpt-5.6-sol`, `gpt-5.6-terra`, `gpt-5.6-luna`, `gpt-5.5`, with reasoning efforts from `low` to `ultra`. These names match your Astra, Sol, Terra and Luna families. They are **not yet confirmed for your account**; setup re-discovers them after sign-in.
- **`account/rateLimits/read`** returns "authentication required" before sign-in, as expected.
- **Not verified:** turns on the real binary, `clientUserMessageId` echo, per-turn model attestation, and macOS behaviour. The upstream schema check from the first round still holds ([evidence/upstream-schema-compat-2026-09-25.json](evidence/upstream-schema-compat-2026-09-25.json)).
- **Blocked sites:** `learn.chatgpt.com`, `developers.openai.com` and `help.openai.com` are blocked by this container's network proxy. Help-centre wording above comes from search-result excerpts.

## 3. Routing suitability (the 95% goal)

[evidence/routing-suitability-2026-09-25.json](evidence/routing-suitability-2026-09-25.json). Independent agents wrote realistic prompt sets without seeing the classifier:

| Rules | Set | Exact | Under-routed | Over-routed | Use |
|---|---|---|---|---|---|
| rev 1 | dev set 1 (120) | 61.7% | 9 | 37 | first measurement |
| rev 1 | dev set 2 (150) | 49.3% | 10 | 66 | baseline |
| rev 2 | dev set 2 (150) | 77.3% | 16 | 18 | held-out, then used for tuning |
| rev 3 | dev sets 1 + 2 | 99.2% / 98.7% | 0 / 0 | 1 / 2 | fitted: says little |
| **rev 3** | **final test (150)** | **86.0%** | **14 (9.3%)** | 7 (4.7%) | **scored once, never tuned on** |

**The 95% goal is not met on synthetic prompts, and it has not been measured on your real prompts.** The final-set misses are listed in the evidence file. Under-routed examples include a JWT middleware fix and a "safe to upgrade on Friday with no staging?" question. The weekly report measures the real override rate once live use starts. An optional external classifier can be plugged in, but it cannot lower hard floors, and it doesn't change subscription access.

## 4. Other gates

| Gate | Status | Evidence |
|---|---|---|
| Offline tests | VERIFIED (synthetic) | `python3 -m unittest discover -s model-router/tests -q` → 188 tests OK |
| Offline routing-policy evaluation | VERIFIED (synthetic) | 33/33 fixture cases; judge self-check usable ([evidence/offline-eval-2026-09-25.json](evidence/offline-eval-2026-09-25.json)) |
| Routing latency | VERIFIED (build container, simulator) | warm p50 1.5 ms, cold p50 3.0 ms ([evidence/latency-build-container-2026-09-25.json](evidence/latency-build-container-2026-09-25.json)); not measured on your Mac |
| Automatic resume | VERIFIED (synthetic) | `tests/test_scheduler.py`: bounded backoff (30 s → 15 min), reset times only move the next check earlier, cancellation, the foreground turn wins, sleep is detected and reconciled, two routers produce one send |
| ChatGPT sign-in, account models, usage buckets | BLOCKED | needs your sign-in; `setup` does it via Codex's own login |
| Live pilot | BLOCKED | `pilot` refuses to start until the spend boundary is VERIFIED |
| Text PDFs | BLOCKED here | `pdftotext` not installed in this container |
| ChatGPT web / Codex desktop control | UNSUPPORTED | no supported integration; the terminal client only |
