"""Finding 2 — the seller-warning text contradicts the status the grader computed.

seller_warnings() derives its wording from the withholding issue alone. It never
consults the SKU's computed status. So when a SKU carries BOTH a withheld
optional-field conflict AND a blocking problem on some other field, the warning
asserts "the rest of this product is published" while the grader has blocked the
SKU and the payload contains nothing.

Two branches exist today: the plain one, and the designated-but-unapproved one
that recommends a value. Both assert publication unconditionally.
"""
import sys
from _common import base, rec, conflict, withhold, report, emit
sys.path.insert(0, '..')
import grader

case, cand = base()
# 1. an OPTIONAL field conflict -> withheld, warning generated
rec(case, 'P1')['fields']['description'] = 'Slim fit'
case['evidence']['P1.description'] = {'sku': 'P1', 'field': 'description', 'value': 'Slim fit'}
conflict(case, 'P1', 'description', 'Relaxed fit')
withhold(cand, 'P1', 'description')
# 2. a REQUIRED field conflict on the SAME SKU -> blocks it
conflict(case, 'P1', 'price', '9999')

r = grader.grade(case, cand)
p1 = next(x for x in r['records'] if x['sku'] == 'P1')
warn = [w for w in r['seller_warnings'] if w['sku'] == 'P1' and w['field'] == 'description']
published = {x['sku'] for x in r['publication_payload']['records']}
asserts_publication = bool(warn) and 'published' in warn[0]['action']

rows = []
report(rows, 'P1 is BLOCKED by the required-field conflict',
       p1['expected_status'] == 'BLOCKED',
       f"P1 expected_status = {p1['expected_status']}", kind='setup')
report(rows, 'P1 is absent from the publication payload',
       'P1' not in published,
       f"payload SKUs = {sorted(published)}", kind='setup')
report(rows, 'yet the seller warning asserts the product IS published',
       asserts_publication,
       f"action = {warn[0]['action'] if warn else '(no warning)'}")
report(rows, 'warning text and computed status disagree',
       p1['expected_status'] == 'BLOCKED' and asserts_publication,
       'branch is derived from the withholding issue alone, never from the status')
sys.exit(emit('Finding 2 - warning branch inconsistent with final status', rows))
