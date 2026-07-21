# Product decisions

These decisions describe the current public product boundaries. They do not attribute personal motivation. Any first-person account must be added only after explicit author review.

## Keep the four standalone skills small

**Decision:** Each standalone skill should encode one problem and one decision mechanism in an inspectable `SKILL.md` rather than becoming a general PM assistant.

**Why:** A small instruction surface is easier to inspect, install independently, compare with its stated output, and retire when a better mechanism supersedes it. The current evidence only establishes structure, so a narrow claim is more honest than a broad capability claim.

**Rejected alternatives:**

- One universal AI PM skill was rejected because it would mix unrelated triggers, decisions, and failure modes.
- Expanding every skill into an application was rejected because most of these mechanisms have not yet earned that implementation cost through behavioral evidence.
- Treating the four skills as a behaviorally tested bundle was rejected because no automated model-run suite is committed.

## Keep ContextPort local-first

**Decision:** ContextPort should run from a public checkout with standard-library Python, local artifacts, synthetic committed fixtures, and no required account, credential, telemetry, hosted model, or production dependency.

**Why:** Conversation content, filenames, project mappings, and derived reports are private by default. Local execution narrows data exposure, makes deterministic checks reproducible, and keeps the public product independent of private development systems.

**Rejected alternatives:**

- A hosted migration service was rejected because it would introduce private-data transmission, account security, retention, and operating-cost decisions that the current product does not solve.
- A model-dependent normalization service was rejected because it would make fidelity and repeatability harder to verify.
- A private runtime dependency was rejected because a public checkout would no longer be independently understandable or testable.

## Keep migration writes unsupported

**Decision:** ContextPort stops at approved reconstruction plans, reconciliation, and a fail-closed destination capability report. It does not write consumer ChatGPT projects, chats, or historical messages.

**Why:** The bounded public-interface review recorded in the [ChatGPT adapter documentation](../context-port/docs/CHATGPT_ADAPTER.md) did not verify the required consumer write interface. An API Platform project is not a substitute for a consumer ChatGPT Project. Invented endpoints, guessed browser selectors, and credential workarounds would turn uncertainty into data-loss and account risk.

**Rejected alternatives:**

- Guessing undocumented endpoints was rejected because attempted calls would not be evidence of a supported contract.
- Browser automation was rejected because no stable, approved selector and account-write workflow is implemented.
- Mapping the workflow to OpenAI API Platform projects was rejected because that is a different product surface.
- Reporting a plan as a completed migration was rejected because no destination effect was observed.

## Separate evidence levels

**Decision:** Portfolio claims use `STRUCTURAL`, `VERIFIED`, `RECORDED`, `UNKNOWN`, and `UNSUPPORTED` as separate evidence states.

**Why:** The repository contains instruction files, deterministic software, manual fixtures, public PR observations based on private data, and deliberately missing write capabilities. Combining these into “built and tested” would hide material differences in reproducibility and product risk.

**Rejected alternatives:**

- A single maturity badge was rejected because it would average unrelated evidence.
- Treating manual fixture documents as automated behavioral tests was rejected because no command executes the four standalone skills against them.
- Treating the private-export aggregate counts as deterministic public evidence was rejected because the private input and generated package are intentionally absent.
- Treating unverified behavior as failure was rejected; `UNKNOWN` is distinct from both `VERIFIED` and `UNSUPPORTED`.

## Keep ContextPort in this repository for now

**Decision:** Do not move ContextPort now. Maintain its standalone runtime and documentation boundary inside this repository, and revisit extraction only when explicit product or maintenance triggers appear.

**Why:** The current repository provides useful shared history and governance, while ContextPort already has an internal product boundary. A move now would add migration work without changing its supported behavior or evidence.

**Rejected alternatives:**

- Immediate extraction was rejected for now because it would disrupt links, history, CI, and contributor workflow without a demonstrated independent release need.
- Permanent co-location was rejected as an irreversible promise because ContextPort already dominates repository size and has a different lifecycle.
- A submodule or subtree was rejected because it would add two-repository coordination before separate ownership exists.

The detailed triggers and migration considerations are in [Decision 001](decisions/001-contextport-repository-separation.md).
