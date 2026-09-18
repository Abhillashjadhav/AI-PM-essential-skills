"""Shared fixture builder for the three reproductions.

Each reproduction is a minimal case built from gold/S1.json, mutated to trigger
exactly one finding. They live here so they survive the repair as regression
cases: run any of them before the fix and it reports REPRODUCED, after the fix
and it reports FIXED.
"""
import copy, json, sys
from pathlib import Path
D = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(D))
from grader import grade   # noqa: E402

def base():
    b = json.loads((D / 'gold/S1.json').read_text())
    return copy.deepcopy(b['input']), copy.deepcopy(b['candidate'])

def rec(obj, sku):
    return next(r for r in obj['records'] if r['sku'] == sku)

def conflict(case, sku, field, alt_value, alt_key=None):
    """Give `sku`.`field` two disagreeing sources, so it carries an unresolved conflict."""
    alt = alt_key or f'{sku}.{field}.alt'
    case['evidence'][alt] = {'sku': sku, 'field': field, 'value': alt_value}
    rec(case, sku).setdefault('conflicts', []).append(
        {'field': field, 'evidence': [f'{sku}.{field}', alt]})
    return [f'{sku}.{field}', alt]

def withhold(cand, sku, field):
    """The candidate does the right thing: omits the disputed field, stays READY."""
    r = rec(cand, sku)
    r['fields'].pop(field, None)
    r['evidence'].pop(field, None)

def report(rows, name, reproduced, detail):
    rows.append({'check': name, 'reproduced': reproduced, 'detail': detail})

def emit(title, rows):
    print(title)
    print('=' * len(title))
    for r in rows:
        print(f"  [{'REPRODUCED' if r['reproduced'] else 'not reproduced'}] {r['check']}")
        print(f"      {r['detail']}")
    any_repro = any(r['reproduced'] for r in rows)
    print()
    print('RESULT:', 'DEFECT PRESENT' if any_repro else 'DEFECT ABSENT (fixed or never present)')
    return 1 if any_repro else 0
