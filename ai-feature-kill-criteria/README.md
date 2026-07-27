# AI Feature Kill Criteria

Define the evidence that would make an AI product team stop before the team starts building.

## Install

```bash
claude plugin marketplace add Abhillashjadhav/AI-PM-essential-skills
claude plugin install ai-feature-kill-criteria@ai-pm-skills
```

Then ask:

```text
Define kill criteria for this AI feature before we prototype it.
```

## Output

The skill returns a decision contract with:

- one falsifiable product claim;
- critical assumptions across problem, behavior, capability, workflow, economics, risk, and adoption;
- approved continue and kill thresholds;
- the cheapest decisive evidence plan;
- a decision owner and date;
- a bounded verdict: `NOT READY TO BUILD`, `READY FOR BOUNDED TEST`, or `READY TO BUILD`.

## Example

```text
FEATURE
AI assistant that suggests fixes for rejected supplier catalog submissions.

KILL CRITERION
If fewer than 6 of 10 support associates resolve the original failure set without escalation, pause the build.

ECONOMIC KILL CRITERION
If cost per resolved case exceeds the current assisted workflow after two iterations, kill the proposed architecture.

DECISION DATE
Two weeks after the frozen failure-set evaluation begins.
```

## Limit

The skill does not choose thresholds on behalf of the accountable product team. Suggested defaults remain proposals until a human owner approves them.
