"""Run the frozen grader against sealed evaluation cases, per 04_DATA_FORMAT.

    python3 run_sealed_cases.py /path/to/cases [--json out.json]

No cases live in this repository. The directory is supplied at run time so the
cases can be authored without the builder seeing them and run without the author
seeing the grader. The grader is imported unmodified; this runner never edits it,
never retries, and never adjusts an expected outcome.

THREE MEASUREMENTS, THREE SUBSETS, THREE DENOMINATORS. Never combined.

  candidate grading      cases with a non-null expected_verdict
  publication            cases with a non-null expected_publication
  seller guidance        cases carrying expected_seller_guidance

A case can be in one, two or all three. Reporting one number over them would
claim coverage that was never checked, so this runner states per case exactly
which expectations it compared.

NOT EXECUTABLE, and excluded from every denominator:
  owner_approval != APPROVED   refused, never scored
  review_status == AMBIGUOUS   deliberately unset, never guessed
  expected_verdict is null     unsettled, never guessed

A case may still be scored on publication or guidance when its verdict is null,
provided it is approved and not AMBIGUOUS — the subsets are independent.
"""
import argparse, json, sys
from pathlib import Path

D = Path(__file__).resolve().parent
sys.path.insert(0, str(D))
from grader import grade, VERSION            # noqa: E402

class CaseSchemaError(Exception):
    """A case is structurally readable but an expectation block is not in the
    published shape, so it cannot be compared. This is reported as its own
    status and excluded from every denominator - never silently skipped, and
    never crashed on. The runner does not reinterpret a nonconforming block.
    """

REQUIRED_KEYS = ('case_id', 'input', 'candidate', 'expected_verdict',
                 'expected_publication', 'owner_approval', 'review_status')
VERDICTS = ('PASS', 'FAIL', None)

def load_case(path):
    try:
        raw = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        raise ValueError(f'{path.name}: not valid JSON - {e}')
    missing = [k for k in REQUIRED_KEYS if k not in raw]
    if missing:
        raise ValueError(f'{path.name}: missing required key(s) {missing}')
    if raw['expected_verdict'] not in VERDICTS:
        raise ValueError(f'{path.name}: expected_verdict must be "PASS", "FAIL" or null, '
                         f'got {raw["expected_verdict"]!r}')
    return raw

# ---------- the three comparisons ----------

def compare_publication(exp, result):
    """expected_publication is a STRUCTURED OBJECT. Its three parts are compared
    separately and each is reported only if the case actually supplied it."""
    checked, mismatches = [], []
    payload = result['publication_payload']['records']

    if not isinstance(exp, dict):
        raise CaseSchemaError(
            'expected_publication must be an object or null; got ' + type(exp).__name__)
    if 'sku_ids' in exp and exp['sku_ids'] is not None:
        checked.append('sku_ids')
        actual = sorted(r['sku'] for r in payload)
        if sorted(exp['sku_ids']) != actual:
            mismatches.append(f"sku_ids expected {sorted(exp['sku_ids'])} got {actual}")

    if 'withheld_fields' in exp and exp['withheld_fields'] is not None:
        checked.append('withheld_fields')
        want = {k: sorted(v) for k, v in exp['withheld_fields'].items() if v}
        got = {k: sorted(v) for k, v in result.get('withheld', {}).items() if v}
        if want != got:
            mismatches.append(f'withheld_fields expected {want} got {got}')

    # parent_links semantics, settled before case authoring:
    #   null          not asserted - skipped, out of the denominator
    #   {}            asserted - NO published SKU carries a parent link
    #   {"C1":"P1"}   asserted for the named SKUs only; silent about others
    #   {"C1":null}   asserted - C1 publishes with no parent link
    # parent_links_exhaustive (default false) additionally forbids a parent link
    # on any SKU the map does not name. An author writing {} to mean "no links"
    # must not get a silent pass: a check that cannot fail is worse than none.
    if 'parent_links' in exp and exp['parent_links'] is not None:
        checked.append('parent_links')
        got = {r['sku']: r.get('parent_sku') for r in payload}
        want = dict(exp['parent_links'])
        exhaustive = bool(exp.get('parent_links_exhaustive', False))
        if not want:
            # {} is an assertion in its own right, and is exhaustive by meaning.
            offenders = {s: p for s, p in got.items() if p is not None}
            if offenders:
                mismatches.append(f'parent_links {{}} asserts no published SKU carries a '
                                  f'parent link, but {offenders} does')
        else:
            narrowed = {k: got.get(k) for k in want}
            if want != narrowed:
                mismatches.append(f'parent_links expected {want} got {narrowed}')
            if exhaustive:
                unnamed = {s: p for s, p in got.items() if p is not None and s not in want}
                if unnamed:
                    mismatches.append(f'parent_links_exhaustive: {unnamed} carries a parent '
                                      f'link and is not named in the map')

    return checked, mismatches

