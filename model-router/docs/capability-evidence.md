# Capability evidence (as of 2026-09-25)

Evidence levels:

- **upstream source:** the public openai/codex repository.
- **real binary:** the released Codex CLI 0.157.0, run in the build container without sign-in.
- **synthetic:** the simulator and a fake App Server.
- **documented / observed elsewhere:** OpenAI Help Center text, and reports on other people's accounts (GitHub issues). The latter are supporting only.
- **live account:** your Mac and ChatGPT account. There is no live-account evidence yet.

## Status at a glance

| Area | Implemented | Tested with simulation | Tested against the real Codex binary | Tested with real models | Blocked on |
|---|---|---|---|---|---|
| Routing, pins, overrides, handoff, queue, recovery | yes | yes (222 tests) | — | no | the spend boundary |
| Automatic resume while running (`chat`, `serve`) | yes | yes | — | no | the spend boundary |
| Codex App Server adapter (stdio, pin, profile) | yes | yes (fake subprocess) | **yes**: initialize, account/read, config/read, model/list, schema compatibility, pin | no | sign-in (owner) |
| Spend boundary (`spend.py`) | yes | yes, including fabricated-evidence and personal-plan tests | partly: before sign-in it correctly stays BLOCKED | no | **provider capability**: no verified included-only mechanism for personal plans (see below) |
| Guided setup (`setup`) | yes | yes | yes, up to the sign-in step | — | sign-in (owner) |
| Bounded live pilot (`pilot`) | yes | yes (all 4 scenarios) | — | **no** | the spend boundary |
| Routing quality | rules rev 7 | yes: 1,020 labelled synthetic prompts; held-out 81.5% (rev 5), 78.5% (rev 6), 80.0% (rev 7) | — | no | real use for the 95% goal |

## 1. Zero added spend: what can and cannot be verified

The owner's requirement splits into three separate questions. None of them answers another.

| Question | Answer | How it is enforced or known |
|---|---|---|
| **(a)** Can the router use paid API credentials or fall back to a paid API? | **No.** Enforced by the router. | API-key auth is refused (`account.type` must be `chatgpt`). The dedicated profile sets `forced_login_method = "chatgpt"`, which `config/read` validates on the real binary. API-key variables are never passed to Codex. No paid API is called anywhere. |
| **(b)** Can the router buy credits, buy a reset, turn on reload, or redeem resets? | **No.** Enforced by the router. | `account/rateLimitResetCredit/consume`, `account/sendAddCreditsNudgeEmail`, login/logout and config writes are hard-blocked in the JSON-RPC client. The router has no purchase path at all. |
| **(c)** Can a send consume purchased credits, or trigger a purchase, on *your* account? | **Personal plan: no verified included-only mechanism.** Live sends stay blocked. **Workspace plan with a member credit limit of 0: allowed by a documented control, UNVERIFIED** (not yet observed on a real account). | See below. |

### Evidence for (c), by kind

Each line says what kind of evidence it is. A user-filed GitHub issue is a report about one account, not a statement from OpenAI about every account.

**Documented provider behaviour** (OpenAI Help Center; `help.openai.com` is blocked from this container, so the wording comes from search-result excerpts of these articles):

- D1. *Using Credits for Flexible Usage in ChatGPT (Personal plans)*: "Your plan's included usage is used first. After you hit plan limits, usage draws from your credit balance."
- D2. Same article, automatic reload: "When your credit balance drops below your selected minimum balance, we automatically purchase enough credits to return it to your selected target balance, up to any maximum monthly spend you set … If your balance is already below the minimum when you turn it on, a purchase may happen right away." It can be turned off in Settings > Usage or the Codex app's Usage & Billing.
- D3. *Using Codex with your ChatGPT plan*: "if you reach a usage limit during an active turn, Codex can continue working on that turn, subject to fair-use limits."
- D4. *Paid weekly Work and Codex rate limit resets*: Plus and Pro users can buy an instant reset from Usage settings or from an in-app offer after reaching the weekly limit.
- D5. *Managing credits and spend controls in ChatGPT Business*: owners and admins set monthly credit limits per seat type and per member; when a member reaches the limit, Codex usage pauses.

