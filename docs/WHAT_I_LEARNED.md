# What I learned

This file is intentionally not presented as finished first-person authorship. Repository evidence can support observations, but it cannot establish the owner's motivation, surprise, or personal learning. Each section below requires human review before it can be converted into an attributed first-person statement.

## HUMAN REVIEW REQUIRED — Small mechanisms

**Evidence-backed observation:** The four standalone skills are easiest to explain when each is reduced to one problem, one decision mechanism, one input, and one output. Their compactness makes instruction review possible, but the repository does not yet show how reliably a model follows them.

**Owner review prompts:**

- Which of the four mechanisms changed an actual product decision?
- Did keeping them small improve adoption, inspection, or iteration?
- Which skill should be retired or superseded if behavioral evidence remains absent?

Do not convert this section to first person until the owner answers or explicitly approves the observation.

## HUMAN REVIEW REQUIRED — Evidence is part of the product

**Evidence-backed observation:** ContextPort's deterministic checks, the recorded private-export observation, and the unsupported destination boundary answer different questions. Separating them prevents a successful local conversion from being misreported as a complete end-to-end migration product.

**Owner review prompts:**

- Which evidence distinction was most important during review?
- Was `RECORDED` the intended description of the private-export run?
- What additional public-safe artifact would make real-export evidence more independently reviewable?

Do not claim that the owner “learned” this until the wording is manually approved.

## HUMAN REVIEW REQUIRED — Local-first boundaries

**Evidence-backed observation:** Local execution and fail-closed writes reduce the number of privacy, account, and reversibility assumptions that ContextPort must make. This improves inspectability but leaves the final destination step outside the product.

**Owner review prompts:**

- Was privacy the primary reason for local-first design, or one of several reasons?
- Which unsupported capability is an intentional permanent boundary versus a temporary gap?
- What evidence would justify adding a destination adapter later?

Do not invent a personal motivation from the architecture alone.

## HUMAN REVIEW REQUIRED — One repository or two

**Evidence-backed observation:** Co-location preserves shared history and makes the laboratory thesis visible, while ContextPort's code volume and evidence model create a real risk of portfolio confusion. Documentation can reduce that confusion now; independent ownership or release cadence may make extraction worthwhile later.

**Owner review prompts:**

- Does the laboratory framing match the intended public identity?
- Which separation trigger would be decisive: users, maintainers, releases, package publication, or CI cost?
- What history and links must be preserved if ContextPort moves?

Do not state a personal preference until the owner reviews [the separation decision note](decisions/001-contextport-repository-separation.md).
