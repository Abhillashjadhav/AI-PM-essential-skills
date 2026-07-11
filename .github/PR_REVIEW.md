# Pull-request quality gates

Every pull request runs the free, deterministic `Deterministic required checks` job. It performs:

- Repository test discovery, including ContextPort tests when present.
- Syntax compilation of changed Python files without writing bytecode.
- `git diff --check` against the pull request base.
- High-signal credential and private-filename scanning over added content.
- Existing-skill impact reporting; ContextPort branches fail if they modify an existing skill.

These checks use Python's standard library and repository tools. They require no paid API, external review service, or private repository.

## Optional Claude review

The `OPTIONAL Claude review` job is supplemental and is not a required product-code gate. When the repository secret `CLAUDESECRET` is absent, the job prints a skip explanation and succeeds without invoking Claude.

A maintainer who independently has an appropriate Claude Code OAuth token may enable the optional review privately:

```sh
gh secret set CLAUDESECRET --repo OWNER/REPOSITORY
```

Enter the value interactively. Never place it in source files, workflow YAML, logs, issues, pull-request descriptions, or chat transcripts. Removing the secret disables the optional review without affecting deterministic checks.
