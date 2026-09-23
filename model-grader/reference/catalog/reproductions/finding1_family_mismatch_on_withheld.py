"""Finding 1 — FAMILY_MISMATCH blocks an optional field the candidate correctly withheld.

subbrand is in SHARED and is OPTIONAL when profile.subbrand_applicable is false.
Give the child an unresolved conflict on subbrand whose value differs from the
parent's. Decision 4 says the conflict withholds the field and blocks nothing.
The family check compares subbrand anyway and emits FAMILY_MISMATCH on the SAME
field, which is blocking — so the field is withheld and blocked at once, and the
candidate is penalised for doing what decision 4 requires.

The defect lives in expected_issues, not in errors: FAMILY_MISMATCH is an
expected issue, so it sets wanted=BLOCKED, and the honest candidate that
published trips FALSE_READY.
"""
import sys
from _common import base, rec, conflict, withhold, report, emit
sys.path.insert(0, '..')
import grader

def build():
    case, cand = base()
    case['profile']['subbrand_applicable'] = False           # subbrand OPTIONAL
    rec(case, 'C1')['fields']['subbrand'] = 'Core'
    case['evidence']['C1.subbrand'] = {'sku': 'C1', 'field': 'subbrand', 'value': 'Core'}
    conflict(case, 'C1', 'subbrand', 'Premium')              # C1 subbrand disputed
    rec(case, 'P1')['fields']['subbrand'] = 'Heritage'       # parent differs
    case['evidence']['P1.subbrand'] = {'sku': 'P1', 'field': 'subbrand', 'value': 'Heritage'}
    rec(cand, 'P1')['fields']['subbrand'] = 'Heritage'
    rec(cand, 'P1')['evidence']['subbrand'] = 'P1.subbrand'
    withhold(cand, 'C1', 'subbrand')                         # candidate does the right thing
    return case, cand

case, cand = build()
records, values = grader.check_setup(case)
issues = grader.expected_issues(case, records, values, 'C1')
blocking, withholding = grader.partition_issues(issues, case['profile'])
withheld = {i['field'] for i in withholding}
r = grader.grade(case, cand)
c1 = next(x for x in r['records'] if x['sku'] == 'C1')

rows = []
report(rows, 'subbrand is withheld on C1',
       'subbrand' in withheld,
       f"withholding = {[(i['code'], i['field']) for i in withholding]}", kind='setup')
report(rows, 'FAMILY_MISMATCH blocks that same withheld field',
       any(i['code'] == 'FAMILY_MISMATCH' and i['field'] in withheld for i in blocking),
       f"blocking = {[(i['code'], i['field']) for i in blocking]}")
report(rows, 'C1 expected BLOCKED, so the correct candidate fails',
       c1['expected_status'] == 'BLOCKED' and r['verdict'] == 'FAIL',
       f"C1 expected_status={c1['expected_status']} verdict={r['verdict']} "
       f"errors={[(e['code'], e.get('sku')) for e in r['errors']]}")
sys.exit(emit('Finding 1 - FAMILY_MISMATCH on a withheld optional field', rows))
