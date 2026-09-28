# Marketplace correctness repair

Owner request: assess the independent review of the 28 September architecture
review and implement the recommendations that survive source verification.

Baseline: `60b61efb1294c10045f6af11ff07ce5aea5bb03b`.

This phase integrates existing PRs #57 and #59 with their original ancestry,
then checks them together. Preserve JSON numeric equality while distinguishing
booleans from numbers, including `1.0`. Invalid skill metadata, duplicate
marketplace names and Git-quoted filenames must fail or reach the proper check.

Use synthetic inputs only. Run verifier, validator and ContextPort tests plus
repository integrity. Keep documentation and broader CI changes in later
branches. Save observed results; push a draft PR for human review. No automatic
merge or release.
