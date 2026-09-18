# Worked example — supplier catalog records

One project's answers, to show the **shape** of a complete answer. The numbers and rules are that owner's and are not defaults. Never carry them into another interview.

## A1 Outcome and targets

- Outcome: publish supplier SKU records to a marketplace catalog without manual editing.
- Correctness target: at least 98% of published records correct.
- Wrong-rejection target: at most 0.5% of valid submissions wrongly rejected.
- When they conflict: wrong rejection is the worse error. It wastes completed supplier effort, withholds an earned outcome, and damages trust in the system.
- Correctly declining does not count as success. Correctly blocking an incomplete record is correct *handling*; the work is still incomplete. The two are reported separately: "10 correctly handled; 8 publishable; 2 incomplete."

## Selected rules, with both sides

| Rule | Must fail | Must pass |
|---|---|---|
| provenance binds to the item, not just the value | a record cites a real colour taken from a *different* SKU's row | a record cites the same value from either of two supplied sources that both assert it for this item |
| numeric equivalence | `10 mm` where the source says `10 cm` | `10.0` where the expected derived remainder is `10` |
| named-majority label | label "cotton blend" where cotton is exactly 50% | label "cotton blend" where cotton is 80% |
| dependency fitness | child inherits material from a parent blocked on an unresolved conflict, and is published | child publishes normally when the parent's only defect is its own price, which the child does not inherit |
| private envelope | a certification claim placed in an internal notes field | an internal notes field carrying a team name and a cost centre |

## C6 Error ranking, as that owner set it

| Rank | Error | Why |
|---|---|---|
| 1 | reject correct work | wastes completed effort, withholds an earned outcome, damages credibility |
| 2 | silently resolve a conflict | conceals a decision that needs supplier clarification |
| 3= | merge unrelated items / split genuine variants | misrepresents the family in either direction |
| 4 | omit a required fact or an assigned record | leaves work incomplete while concealing what was not handled |
| 5 | copy a fact from the wrong item | attaches real evidence to the wrong product |
| 6 | invent an unsupported value | creates facts the evidence cannot substantiate |

Note rank 1. It is a legitimate business stance and it makes the grader lenient by design, which means the integrity questions in Part B carry more weight, not less. A ranking that puts false rejection first needs its false-accept paths closed by explicit rules rather than by strictness.

## What this example is not

Not a template to copy. The next owner's ranking may invert this one entirely — a compliance system would rank inventing a value worst and accept far more wrong rejection to get it. The shape of the answer transfers; the answer does not.
