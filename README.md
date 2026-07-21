# AI PM Essential Skills

This repository contains four Claude Code skills for AI Product Manager workflows and the standalone ContextPort toolkit under [`context-port/`](context-port/). ContextPort is not one of the four skills.

## Repository structure

| Path | Contents | Evidence status |
|---|---|---|
| [`token-cost-estimator/`](token-cost-estimator/) | A skill instruction for comparing projected inference cost and latency. | Manual skill fixture not included in this repository. Model and pricing information must be verified against current official pricing before use. |
| [`eval-rubric-generator/`](eval-rubric-generator/) | A skill instruction for turning a feature requirement into a binary evaluation rubric. | Manual skill fixture not included in this repository. |
| [`context-auditor/`](context-auditor/) | A skill instruction for reviewing supplied context for poisoning, distraction, confusion, and clash. | Manual skill fixture not included in this repository. |
| [`concise-rewriter/`](concise-rewriter/) | A skill instruction for rewriting supplied text more concisely and reporting a token delta. | Manual skill fixture not included in this repository. |
| [`context-port/`](context-port/) | A standalone, local-first toolkit with its own CLI, synthetic fixtures, unit tests, and documentation. | See [ContextPort evidence](#contextport-evidence). |

The plugin directories elsewhere in the repository are separate products and are not part of this four-skill set.

## Install the four skills

```bash
git clone https://github.com/Abhillashjadhav/AI-PM-essential-skills.git
cd AI-PM-essential-skills

mkdir -p ~/.claude/skills
cp -r token-cost-estimator ~/.claude/skills/
cp -r eval-rubric-generator ~/.claude/skills/
cp -r context-auditor ~/.claude/skills/
cp -r concise-rewriter ~/.claude/skills/
```

Claude Code installation behavior, skill discovery, and hot reload behavior are not continuously verified by this repository. Review the installed [`SKILL.md`](token-cost-estimator/SKILL.md) files in your target Claude Code environment before relying on them.

## Evidence and validation

This repository does **not** make a blanket claim that every product is shipped or tested. The evidence is deliberately separated:

- **Automated structural validation:** [`scripts/check_repository_integrity.py`](scripts/check_repository_integrity.py) checks the four declared skill directories, their `SKILL.md` files, README-local links, README-mentioned fixtures, and ContextPort quick-start paths.
- **Automated tests:** ContextPort has Python unit tests in [`context-port/tests/`](context-port/tests/). They exercise the local toolkit using committed synthetic fixtures; they do not run Claude Code skills or external assistant services.
- **Manual fixtures and expected outputs:** fixture documents under [`tests/`](tests/) and examples in product directories are review inputs and expected outputs. They are not automated behavioural tests unless a test command explicitly consumes them.
- **Recorded behavioural model runs:** no recorded model-run evidence is claimed for the four standalone skills. ContextPort's committed evaluation notes document synthetic, deterministic checks rather than external-model runs.
- **Unverified behaviour:** cross-runtime compatibility, external skill-library coverage, current model availability, current model pricing, and live Claude Code invocation behavior are unverified here. Any model or price used as an example is illustrative only and must be checked against current official pricing.

See [`docs/VALIDATION.md`](docs/VALIDATION.md) for evidence boundaries and exact reviewer commands.

## ContextPort evidence

ContextPort's evidence is scoped to deterministic local behavior over committed synthetic fixtures. Its capability matrix labels real-export compatibility `UNKNOWN` and consumer ChatGPT reconstruction writes `UNSUPPORTED`; it does not establish live assistant migration behavior.

## ContextPort quick start

ContextPort is a separate toolkit. Its quick start uses only committed synthetic fixtures:

```bash
python3 context-port/contextport.py --version
python3 context-port/contextport.py capabilities
python3 context-port/contextport.py validate context-port/fixtures/contextpack-valid.json
python3 context-port/demo.py
python3 -m unittest discover -s context-port/tests -q
```

See [`context-port/README.md`](context-port/README.md) for its safety boundaries, supported synthetic workflow, and installation procedure.

## Contributing

Review [`AGENTS.md`](AGENTS.md) before contributing. In particular, ContextPort changes must not modify existing AI-PM skills without explicit human approval. Pull requests require review before merge.

## License

MIT. See the repository license terms when they are added or updated.
