# The blind-author probe

A one-hour test that tells you whether your pass rate means anything. Run it before trusting
any eval number.

## The probe

Have someone who has never seen the code write evaluation cases from the written contract alone.

**If they cannot produce even a valid input, stop.** The system has requirements that exist
only in its own code and its own fixtures. Every green check you have is measuring its author.

This is not a test of the cases. It is a test of whether your contract is a contract.

## What it found in the source project

Nine cases, written by a party with the full contract, the owner's eight judgments, the candidate
interface and a data-format guide. Zero were parsed. All nine were rejected before grading.

The cause: the grader required each evidence value to mirror its field's shape exactly. No clause
said so. No document mentioned it. The rule lived in the code and in the 102 fixtures the same
party had written.

The 102 green checks had never been a measurement. They passed because one party wrote both
halves. The moment an outsider supplied one half, nothing ran.

## Reading the result

| Outcome | Means |
|---|---|
| Cases cannot be parsed | Undocumented contract. Write the rule down, re-encode, re-run. Your prior pass rate was meaningless. |
| Cases parse, verdicts disagree | A real measurement. Classify and escalate per the three-hand protocol. |
| Cases parse, everything agrees | Weak positive. Check the cases exercise both error directions before believing it. |

## Keep the expectations frozen

Re-encoding the *input* to match a newly documented format is legitimate. Changing an
**expectation** is not — that is the implementation reaching back into the spec.

Verify it rather than assert it. Hash every immutable key across every round:

    expected_verdict, expected_publication, expected_seller_guidance, reason, candidate

In the source project these were byte-identical across three encoding rounds while inputs moved
twice. State that verification alongside the result; without it the independence claim is a
promise rather than a fact.

## Disclose the weakness

If the format was documented *after* the cases failed against it, say so before reporting any
number. A reader deserves to judge whether re-encoding damaged the independence the method exists
to protect.
