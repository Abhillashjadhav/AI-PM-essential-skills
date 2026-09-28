# Expected audit for the synthetic sample configuration

Manual fixture, revised 2026-09-28. This is expected output, not a recorded skill
run or a live server check. Findings assume a migration to protocol 2026-07-28;
confirm the deployed versions before applying them to an existing service.

| Server | Finding | Evidence and action |
|---|---|---|
| ticket-gateway | BREAKS under target session rules (R1) | Config declares an HTTP session dependency. Replace that dependency with explicit state handling; verify the implementation before changing infrastructure. |
| research-assistant | DEGRADED for confirmed sampling use (R3) | The fixture confirms sampling. Plan migration and inspect method-level changes; deprecation alone is not proof of an immediate outage. |
| local-files | SAFE for the HTTP-session check only (R6) | Uses stdio. Hidden capabilities and other protocol requirements remain unconfirmed. |

Prioritize the declared session dependency, then the sampling migration. Ask
about Tasks and other uninspected behavior. Do not remove a session store merely
because the protocol no longer requires one; it may hold application state.

Sources and exclusions: [source ledger](../references/spec-changes.md).
