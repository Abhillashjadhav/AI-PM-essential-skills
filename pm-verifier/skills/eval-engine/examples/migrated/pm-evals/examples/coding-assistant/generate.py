"""Deterministic generator for the coding-assistant case study (500 traces).

An AI pair-programmer across six languages. Each trace pairs an input
`code_snippet` + request with a `generated_code` output and an
`expected_behavior` description, tagged with a ground-truth `quality_label`.

Quality distribution (500 total):
    160 correct code that runs        (trimmed from a nominal 200 so named
                                       buckets below sum exactly to 500)
    100 subtle bugs (off-by-one, wrong var, deprecated API)
     80 hallucinated library calls
     50 over-confident wrong answers
     40 incomplete implementations (signature + TODO)
     30 right-but-wrong-question explanations
     20 security issues (sqli, eval, hardcoded secrets, log injection)
     20 outdated patterns (py2, deprecated React class components)

Run: python examples/coding-assistant/generate.py
"""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta
from pathlib import Path

SEED = 20260522
random.seed(SEED)
OUT = Path(__file__).parent / "traces.jsonl"

LANGUAGES = ["python", "javascript", "typescript", "go", "rust", "sql"]
TASK_TYPES = ["bug_fix", "new_feature", "refactor", "explain", "test"]
CHANNELS = ["chat", "email", "in-app"]
TIERS = ["free", "pro", "enterprise"]
MODELS = ["claude-3.5-sonnet", "gpt-4o", "claude-3-haiku"]

# Per-language realistic building blocks: (request, input_snippet, good_output,
# expected_behavior). Kept compact; padded to 10-80 lines at assembly time.
BASE = {
    "python": (
        "Write a function that returns the sum of even numbers in a list.",
        "def sum_evens(nums):\n    pass",
        "def sum_evens(nums):\n    return sum(n for n in nums if n % 2 == 0)",
        "Returns the sum of all even integers in the input list; 0 for empty input.",
    ),
    "javascript": (
        "Write a function that debounces a callback by a given delay.",
        "function debounce(fn, delay) {\n  // TODO\n}",
        "function debounce(fn, delay) {\n  let t;\n  return (...args) => {\n    clearTimeout(t);\n    t = setTimeout(() => fn(...args), delay);\n  };\n}",
        "Returns a debounced wrapper that calls fn at most once per delay window.",
    ),
    "typescript": (
        "Implement a typed LRU get/set cache with a max size.",
        "class LRU<K, V> {\n  constructor(private max: number) {}\n}",
        "class LRU<K, V> {\n  private map = new Map<K, V>();\n  constructor(private max: number) {}\n  get(k: K): V | undefined {\n    if (!this.map.has(k)) return undefined;\n    const v = this.map.get(k)!;\n    this.map.delete(k);\n    this.map.set(k, v);\n    return v;\n  }\n  set(k: K, v: V): void {\n    if (this.map.has(k)) this.map.delete(k);\n    this.map.set(k, v);\n    if (this.map.size > this.max) this.map.delete(this.map.keys().next().value);\n  }\n}",
        "Evicts the least-recently-used entry once size exceeds max.",
    ),
    "go": (
        "Write a function that returns the max value in a slice of ints.",
        "func Max(xs []int) int {\n\treturn 0\n}",
        "func Max(xs []int) (int, error) {\n\tif len(xs) == 0 {\n\t\treturn 0, errors.New(\"empty slice\")\n\t}\n\tm := xs[0]\n\tfor _, x := range xs[1:] {\n\t\tif x > m {\n\t\t\tm = x\n\t\t}\n\t}\n\treturn m, nil\n}",
        "Returns the maximum element, or an error for an empty slice.",
    ),
    "rust": (
        "Write a function that counts vowels in a string.",
        "fn count_vowels(s: &str) -> usize {\n    0\n}",
        "fn count_vowels(s: &str) -> usize {\n    s.chars().filter(|c| \"aeiouAEIOU\".contains(*c)).count()\n}",
        "Returns the number of vowel characters in the input string.",
    ),
    "sql": (
        "Write a query for the top 5 customers by total order value.",
        "-- orders(id, customer_id, amount)",
        "SELECT customer_id, SUM(amount) AS total\nFROM orders\nGROUP BY customer_id\nORDER BY total DESC\nLIMIT 5;",
        "Aggregates order amounts per customer and returns the five highest.",
    ),
}

