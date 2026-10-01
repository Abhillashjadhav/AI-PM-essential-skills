# Model Router

A local terminal tool that picks a suitable model tier for each new chat and keeps that choice fixed for the whole chat. When you accept an architecture, it opens a separate implementation chat for you. GPT work uses the existing subscription eligibility checks. Optional TypeSafe Jev classification uses provider-managed credits.

> **TypeSafe update, 2026-09-27:** Jev integration is implemented and tested offline. TypeSafe enforces its credit limits; there is **no local spending cap**. The router runs on your Mac, while Jev and GPT run online. Run it inside the desktop app's integrated terminal if available. It does not intercept the native Codex/ChatGPT composer. [Architecture and activation](docs/jev-integration.md) · [Return-to-work note](docs/owner-follow-ups.md).

> **Status: not complete. Built and tested offline; live GPT sends are blocked because no verified included-only mechanism exists for personal ChatGPT plans.** The router, automatic resume, one-command setup and the bounded pilot are built and tested offline (280 tests in the main-based integration, including Jev). The Codex adapter was verified against the real Codex CLI 0.157.0 up to sign-in. **No real GPT turn has been established for this integrated tree.**
>
> On a personal plan the router can verify a zero credit balance live. It cannot verify that automatic reload is off, and it cannot guarantee that no purchase happens during a task, so the ₹0 rule keeps live sends blocked. That is a missing provider guarantee, not proof that personal plans can never work. A workspace member credit limit of 0 is a documented control, but it is **unverified** until a real account shows it working. Routing quality on unseen synthetic prompts: 78.5–81.5% exact for rules revisions 5–7, each scored once on 200 prompts it had never seen (6–10.5% under-routed). The 95% real-use goal needs real use. Details: [docs/capability-evidence.md](docs/capability-evidence.md). Routing works **only in this terminal client**.

## Try it (no account needed)

```bash
python3 model-router/router.py demo                     # synthetic end-to-end walkthrough
python3 -m unittest discover -s model-router/tests -q   # offline tests (no network, no account)
python3 model-router/router.py eval run --offline --simulate
```

What the demo shows (every step is SIMULATED):

```text
Project: Portfolio
You: Review this product architecture for CSV export and finalise it.
Router: Highest reasoning — architecture decision. Model stays fixed for this chat.
You: Approved, implement this.
Router: Architecture saved. Opening implementation in this project.
Router: Middle reasoning — implementation from the agreed architecture.
Router: Included usage is unavailable. Work is saved.
Router: This chat will continue with the same model when it becomes available ...
Router: Using the approved lower model for this new coding chat:
the steps are clear, the work is low risk, and included usage looks tight.
```

## On your Mac

```bash
python3 model-router/router.py setup    # pin Codex, ChatGPT sign-in, approve models, check spend (no model turn)
python3 model-router/router.py pilot    # bounded live check; refuses unless the spend boundary is verified
```

Or hand the rest to Codex on your Mac with one prompt: [docs/local-pilot.md](docs/local-pilot.md).

## Prerequisites

- Python 3.11 or newer. Only the standard library is used, with no `pip install`.
- For live use (later): the Codex CLI on your Mac, signed in with ChatGPT under the router's own profile, then `doctor`, `adapter pin`, and a verified spend boundary.
- Optional: `pdftotext` (poppler-utils) for text PDFs. Without it, PDF input is reported as BLOCKED.

## Commands

| Command | What it does |
|---|---|
| `router.py setup` | One guided setup. It pins the installed Codex CLI, checks the router's own ChatGPT-only profile, opens Codex's sign-in if needed, approves one model per role, and checks the spend boundary. |
| `router.py pilot` | A bounded live pilot of at most 8 turns: normal answer, handoff, override, restart/resume. It only runs when the spend boundary is verified. |
| `router.py serve` | Keeps queued work resuming automatically while this window is open. |
| `router.py doctor` | Read-only checks: Python, local store, Codex CLI version and checksum, protocol schema, sign-in, config, models, usage, spend boundary. It runs no model turn and prints no credentials. |
| `router.py demo` | Synthetic walkthrough in a temporary folder. |
| `router.py project add --name <name> --path <dir>` | Links a project name to a working directory. |
| `router.py chat --project <name>` | Starts chatting. Add `--simulate` to use the simulator. |
| `router.py threads --project <name>` | Lists chats and their fixed models. |
| `router.py resume <thread-id>` | Continues a chat, and any queued work, on the same model. |
| `router.py model set <thread-id> <model-id> [--reason quality\|task\|preference]` | Deliberately changes one chat's model. |
| `router.py models [list\|propose\|approve]` | Shows discovered models and approved roles, and approves a mapping. |
| `router.py eval run --offline` | Routing-policy and grader checks. No model calls. |
| `router.py eval report --week 2026-W39` | Weekly JSON and Markdown report. |
| `router.py status` | Queued or blocked work, and process memory. |
| `router.py wake` | Recovers after a restart and re-checks queued work. |
| `router.py recover <job> resend\|drop` | Answers a question about a send whose outcome is uncertain. |
| `router.py import --file <export.json>` | Imports an authorised export in the documented format. |
| `router.py export [--private]` | Diagnostic export. Redacted unless you ask for `--private`. |
| `router.py adapter pin [--approve <digest>]` | Measures, then pins, the installed Codex CLI. |

Inside `chat`, you can use: `/attach`, `/fetch`, `/history`, `/cancel`, `/model`, `/choose`, `/done`, `/feedback`, `/newtask`, `/finalise`, `/wake`, `/recover`, `/threads`, `/status`, `/help`, `/quit`.

