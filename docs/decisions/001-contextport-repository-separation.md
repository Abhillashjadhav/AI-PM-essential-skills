# Decision 001: evaluate future ContextPort repository separation

## Status

Retain ContextPort in this repository now. Revisit the decision when the triggers below are met. No files are moved by this decision.

## Question

Should ContextPort later become its own repository rather than remain a standalone toolkit inside the AI PM building-blocks laboratory?

## Evidence

Reasons to keep the current boundary:

- ContextPort already has a clear internal root, documentation map, tests, schemas, prompts, decisions, and contribution rules under [`context-port/`](../../context-port/).
- Shared repository governance keeps privacy, claim quality, and human approval gates visible in one place.
- Current public evidence does not show separate maintainers, users, release cadence, or package publication that require independent repository operations.
- Moving now would not add a supported destination write or strengthen real-export evidence.

Reasons separation may become valuable:

- ContextPort is much larger than the four standalone skills and dominates the repository's code, tests, and PR history.
- It has a different runtime, safety model, evidence ladder, release gate, and user journey.
- Independent packaging, licensing, release notes, issues, and CI may eventually be easier to understand in a dedicated repository.
- Continued growth could make the laboratory landing page an unnecessary indirection for ContextPort users.

## Decision

Keep ContextPort here now, with explicit product and evidence boundaries. Re-evaluate extraction when at least two of these triggers are present:

1. ContextPort has an independent release cadence or package publication plan.
2. ContextPort has maintainers or contributors who do not work on the skill portfolio.
3. Most repository issues and pull requests are ContextPort-specific for a sustained period.
4. Shared CI materially slows or complicates unrelated skill work.
5. Users repeatedly confuse skill installation with ContextPort installation after the portfolio rewrite.
6. ContextPort needs a separate license, roadmap, security policy, or support commitment.

## Rejected alternatives

- **Move immediately:** rejected because the current task requires no move, and no operational trigger currently justifies the disruption.
- **Promise permanent co-location:** rejected because future product ownership and release evidence may diverge.
- **Use a submodule or subtree now:** rejected because it creates coordination overhead without independent ownership.
- **Copy ContextPort into a new repository and leave both active:** rejected because duplicate sources would make evidence and support boundaries ambiguous.

## Conditions for a later move

A future extraction plan should:

- preserve relevant Git history rather than copy only the latest files;
- redirect or update public documentation, clone paths, issue templates, and CI;
- identify the canonical issue and pull-request tracker;
- keep aggregate real-export evidence public-safe and keep private artifacts uncommitted;
- rerun quick starts, integrity checks, unit tests, packaging, and compilation in both repositories; and
- leave an archived pointer here rather than two maintained ContextPort copies.

## Recommendation

Do not separate ContextPort yet. Treat the current documentation rewrite as a lower-cost test: if explicit navigation and evidence labels remove visitor confusion, co-location still serves the laboratory purpose. If the triggers above appear, extract ContextPort through a dedicated, human-reviewed migration plan.
