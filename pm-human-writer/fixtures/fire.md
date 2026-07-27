# Fire fixture

User request:

```text
Please rewrite this LinkedIn post so it sounds less AI-generated while keeping my product judgment and facts.
```

Expected behaviour: trigger `human-product-writer`, preserve the supplied claims, remove named machine-writing patterns, and return the edited draft plus `What changed`.