COMMENTS = {
    "python": "# handles the common case; extend as needed",
    "javascript": "// keep this pure; no side effects",
    "typescript": "// generics keep call sites type-safe",
    "go": "// callers must check the returned error",
    "rust": "// borrow the slice; no allocation",
    "sql": "-- assumes amount is non-null",
}


def _pad_code(code: str, lang: str, target_lines: int) -> str:
    """Pad code with neutral comment lines to reach a target line count (<=80)."""
    lines = code.splitlines()
    c = COMMENTS[lang]
    i = 0
    while len(lines) < target_lines and i < 80:
        lines.append(f"{c} ({i})")
        i += 1
    return "\n".join(lines[:80])


def correct(lang: str, good: str) -> str:
    return good


def subtle_bug(lang: str, good: str) -> str:
    bugs = {
        "python": good.replace("% 2 == 0", "% 2 == 1"),  # wrong parity
        "javascript": good.replace("clearTimeout(t)", "/* forgot clearTimeout */"),
        "typescript": good.replace("> this.max", ">= this.max"),  # off-by-one eviction
        "go": good.replace("xs[1:]", "xs[0:]"),  # redundant/edge bug
        "rust": good.replace("aeiouAEIOU", "aeiou"),  # misses uppercase
        "sql": good.replace("DESC", "ASC"),  # wrong sort order
    }
    return bugs[lang]


def hallucinated_lib(lang: str, good: str) -> str:
    snippets = {
        "python": "import fastmath\n\ndef sum_evens(nums):\n    return fastmath.even_sum(nums)  # fastmath does not exist",
        "javascript": "import { autoDebounce } from 'react-debounce-magic';\nexport const debounce = autoDebounce; // package does not exist",
        "typescript": "import { LruMap } from '@types/lru-fast';\n// @types/lru-fast is not a real runtime package",
        "go": "import \"github.com/gomax/maxutil\"\n\nfunc Max(xs []int) int {\n\treturn maxutil.IntMax(xs) // no such module\n}",
        "rust": "use stringtools::vowel_count;\n\nfn count_vowels(s: &str) -> usize {\n    vowel_count(s) // stringtools crate does not exist\n}",
        "sql": "SELECT TOP_N(customer_id, 5) FROM orders; -- TOP_N() is not a real SQL function",
    }
    return snippets[lang]


def overconfident_wrong(lang: str, good: str) -> str:
    return (
        "// This is definitely correct and handles every edge case.\n" + subtle_bug(lang, good)
        if lang != "python"
        else "# This is 100% correct and production-ready.\n" + subtle_bug(lang, good)
    )


def incomplete(lang: str, good: str) -> str:
    sig = good.splitlines()[0]
    todo = {
        "python": "    # TODO: implement\n    raise NotImplementedError",
        "javascript": "  // TODO: implement\n}",
        "typescript": "  // TODO: implement\n}",
        "go": "\t// TODO: implement\n}",
        "rust": "    // TODO: implement\n    unimplemented!()\n}",
        "sql": "-- TODO: finish the query",
    }
    return sig + "\n" + todo[lang]


def wrong_question(lang: str, good: str) -> str:
    # Correct explanation, but of a different concept than asked.
    return (
        f"Great question. Here's how garbage collection works in {lang}: the runtime "
        f"periodically reclaims unreachable objects. (This is accurate, but it does not "
        f"answer the actual request.)"
    )