## How routing works (plain language)

1. Your first message in a new chat is classified by local rules. With optional Jev enabled, an eligible text-only first prompt also gets a structured TypeSafe classification. Rules alone use no model call or confidence score. Quoted text and attachments count as data, never as instructions.
2. Consequences set a minimum tier. Architecture, product or UI decisions, résumés, LinkedIn posts, research articles, job applications, and coding that touches money, privacy or security go to **highest**. Ordinary implementation goes to **middle**. Routine notes, summaries, messages and literal extraction go to **lowest**. If the router isn't sure, it goes **up** and says why.
3. The choice is saved before anything is sent, and it stays fixed for that chat. Usage changes, new models and registry updates never move an existing chat. Only you can, with `/model` or `model set`.
4. If automatic routing takes longer than 4 seconds, your message is kept and you choose the model. A late automatic result is discarded.

The retired "80% priority + 20% usage" formula isn't used. The only usage-driven downgrade happens once, when an implementation chat is created. It applies only if the architecture is **proven** clear and simple, the work is low risk, an approved and capable lowest model exists, **and** capacity is estimated TIGHT. Capacity is **UNKNOWN** until you approve a calibration, so out of the box there's no downgrade.

## Optional classifier plugin

For the built-in TypeSafe integration:

```bash
python3 model-router/router.py jev setup    # private local key entry; no network call
python3 model-router/router.py jev pilot    # six example Jev calls; no GPT or queued work
python3 model-router/router.py jev status   # status and usage, no network
python3 model-router/router.py jev disable  # return to rules
```

Provider errors stop Jev calls until you reactivate locally. Your existing model pins and GPT spend gate are unchanged. See the [complete Jev guide](docs/jev-integration.md) for limitations, credit behavior, and testing.

The deterministic rules remain available without configuration. Alternatively, set `MODEL_ROUTER_CLASSIFIER=package.module:function` to consult another classifier (for example a local model). This explicit plugin takes precedence over built-in Jev; external plugins are ignored in simulation. A plugin can raise a role or classify a task the rules didn't recognise, but cannot lower a hard floor. If it fails, the rules take over. A classifier does not change GPT subscription eligibility.

## Approving models

The default configuration contains no executable model IDs. "Astra (highest)" and "Sol (middle)" are labels only.

```bash
python3 model-router/router.py models propose           # suggestions by family name (name match only)
python3 model-router/router.py models approve --role middle --model <id> --effort <e>
# review the exact mapping and evidence, then re-run with --confirm <hash> printed above
```

An approval is bound to that exact model, setting, tool scope and evaluation list. It creates a new registry revision that applies to **new** chats only. New models are recorded as candidates and are never promoted automatically.

## Queued work and resume

If included usage runs out, the chat is saved (with a checkpoint if a turn was cut short) and queued. **While `chat` or `serve` is open, the router re-checks automatically**:
- It starts at 30 s and doubles up to 15 min, or checks sooner around a reported reset time.
- Every check re-reads sign-in, spend and usage fresh, holds the dispatch lease, and continues **on the same model**.
- Your foreground turns always go first.

Nothing runs while the router is closed or the Mac is asleep. After the Mac wakes, the router reconciles any uncertain sends before continuing. `wake`, `resume` and `/wake` still work by hand. The router never redeems reset offers, buys credits, or changes payment settings. If a send's outcome is uncertain after a crash, the router doesn't resend it. It asks you instead.

## Data, privacy and removal

- Data location: `~/Library/Application Support/AI-PM-Model-Router/` on macOS, `$XDG_DATA_HOME/AI-PM-Model-Router/` (or `~/.local/share/...`) elsewhere. Override with `--data-dir` or `MODEL_ROUTER_DATA_DIR`. `--simulate` uses a separate `simulator/` subfolder.
- The directory is `0700` and files are `0600`. **No encryption at rest is claimed** beyond what your operating system provides.
- Conversations, résumés, usage responses and provider logs stay in that directory. They are never written to this repository. Records are kept until you delete them.
- GPT credentials are handled by Codex's own sign-in, under a dedicated `CODEX_HOME` (`<data-dir>/codex-home`). API-key environment variables, including TypeSafe's, are never passed to Codex. Optional Jev stores its separate private key and request audit records under `<data-dir>/jev/`; it sends eligible first-prompt text to TypeSafe.
- **To remove the tool** without losing data: delete the `model-router/` folder. Your records stay in the data directory. **To remove the data**, delete that directory yourself. The router never deletes it. No background service is installed.

## Test inputs and expected outputs

These come from the synthetic routing fixtures (`fixtures/routing-cases.json`) and the implementation branches (`fixtures/implementation-cases.json`):

| Input | Expected |
|---|---|
| "Quick check: is this SQL safe on production?" | highest (the word "quick" doesn't lower it) |
| "Just rewrite my LinkedIn post" | highest |
| "Extract the dates from my resume" | lowest |
| "Implement the CSV export per the agreed architecture" | middle |
| Clear, low-risk implementation with TIGHT capacity and an approved lowest model | lowest |
| The same, with UNKNOWN capacity | middle |

More: [docs/architecture.md](docs/architecture.md) · [docs/decisions.md](docs/decisions.md) · [docs/capability-evidence.md](docs/capability-evidence.md) · [docs/local-pilot.md](docs/local-pilot.md) · [PRD](../prds/2026-09-25-model-router.md) · [original prompt](docs/implementation-prompt.md)
