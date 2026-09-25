# Local pilot runbook (owner's Mac)

The pilot has not been run yet. Do the steps in order and stop at the first BLOCKED gate. None of these steps sends a model turn until step 5.

## 1. Read-only doctor

```bash
python3 model-router/router.py doctor
```

This checks Python, the data directory's permissions, the Codex CLI (version, checksum, launcher), protocol compatibility with the installed schema, ChatGPT sign-in under the router's own profile, effective config, discovered models, usage signals, and the spend boundary. If sign-in is BLOCKED:

```bash
CODEX_HOME="$HOME/Library/Application Support/AI-PM-Model-Router/codex-home" codex login
```

This is a separate profile, so your normal Codex settings are left alone.

## 2. Pin the installation

```bash
python3 model-router/router.py adapter pin                  # review the manifest and digest
python3 model-router/router.py adapter pin --approve <digest>
```

If Codex updates later, `doctor` reports drift, and sends are blocked until you re-pin.

## 3. Verify the spend boundary (release condition)

Live sends stay blocked while `doctor` shows `spend boundary: UNKNOWN`. See [capability-evidence.md](capability-evidence.md#what-would-unblock-live-sends). Don't bypass this step.

## 4. Approve role mappings

```bash
python3 model-router/router.py models            # discovered candidates
python3 model-router/router.py models propose    # name-based suggestions (Astra → highest, Sol → middle)
python3 model-router/router.py models approve --role highest --model <id> --effort <e>
```

Each approval prints a hash. Re-run the same command with `--confirm <hash>` to approve exactly that mapping.

## 5. Small, finite live checks (only after steps 1–4 pass)

- One normal answer (routine note → lowest).
- One architecture → "Approved, implement this" handoff in a scratch project.
- One manual override (`/model`).
- A restart during a queued job (`Ctrl-C`, then `router.py wake`).
- Simulate limits and errors rather than deliberately using up real usage.
- Record usage before and after each check (`status`). Deltas are rounded and shared with your other sessions, so don't read them as model efficiency.
- Treat a same-model comparison with ChatGPT web as "a different interface/system" unless the same model and settings are confirmed.

## 6. Mac performance

With your usual apps open, note memory pressure, any new swap growth, and responsiveness while `chat` is idle and while it is streaming. Existing swap doesn't count as a failure. `router.py status` reports the process's peak RSS. The routing latency for real sessions appears in `eval report`.

## 7. Weekly review (about 30 minutes or less)

```bash
python3 model-router/router.py eval report --week <ISO-week>
```

Read the guardrail with its sample size, the prioritised failures, the quality overrides, and the approval queue. Record outcomes with `/done` in chat, or `router.py outcome <thread> resolved|partial|failed|abandoned`.