**Observed behaviour on other people's accounts** (supporting only):

- O1. [openai/codex#31987](https://github.com/openai/codex/issues/31987) (open, labelled bug, 10 July 2026): the auto-recharge toggle "keeps getting turned back on", is pre-selected every time credits are bought, and caused an unwanted $10 charge.
- O2. [openai/codex#23511](https://github.com/openai/codex/issues/23511) (open, 19 May 2026, Pro): auto-reload shown as Active did not purchase when the balance was below the minimum.
- O3. [openai/codex#28382](https://github.com/openai/codex/issues/28382) (open feature request, 15 June 2026): asks for a toggle to stop purchased credits being used automatically. It is a request, not documentation.

**Observed behaviour on your account:** none yet. `setup` on your Mac records it (see [local-pilot.md](local-pilot.md)).

**What the Codex protocol exposes** (checked in openai/codex source at `d9275a6` and in the real 0.157.0 schema):

- I1. Readable per snapshot: `credits {hasCredits, unlimited, balance}`, `ordinaryUsageAllowed`, `individualLimit {limit, used, remainingPercent, resetsAt}`, `spendControlReached`, `rateLimitReachedType`, `planType`. Rolling `account/rateLimits/updated` notifications may omit `credits`; Codex's own client then keeps the previous value, so the router re-reads the full snapshot instead.
- I2. **Not readable anywhere:** whether automatic reload is on, its minimum/target balance, its maximum monthly spend, or the payment method. There is no reload, top-up or recharge field in the source or the schema.
- I3. No per-request option asks for "included usage only".

**Unknown until tested:** whether a personal account with a zero balance and reload off stops a turn at the included limit, or continues it under fair use (D3) without drawing anything; whether a turn can trigger a reload when the balance is already zero; and what your account reports (a zero balance, or no credit fields at all).

### Can included-only be established for a personal account with no purchased credits and reload off?

What the router can verify, live, before every send and again on every usage notification during a turn:

- the plan is personal and the account and usage signals agree;
- the credit balance is exactly 0, `hasCredits` is false and credits are not unlimited;
- included usage is allowed right now.

`spend.py` now records exactly these facts (`assess_personal_plan`) and shows them in `setup`, `doctor` and the pilot report. Even when every one of them holds, the decision stays **UNKNOWN**, for two reasons:

1. **Reload cannot be verified.** Its state is not exposed (I2), and O1 reports it turning itself back on. A zero balance is not proof that reload is off: O2 shows reload marked Active with a balance below the minimum.
2. **The protection does not hold throughout a task.** Credits can appear mid-task (a reload, or a purchase in another window). The router would see them only on its next read, after the purchase had already happened. D3 also says a turn can continue past the limit.

**The precise missing guarantee:** a provider-readable state, or a per-request option, that proves no credit purchase or credit use can happen for this account during the turn. Examples would be a readable reload state plus a documented stop at the included limit, or an "included usage only" request flag. If OpenAI ships one, it is added to `MECHANISMS` in code, with tests. Nothing the owner types or screenshots can stand in for it.

This does not mean personal plans are inherently unusable. It means there is **no verified included-only mechanism** today.

### What the router does

- `spend.py` holds a code-defined registry of mechanisms. The only entry is `workspace_member_zero_credit_limit`, labelled `documented_not_observed`. It returns ALLOWED_INCLUDED_ONLY only when **all** of these hold:
  - the account and usage signals both report the same workspace plan;
  - every limit where credits can apply reports a member credit limit of exactly 0;
  - credits are not unlimited;
  - the signals are live, not synthetic, and belong to this account;
  - the adapter pin is valid.

  It is re-checked before every send. A limit or credit notification during a turn triggers a re-check, and the turn stops if sends are no longer allowed. The label changes to `observed` only after a real account shows Codex pausing as documented.
- Personal plans get `assess_personal_plan`: verified facts, unmet conditions and the missing guarantee, always UNKNOWN.
- Nothing else can allow a send. Hand-written "enforcement" records are ignored, and `decide_spend` has no file or record input. Usage percentages, zero balances, owner attestations and screenshots are supporting observations only. Tests fabricate each of these, and every one stays UNKNOWN (`tests/test_spend.py`).

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

## 3. Routing quality on unseen prompts (not the 95% goal)

[evidence/routing-suitability-2026-09-25.json](evidence/routing-suitability-2026-09-25.json). The method: freeze a rules revision in a commit, then score it **once** on 200 new prompts. Two independent agents write each set, blind to the classifier and to every earlier set. A separate agent re-labels the set from the prompts alone. After scoring, the set becomes development data for the next revision.

| Frozen rules | Unseen set | Exact (95% interval) | Under-routed | Over-routed | Same set, older rules |
|---|---|---|---|---|---|
| rev 3 | final set (150) | 86.0% | 9.3% | 4.7% | — |
| rev 5 (`f50fa23`) | fresh set 1 (200) | **81.5%** (75.5–86.3%) | **6.0%** | 12.5% | rev 4: 78.5%, 9.0% under |
| rev 6 (`12e0d73`) | fresh set 2 (200) | **78.5%** (72.3–83.6%) | **9.0%** | 12.5% | rev 4: 71.5%; rev 5: 76.0% |
| rev 7 (`e7a7e1d`) | fresh set 3 (200) | **80.0%** (73.9–85.0%) | **10.5%** | 9.5% | rev 5: 71.5%; rev 6: 74.0% |

Model distribution on fresh set 2 (expected → observed with rev 6): highest 78 → 93, middle 59 → 50, lowest 63 → 57. Over-routing leans toward the highest tier, but the router does not send everything there. Label agreement between the authors and the independent re-labeller was 200/200 on set 1, 199/200 on set 2 and 199/200 on set 3. That shows the labels follow the written policy consistently. It does not show that you would label them the same way, because all the labellers are AI agents.

**What this means.** Each revision improves the same unseen prompts: fresh set 2 went 71.5% → 76.0% → 78.5% across revisions 4 to 6, and fresh set 3 went 71.5% → 74.0% → 80.0% across revisions 5 to 7. But each new, differently written set exposes new phrasings, so held-out accuracy sits around 78–82%, with 6–10.5% under-routed. The common under-routed categories were:
- security bugs described without security words ("change the id in the url and you see someone else's data");
- decisions written as lettered options;
- personal-data exports;
- money code where a rule mistook the task for styling (a revision 6 defect, fixed in revision 7).

Development-set scores are close to 100% and are fitted, so they say little.

**The 95% goal is a different measure.** It asks that 95% of your real chat threads stay on the model the router chose. Synthetic label matching can't show that. It needs real use and the weekly override report, and it is not claimed. Kev (an optional local classifier plugin) remains optional and is not installed, and no paid classifier is used.

## 4. Other gates

| Gate | Status | Evidence |
|---|---|---|
| Offline tests | VERIFIED (synthetic) | `python3 -m unittest discover -s model-router/tests -q` → 222 tests OK |
| Offline routing-policy evaluation | VERIFIED (synthetic) | 33/33 fixture cases; judge self-check usable ([evidence/offline-eval-2026-09-25.json](evidence/offline-eval-2026-09-25.json)) |
| Routing latency | VERIFIED (build container, simulator) | rules rev 6: warm p50 1.7 ms (p99 9.9 ms), cold p50 3.0 ms; worst adversarial 60,000-character input 0.52 s ([evidence/latency-build-container-2026-09-25.json](evidence/latency-build-container-2026-09-25.json)); not measured on your Mac |
| Automatic resume | VERIFIED (synthetic) | `tests/test_scheduler.py`: bounded backoff (30 s → 15 min), reset times only move the next check earlier, cancellation, the foreground turn wins, sleep is detected and reconciled, two routers produce one send |
| ChatGPT sign-in, account models, usage buckets | BLOCKED | needs your sign-in; `setup` does it via Codex's own login |
| Live pilot | BLOCKED | `pilot` refuses to start until the spend boundary is VERIFIED |
| Text PDFs | BLOCKED here | `pdftotext` not installed in this container |
| ChatGPT web / Codex desktop control | UNSUPPORTED | no supported integration; the terminal client only |