COMPARABLE = frozenset({'sku', 'field', 'branch',
                        'must_reference_evidence', 'recommended_value'})

def normalise_guidance(req):
    """Both accepted shapes, reduced to one.

    Owner ruling 2026-09-20: a plain list is valid. A list IS the `required`
    list, written without the wrapper - the shape an author reaches for when
    every entry is an assertion that guidance exists. The object form is the
    only way to express `must_not_warn`, so both stay.

    This is a shape normalisation, not a reinterpretation: no entry's meaning
    changes, and keys the schema does not compare are still not compared.
    """
    if isinstance(req, list):
        return {'required': req}
    if isinstance(req, dict):
        return req
    raise CaseSchemaError(
        'expected_seller_guidance must be a list of required entries, or an '
        'object with "required" and/or "must_not_warn" lists; got '
        + type(req).__name__)

def compare_guidance(req, result):
    """expected_seller_guidance is a STRUCTURED REQUIREMENT, never a string match.

    Each entry asserts that guidance exists for a named sku+field, and optionally
    that it carries a given branch, references given evidence ids, or recommends
    a given value. Wording is never compared; prose keys are reported as not
    compared rather than silently ignored.
    """
    checked, mismatches, not_compared = [], [], []
    req = normalise_guidance(req)
    warnings = result.get('seller_warnings', [])
    for i, want in enumerate(req.get('required', [])):
        label = f"{want.get('sku')}/{want.get('field')}"
        checked.append(label)
        # Anything outside COMPARABLE is prose. The schema rule is "meaning,
        # never wording", so it is not compared - and it is named, so the
        # guidance denominator never implies coverage it does not have.
        for key in sorted(set(want) - COMPARABLE):
            not_compared.append(f'{label}: {key}')
        hit = next((w for w in warnings
                    if w.get('sku') == want.get('sku') and w.get('field') == want.get('field')), None)
        if hit is None:
            mismatches.append(f'{label}: no seller guidance emitted'); continue
        if 'branch' in want and hit.get('branch') != want['branch']:
            mismatches.append(f"{label}: branch expected {want['branch']!r} got {hit.get('branch')!r}")
        if 'must_reference_evidence' in want:
            got_ev = {e.get('evidence_id') for e in hit.get('conflicting_values', [])}
            missing = set(want['must_reference_evidence']) - got_ev
            if missing:
                mismatches.append(f'{label}: guidance does not reference evidence {sorted(missing)}')
        if 'recommended_value' in want and hit.get('recommended_value') != want['recommended_value']:
            mismatches.append(f"{label}: recommended_value expected {want['recommended_value']!r} "
                              f"got {hit.get('recommended_value')!r}")
    for forbidden in req.get('must_not_warn', []):
        label = f"{forbidden.get('sku')}/{forbidden.get('field')}"
        checked.append(f'!{label}')
        if any(w.get('sku') == forbidden.get('sku') and w.get('field') == forbidden.get('field')
               for w in warnings):
            mismatches.append(f'{label}: guidance emitted where the case forbids it')
    return checked, mismatches, not_compared

