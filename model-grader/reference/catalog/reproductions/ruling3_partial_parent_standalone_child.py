"""Owner ruling 2026-09-20: parent-derived logic for a field runs only where the
parent actually supplies that field.

Built from a fixture shipped in this repository. inputs/D01.json is a valid
parent/child pair. Remove ONLY the parent's material and its evidence: the
parent becomes a partial submission, the child still carries its own complete,
well-formed values.

Before the repair (frozen-v2.3) the grader:
  - reported MALFORMED_RECORD against C1 with detail "'material'", because
    source_ref read values['P1']['material'] and the catch-all in grade()
    swallowed the KeyError and blamed the candidate;
  - abandoned every remaining check on C1, since MALFORMED_RECORD is raised from
    the catch-all wrapping the whole per-record block;
  - expected C1 BLOCKED via the parent, so a valid child could not publish.

After the repair all three are gone and C1 is graded on its own values.
"""
import copy, json, sys
from pathlib import Path
D = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(D))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import report, emit        # noqa: E402
from grader import grade, check_setup, expected_issues, partition_issues   # noqa: E402

case = json.loads((D / 'inputs/D01.json').read_text())
case['records'][0]['fields'].pop('material')
case['evidence'].pop('P1.material')

def candidate_for(case):
    """A candidate that does the right thing with what it was given: every
    supplied fact echoed with its evidence, and the composition text the
    grammar requires."""
    out = {'case_id': case.get('case_id'), 'records': []}
    for r in case['records']:
        fields = copy.deepcopy(r['fields'])
        row = {'sku': r['sku'], 'role': r['role'], 'parent_sku': r.get('parent_sku'),
               'record_status': r['record_status'], 'fields': fields,
               'evidence': {f: f"{r['sku']}.{f}" for f in fields},
               'status': 'READY', 'issues': [], 'measurements': []}
        m = fields.get('material')
        if m:
            row['display'] = {'text': ', '.join(
                f"{c['percent']}% {c['material']}" for c in m['components'])}
        out['records'].append(row)
    return out

cand = candidate_for(case)
recs, vals = check_setup(case)
res = grade(case, cand)

rows = []

# --- setup: the fixture really does reach the state under test ---------------
report(rows, 'the parent supplies no material', 'material' not in vals['P1'],
       f"P1 fields: {sorted(vals['P1'])}", kind='setup')
report(rows, 'the child supplies its own material', 'material' in vals['C1'],
       f"C1 material: {json.dumps(vals['C1']['material'])}", kind='setup')

# --- the defect itself -------------------------------------------------------
c1_malformed = [e for e in res['errors']
                if e['code'] == 'MALFORMED_RECORD' and e['sku'] == 'C1']
report(rows, 'MALFORMED_RECORD blamed on the well-formed child', bool(c1_malformed),
       f"{c1_malformed}" if c1_malformed else 'no MALFORMED_RECORD against C1')

c1_issues = expected_issues(case, recs, vals, 'C1')
c1_blocking, _ = partition_issues(c1_issues, case['profile'])
parent_derived = [i for i in c1_blocking
                  if i['code'] in ('PARENT_UNRESOLVED', 'FAMILY_MISMATCH')]
report(rows, 'the child is blocked by its partial parent', bool(parent_derived),
       f"C1 blocking: {[(i['code'], i['field']) for i in c1_blocking]}")

published = [r['sku'] for r in res['publication_payload']['records']]
report(rows, 'the valid child is held back from publication', 'C1' not in published,
       f"published: {published}")

# --- the remaining checks must actually run on that record -------------------
# MALFORMED_RECORD is raised from the catch-all wrapping the whole per-record
# block, so its presence means every later check on C1 was abandoned. Proving it
# absent is not enough; prove the later checks now reach the record by breaking
# one of them and seeing the specific error it is supposed to raise.
broken = copy.deepcopy(cand)
c1 = next(r for r in broken['records'] if r['sku'] == 'C1')
c1['display']['text'] = '70% cotton, 30% polyester'
res_broken = grade(case, broken)
display_err = [e for e in res_broken['errors']
               if e['sku'] == 'C1' and e['code'] == 'DISPLAY_VALUE']
report(rows, 'later checks on the child are still abandoned', not display_err,
       f"C1 errors with a wrong composition text: "
       f"{[(e['code'], e['field']) for e in res_broken['errors'] if e['sku'] == 'C1']}")

# --- what must NOT change ----------------------------------------------------
p1_blocking, _ = partition_issues(expected_issues(case, recs, vals, 'P1'), case['profile'])
report(rows, 'the partial parent stopped being the seller\'s to complete',
       not p1_blocking,
       f"P1 blocking: {[(i['code'], i['field']) for i in p1_blocking]}")

sys.exit(emit('Ruling 3 - a partial parent never holds back a valid child', rows))
