# pm-tactical

Six Claude Code skills for model choice, artifact review, prompt revision,
connector context cost, project memory and workflow-effort measurement.

```bash
claude plugin marketplace add Abhillashjadhav/AI-PM-essential-skills
claude plugin install pm-tactical@ai-pm-skills
```

AI Workflow Comparison requires a revision containing its new skill name;
it is not exposed on public `main` until those changes are merged. Its
[installed-skill instructions](skills/ai-workflow-trial/README.md#use-the-installed-skill)
include the local-checkout marketplace path for reviewing this revision.

| Skill | Example request | Output |
|---|---|---|
| model-complexity-router | “Does this task need a stronger model?” | A model-tier recommendation and reasoning |
| builder-validator | “Build this artifact and check it against this spec.” | An artifact and a checklist against the frozen spec |
| prompt-optimizer-loop | “Improve this prompt using these failures.” | A bounded revision with one change per round |
| cli-over-mcp-auditor | “Audit my connector context cost.” | An inventory that distinguishes loaded and deferred tools |
| pm-context-system | “Remember this approved product decision.” | A proposed project-memory entry |
| [AI Workflow Comparison](skills/ai-workflow-trial/README.md) | “Compare AI-assisted work with our standard workflow and collect customer outcomes and human effort.” | Frozen assignments, ready-to-fill templates and complete descriptive accounting |

Provide the task, constraints and relevant source material. Missing product
facts remain questions; the skills do not supply evidence that has not been
observed. Model recommendations do not switch your active model automatically.

For AI Workflow Comparison, use the request in the table or invoke
`/pm-tactical:ai-workflow-comparison`. The skill helps define the collection
plan, freezes supplied eligible tasks, creates a blank results sheet, and
audits all supplied observations at the common cutoff. Record actual active
person-time and customer outcomes manually. The bundled tool makes no model
calls; Claude Code host access and ordinary permissions still apply.

## Evidence and limitations

The repository includes manual trigger and expected-output cases under
[repository `tests/`](https://github.com/Abhillashjadhav/AI-PM-essential-skills/tree/main/tests). Metadata checks do not establish live trigger accuracy,
editing quality or cost savings. Separate executor prompts are not proof of
independent adjudication. Tool access and write permissions are enforced by the
host; these Markdown instructions are not a sandbox.

AI Workflow Comparison adds a Python standard-library plan/audit runtime with
synthetic core tests, CLI UAT and offline copied-plugin checks. Start with its
[adaptation steps and templates](skills/ai-workflow-trial/README.md#adapt-this-to-your-own-workflow).
It retains failed and unfinished units and shows customer successes alongside
measured active person-time. It makes no workflow-winner, causal or launch verdict.
Offline copied-plugin checks do not establish live productivity gains, native
host installation or trigger quality. Repository evidence links are outside
the installed bundle; inspect a source revision matching the installed plugin.

See the [repository evidence table](https://github.com/Abhillashjadhav/AI-PM-essential-skills/blob/main/docs/VALIDATION.md) before treating a generated
artifact as a release decision.
