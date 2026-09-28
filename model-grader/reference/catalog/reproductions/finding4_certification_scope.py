"""Adjudication 6 — certification must be a FAMILY-WIDE hold, not a per-SKU one.

The owner's clarification: a certification applies to a group, not to an
individual SKU. It does not come individually, so it must be evaluated at group
level. Until the catalog review team approves the certificate, the parent AND
every variant are held.

v2.2 behaviour: `certification` is not in SHARED, so an unapproved certificate on
the parent blocks only the parent. A valid child publishes straight past it.

Asserted on the publication payload itself — not a status field, not a substring.
The payload is what a downstream consumer actually receives, and it is the only
place "no variant is published" can be checked honestly.
"""
import sys
from _common import base, rec, report, emit
sys.path.insert(0, '..')
import grader

def pending_certificate():
    """Parent carries a certification claim with no approved human review."""
    case, cand = base()
    rec(case, 'P1')['fields']['certification'] = 'ISO-9001'
    case['evidence']['P1.certification'] = {'sku': 'P1', 'field': 'certification', 'value': 'ISO-9001'}
    return case, cand

case, cand = pending_certificate()
records, values = grader.check_setup(case)
blocking = {}
for sku in records:
    b, _ = grader.partition_issues(grader.expected_issues(case, records, values, sku), case['profile'])
    blocking[sku] = [(i['code'], i['field']) for i in b]
r = grader.grade(case, cand)
published = sorted(x['sku'] for x in r['publication_payload']['records'])

rows = []
report(rows, 'the parent is held on the pending certificate',
       any(c == 'HUMAN_VALIDATION_REQUIRED' for c, f in blocking['P1']),
       f"P1 blocking = {blocking['P1']}", kind='setup')
report(rows, 'a variant still publishes while approval is pending',
       bool(published),
       f"P1 blocking={blocking['P1']}  C1 blocking={blocking['C1']}  "
       f"publication_payload = {published}")
report(rows, "certification is treated as per-SKU, not family-wide",
       'certification' not in grader.SHARED and not blocking['C1'],
       f"'certification' in SHARED = {'certification' in grader.SHARED}; C1 blocking = {blocking['C1']}")
sys.exit(emit('Adjudication 6 - certification scope is per-SKU, must be family-wide', rows))