# ---------- execution ----------

def run(folder):
    files = sorted(Path(folder).glob('*.json'))
    if not files:
        raise SystemExit(f'No .json cases found in {folder}')
    rows, load_errors = [], []
    for f in files:
        try:
            c = load_case(f)
        except ValueError as e:
            load_errors.append(str(e)); continue

        row = {'case_id': c['case_id'], 'file': f.name,
               'owner_approval': c.get('owner_approval'),
               'review_status': c.get('review_status'),
               'reason': c.get('reason', ''),
               'checked': [], 'mismatches': [], 'schema_errors': [],
               'guidance_not_compared': [],
               'verdict_scored': False, 'publication_scored': False, 'guidance_scored': False}

        ep = c.get('expected_publication')
        if isinstance(ep, dict) and ep.get('parent_links') is None \
                and 'parent_links_exhaustive' in ep:
            row['status'] = 'MALFORMED'
            row['note'] = ('parent_links is null but parent_links_exhaustive is supplied - '
                           'the flag is meaningless without a map; not interpreting it')
            rows.append(row); continue

        if c.get('owner_approval') != 'APPROVED':
            row['status'] = 'UNAPPROVED'
            row['note'] = f"owner_approval is {c.get('owner_approval')!r}, not APPROVED - refused"
            rows.append(row); continue
        if c.get('review_status') == 'AMBIGUOUS':
            row['status'] = 'NOT EXECUTABLE'
            row['note'] = 'review_status AMBIGUOUS - expectation deliberately unset'
            rows.append(row); continue

        try:
            result = grade(c['input'], c['candidate'])
        except Exception as e:
            row['status'] = 'GRADER ERROR'
            row['note'] = f'{type(e).__name__}: {e}'
            row['actual_verdict'] = f'ERROR:{type(e).__name__}'
            rows.append(row); continue

        # SETUP_ERROR is the grader's "this fixture is unusable" outcome. It returns
        # no publication_payload, so nothing downstream can be compared. Report it as
        # its own status and score nothing rather than crashing on the missing key.
        if 'publication_payload' not in result:
            row['status'] = 'SETUP_ERROR'
            row['actual_verdict'] = result.get('verdict', 'SETUP_ERROR')
            row['expected_verdict'] = c['expected_verdict']
            row['note'] = ('grader rejected the fixture before grading: '
                           + '; '.join(str(e.get('detail') or e.get('code') or e) if isinstance(e, dict) else str(e)
                                       for e in result.get('errors', []))
                           + ' - nothing scored')
            rows.append(row); continue

        row['actual_verdict'] = result['verdict']
        row['expected_verdict'] = c['expected_verdict']

        if c['expected_verdict'] is None:
            row['verdict_note'] = 'expected_verdict null - unsettled, not scored'
        else:
            row['verdict_scored'] = True
            row['checked'].append('verdict')
            row['verdict_agrees'] = result['verdict'] == c['expected_verdict']
            row['direction'] = ('incorrect_approval' if c['expected_verdict'] == 'FAIL' and result['verdict'] == 'PASS'
                                else 'incorrect_rejection' if c['expected_verdict'] == 'PASS' and result['verdict'] == 'FAIL'
                                else 'agreement')

        score_expectations(c, result, row)

        # A nonconforming expectation block costs its OWN measurement and nothing
        # else. The three are separate subsets by design - "the three are compared
        # separately and reported separately" - so a guidance block in the wrong
        # shape must not suppress the verdict and publication comparisons, which
        # are readable and were asserted. Suppressing them hides real
        # disagreements behind a formatting problem.
        if row['schema_errors'] and not row['checked']:
            row['status'] = 'CASE_SCHEMA_ERROR'
        else:
            row['status'] = 'SCORED' if row['checked'] else 'NOTHING TO CHECK'
        rows.append(row)
    return rows, load_errors

