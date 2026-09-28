# Remaining decisions and integration work

## Workflow question

Decision 5 describes a seller supplying a missing percentage later. The scope
of validating and updating affected records needs the later workflow/ruling
work reviewed with its implementation. This D4/D2 repair adds no update engine.

## Settled decisions

The repository's existing [PR #54](https://github.com/Abhillashjadhav/AI-PM-essential-skills/pull/54)
records these owner decisions; do not ask the owner to decide them again:

- D4 warnings are grader-generated from source evidence. Implemented here.
- Withheld fields are absent from candidate fields; optional issue reporting
  is allowed. Publishing a disputed field fails that SKU. Implemented here.
- D2 later relinking is a manual supplier action outside the grader.
- Certification is family-wide. Its separate #54 implementation is not included
  in this D4/D2 repair; current code remains per-SKU.

## Evidence boundary

Later grader branches include additional adjudication, sealed-case attempts,
input-format decisions and runner repairs. This package does not import or
certify their evidence. They require a separate combined review rather than a
bulk merge of their overlapping PRs.

The 55 revision checks and six publication regression tests are development
checks. They do not measure the two accuracy targets or establish an independent
holdout. The model-grader interview's exit test still needs a filled contract
from a real interview handed to an implementer who did not see that interview.
