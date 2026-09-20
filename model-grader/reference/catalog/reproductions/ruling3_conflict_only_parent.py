"""D1, second half: a parent that supplies a field ONLY as a declared conflict.

v2.4 narrowed the F3 class with supplies() and left this half open. A green
suite and a passing review both missed it, so it gets its own regression case.

The shape: the parent carries no settled `material` because its two sources
disagree, and declares the conflict. So

    supplies(parent, 'material') is True   - it HAS supplied the field, disputed
    settled (parent, 'material') is False  - there is no agreed value

Blocking propagation asks supplies(), and must still fire PARENT_UNRESOLVED on
the child. Value resolution asks settled(), and must never read
values[parent]['material'] - which is what raised KeyError 'material' and was
reported as MALFORMED_RECORD against a well-formed child.

Before the repair this reports DEFECT PRESENT; after it, DEFECT ABSENT. Both
halves are asserted: the crash is gone AND the child is still blocked. A repair
that silenced the crash by dropping the propagation would fail this file.
"""
import copy, json, sys
from pathlib import Path
D = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(D))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import base, rec, report, emit                       # noqa: E402
from grader import grade, check_setup, expected_issues, partition_issues   # noqa: E402

A = {'components': [{'material': 'cotton', 'percent': '60'},
                    {'material': 'polyester', 'percent': '40'}]}
B = {'components': [{'material': 'cotton', 'percent': '80'},
                    {'material': 'polyester', 'percent': '20'}]}

case, cand = base()
p1 = rec(case, 'P1')
p1['fields'].pop('material')                 # no settled value ...
case['evidence'].pop('P1.material')
case['evidence']['P1.material.a'] = {'sku': 'P1', 'field': 'material', 'value': A}
case['evidence']['P1.material.b'] = {'sku': 'P1', 'field': 'material', 'value': B}
p1['conflicts'] = [{'field': 'material',                 # ... but a declared conflict
                    'evidence': ['P1.material.a', 'P1.material.b']}]

# The child carries a material of its own. That is what makes the grader reach
# for the parent's value to compare against: without it the branch is not taken
# for any reason and the fixture would prove nothing.
rec(case, 'C1')['fields']['material'] = copy.deepcopy(A)
case['evidence']['C1.material'] = {'sku': 'C1', 'field': 'material', 'value': copy.deepcopy(A)}

recs, vals = check_setup(case)
res = grade(case, cand)
rows = []

# --- setup: the fixture really is the shape under test -----------------------
# Stated from the fixture itself, not via grader helpers, so this file runs
# unchanged against a grader that predates them.
def has_value(sku):
    v = vals.get(sku, {}).get('material')
    return v is not None and v != ''

declares_conflict = any(c.get('field') == 'material'
                        for c in rec(case, 'P1').get('conflicts', []))
report(rows, 'the parent supplies material only as a declared conflict',
       declares_conflict and not has_value('P1'),
       f"declares a material conflict={declares_conflict}  "
       f"carries a settled material={has_value('P1')}", kind='setup')
report(rows, 'the child carries a material of its own', has_value('C1'),
       f"C1 material={json.dumps(vals['C1'].get('material'))}", kind='setup')

# --- half one: the crash --------------------------------------------------
crash = [e for e in res['errors']
         if e['code'] == 'MALFORMED_RECORD' and e['sku'] == 'C1'
         and e['detail'] == "'material'"]
report(rows, "KeyError 'material' reported as MALFORMED_RECORD against the child",
       bool(crash), f"{crash}" if crash else "no KeyError-derived MALFORMED_RECORD against C1")

# --- half two: what must NOT be lost to the repair ------------------------
blocking, _ = partition_issues(expected_issues(case, recs, vals, 'C1'), case['profile'])
held = [i for i in blocking if i['code'] == 'PARENT_UNRESOLVED' and i['field'] == 'material']
report(rows, 'the child stopped being blocked by its disputed parent', not held,
       f"C1 blocking={[(i['code'], i['field']) for i in blocking]}")

p_blocking, _ = partition_issues(expected_issues(case, recs, vals, 'P1'), case['profile'])
report(rows, 'the disputed parent stopped being blocked', not p_blocking,
       f"P1 blocking={[(i['code'], i['field']) for i in p_blocking]}")

sys.exit(emit('D1 second half - a conflict-only parent blocks without crashing', rows))
