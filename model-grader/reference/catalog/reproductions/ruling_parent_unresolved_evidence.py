"""(l): a child's PARENT_UNRESOLVED carries only the FIRST parent problem's evidence.

Owner ruling 2026-09-20: a child's PARENT_UNRESOLVED carries the evidence of
every parent problem on that field, not the first one encountered. A candidate
that cites the conflicting sources is doing what the seller needs and must
never be failed for it.

The shape: a required shared field whose sources disagree, so the parent carries
no settled value and trips TWO problems on the same field. expected_issues
builds them in this order -

    MISSING_REQUIRED  material  evidence []
    SOURCE_CONFLICT   material  evidence [a, b]

- because the required-field loop runs before conflicts are appended. The
propagation loop then takes the first problem for the field and skips the rest,
so the child's PARENT_UNRESOLVED inherits the EMPTY evidence and the conflict's
sources are discarded.

ISSUE_EVIDENCE compares both directions: every cited ref must match an expected
ref AND every expected ref must match a cited one. So a candidate that cites
[a, b] against an expectation of [] is failed - for supplying exactly what the
ruling says the seller needs.

Version-portable: uses no helper introduced by the repair. Reports DEFECT
PRESENT on frozen-v2.5 and DEFECT ABSENT on frozen-v2.6.
"""
import copy, json, sys
from pathlib import Path
D = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(D))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import base, rec, report, emit                              # noqa: E402
from grader import grade, check_setup, expected_issues, partition_issues  # noqa: E402

A = {'components': [{'material': 'cotton', 'percent': '60'},
                    {'material': 'polyester', 'percent': '40'}]}
B = {'components': [{'material': 'cotton', 'percent': '80'},
                    {'material': 'polyester', 'percent': '20'}]}
REFS = ['P1.material.a', 'P1.material.b']

case, cand = base()
p1 = rec(case, 'P1')
p1['fields'].pop('material')
case['evidence'].pop('P1.material')
case['evidence']['P1.material.a'] = {'sku': 'P1', 'field': 'material', 'value': A,
                                     'source_note': 'spec sheet A'}
case['evidence']['P1.material.b'] = {'sku': 'P1', 'field': 'material', 'value': B,
                                     'source_note': 'supplier invoice, 12 Aug'}
p1['conflicts'] = [{'field': 'material', 'evidence': REFS}]

# The candidate does the right thing: blocks both, and cites where the conflict is.
cp = rec(cand, 'P1')
cp['fields'].pop('material', None); cp['evidence'].pop('material', None)
cp['display'] = {}
cp['status'] = 'BLOCKED'
cp['issues'] = [
    {'code': 'MISSING_REQUIRED', 'field': 'material', 'evidence': [],
     'action': 'Supply the agreed material composition for this SKU.'},
    {'code': 'SOURCE_CONFLICT', 'field': 'material', 'evidence': list(REFS),
     'action': 'Designate the supplier-approved source for material.'}]
cc = rec(cand, 'C1')
cc['status'] = 'BLOCKED'
cc['issues'] = [
    {'code': 'PARENT_UNRESOLVED', 'field': 'material', 'evidence': list(REFS),
     'action': "Resolve the parent's material conflict before publishing this child."}]

recs, vals = check_setup(case)
res = grade(case, cand)
rows = []

# --- setup: the ordering that causes it --------------------------------------
p_problems, _ = partition_issues(expected_issues(case, recs, vals, 'P1'), case['profile'])
order = [(i['code'], i['evidence']) for i in p_problems if i['field'] == 'material']
report(rows, 'MISSING_REQUIRED is ordered ahead of SOURCE_CONFLICT on material',
       [c for c, _ in order] == ['MISSING_REQUIRED', 'SOURCE_CONFLICT'],
       f"parent problems on material, in order: {order}", kind='setup')
report(rows, 'the candidate cites the conflicting sources',
       rec(cand, 'C1')['issues'][0]['evidence'] == REFS,
       f"C1 PARENT_UNRESOLVED evidence={rec(cand, 'C1')['issues'][0]['evidence']}", kind='setup')

# --- the defect ---------------------------------------------------------------
c_blocking, _ = partition_issues(expected_issues(case, recs, vals, 'C1'), case['profile'])
pu = next((i for i in c_blocking if i['code'] == 'PARENT_UNRESOLVED'
           and i['field'] == 'material'), None)
report(rows, "the child's PARENT_UNRESOLVED drops the conflicting sources",
       pu is not None and sorted(pu['evidence']) != sorted(REFS),
       f"expected evidence={pu['evidence'] if pu else None}, "
       f"the conflict cites {REFS}")

issue_ev = [e for e in res['errors']
            if e['code'] == 'ISSUE_EVIDENCE' and e['sku'] == 'C1']
report(rows, 'the candidate is failed for citing them', bool(issue_ev),
       f"{issue_ev}" if issue_ev else 'no ISSUE_EVIDENCE against C1')

# --- what must survive the repair ---------------------------------------------
report(rows, 'the child stopped being blocked by its disputed parent', pu is None,
       f"C1 blocking={[(i['code'], i['field']) for i in c_blocking]}")

sys.exit(emit("(l) PARENT_UNRESOLVED must carry every parent problem's evidence", rows))
