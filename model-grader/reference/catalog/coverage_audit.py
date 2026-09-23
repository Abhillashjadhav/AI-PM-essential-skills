"""Coverage audit: does every input and issue code in grader.py trace to a question?

Re-runs Check 1 of model-grader/VERIFICATION.md against grader.py as it is.

Two halves, and they are not equally trustworthy:

  EXTRACTION is mechanical. Regexes over grader.py find every consumed key and
  every emitted issue code. Anyone can re-run this and get the same set.

  MAPPING is judgment. INPUT_MAP and CODE_MAP below were written by hand. A
  different reader could map some entries to a different question.

So "45/45" means every extracted input has a question somebody argued it
belongs to. It does not mean coverage is independently confirmed. The mapping
tables are in this file so a reader can disagree with a specific line.

Usage:  python3 coverage_audit.py
"""
import re, json
src=open('grader.py').read()

INPUT_MAP = {
 ('case','case_id'):'B2',('case','catalog'):'B7',('case','contract_version'):'B7',
 ('case','evidence'):'A7',('case','flagship_skus'):'A5',('case','profile'):'A6',
 ('case','records'):'A4',('case','authority_registry'):'A10',('case','supplier_edits'):'A10',
 ('profile','aliases'):'B3',('profile','allowed'):'A6',('profile','human_review_fields'):'C7',
 ('profile','known_corrections'):'A9',('profile','subbrand_applicable'):'A5',
 ('record','sku'):'A4',('record','role'):'A8',('record','parent_sku'):'A8',
 ('record','record_status'):'A9',('record','fields'):'A4',('record','claims'):'A7',
 ('record','conflicts'):'A10',('record','measurements'):'A4',
 ('record','inherit_fields'):'B5',('record','proposed_corrections'):'A9',
 ('candidate','case_id'):'B2',('candidate','catalog'):'B7',('candidate','records'):'A4',
 ('output','status'):'C1',('output','fields'):'A4',('output','issues'):'C2',
 ('output','evidence'):'A7',('output','measurements'):'A4',('output','display'):'A6',
 ('output','role'):'A8',('output','parent_sku'):'A8',('output','record_status'):'A9',
 ('measurement','id'):'A4',('measurement','type'):'A6',('measurement','measurement_type'):'A6',
 ('measurement','value'):'B3',('measurement','unit'):'A6',('measurement','label'):'A6',
 ('measurement','bands'):'A6',('measurement','components'):'B3',('measurement','evidence_id'):'A7',
}
CODE_MAP = {
 'CASE_ID':'B2','CATALOG_CONTEXT':'B7','COMPOSITION_ROUNDING':'C4','CONVERSION_ERROR':'A6',
 'CONVERSION_P2':'C4','DISPLAY_VALUE':'A6','DUPLICATE_MEASUREMENT':'A4','DUPLICATE_SKU':'A4',
 'EMPTY_OR_REFUSAL':'B8','FALSE_BLOCK':'C1','FALSE_READY':'C1','FAMILY_LINK':'A8',
 'INVENTED_SKU':'B1','ISSUE_COVERAGE':'C2','ISSUE_EVIDENCE':'A7','MALFORMED_RECORD':'A4',
 'MEASUREMENT_COVERAGE':'A4','MEASUREMENT_PRECISION':'C4','MEASUREMENT_SOURCE':'A7',
 'MEASUREMENT_UNIT':'A6','MISSING_ACTION':'B8','MISSING_MEASUREMENT':'A4','OMITTED_FACT':'B4',
 'OMITTED_SKU':'B4','RECORD_STATUS':'A9','REMAINDER_PROVENANCE':'A7','SIZE_BOUNDARY':'A6',
 'SPURIOUS_ISSUE':'B1','UNSUPPORTED_OUTPUT_FIELD':'B6','UNSUPPORTED_VALUE':'B1',
 'WRONG_EVIDENCE':'A7','WRONG_VALUE':'B3','SIZE_CHART_CONFLICT':'A6',
 'COMPOSITION_EXCESS':'A6','COMPOSITION_INCOMPLETE':'A6','FAMILY_MISMATCH':'A8',
 'HUMAN_VALIDATION_REQUIRED':'C7','MEASUREMENT_INPUT':'A4','MISSING_REQUIRED':'A5',
 'NAMED_BLEND_MAJORITY':'A6','PARENT_UNRESOLVED':'B5','SOURCE_CONFLICT':'A10',
 'SUPPLIER_APPROVAL_REQUIRED':'A10','UNMAPPED_VALUE':'A6',
 # Withholding exists only because a field's requirement class decides whether a
 # conflict blocks or withholds. Without A5 there is no optional/required split
 # to partition on, and this code could not exist.
 'WITHHELD_FIELD_PUBLISHED':'A5',
}
def keys(*vs):
    s=set()
    for v in vs: s|=set(re.findall(rf"\b{v}(?:\[|\.get\()\s*'([a-z_][a-z0-9_]*)'",src))
    return s
groups={'case':keys('case'),'profile':keys('p','profile'),'record':keys('r','rec'),
        'candidate':keys('cand','candidate'),'output':keys('o','out'),'measurement':keys('m')}
emitted=set(re.findall(r"\berr\(\s*'([A-Z][A-Z0-9_]+)'",src))|set(re.findall(r"else\s+'([A-Z][A-Z0-9_]+)'\s*,",src))|set(re.findall(r"'code'\s*:\s*'([A-Z][A-Z0-9_]+)'",src))
emitted-={'PASS','FAIL','READY','BLOCKED','SETUP_ERROR'}
expected=set(re.findall(r"\badd\(\s*'([A-Z][A-Z0-9_]+)'",src))
codes=sorted(emitted|expected)

inputs=[(g,k) for g,ks in groups.items() for k in sorted(ks)]
imiss=[x for x in inputs if x not in INPUT_MAP]
cmiss=[c for c in codes if c not in CODE_MAP]
print(f"grader.py: {len(src.splitlines())} lines, VERSION {re.search(chr(39)+r'([a-z0-9.-]+)'+chr(39), src[src.index('VERSION'):]).group(1)}")
print()
print(f"CONSUMED INPUTS : {len(inputs)-len(imiss)} / {len(inputs)} trace to a question")
if imiss: print("   UNTRACED:",imiss)
print(f"ISSUE CODES     : {len(codes)-len(cmiss)} / {len(codes)} trace to a question")
if cmiss: print("   UNTRACED:",cmiss)
print()
used=sorted({INPUT_MAP[x] for x in inputs if x in INPUT_MAP}|{CODE_MAP[c] for c in codes if c in CODE_MAP},
            key=lambda q:(q[0],int(q[1:])))
allq=[f"A{i}" for i in range(1,11)]+[f"B{i}" for i in range(1,9)]+[f"C{i}" for i in range(1,9)]
print(f"QUESTIONS EXERCISED: {len(used)} / 26  -> {used}")
print(f"NOT EXERCISED      : {[q for q in allq if q not in used]}")
