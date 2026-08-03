# Prompt: strengthen PM Human Writer validation

Strengthen the existing PM Human Writer plugin without changing its product promise.

Requirements:

- preserve the current voice-protection and minimum-edit behaviour;
- make evidence traceability and placeholder handling explicit in the skill;
- replace incomplete or misleading examples with synthetic, fully specified inputs;
- add executable, dependency-free contract checks covering trigger, no-trigger, fact preservation, anti-invention, banned-pattern removal, and minimum-edit behaviour;
- run those checks in the repository's existing integrity gate;
- add the MIT licence file already claimed by the repository documentation;
- state the limits honestly: deterministic fixtures validate the written contract, not quality across every live model or environment.

Use only synthetic data. Do not add production dependencies.
