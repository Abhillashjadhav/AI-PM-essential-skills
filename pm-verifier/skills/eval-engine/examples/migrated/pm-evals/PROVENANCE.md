# pm-evals data provenance

Source: [`Abhillashjadhav/pm-evals`](https://github.com/Abhillashjadhav/pm-evals)
at commit `a9adae024bfc9ace166152ffe19f7110fa1619d0`.

These are immutable synthetic trace, source, rubric, pairwise, human-golden,
and judge-result snapshots retained for migration and regression work. The
four large JSONL files are losslessly stored as `.xz`; the hashes below are for
the decompressed original bytes. Python's standard-library `lzma` module or
`xz -dc` restores each exact source file. They are not automatically trusted as
current production distributions. New product decisions should version a new
dataset and record its provenance in `dataset.json`.

| Path | SHA-256 |
|---|---|
| `examples/coding-assistant/traces.jsonl.xz` | `4d410728942947e1d75bec11e69b419b31f01903e6d6283450ef5a8f6ef92182` |
| `examples/customer-support/traces.jsonl.xz` | `852faec7628b5866000515515ed990dd669c8bc2f02d4dfe9553db8259386784` |
| `examples/summarization/sources.jsonl.xz` | `1c69abd25163de3d87f2b948be4681f8c0ef48db7bd26fa51a0ce500b2e0ae90` |
| `examples/summarization/traces.jsonl.xz` | `b6dc285179f89266b0ad94c0eb96f838ddc681971d45b95eeb83030de3ba53d5` |
| `examples/pairwise/pairs.jsonl` | `64a5f8e9635852652db4f2226674ae23c1a59fc1d0a3d875c8d6428fdbe34150` |
| `golden/golden_traces.jsonl` | `7aca3e26e32fd6e1aee1fb1706b77615ba1cdb72663d5bb1d0468aea06e2740e` |
| `golden/golden_scores.json` | `fe1c6576e8f379797d56bf85f99cdf79795375e1caeb53ca8ef7776839739ab6` |
| `golden/judge_results_golden.json` | `fa54c03f499d122cd9af9ad20c64fd78d68e90427f8dfdd000eb7d2d5d4eb37f` |

Rubrics, generators, grading workbooks, and source README files are retained
beside those datasets. Their exact content remains traceable through Git and
the source commit above.
