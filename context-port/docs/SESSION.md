# Generated session memory

`SESSION.md` and `SESSION.json` are ContextPort's canonical cross-session working memory for ChatGPT, Claude, Codex, and human maintainers. They are generated artifacts; never edit them manually.

Regenerate both from observable repository state:

```sh
python3 context-port/contextport.py handoff
```

Check freshness without writing:

```sh
python3 context-port/contextport.py handoff --check
```

Generation observes local Git history, `main`, the current branch, phase prompt files merged into `main`, ContextPort commit/PR history, live open ContextPort PRs through authenticated GitHub CLI, the full unit-test result, Python syntax, capability documentation, repository license presence, and working-tree health.

Line coverage is reported as `UNKNOWN` until a coverage instrument is configured. The generator never invents a percentage. Real exports, credentials, private content, browser state, and assistant accounts are not inspected.

Every successful phase must regenerate and commit both artifacts before its PR is created. Refresh them once more after PR creation when the open-PR snapshot changes. CI or reviewers may use `handoff --check` when the external PR snapshot is stable.
