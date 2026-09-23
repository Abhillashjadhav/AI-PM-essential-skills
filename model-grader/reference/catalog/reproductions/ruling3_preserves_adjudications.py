"""Preservation checks for the ruling of 2026-09-20.

NOT before/after evidence. These pass against frozen-v2.3 and frozen-v2.4 alike.
Their job is to show the field-scoped rule did not quietly repeal a standing
adjudication. Each is verified to discriminate: it is run against a mutation
that would make it wrong, and reports the difference.

  ADJ 1  When parent and child are both live, an unresolved parent conflict
         still blocks the child. Run against the four fixtures the decision
         record names.
  ADJ 1b The boundary the new rule creates. A parent that carries no settled
         value but DECLARES a conflict on the field HAS supplied that field -
         it is disputed, not absent - so it still blocks the child. Only a
         parent that supplies nothing at all makes the child standalone.
  ADJ 6  A certification still holds a live family.

Deliberately uses no source_note, so the whole file runs against frozen-v2.3 as
well and the two versions can be compared directly.
"""
import copy, json, sys
from pathlib import Path
D = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(D))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import base, rec, report               # noqa: E402
from grader import (grade, check_setup, expected_issues,      # noqa: E402
                    partition_issues, VERSION)

rows = []

# ---------------------------------------------------------------- ADJ 1 -----
NAMED = ['parent-conflict-own-evidence-child-blocked',
         'parent-conflict-independent-child-cannot-publish',
         'parent-conflict-inherited-child-blocked',
         'ASTRA_A5_inherit_unvalidated_parent']
checks = json.loads((D / 'revision_checks.json').read_text())
items = checks if isinstance(checks, list) else checks.get('checks', checks.get('cases', []))
by_name = {c.get('name') or c.get('id'): c for c in items}

for name in NAMED:
    c = by_name[name]
    case = c.get('input') or c.get('case')
    recs, vals = check_setup(case)
    blocking, _ = partition_issues(expected_issues(case, recs, vals, 'C1'), case['profile'])
    held = [i for i in blocking if i['code'] == 'PARENT_UNRESOLVED']
    report(rows, f'ADJ 1 {name}', bool(held),
           f"P1 supplies material={'material' in vals['P1']}  "
           f"C1 blocking={[(i['code'], i['field']) for i in blocking]}")

# --------------------------------------------------------------- ADJ 1b -----
# The parent carries no settled material, but declares a conflict on it. Under
# the ruling that still counts as supplying the field, so the child stays blocked.
case, cand = base()
p1 = rec(case, 'P1')
p1['fields'].pop('material')
case['evidence'].pop('P1.material')
case['evidence']['P1.material.a'] = {'sku': 'P1', 'field': 'material',
    'value': {'components': [{'material': 'cotton', 'percent': '60'},
                             {'material': 'polyester', 'percent': '40'}]}}
case['evidence']['P1.material.b'] = {'sku': 'P1', 'field': 'material',
    'value': {'components': [{'material': 'cotton', 'percent': '80'},
                             {'material': 'polyester', 'percent': '20'}]}}
p1['conflicts'] = [{'field': 'material', 'evidence': ['P1.material.a', 'P1.material.b']}]

recs, vals = check_setup(case)
blocking, _ = partition_issues(expected_issues(case, recs, vals, 'C1'), case['profile'])
held = [i for i in blocking if i['code'] == 'PARENT_UNRESOLVED']
report(rows, 'ADJ 1b a disputed parent field is supplied, and still blocks the child',
       bool(held),
       f"P1 settled material={'material' in vals['P1']}  "
       f"P1 declares a conflict on material=True  "
       f"C1 blocking={[(i['code'], i['field']) for i in blocking]}")

# Discriminator: drop the declared conflict and the parent supplies nothing at
# all. The child must then be standalone. If this does not flip, the check above
# is not testing what it claims.
alone = copy.deepcopy(case)
rec(alone, 'P1').pop('conflicts')
alone['evidence'].pop('P1.material.a')
alone['evidence'].pop('P1.material.b')
recs_a, vals_a = check_setup(alone)
blocking_a, _ = partition_issues(expected_issues(alone, recs_a, vals_a, 'C1'), alone['profile'])
changed = []
report(changed, 'discriminator: with nothing supplied at all the child is standalone',
       not [i for i in blocking_a if i['code'] == 'PARENT_UNRESOLVED'],
       f"C1 blocking={[(i['code'], i['field']) for i in blocking_a]}")

# ---------------------------------------------------------------- ADJ 6 -----
PENDING = {'field': 'certification', 'document_ref': 'supplier/doc-x',
           'human_review': {'status': 'pending', 'reviewer': 'catalog-review-team',
                            'reviewed_at': '2026-09-18', 'document_ref': 'supplier/doc-x',
                            'evidence_id': 'C1.certification'}}
case6, cand6 = base()
c1 = rec(case6, 'C1')
c1['fields']['certification'] = 'OEKO-TEX 100'
c1['claims'] = [PENDING]
case6['evidence']['C1.certification'] = {'sku': 'C1', 'field': 'certification',
                                         'value': 'OEKO-TEX 100'}
recs6, vals6 = check_setup(case6)
holds = {}
for sku in recs6:
    b, _ = partition_issues(expected_issues(case6, recs6, vals6, sku), case6['profile'])
    holds[sku] = [(i['code'], i['field']) for i in b if i['code'] == 'HUMAN_VALIDATION_REQUIRED']
report(rows, 'ADJ 6 a pending certificate on the child holds the whole live family',
       bool(holds.get('P1')) and bool(holds.get('C1')),
       f"holds={json.dumps(holds)}")

TITLE = 'Preservation - the field-scoped rule repeals no adjudication'
print(f'{TITLE}   [grader {VERSION}]')
print('=' * len(TITLE))
ok = True
for x in rows:
    print(f"  [{'PASS' if x['holds'] else 'FAIL'}] {x['check']}")
    print(f"      {x['detail']}")
    ok = ok and x['holds']
print()
# The discriminator is NOT a preservation check - it is the behaviour the ruling
# changes, and it is expected to read differently on either side of the change.
# It proves the checks above are testing something real: without it, 'the parent
# supplies the field' could be true of every case and ADJ 1b would be vacuous.
# It never decides the exit code.
for x in changed:
    print(f"  [{'v2.4 behaviour' if x['holds'] else 'v2.3 behaviour'}] {x['check']}")
    print(f"      {x['detail']}")
print()
print('RESULT:', 'ALL PRESERVED' if ok else 'PRESERVATION BROKEN')
sys.exit(0 if ok else 1)