def score_expectations(c, result, row):
    """Fill row's publication and guidance scoring.

    A CaseSchemaError is caught per block, not per case: it removes that one
    measurement from its own denominator and leaves the other two alone.
    """
    if c['expected_publication'] is None:
        row['publication_note'] = 'expected_publication null - contract does not determine it, not scored'
    else:
        try:
            ck, mm = compare_publication(c['expected_publication'], result)
        except CaseSchemaError as e:
            row['schema_errors'].append('expected_publication: ' + str(e))
            row['publication_note'] = ('expected_publication not in the published shape - '
                                       'not scored, and out of the publication denominator')
        else:
            row['publication_parts_checked'] = ck
            row['checked'] += [f'pub.{p}' for p in ck]
            row['mismatches'] += mm
            if ck:
                row['publication_scored'] = True
                row['publication_agrees'] = not mm
            else:
                row['publication_note'] = 'expected_publication supplied but named no part - not scored'

    g = c.get('expected_seller_guidance')
    if g:
        try:
            ck, mm, nc = compare_guidance(g, result)
        except CaseSchemaError as e:
            row['schema_errors'].append('expected_seller_guidance: ' + str(e))
            row['guidance_note'] = ('expected_seller_guidance not in the published shape - '
                                    'not scored, and out of the guidance denominator')
        else:
            row['guidance_parts_checked'] = ck
            row['checked'] += [f'guid.{p}' for p in ck]
            row['mismatches'] += mm
            row['guidance_not_compared'] = nc
            if ck:
                row['guidance_scored'] = True
                row['guidance_agrees'] = not mm


