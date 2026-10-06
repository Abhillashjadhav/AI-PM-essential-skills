# pm-tactical

Six Claude Code skills for model choice, artifact review, prompt revision,
connector context cost, project memory and workflow-effort measurement.

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
| [ai-workflow-trial](skills/ai-workflow-trial/README.md) | “Measure customer outcomes and human effort in my AI workflow.” | Frozen assignments, ready-to-fill templates and complete descriptive accounting |

Provide the task, constraints and relevant source material. Missing product
facts remain questions; the skills do not supply evidence that has not been
observed. Model recommendations do not switch your active model automatically.

## Evidence and limitations

The repository includes manual trigger and expected-output cases under
[`tests/`](../tests/). Metadata checks do not establish live trigger accuracy,
editing quality or cost savings. Separate executor prompts are not proof of
independent adjudication. Tool access and write permissions are enforced by the
host; these Markdown instructions are not a sandbox.

AI Workflow Trial Kit adds a Python standard-library plan/audit runtime with
synthetic tests and CLI UAT. Start with its [adaptation steps and templates](skills/ai-workflow-trial/README.md#adapt-this-to-your-own-workflow).
It retains failed and unfinished units and shows customer successes alongside
measured active person-time. It makes no workflow-winner, causal or launch verdict.
Offline runtime checks do not establish live productivity gains or installed
skill quality.

See the [evidence table](../docs/VALIDATION.md) before treating a generated
artifact as a release decision.
