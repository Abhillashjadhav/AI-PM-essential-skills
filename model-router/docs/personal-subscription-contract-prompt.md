# Reusable personal-subscription operation — approved scope

Implement the owner's requested production path for subscription-backed Codex.
The owner confirmed automatic credit purchases are disabled and asked for normal
use and a reusable public product, not a special two-request bypass. No merge or
release is authorized. Do not commit the owner's screenshot, account data or logs.

Replace the blanket personal-plan exclusion with an explicit opt-in policy. Each
installer must confirm automatic reload is off for their own signed-in account
and understand that the client cannot monitor changes to that setting. This is
supporting evidence, not a provider-enforced guarantee. Store confirmation locally,
bound to account, plan, dedicated profile and approved Codex installation. Provide
status and disable commands. Never infer confirmation from the author's account.

Every send still needs fresh, consistent, live account and usage information,
ChatGPT authentication, a valid installation pin, included usage allowed, zero
credits, hasCredits=false and unlimited=false for every reported limit. Missing,
invalid, conflicting or stale signals block. Account/profile/pin changes require
new confirmation; observed credits revoke it. Usage exhaustion only pauses work,
so it can resume on the same pinned model after included usage returns. No credit
purchase, paid API fallback, reset redemption or silent model replacement.

Use ALLOWED_ACCOUNT_CONFIRMED, separate from ALLOWED_INCLUDED_ONLY. Display the
dependency and confirmation date honestly. Keep existing strict provider-control
operation available. Tests must cover happy-path dispatch, all rejection cases,
cross-process revocation, setup reruns, persistence and queued-work isolation.

Run the two public task probes once on the owner's Mac after offline verification.
Report actual answers and provider configuration separately from per-turn model
attestation. Neither two probes nor offline passing tests establish 95% routing
accuracy or production readiness. Native Codex's composer remains unintegrated.