def report(rows, load_errors, folder):
    unapproved  = [r for r in rows if r['status'] == 'UNAPPROVED']
    malformed   = [r for r in rows if r['status'] == 'MALFORMED']
    setup_err   = [r for r in rows if r['status'] == 'SETUP_ERROR']
    schema_err  = [r for r in rows if r['status'] == 'CASE_SCHEMA_ERROR']
    notexec     = [r for r in rows if r['status'] == 'NOT EXECUTABLE']
    errored     = [r for r in rows if r['status'] == 'GRADER ERROR']
    v_scored    = [r for r in rows if r['verdict_scored']]
    p_scored    = [r for r in rows if r['publication_scored']]
    g_scored    = [r for r in rows if r['guidance_scored']]
    approvals   = [r for r in v_scored if r.get('direction') == 'incorrect_approval']
    rejections  = [r for r in v_scored if r.get('direction') == 'incorrect_rejection']

    print(f'Sealed-case run - grader {VERSION}')
    print(f'cases from: {folder}')
    print('=' * 120)
    print(f"{'case':<36}{'status':<18}{'exp.vrd':<9}{'act.vrd':<13}{'vrd':<5}{'pub':<5}{'guid':<6}{'checked'}")
    print('-' * 120)
    for r in rows:
        def mark(scored, key):
            if not scored: return '-'
            return 'yes' if r.get(key) else 'NO'
        print(f"{r['case_id']:<36}{r['status']:<18}"
              f"{str(r.get('expected_verdict','-')):<9}{str(r.get('actual_verdict','-')):<13}"
              f"{mark(r['verdict_scored'],'verdict_agrees'):<5}"
              f"{mark(r['publication_scored'],'publication_agrees'):<5}"
              f"{mark(r['guidance_scored'],'guidance_agrees'):<6}"
              f"{','.join(r['checked']) if r['checked'] else '(nothing)'}")
        for m in r['mismatches']: print(f"{'':<36}  -> {m}")
        for e in r.get('schema_errors', []): print(f"{'':<36}  -> not in the published shape, {e}")
        for n in r.get('guidance_not_compared', []):
            print(f"{'':<36}  -> not compared (prose, never matched by wording): {n}")
        if r.get('note'): print(f"{'':<36}  -> {r['note']}")
    print('-' * 120)

    print('WHAT WAS ACTUALLY CHECKED - three separate measurements, three subsets')
    print()
    print(f'CANDIDATE GRADING    denominator {len(v_scored)} case(s) with a settled expected_verdict')
    print(f'  agreements         : {sum(1 for r in v_scored if r.get("verdict_agrees"))} / {len(v_scored)}')
    print(f'PUBLICATION          denominator {len(p_scored)} case(s) with a structured expected_publication')
    print(f'  agreements         : {sum(1 for r in p_scored if r.get("publication_agrees"))} / {len(p_scored)}')
    if p_scored:
        parts = sorted({p for r in p_scored for p in r.get('publication_parts_checked', [])})
        print(f'  parts compared     : {parts}   (only the parts each case supplied)')
    blocked_blocks = [(r['case_id'], e) for r in rows for e in r.get('schema_errors', [])]
    print(f'SELLER GUIDANCE      denominator {len(g_scored)} case(s) carrying expected_seller_guidance')
    print(f'  agreements         : {sum(1 for r in g_scored if r.get("guidance_agrees"))} / {len(g_scored)}')
    if blocked_blocks:
        print()
        print(f'EXPECTATION BLOCKS NOT IN THE PUBLISHED SHAPE: {len(blocked_blocks)}')
        print('  Each costs its own measurement only. The other two subsets for that')
        print('  case are still compared and still counted.')
        for cid, e in blocked_blocks: print(f'  - {cid:<36} {e}')
    print()
    print(f'INCORRECT APPROVALS  : {len(approvals)}   '
          f'{[r["case_id"] for r in approvals] if approvals else "none"}')
    print('   (expected FAIL, grader returned PASS - accepted what should have been rejected)')
    print(f'INCORRECT REJECTIONS : {len(rejections)}   '
          f'{[r["case_id"] for r in rejections] if rejections else "none"}')
    print('   (expected PASS, grader returned FAIL - rejected what should have been accepted)')
    print()
    print('Directions are keyed off the candidate verdict, never off publication. A')
    print('product correctly left unpublished by a candidate that handled it right is')
    print('an agreement, not a rejection.')
    print()
    print('A verdict agreement says nothing about payload or guidance correctness on')
    print('that case - only the columns marked yes/NO were compared. The three')
    print('denominators are separate and are never combined into one number.')

    excluded = unapproved + notexec + malformed + setup_err + schema_err
    if excluded:
        print()
        print(f'EXCLUDED FROM EVERY DENOMINATOR: {len(excluded)}')
        for r in excluded: print(f'  - {r["case_id"]:<36} {r["status"]:<18} {r["note"]}')
    if errored:
        print()
        print(f'GRADER ERRORS: {len(errored)}')
        for r in errored: print(f'  - {r["case_id"]}: {r["note"]}')
    if load_errors:
        print()
        print(f'CASES THAT COULD NOT BE LOADED: {len(load_errors)}')
        for e in load_errors: print(f'  - {e}')
    print()
    print(f'{len(rows)} case(s) are an initial independent check. A run this size does')
    print('not measure the >98% publication-accuracy target or the <0.5%')
    print('wrong-rejection target.')

    return (len(approvals) + len(rejections) + len(errored) + len(load_errors) + len(malformed) + len(setup_err) + len(schema_err)
            + sum(1 for r in p_scored if not r.get('publication_agrees'))
            + sum(1 for r in g_scored if not r.get('guidance_agrees')))

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cases', help='directory of sealed case .json files')
    ap.add_argument('--json', help='also write the full result as JSON to this path')
    a = ap.parse_args()
    rows, load_errors = run(a.cases)
    problems = report(rows, load_errors, a.cases)
    if a.json:
        Path(a.json).write_text(json.dumps(
            {'grader_version': VERSION, 'cases_dir': str(a.cases),
             'results': rows, 'load_errors': load_errors}, indent=2))
    return 0 if problems == 0 else 1

if __name__ == '__main__':
    sys.exit(main())
