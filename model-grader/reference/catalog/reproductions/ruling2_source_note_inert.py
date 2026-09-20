"""Ruling 2: an evidence entry's optional `source_note` is inert.

Two assertions, both required by the ruling:

  1. The grader accepts an evidence entry carrying `source_note`, and rejects a
     non-string one. Acceptance alone is not the point.
  2. The SAME case with notes and without notes produces an identical verdict,
     an identical error list and an identical publication payload. Only the
     guidance text may differ.

Absence must never change a verdict, so the comparison is byte-for-byte on
everything except the guidance channels.
"""
import copy, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import base, rec, conflict, withhold, report, emit   # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from grader import grade   # noqa: E402

# grade() does not raise on a bad fixture: it returns verdict SETUP_ERROR with the
# message in errors and no publication_payload. Check the return, not an exception.

NOTES = {'P1.description': 'spec sheet A, page 4',
         'P1.description.alt': 'supplier invoice, 12 Aug'}

def build(with_notes):
    case, cand = base()
    # gold/S1 carries no description, so supply the first source before the second.
    case['evidence']['P1.description'] = {
        'sku': 'P1', 'field': 'description', 'value': 'A light summer weave'}
    refs = conflict(case, 'P1', 'description', 'A heavier winter weave',
                    alt_key='P1.description.alt')
    withhold(cand, 'P1', 'description')
    if with_notes:
        for ref, note in NOTES.items():
            case['evidence'][ref]['source_note'] = note
    return case, cand, refs

rows = []

# --- 1. accepted, and a non-string is refused -------------------------------
case, cand, refs = build(True)
res_notes = grade(case, cand)
accepted = res_notes['verdict'] != 'SETUP_ERROR'
report(rows, 'source_note is accepted on an evidence entry', accepted,
       f"verdict {res_notes['verdict']}" if accepted else f"rejected: {res_notes['errors']}",
       kind='setup')

bad, bad_cand, _ = build(True)
bad['evidence']['P1.description']['source_note'] = 17
res_bad = grade(bad, bad_cand)
refused = res_bad['verdict'] == 'SETUP_ERROR'
report(rows, 'a non-string source_note is refused', refused,
       f"{res_bad['verdict']}: {res_bad['errors']}", kind='setup')

# --- 2. inert: same verdict, same errors, same payload ----------------------
plain_case, plain_cand, _ = build(False)
res_plain = grade(plain_case, plain_cand)

same_verdict = res_notes['verdict'] == res_plain['verdict']
same_errors  = res_notes['errors'] == res_plain['errors']
same_payload = res_notes['publication_payload'] == res_plain['publication_payload']
same_withheld = res_notes['withheld'] == res_plain['withheld']

report(rows, 'verdict unchanged by source_note', not same_verdict,
       f"with notes {res_notes['verdict']}, without {res_plain['verdict']}")
report(rows, 'error list unchanged by source_note', not same_errors,
       f"{len(res_notes['errors'])} error(s) with notes, {len(res_plain['errors'])} without"
       f"{'' if same_errors else ' - AND THEY DIFFER'}")
report(rows, 'publication payload unchanged by source_note', not same_payload,
       'payloads byte-identical' if same_payload else 'PAYLOADS DIFFER')
report(rows, 'withheld map unchanged by source_note', not same_withheld,
       f"{json.dumps(res_plain['withheld'])}")

# --- 3. the only thing that may differ is guidance text ---------------------
g_notes = [w['action'] for w in res_notes['seller_warnings']]
g_plain = [w['action'] for w in res_plain['seller_warnings']]
report(rows, 'guidance text differs when notes are present', g_notes == g_plain,
       f"with notes: {g_notes[0] if g_notes else '(none)'}\n"
       f"      without  : {g_plain[0] if g_plain else '(none)'}")

sys.exit(emit('Ruling 2 - source_note is carried, quoted, and never decides anything', rows))
