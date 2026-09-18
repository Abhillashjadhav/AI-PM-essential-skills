# When a rule cannot be code

Most rules in a good contract are deterministic: numeric equality, allowed values, unit conversion, provenance, inheritance, completeness. Check them in code and they are exact, fast and free.

Some are not. Whether a document constitutes approval. Whether a summary is faithful. Whether a tone is appropriate. Whether a claim is substantiated by an attached certificate.

Pretending these are deterministic produces a proxy metric that is confidently wrong — worse than no metric, because it is trusted.

## What a non-deterministic rule must carry

| Element | Why |
|---|---|
| **Named reviewer or role** | "a human reviews it" is not a process. Who, by role, and what happens when they are unavailable |
| **Required evidence** | exactly what must be in front of them. A decision made without the document is not a document review |
| **Decision criteria** | what they are deciding, in terms specific enough that two reviewers would usually agree |
| **What the grader records** | the attestation, the reviewer, the timestamp, the criteria version — never the judgment itself |

## The division of labour

The grader **records** the human decision and **checks that the decision exists, is attached to the right item, and was made against the required evidence**. It does not make the judgment and it does not second-guess it.

This makes an otherwise unverifiable rule mechanically checkable without lying about what was verified. The grader can prove *a named reviewer decided this, with this evidence, under these criteria*. It cannot prove they were right, and it should not claim to.

## What is not allowed

- **Inventing a proxy.** Scoring "faithfulness" with a similarity threshold because faithfulness is hard.
- **Attestation without evidence binding.** An approval that does not name what was approved can be reused for anything.
- **A model standing in for the reviewer** unless the owner explicitly decided that, in which case it is a model judgment with its own error rate — record it as such, never as human approval.

## In the contract

Non-deterministic rules go in their own section with all four elements filled. A rule that cannot carry them is marked `NOT DECIDABLE` and returned to the owner to restate or drop.
