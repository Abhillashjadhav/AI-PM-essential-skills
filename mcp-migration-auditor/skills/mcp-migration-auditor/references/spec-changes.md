# Source ledger — MCP 2026-07-28

Rechecked 2026-09-28 against the versioned specification. July 28 is a past
revision date, not a future deadline. Audit the deployed protocol version and
implementation; the calendar alone cannot establish that a server broke.

| Rule | Scoped finding | Primary source |
|---|---|---|
| R1 | Streamable HTTP no longer has protocol sessions; move required cross-call state into explicit handles. | [Transport](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http), SEP-2567 |
| R2 | The old initialization handshake is replaced by per-request metadata and capability discovery. Client identity is recommended, not universally mandatory. | [Changelog](https://modelcontextprotocol.io/specification/2026-07-28/changelog), SEP-2575 |
| R3 | Roots, Sampling and Logging are deprecated. Deprecation does not mean immediate removal; individual method changes need separate inspection. | [Changelog](https://modelcontextprotocol.io/specification/2026-07-28/changelog), SEP-2577 |
| R4 | The experimental Tasks API moves to an extension with a changed lifecycle. | [RC announcement](https://blog.modelcontextprotocol.io/posts/2026-07-28-release-candidate/), SEP-2663 |
| R5 | Validate a present authorization-response `iss`; bind credentials to their issuer; supply the appropriate DCR application type where DCR is used. | [Changelog](https://modelcontextprotocol.io/specification/2026-07-28/changelog), SEP-2468/2352/837 |
| R6 | HTTP session changes alone do not establish a stdio transport failure. Other protocol and capability checks still apply. | [RC announcement](https://blog.modelcontextprotocol.io/posts/2026-07-28-release-candidate/), unaffected deployments |

The [lifecycle policy](https://modelcontextprotocol.io/community/feature-lifecycle)
sets a normal minimum twelve-month window from the revision introducing a
deprecation. Removal needs a subsequent change; an expedited security exception
exists. Check the registry and actual SDK support instead of promising a fixed
removal date from an old announcement.

## Scope limits

R1–R6 are selected migration checks, not a full conformance suite. The versioned
changelog also lists result envelopes, subscriptions, method removals, cache
metadata, headers and DCR deprecation. A `SAFE` finding applies only to the named
checks supported by evidence. Uninspected rules stay `UNCONFIRMED`; do not certify
all of 2026-07-28 compatibility from a config file.
