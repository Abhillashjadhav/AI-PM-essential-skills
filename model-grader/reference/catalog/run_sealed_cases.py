"""Run the frozen grader against sealed evaluation cases the builder has not seen.

    python3 run_sealed_cases.py /path/to/cases [--json out.json]

No cases live in this repository. The directory is supplied at run time so the
cases can be authored without the builder seeing them and run without the author
seeing the grader.

The grader is imported unmodified. This runner never edits it, never retries, and
never adjusts an expected verdict.

THE TWO ERROR DIRECTIONS ARE NEVER COMBINED.

    INCORRECT APPROVAL  - the case expected FAIL, the grader said PASS.
                          The grader accepted work that should have been rejected.
    INCORRECT REJECTION - the case expected PASS, the grader said FAIL.
                          The grader rejected work that should have been accepted.

They have different costs and different owners, and a single accuracy number
hides which one is happening. There is deliberately no such number in this output.
"""
import argparse, json, sys
from pathlib import Path

D = Path(__file__).resolve().parent
sys.path.insert(0, str(D))
from grader import grade, VERSION            # noqa: E402

VALID = ('PASS', 'FAIL')

def load_case(path):
    """Read one case file. Raises ValueError with the file name on any problem."""
    try:
        raw = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        raise ValueError(f'{path.name}: not valid JSON - {e}')
    for key in ('case_id', 'expected_verdict', 'input', 'candidate'):
        if key not in raw:
            raise ValueError(f'{path.name}: missing required key {key!r}')
    if raw['expected_verdict'] not in VALID:
        raise ValueError(f'{path.name}: expected_verdict must be one of {VALID}, '
                         f'got {raw["expected_verdict"]!r}')
    return raw

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
        try:
            actual = grade(c['input'], c['candidate'])['verdict']
        except Exception as e:
            # A grader crash is a result, not an excuse to skip the case.
            actual = f'ERROR:{type(e).__name__}'
        expected = c['expected_verdict']
        rows.append({'case_id': c['case_id'], 'file': f.name,
                     'expected_verdict': expected, 'actual_verdict': actual,
                     'agrees': actual == expected,
                     'reason': c.get('reason', ''),
                     'direction': ('incorrect_approval' if expected == 'FAIL' and actual == 'PASS'
                                   else 'incorrect_rejection' if expected == 'PASS' and actual == 'FAIL'
                                   else 'other_disagreement' if actual != expected
                                   else 'agreement')})
    return rows, load_errors

def report(rows, load_errors, folder):
    approvals  = [r for r in rows if r['direction'] == 'incorrect_approval']
    rejections = [r for r in rows if r['direction'] == 'incorrect_rejection']
    other      = [r for r in rows if r['direction'] == 'other_disagreement']
    agree      = [r for r in rows if r['agrees']]

    print(f'Sealed-case run - grader {VERSION}')
    print(f'cases from: {folder}')
    print('=' * 68)
    print(f"{'case':<16}{'expected':<12}{'actual':<12}{'agreement'}")
    print('-' * 68)
    for r in rows:
        print(f"{r['case_id']:<16}{r['expected_verdict']:<12}{r['actual_verdict']:<12}"
              f"{'yes' if r['agrees'] else 'NO'}")
    print('-' * 68)
    print(f'Total cases        : {len(rows)}')
    print(f'Agreements         : {len(agree)}')
    print()
    print(f'INCORRECT APPROVALS : {len(approvals)}   '
          f'{[r["case_id"] for r in approvals] if approvals else "none"}')
    print('   (expected FAIL, grader returned PASS - accepted what should have been rejected)')
    print(f'INCORRECT REJECTIONS: {len(rejections)}   '
          f'{[r["case_id"] for r in rejections] if rejections else "none"}')
    print('   (expected PASS, grader returned FAIL - rejected what should have been accepted)')
    if other:
        print(f'OTHER DISAGREEMENTS : {len(other)}   {[r["case_id"] for r in other]}')
        print('   (grader raised an error or returned a verdict outside PASS/FAIL)')
    print()
    print('The two error directions are reported separately and are not combined')
    print('into an accuracy figure. Ten cases are an initial independent check;')
    print('they do not measure the >98% publication-accuracy or <0.5%')
    print('wrong-rejection targets.')
    if load_errors:
        print()
        print(f'CASES THAT COULD NOT BE LOADED: {len(load_errors)}')
        for e in load_errors: print('  -', e)
    return len(approvals) + len(rejections) + len(other) + len(load_errors)

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
             'results': rows, 'load_errors': load_errors,
             'incorrect_approvals': [r['case_id'] for r in rows if r['direction'] == 'incorrect_approval'],
             'incorrect_rejections': [r['case_id'] for r in rows if r['direction'] == 'incorrect_rejection']},
            indent=2))
    return 0 if problems == 0 else 1

if __name__ == '__main__':
    sys.exit(main())
