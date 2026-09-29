# Personal subscription operation

This version supports ordinary terminal chat using an existing personal ChatGPT
subscription. It is not limited to a two-turn test. It adds no API-key fallback,
purchase action, payment integration or local model download.

**Release status: implementation and offline tests complete; live Mac validation,
independent review and the real-use accuracy target remain open.** No release or
merge is implied. Native Codex and ChatGPT chat boxes are not connected.

## Install and use

Python 3.11+ and the local Codex CLI are required. No pip dependencies. While the
PRs are draft, reviewers can clone the complete branch:

```bash
git clone --branch docs/model-router-personal-subscription --single-branch https://github.com/Abhillashjadhav/AI-PM-essential-skills.git model-router
cd model-router
python3 model-router/router.py setup
python3 model-router/router.py pilot --routing-check
```

Setup opens Codex's own ChatGPT login if needed. It asks you to approve the
highest, middle and lowest models available to your account. Each installer must
check **automatic reload is OFF** in their account's Usage settings and accept
the explained dependency. No confirmation is inherited from this repository.
Existing approved mappings and a still-valid billing confirmation are reused.

After reviewing the two task responses, start normal chat:

```bash
python3 model-router/router.py start --project my-project --path /absolute/path/to/your/project
```

Enter prompts at `You:`. The first prompt selects a model; follow-ups stay on it.
`/new` starts a fresh chat. `/model` is your override. A finalised architecture
opens a separate implementation thread, subject to the existing capability checks.
Coding/shell/web tool availability still needs verification; enabling billing
does not certify those tools or unblock a `BLOCKED_CAPABILITY` result.

Jev is optional and uses separate TypeSafe credits. An existing timeout remains
disabled until you intentionally run `router.py jev setup`. Local rules can run
the GPT test without Jev. Enabling GPT never re-enables Jev or promotes a prompt.

## What the billing check means

| Result | Meaning |
|---|---|
| `ALLOWED_INCLUDED_ONLY` | Existing code-recognized provider control; workspace behavior still needs live validation. |
| `ALLOWED_ACCOUNT_CONFIRMED` | You confirmed reload off, and current account/credit/usage checks passed. This authorizes normal chat, explicit pilots and queued work while the router is running. |
| `BLOCKED` or `UNKNOWN` | No send. Read the reason; no paid fallback. |

The second result is **not an absolute account-wide zero-spend guarantee**.
Codex does not expose the automatic-reload setting to this client. The router
cannot prevent a setting changing or credits being bought elsewhere during a
turn. Interrupting later cannot undo a purchase or usage already incurred.

Before each send, the router requires ChatGPT-only authentication, a valid pin,
matching account/plan, live observations at most 30 seconds old, included usage
explicitly allowed, known unexhausted windows and zero credits with
`hasCredits=false` and `unlimited=false` in every reported billing limit.
Malformed, missing or conflicting data blocks. It checks again after provider
thread creation/resume and on usage/account notifications during a turn.

Confirmation lives in the private local SQLite store and is bound to account,
plan, profile and Codex pin. It is retained until disabled or invalidated; it is
not a claim that the billing setting has been re-checked continuously. An account,
profile, plan or pin change requires confirmation again. Observed nonzero or
unlimited credits revoke it, including when included usage is exhausted.
Ordinary included-usage exhaustion only pauses; when usage returns, saved work
can resume on the same model while `chat` or `serve` remains open.

```bash
python3 model-router/router.py billing status
python3 model-router/router.py billing disable
```

Disable before buying credits or turning reload on, and close active router
sessions. Disable is seen by other processes at their next check; it does not
cancel an already sent request immediately. To enable again, run `setup` and
check the setting again. No periodic confirmation prompt or local spending cap
is added. These settings do not affect TypeSafe's separate credit policy.

## Reading the two-task test

The check runs one supplied-list formatting task and one architecture review in
two fresh evaluation chats, using your approved lowest/highest mappings. It
sends at most one explicit request per case and does not run other queued jobs.
It saves full answers and routing/dispatch evidence in the local data directory.

`configured_execution_passed: true` means both real responses completed with
matching requested models and provider-acknowledged thread configurations.
`MODEL_USE_UNVERIFIED` means Codex did not separately report the actual model
identity for each turn. `passed: true` requires that additional matching evidence.
The current adapter normally lacks it; do not ask the model to self-identify as
proof. The command exits 1 for incomplete model verification even if both answers
completed. Simulator output always remains `SIMULATED`, with both pass flags false.

This is integration evidence, not a 95% accuracy result. Read the actual answers.
Before public promotion, run real-task evaluations against the owner's weekly
95% no-correction target, resolve remaining capability/model-evidence issues,
complete independent review and obtain merge/release approval.

## Evidence for this revision

- 320 offline router tests pass, including 15 new personal-subscription tests
  plus two contract tests. Provider-process tests use a local fake App Server.
- Required checks pass: router tests, 107 ContextPort tests, compilation,
  privacy, whitespace and existing-skill impact checks.
- Checks cover actual JSONL dispatch of two distinct fixture models, normal
  chat, setup reuse, refusal, malformed/multiple limits, account/pin/profile
  changes, cross-process disable, pre-send revocation, pause/reset and mid-turn
  credit changes. No actual GPT or Jev call was made by these checks.
- Testing uncovered that the previous complex probe's security/implementation
  terms demanded editing tools. This probe now asks for an architecture review;
  that classifier/tool distinction remains an open issue, not an accuracy fix.

Official references checked 2026-09-29:
- https://learn.chatgpt.com/docs/pricing
- https://help.openai.com/en/articles/12642688-using-credits-for-flexible-usage-in-chatgpt-personal-plans

These explain included usage and account credit purchases. The distinction between
provider enforcement and owner-confirmed operation is this product's contract.
