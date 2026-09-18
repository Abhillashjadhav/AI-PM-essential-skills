"""Finding 3 — MISSING_ACTION penalises a candidate for reporting a PERMITTED issue.

A permitted issue is optional in both directions: the candidate may report it or
stay silent, and neither is wrong. But the per-issue loop applies the same
action-string requirement to permitted issues as to expected ones, so a
candidate that mentions a withheld conflict without an action string is
penalised — strictly worse off than one that said nothing at all.
"""
import sys
from _common import base, rec, conflict, withhold, report, emit
sys.path.insert(0, '..')
import grader

def build(issue):
    case, cand = base()
    rec(case, 'P1')['fields']['description'] = 'Slim fit'
    case['evidence']['P1.description'] = {'sku': 'P1', 'field': 'description', 'value': 'Slim fit'}
    refs = conflict(case, 'P1', 'description', 'Relaxed fit')
    withhold(cand, 'P1', 'description')
    if issue is not None:
        rec(cand, 'P1')['issues'].append(dict(issue, evidence=refs))
    return case, cand

silent = grader.grade(*build(None))
no_action = grader.grade(*build({'code': 'SOURCE_CONFLICT', 'field': 'description'}))
with_action = grader.grade(*build(
    {'code': 'SOURCE_CONFLICT', 'field': 'description', 'action': 'Supplier: confirm the description.'}))

def codes(r): return [(e['code'], e.get('sku'), e.get('field')) for e in r['errors']]

rows = []
report(rows, 'staying silent about the permitted issue passes',
       silent['verdict'] == 'PASS', f"verdict = {silent['verdict']}, errors = {codes(silent)}", kind='setup')
report(rows, 'reporting it WITH an action passes',
       with_action['verdict'] == 'PASS', f"verdict = {with_action['verdict']}, errors = {codes(with_action)}", kind='setup')
report(rows, 'reporting it WITHOUT an action is penalised',
       any(c == 'MISSING_ACTION' for c, s, f in codes(no_action)),
       f"verdict = {no_action['verdict']}, errors = {codes(no_action)}")
report(rows, 'so a permitted issue is not optional in both directions',
       silent['verdict'] == 'PASS' and no_action['verdict'] == 'FAIL',
       'silent PASS vs mentioned-without-action FAIL on identical facts')
sys.exit(emit('Finding 3 - MISSING_ACTION on permitted issues', rows))
