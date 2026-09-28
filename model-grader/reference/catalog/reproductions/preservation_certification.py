"""Tests 2 and 3 — preservation checks for the family-wide certification hold.

These are NOT before/after evidence. They are expected to pass against v2.2 and
v2.3 alike: their job is to show the change did not break what already worked.
Each is verified to discriminate by a mutation that introduces the specific
mistake it guards against.

Test 2 — approval lifts the hold, it does not grant a pass. A SKU with an
         unrelated blocking issue stays blocked after the certificate is approved.
Test 3 — a family with no certification requirement is untouched by the change.
"""
import sys
from _common import base, rec, conflict, report, emit
sys.path.insert(0, '..')
import grader

APPROVED = {'field': 'certification', 'document_ref': 'supplier/doc-x',
            'human_review': {'status': 'approved', 'reviewer': 'catalog-review-team',
                             'reviewed_at': '2026-09-18', 'document_ref': 'supplier/doc-x',
                             'evidence_id': 'P1.certification'}}

def approved_cert_plus_unrelated_blocker():
    """Certificate approved; C1 independently broken on a required field."""
    case, cand = base()
    rec(case, 'P1')['fields']['certification'] = 'Lab certificate X'
    case['evidence']['P1.certification'] = {'sku': 'P1', 'field': 'certification',
                                            'value': 'Lab certificate X'}
    rec(case, 'P1')['claims'] = [APPROVED]
    refs = conflict(case, 'C1', 'price', '9999')  # required field -> C1 must stay blocked
    # Make the candidate otherwise CORRECT, so the payload reflects the hold and the
    # blocker rather than unrelated candidate defects. Without this P1 is missing from
    # the payload for omitting certification, and the test would pass for the wrong reason.
    rec(cand, 'P1')['fields']['certification'] = 'Lab certificate X'
    rec(cand, 'P1')['evidence']['certification'] = 'P1.certification'
    c1 = rec(cand, 'C1')
    c1['status'] = 'BLOCKED'
    c1['issues'] = [{'code': 'SOURCE_CONFLICT', 'field': 'price', 'evidence': refs,
                     'action': 'Supplier: confirm the correct price.'}]
    return case, cand

def no_certification_at_all():
    case, cand = base()
    return case, cand

def blocking_for(case):
    records, values = grader.check_setup(case)
    return {sku: [(i['code'], i['field'])
                  for i in grader.partition_issues(
                      grader.expected_issues(case, records, values, sku), case['profile'])[0]]
            for sku in records}

rows = []

# ---- Test 2 ----
case, cand = approved_cert_plus_unrelated_blocker()
b = blocking_for(case)
r = grader.grade(case, cand)
published = sorted(x['sku'] for x in r['publication_payload']['records'])
report(rows, 'TEST 2 approval lifts the certification hold',
       not any(c == 'HUMAN_VALIDATION_REQUIRED' for c, f in b['P1'] + b['C1']),
       f"P1 blocking={b['P1']}  C1 blocking={b['C1']}")
report(rows, 'TEST 2 the unrelated blocker still blocks C1, and P1 publishes',
       any(c == 'SOURCE_CONFLICT' and f == 'price' for c, f in b['C1'])
       and published == ['P1'] and r['verdict'] == 'PASS',
       f"C1 blocking={b['C1']}  publication_payload={published}  verdict={r['verdict']}")

# ---- Test 3 ----
case3, cand3 = no_certification_at_all()
b3 = blocking_for(case3)
r3 = grader.grade(case3, cand3)
published3 = sorted(x['sku'] for x in r3['publication_payload']['records'])
report(rows, 'TEST 3 a family with no certification requirement is unaffected',
       not any(c == 'HUMAN_VALIDATION_REQUIRED' for sku in b3 for c, f in b3[sku])
       and published3 == ['C1', 'P1'] and r3['verdict'] == 'PASS',
       f"blocking={b3}  publication_payload={published3}  verdict={r3['verdict']}")

print('Preservation checks - certification family-wide hold')
print('=' * 51)
ok = True
for x in rows:
    print(f"  [{'PASS' if x['holds'] else 'FAIL'}] {x['check']}")
    print(f"      {x['detail']}")
    ok = ok and x['holds']
print()
print('RESULT:', 'ALL PRESERVED' if ok else 'PRESERVATION BROKEN')
sys.exit(0 if ok else 1)
