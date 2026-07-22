# AI PM Essential Skills

**Four focused Claude Code skills for recurring AI product decisions, plus the separate ContextPort local migration toolkit.**

This repository is intentionally small. The skills help compare model cost, design an evaluation rubric, audit supplied context, and rewrite text concisely. ContextPort is a standalone toolkit under `context-port/`; it is not one of the four skills.

## Install the four skills

```bash
git clone https://github.com/Abhillashjadhav/AI-PM-essential-skills.git
cd AI-PM-essential-skills
mkdir -p ~/.claude/skills
cp -r token-cost-estimator eval-rubric-generator context-auditor concise-rewriter ~/.claude/skills/
python3 scripts/check_repository_integrity.py
```

## What each skill does

| Skill | Decision it supports | Evidence status |
|---|---|---|
| `token-cost-estimator` | Compare projected inference cost and latency | Instruction available; current prices must be verified from official sources |
| `eval-rubric-generator` | Convert a feature requirement into binary evaluation criteria | Instruction available; no recorded behavioural run claimed |
| `context-auditor` | Identify poisoning, distraction, confusion, and conflicting context | Instruction available; no recorded behavioural run claimed |
| `concise-rewriter` | Reduce supplied text while reporting token change | Instruction available; no recorded behavioural run claimed |

Review each installed `SKILL.md` before relying on it in a live environment. Claude Code discovery and cross-runtime behaviour are not continuously certified here.

## Try ContextPort locally

ContextPort validates and demonstrates a synthetic, local-first context-package workflow.

```bash
python3 context-port/contextport.py --version
python3 context-port/contextport.py capabilities
python3 context-port/contextport.py validate context-port/fixtures/contextpack-valid.json
python3 context-port/demo.py
python3 -m unittest discover -s context-port/tests -q
```

The demo uses committed synthetic fixtures. It does not prove compatibility with every real assistant export, and it does not write reconstructed conversations into consumer ChatGPT.

See [`context-port/README.md`](context-port/README.md) for supported operations and safety boundaries.

## Repository boundaries

- The four top-level skill directories are the AI PM skill set.
- `context-port/` is a separate executable toolkit.
- Other plugin directories are separate products and are not part of the four-skill claim.
- Manual fixtures and examples are review inputs unless a test command explicitly executes them.

## Validation

```bash
python3 scripts/check_repository_integrity.py
python3 -m unittest discover -s context-port/tests -q
```

Validated:

- declared skill directories and `SKILL.md` files exist;
- README-local paths and documented commands are checked;
- ContextPort deterministic behaviour is covered by unit tests over synthetic fixtures.

Not validated:

- live behavioural quality of the four Claude Code skills;
- current model pricing or availability;
- cross-runtime compatibility;
- broad compatibility with real exports;
- consumer ChatGPT reconstruction writes.

See [`docs/VALIDATION.md`](docs/VALIDATION.md).

## Contributing

Read [`AGENTS.md`](AGENTS.md) before changing the repository. Keep changes within one product boundary, add reproducible validation where possible, and do not broaden capability claims beyond committed evidence.

## License

MIT.