def security_issue(lang: str, good: str) -> str:
    snippets = {
        "python": "import os\nAPI_KEY = 'sk-live-1234567890abcdef'  # hardcoded secret\n\ndef run(cmd):\n    return os.system(cmd)  # command injection",
        "javascript": "function calc(expr) {\n  return eval(expr); // eval on user input\n}",
        "typescript": "const token = '<REDACTED_GITHUB_TOKEN>'; // hardcoded secret\nexport const auth = () => token;",
        "go": "func log(user string) {\n\tfmt.Printf(user) // format-string / log injection\n}",
        "rust": "fn run(cmd: &str) {\n    std::process::Command::new(\"sh\").arg(\"-c\").arg(cmd).spawn().unwrap(); // shell injection\n}",
        "sql": "SELECT * FROM users WHERE name = '\" + userInput + \"'; -- SQL injection",
    }
    return snippets[lang]


def outdated(lang: str, good: str) -> str:
    snippets = {
        "python": "def sum_evens(nums):\n    print 'summing'  # Python 2 print statement\n    return reduce(lambda a, n: a + (n if n % 2 == 0 else 0), nums, 0)",
        "javascript": "var debounce = function (fn, delay) {\n  var t;\n  return function () { /* uses var and arguments, pre-ES6 */ };\n};",
        "typescript": "class Counter extends React.Component {\n  render() { return null; } // deprecated class component pattern\n}",
        "go": "// uses ioutil.ReadAll (deprecated since Go 1.16)\nimport \"io/ioutil\"",
        "rust": "fn count_vowels(s: &str) -> usize {\n    try!(Ok::<_, ()>(())); // try! macro deprecated in favor of ?\n    0\n}",
        "sql": "SELECT * FROM orders, customers WHERE orders.customer_id = customers.id; -- old implicit-join style",
    }
    return snippets[lang]


GENERATORS = {
    "correct": correct,
    "subtle_bug": subtle_bug,
    "hallucinated_lib": hallucinated_lib,
    "overconfident_wrong": overconfident_wrong,
    "incomplete": incomplete,
    "wrong_question": wrong_question,
    "security": security_issue,
    "outdated": outdated,
}

COUNTS = {
    "correct": 160,
    "subtle_bug": 100,
    "hallucinated_lib": 80,
    "overconfident_wrong": 50,
    "incomplete": 40,
    "wrong_question": 30,
    "security": 20,
    "outdated": 20,
}
assert sum(COUNTS.values()) == 500


def build() -> list[dict]:
    cats: list[str] = []
    for c, n in COUNTS.items():
        cats += [c] * n
    random.shuffle(cats)

    base_time = datetime(2026, 3, 1, 9, 0, 0)
    traces: list[dict] = []
    for i in range(500):
        cat = cats[i]
        lang = LANGUAGES[i % len(LANGUAGES)]
        request, input_snippet, good, expected = BASE[lang]
        task_type = (
            "explain" if cat == "wrong_question" else random.choice(TASK_TYPES)
        )
        generated = GENERATORS[cat](lang, good)
        if cat != "wrong_question":
            generated = _pad_code(generated, lang, random.randint(10, 80))

        has_ctx = random.random() < 0.6
        ctx = [request, expected] if has_ctx else None

        ts = base_time + timedelta(minutes=i * 7)
        trace = {
            "trace_id": f"ca_{i + 1:03d}",
            "conversation_id": f"single_{i:03d}",
            "turn_index": 0,
            "user_message": request,
            "agent_response": generated,
            "language": lang,
            "task_type": task_type,
            "code_snippet": input_snippet,
            "generated_code": generated,
            "expected_behavior": expected,
            "timestamp": ts.isoformat() + "Z",
            "metadata": {
                "channel": random.choice(CHANNELS),
                "user_tier": random.choice(TIERS),
                "response_latency_ms": random.randint(300, 6000),
                "model": random.choice(MODELS),
                "quality_label": cat,
                "language": lang,
            },
        }
        if ctx:
            trace["retrieved_context"] = ctx
        traces.append(trace)
    return traces


def main() -> None:
    traces = build()
    with OUT.open("w", encoding="utf-8") as fh:
        for t in traces:
            fh.write(json.dumps(t) + "\n")
    print(f"Wrote {len(traces)} traces to {OUT}")


if __name__ == "__main__":
    main()
