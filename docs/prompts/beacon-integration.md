# Saved execution request

Implement the approved local Beacon integration across the existing repositories.
Keep workflows nonblocking, dashboards optional, and product decisions open for
review. Use focused QA around 5% of build effort. Start with LinkedIn OS correction
reuse; add thin adapters to other runtimes without changing their domain contracts.

Scope here: optional lifecycle integration for ContextPort and PM Verifier, a
registered command runner, pinned installation and coverage documentation. No real
exports, browser activity, scoring changes or external account writes are needed.

Provisional decision: shared package source lives in LinkedIn OS under
`packages/workflow_beacon`; extraction to its own repo can happen later without
changing workflow APIs. No user decision blocks this reversible branch.
