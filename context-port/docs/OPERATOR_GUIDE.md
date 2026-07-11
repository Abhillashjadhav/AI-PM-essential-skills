# Operator guide

## 1. Establish the boundary

Use a clean public checkout and Python 3.11 or newer. Do not provide credentials. Do not place exports, conversations, cookies, sessions, private mappings, or derived private reports inside the repository.

```sh
python3 context-port/contextport.py --version
python3 context-port/contextport.py capabilities
```

## 2. Prove the synthetic workflow

```sh
python3 context-port/contextport.py validate context-port/fixtures/contextpack-valid.json
python3 context-port/demo.py
python3 -m unittest discover -s context-port/tests -v
```

Expected evidence:

- validation exits `0`;
- the demo binds itself to checkout `HEAD`;
- independent reconciliation reports zero differences;
- ChatGPT capability assessment is `UNSUPPORTED` and accounts for every unwritten operation;
- network, browser, and migration-write flags are false.

## 3. Understand artifact sensitivity

Synthetic fixtures are safe to commit. Any artifact derived from a real export is private by default, including filenames, project titles, hashes, inventories, structure reports, review packages, reconstruction plans, adapter reports, and logs. Keep private artifacts outside version control.

## 4. Real export gate

Stop and obtain fresh explicit human approval before locating or accessing a real export. Approval must identify the artifact and authorize local inspection. The `approved-private` CLI classification records a declaration; it does not create permission.

After approval, safe inspection remains local and metadata-only. It must not infer an export schema, guess project relationships, emit message values, upload data, or commit derived reports. Any ambiguous mapping stops for a human decision.

## 5. Review before planning

Segregation uses stable identifiers and preserves duplicate titles. A ready segregation plan feeds a metadata-only review package. Approval must match the package digest and every required confirmation. Rejection authorizes no automatic repair.

## 6. Plan and reconcile

The reconstruction engine produces only a dry run. The independent reviewer compares source and plan without trusting writer flags. A clean result requires zero unexplained differences.

## 7. Destination boundary

The ChatGPT adapter is a fail-closed capability assessment. Exit `7` means assessment completed but writes are unsupported. It is not an error to repair with guessed endpoints, API Platform projects, browser selectors, or credentials.

## 8. Incremental changes

The sync planner compares ContextPacks and produces replay-safe changes, tombstones, and human-required conflicts. It does not apply changes. Never resolve divergent edits, ambiguous mappings, deletions, or overwrites automatically.

## 9. Install safely

The installer previews by default and accepts only a new target. Explicit installation builds the local wheel, disables package-index access, installs no dependencies, and verifies the installed CLI. A partial failure is retained and reported; cleanup is destructive and remains human-controlled.

## 10. Interpret outcomes

Use the [CLI exit table](CLI.md) and [capability matrix](CAPABILITIES.md). An attempted action is never success evidence. Preserve all skipped, transformed, ambiguous, failed, and unsupported dispositions.
