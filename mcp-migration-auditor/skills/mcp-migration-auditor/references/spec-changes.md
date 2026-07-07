# Verified spec changes — MCP 2026-07-28 release candidate

Every audit rule in SKILL.md traces to this file. Each entry quotes or closely
paraphrases an official source and links it. If a claimed "breaking change"
isn't here, the auditor treats it as unverified.

Primary sources:
- **[BLOG]** "The 2026-07-28 MCP Specification Release Candidate" — official MCP blog:
  https://blog.modelcontextprotocol.io/posts/2026-07-28-release-candidate/
- **[CHANGELOG]** Key Changes, MCP specification changelog:
  https://modelcontextprotocol.io/specification/draft/changelog
- SEP pull requests live at https://github.com/modelcontextprotocol/modelcontextprotocol/pull/<SEP-number>

Verified: 2026-07-07 (this file's audit rules reflect the RC as announced; re-verify against [CHANGELOG] if the final spec diverges after July 28, 2026).

---

## Timeline [BLOG]

- Release candidate locked: **May 21, 2026**
- Final specification: **July 28, 2026**
- "Ten weeks for SDK maintainers and client implementers" to validate.

## R1 — Sessions removed (SEP-2567) [BLOG, CHANGELOG]

- "The `Mcp-Session-Id` header and the protocol-level session that came with it are removed."
- "Any MCP request can land on any server instance, and the sticky routing and shared session stores that horizontal deployments needed before are no longer required at the protocol layer."
- Migration pattern, quoted: "The explicit-handle pattern simply makes the state visible to the model rather than hidden away" — servers mint handles from tools; models thread identifiers across calls.
- SEP-2567 title: "Sessionless MCP via Explicit State Handles".

## R2 — Handshake removed (SEP-2575) [BLOG, CHANGELOG]

- "The specification makes MCP stateless by removing the `initialize`/`notifications/initialized` handshake."
- "Every request now carries its protocol version, client identity, and client capabilities in `_meta`. Version mismatches return `UnsupportedProtocolVersionError`."
- New `server/discover` method lets clients fetch server capabilities up front.
- Related transport changes: `Mcp-Method` and `Mcp-Name` headers required (SEP-2243); list/resource results carry `ttlMs` and `cacheScope` (SEP-2549); server-initiated requests only during active client request processing (SEP-2260); Multi Round-Trip Requests replace SSE streams via `InputRequiredResult` with `requestState` (SEP-2322).

## R3 — Roots, Sampling, Logging deprecated (SEP-2577) [BLOG, CHANGELOG]

- "The Roots, Sampling, and Logging features are deprecated (SEP-2577). The methods, types, and capability flags continue to work in this release and in every specification version published within a year of it, and removing any of them will require a separate SEP under the lifecycle policy."
- Official replacements [BLOG]:
  - Roots → tool parameters, resource URIs, server config
  - Sampling → direct LLM provider API integration
  - Logging → `stderr` (stdio servers); OpenTelemetry (structured logging)

## R4 — Tasks moved to an official extension (SEP-2663) [BLOG]

- Tasks moved from core experimental feature to official extension. "Anyone who shipped against the `2025-11-25` experimental Tasks API will need to migrate to the new lifecycle."
- New lifecycle: server answers `tools/call` with a task handle; client drives via `tasks/get`, `tasks/update`, `tasks/cancel`; **`tasks/list` removed** ("cannot scope safely without sessions").
- Extensions framework (SEP-2133): reverse-DNS IDs, negotiated via `extensions` map, versioned independently in `ext-*` repositories.

## R5 — Authorization hardening (six SEPs) [BLOG]

- `iss` parameter validation required on authorization responses per RFC 9207 (SEP-2468).
- Clients declare OpenID Connect `application_type` during Dynamic Client Registration (SEP-837).
- "Credentials bound to issuing authorization server's `issuer`; re-register on migration" (SEP-2352).
- Refresh token request guidance for OpenID Connect (SEP-2207); scope accumulation during step-up clarified (SEP-2350); `.well-known` discovery suffix documented (SEP-2351).

## R6 — Unaffected deployments [BLOG]

- "Stdio and local transports — using standard input/output directly — operate independently of Streamable HTTP statelessness requirements and session infrastructure changes."

## Deprecation policy (SEP-2596) [BLOG, CHANGELOG]

- Feature lifecycle: Active → Deprecated → Removed, with "at least twelve months between deprecation and the earliest possible removal."
- Conformance requirement (SEP-2484): a Standards Track SEP cannot reach Final without a matching scenario in the conformance suite.

## Client-code note — error code change (SEP-2164) [BLOG]

- Missing-resource error changes from MCP-custom `-32002` to JSON-RPC standard `-32602` Invalid Params. "Update client code matching literal `-32002`."

## Schema note (SEP-2106) [BLOG]

- Tool `inputSchema`/`outputSchema` support full JSON Schema 2020-12 (composition, conditionals, `$ref`); implementations must not auto-dereference external URIs. Informational for tool authors; not an audit verdict on its own.
