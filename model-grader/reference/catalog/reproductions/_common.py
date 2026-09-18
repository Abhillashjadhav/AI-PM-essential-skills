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

def report(rows, name, holds, detail, kind='defect'):
    """kind='setup' asserts the fixture reached the state under test.
    kind='defect' asserts the defective behaviour itself. Only defect rows decide
    the exit code — a setup row that stops holding means the fixture broke, which
    is reported separately so it cannot be mistaken for a fix."""
    rows.append({'check': name, 'holds': holds, 'detail': detail, 'kind': kind})

def emit(title, rows):
    print(title)
    print('=' * len(title))
    for r in rows:
        if r['kind'] == 'setup':
            tag = 'setup ok' if r['holds'] else 'SETUP BROKEN'
        else:
            tag = 'DEFECT' if r['holds'] else 'clean'
        print(f"  [{tag}] {r['check']}")
        print(f"      {r['detail']}")
    setup_broken = [r for r in rows if r['kind'] == 'setup' and not r['holds']]
    defects = [r for r in rows if r['kind'] == 'defect' and r['holds']]
    print()
    if setup_broken:
        print('RESULT: FIXTURE BROKEN - the case no longer reaches the state under test')
        return 2
    print('RESULT:', 'DEFECT PRESENT' if defects else 'DEFECT ABSENT')
    return 1 if defects else 0
