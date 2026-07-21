# Portfolio map

## Portfolio purpose

This repository is a laboratory for small, inspectable mechanisms that address recurring AI product-management work. Co-location makes the mechanisms and their evidence easy to compare. It does not make them one product.

## Product boundaries

| Component | One problem | Primary artifact | Evidence boundary | Install or run boundary |
|---|---|---|---|---|
| Four standalone AI PM skills | Repeated PM decisions are otherwise handled as unstructured prompting. | Four independent `SKILL.md` instruction files. | Structure is checked; live model behavior is not recorded here. | Copy individual skill directories into a compatible skill directory. |
| ContextPort | Conversational context needs a local, reviewable representation and plan before migration. | A Python CLI, schemas, deterministic engines, and reports under [`context-port/`](../context-port/). | Synthetic behavior is verified; one private real-export conversion is recorded; destination writes are unsupported. | Run or install ContextPort independently from the four skills. |
| Plugin experiments | Broader workflows need a place to test multi-skill packaging, examples, and trigger design. | Four plugin directories registered by [the marketplace manifest](../.claude-plugin/marketplace.json). | Mixed: inspectable instructions, manual fixtures, examples, and selected runnable scripts. No single evidence claim covers every plugin. | Install a named plugin separately; plugin installation does not install ContextPort. |
| Historical and operational material | Decisions, prompts, reviews, and prior work need traceability. | `prds/`, `reviews/`, saved prompts, validation records, and repository commands. | Documentary evidence only unless a named command consumes the artifact. | Not an end-user product. |

## Why these components coexist

The four skills test whether one recurring decision can be expressed as a compact instruction mechanism. The plugins test packaging and multi-step workflow ideas. ContextPort tests a different proposition: whether a sensitive, multi-stage workflow can be implemented as deterministic local software with explicit safety and evidence boundaries.

Keeping these lines of work together currently provides:

- one public place to compare instruction-only and deterministic-software approaches;
- shared contribution, privacy, and claim-quality rules;
- traceable progression from small decision mechanisms to a deeper standalone toolkit; and
- enough history to evaluate which mechanisms deserve independent product investment.

Co-location does **not** imply shared release status, installation, runtime dependencies, support, or validation maturity.

## Evidence boundaries

The portfolio evidence ladder is intentionally not averaged across products:

1. `STRUCTURAL` checks establish that declared files, manifests, paths, and links exist.
2. `VERIFIED` checks establish repeatable behavior on declared committed inputs.
3. `RECORDED` observations are public but not reproducible because approved private inputs or outputs remain uncommitted.
4. `UNKNOWN` claims remain open questions.
5. `UNSUPPORTED` behavior is outside the current product contract.

The four standalone skills stop at `STRUCTURAL` evidence for live behavior. ContextPort has `VERIFIED` deterministic evidence, one `RECORDED` real-export observation, `UNKNOWN` general export compatibility, and `UNSUPPORTED` destination writes. Plugin evidence must be read per directory.

## Navigation rule

A visitor should choose a surface by problem, not by repository path:

- For one of the four named decisions, inspect and install the corresponding standalone skill.
- For local conversational-context representation and migration planning, start with the [ContextPort README](../context-port/README.md).
- For plugin experiments, read the relevant plugin manifest, examples, and fixture limitations before installation.
- For historical rationale, use the decision and validation documents; do not treat them as runtime features.

The future repository boundary for ContextPort is evaluated separately in [Decision 001](decisions/001-contextport-repository-separation.md).
