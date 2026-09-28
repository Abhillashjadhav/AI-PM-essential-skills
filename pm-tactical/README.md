# pm-tactical

Five Claude Code skills for model choice, artifact review, prompt revision,
connector context cost and project memory.

```bash
claude plugin marketplace add Abhillashjadhav/AI-PM-essential-skills
claude plugin install pm-tactical@ai-pm-skills
```

| Skill | Example request | Output |
|---|---|---|
| model-complexity-router | “Does this task need a stronger model?” | A model-tier recommendation and reasoning |
| builder-validator | “Build this artifact and check it against this spec.” | An artifact and a checklist against the frozen spec |
| prompt-optimizer-loop | “Improve this prompt using these failures.” | A bounded revision with one change per round |
| cli-over-mcp-auditor | “Audit my connector context cost.” | An inventory that distinguishes loaded and deferred tools |
| pm-context-system | “Remember this approved product decision.” | A proposed project-memory entry |

Provide the task, constraints and relevant source material. Missing product
facts remain questions; the skills do not supply evidence that has not been
observed. Model recommendations do not switch your active model automatically.

## Evidence and limitations

The repository includes manual trigger and expected-output cases under
[`tests/`](../tests/). Metadata checks do not establish live trigger accuracy,
editing quality or cost savings. Separate executor prompts are not proof of
independent adjudication. Tool access and write permissions are enforced by the
host; these Markdown instructions are not a sandbox.

See the [evidence table](../docs/VALIDATION.md) before treating a generated
artifact as a release decision.
