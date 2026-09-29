# Terminal activation and demonstrated boundaries — 29 September 2026

## Task and diagnosis

The owner ran Jev setup, pilot and comparison, and expected the normal Codex
app's first prompt to choose a GPT model. Complete the unblocked terminal
experience, demonstrate it, and make remaining blockers explicit. Do not merge
main, spend money, weaken the GPT spending checks, or invent host integration.

VERIFIED from source: the shipped adapter receives prompts only through
`router.py chat`. Nothing registers a first-prompt/model-selection integration
with Codex's normal composer. Jev commands never start GPT work. Installing or
fetching this repo does not activate the native Codex composer.

The current `spend.py` deliberately returns UNKNOWN for personal ChatGPT plans,
including Pro, even with zero credit balance and included usage available. This
is a restriction of this implementation's strict included-only guarantee, not
evidence that personal plans cannot use Codex. Keep it in place until a supported
enforcement mechanism is verified or the owner explicitly changes that contract.
Do not recommend paying for another plan as a silent implementation choice.

## Latest owner-reported Jev result

Comparison run `57c06ef4ea824319a1a13c500ce2a0c4`, code `92df321`:

- 20 requests completed; request 21 timed out. Zero GPT calls.
- Ten cases have both results: baseline 49/50 checks, candidate 50/50.
- Ordinary code: baseline highest with consequence 0.30; candidate middle with
  consequence 0.17. The other nine completed cases matched their expected tier.
- The architecture-reconsideration and mixed decision/coding cases remain
  incomplete/unrun. Full denominator remains 60 checks per variant.
- Result is incomplete; no promotion. This is not 95% real-task accuracy proof.
- Existing Jev failure behavior disables further Jev calls on timeout until the
  owner intentionally runs `jev setup` locally again. Local routing rules remain
  available. Do not retry this uncertain request automatically.

## Implement

1. Add `router.py start --path <project>`: disclose terminal-only operation,
   display Jev's enabled/disabled reason, run the existing guided live setup,
   and open terminal chat only if that setup passes. Reuse existing credentials
   and approvals; no new dependency or billing configuration. Live mode must
   require an interactive terminal. Never present blocked setup as activation.
2. `start --simulate` opens an interactive, prominently labelled offline demo
   using the existing fake models and separate simulator store. It may seed only
   synthetic bindings. It must ignore live external classifiers and never log in,
   call Jev/GPT, or change the live registry.
3. Register a project idempotently by exact name/path. Refuse a name collision
   with another directory; do not remap or delete the existing project.
4. Display the actual chosen model ID before its first response.
5. Add `/new` to start another chat in the same terminal/project. The previous
   chat and pin remain saved. Never discard pending attachments silently.
6. Fix the CLI's architecture-to-implementation focus: after a CREATED/EXISTING
   handoff, both natural approval and `/finalise` must direct subsequent input
   to the implementation thread. A held/blocked handoff keeps the existing chat.
7. Close the short-lived project-registration coordinator, adapter and store
   before handing control to the existing chat lifecycle.

Test actual CLI subprocesses and real coordinator/store interactions with the
fake adapter. Include the handoff regression failing on prior code. Preserve
first-prompt classification, thread pins, approvals and spend checks. Publish on
a feature branch with a draft PR and report exact demo/test evidence.

## Supported workflow and unresolved work

Inside Codex's integrated terminal (or Mac Terminal), run `start`, type a task at
`You:`, see its selected model, and continue that pinned chat. `/new` starts the
next chat; approved architecture handoff switches focus to implementation.

This is not the native Codex composer. The official UserPromptSubmit hook can
add context or block a prompt but does not document a model-switch output.
App Server documents a model parameter when the custom client creates a thread.
Inference: the documented hook is insufficient for native automatic model
selection; do not install a no-op hook and claim activation.

Official sources checked 29 September 2026:

- https://learn.chatgpt.com/docs/hooks (UserPromptSubmit and common output fields)
- https://learn.chatgpt.com/docs/app-server (thread/start and model/list)
- https://learn.chatgpt.com/docs/environments/local-environment (actions run in
  the integrated terminal; their configuration uses the app settings UI)

Owner Mac status/real GPT execution are not accessible from this cloud runtime.
Demonstrate simulated behavior explicitly. Native automatic composer routing,
the personal-plan spending contract, and complete live Jev evaluation remain
open. Neither a green unit-test suite nor a scripted demo closes these gaps.
