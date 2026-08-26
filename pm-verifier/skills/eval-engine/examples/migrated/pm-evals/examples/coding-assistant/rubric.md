# Coding-assistant rubric

Ten criteria for evaluating AI-generated code. One criterion per bullet;
negations are detected automatically.

- syntactic correctness: the code parses and is valid for its language
- runs without errors: executes on the stated inputs without crashing
- solves the stated problem: output matches the requested behavior
- uses real APIs: no hallucinated functions, methods, packages, or crates
- no security anti-patterns: no SQL injection, eval, hardcoded secrets, or log injection
- modern idiomatic style: uses current, idiomatic patterns for the language
- handles edge cases mentioned in the user request
- explanation matches implementation: any prose accurately describes the code
- no unnecessary complexity: as simple as the problem allows
- includes necessary imports/setup: the snippet is complete enough to run
