"""Finding 2 — the seller-warning branch contradicts the status the grader computed.

seller_warnings() derived its wording from the withholding issue alone and never
consulted the SKU's status. A SKU carrying BOTH a withheld optional-field
conflict AND a blocking problem on some other field got a warning asserting "the
rest of this product is published" while the grader had blocked it and the
payload contained nothing.

Asserted on `branch`, not on prose: the branch is the template choice, and it is
a pure function of (status, designated-but-unapproved). Checking the substring
"published" is not enough — "not published" contains it.

Reported shape vs actual: the report named three branches, blocked / eligible
for publication / awaiting approval. Before the repair only two existed and
neither consulted status. The three now exist and are named in `branch`.
"""
import sys
from _common import base, rec, conflict, withhold, report, emit
sys.path.insert(0, '..')
import grader

def build(block_it, designate):
    case, cand = base()
    rec(case, 'P1')['fields']['description'] = 'Slim fit'
    case['evidence']['P1.description'] = {'sku': 'P1', 'field': 'description', 'value': 'Slim fit'}
    conflict(case, 'P1', 'description', 'Relaxed fit')
    withhold(cand, 'P1', 'description')
    if block_it:
        conflict(case, 'P1', 'price', '9999')       # required field -> blocks the SKU
    if designate:
        case['authority_registry'] = {'P1.description': {
            'evidence_id': 'P1.description.alt',
            'source_location': 'supplier-master/spec-v2', 'supplier_approved': False}}
    return grader.grade(case, cand)

def warn(r):
    return next((w for w in r['seller_warnings']
                 if w['sku'] == 'P1' and w['field'] == 'description'), None)

blocked = build(True, False)
eligible = build(False, False)
awaiting = build(False, True)

rows = []
p1 = next(x for x in blocked['records'] if x['sku'] == 'P1')
report(rows, 'the blocked case really is BLOCKED and absent from the payload',
       p1['expected_status'] == 'BLOCKED'
       and 'P1' not in {x['sku'] for x in blocked['publication_payload']['records']},
       f"expected_status={p1['expected_status']} "
       f"payload={sorted(x['sku'] for x in blocked['publication_payload']['records'])}",
       kind='setup')

# The defect: branch disagreeing with the status the grader computed.
mismatches = []
for name, r in (('blocked', blocked), ('eligible', eligible), ('awaiting', awaiting)):
    for w in r['seller_warnings']:
        st = next(x['expected_status'] for x in r['records'] if x['sku'] == w['sku'])
        want = grader.warning_branch(st, 'recommended_from' in w)
        if w.get('branch') != want:
            mismatches.append((name, w['sku'], w['field'], w.get('branch'), want, st))
report(rows, 'a warning branch disagrees with the computed status',
       bool(mismatches), f"mismatches = {mismatches or 'none'}")

report(rows, 'the three branches are distinct and status-driven',
       not (warn(blocked)['branch'] == 'blocked'
            and warn(eligible)['branch'] == 'eligible_for_publication'
            and warn(awaiting)['branch'] == 'awaiting_approval'),
       f"blocked={warn(blocked)['branch']} eligible={warn(eligible)['branch']} "
       f"awaiting={warn(awaiting)['branch']}")
sys.exit(emit('Finding 2 - warning branch inconsistent with final status', rows))
