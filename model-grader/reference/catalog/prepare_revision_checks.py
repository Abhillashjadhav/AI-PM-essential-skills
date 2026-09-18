"""Explicit development expectations derived from owner decisions; no grader oracle."""
import copy,json
from pathlib import Path
D=Path(__file__).parent
BASE=json.loads((D/'gold/S1.json').read_text())
cases=[]
def fresh(): return copy.deepcopy(BASE['input']),copy.deepcopy(BASE['candidate'])
def source(c,sku,f,v):
    r=next(r for r in c['records'] if r['sku']==sku)
    r['fields'][f]=copy.deepcopy(v)
    c['evidence'][sku+'.'+f]={'sku':sku,'field':f,'value':copy.deepcopy(v)}
def output(o,sku,f,v,ref=None):
    r=next(r for r in o['records'] if r['sku']==sku)
    r['fields'][f]=copy.deepcopy(v);r['evidence'][f]=ref or sku+'.'+f
def withhold(o,sku,f,refs):
    """Owner decision 4: the disputed optional field is withheld, the record still publishes.

    The field is absent from the published record, the SKU stays READY, and supplier
    guidance names the field and the conflicting sources.
    """
    r=next(r for r in o['records'] if r['sku']==sku)
    r['fields'].pop(f,None); r['evidence'].pop(f,None)
    r['status']='READY'
    r.setdefault('withheld',[]).append({'field':f,'reason':'SOURCE_CONFLICT','evidence':refs,
        'action':'Supplier: resolve '+f+' using confirmed source information. The rest of this product is published.'})

def block(o,sku,code,f,refs):
    r=next(r for r in o['records'] if r['sku']==sku)
    r['status']='BLOCKED';r['issues'].append({'code':code,'field':f,'evidence':refs,'action':'Supplier: resolve '+f+' using confirmed source information.'})
def add(name,c,o,expected='PASS',code=None,rule=''):
    cases.append({'name':name,'input':copy.deepcopy(c),'candidate':copy.deepcopy(o),
                  'expected':expected,'required_error':code,'rule':rule,
                  'label_status':'development expectation derived from owner rules; not independent gold'})

# Equivalent formats must not become arbitrary factual changes.
c,o=fresh();o['records'][0]['fields']['price']='1490.0'
add('numeric-price-equivalence',c,o,rule='Numeric equality')
c,o=fresh();o['records'][0]['fields']['material']['components'].reverse()
add('material-order-equivalence',c,o,rule='Component order is non-blocking')
c,o=fresh();o['records'][0]['fields']['material']['components'][0]['percent']='80.0'
add('component-number-equivalence',c,o,rule='Numeric equality')
for label in ['Cotton Blend',' cotton   blend ']:
    c,o=fresh()
    for sku in ('P1','C1'):
        source(c,sku,'material',{'label':'cotton blend'});output(o,sku,'material',{'label':label})
    for r in o['records']:r['display']={'text':label}
    add('case-and-spaces-'+label.strip().replace(' ','_'),c,o,rule='Case and whitespace are equivalent')
c,o=fresh();o['records'][0]['fields']['material']['components'][0]['material']='cottn'
add('unapproved-material-spelling-change',c,o,'FAIL','WRONG_VALUE','No automatic factual correction')
c,o=fresh();o['records'][0]['evidence']['price']='C1.price'
add('wrong-sku-evidence',c,o,'FAIL','WRONG_EVIDENCE','Own-SKU evidence binding')
c,o=fresh();c['evidence']['P1.price.backup']=copy.deepcopy(c['evidence']['P1.price']);o['records'][0]['evidence']['price']='P1.price.backup'
add('matching-backup-source',c,o,rule='Either matching document may be cited')
c,o=fresh();c['evidence']['bad-entry']={'value':'1490'}
add('malformed-evidence-setup',c,o,'SETUP_ERROR',rule='Fixture error is not a model error')
c,o=fresh();o['case_id']='OTHER'
add('wrong-case-routing',c,o,'FAIL','CASE_ID','Experiment identity')

# Inherited catalog context is permitted; unsupported changes are not.
c,o=fresh();o['catalog']=copy.deepcopy(c['catalog']);add('explicit-destination',c,o)
c,o=fresh();c['catalog']={'country':'US','currency':'USD'};o['catalog']=copy.deepcopy(c['catalog'])
add('supported-us-destination',c,o,rule='Country flexible; supplied numbers already destination prices')
c,o=fresh();o['catalog']={'country':'IN','currency':'USD'};add('unsupported-currency',c,o,'FAIL','CATALOG_CONTEXT')
c,o=fresh();o['records'][0]['certification']='Certified safe for infants'
add('invented-claim-outside-fields',c,o,'FAIL','UNSUPPORTED_OUTPUT_FIELD')
c,o=fresh();source(c,'P1','description','Plain red crew-neck T-shirt');output(o,'P1','description','Plain red crew-neck T-shirt')
add('supported-extra-description',c,o,rule='Extra descriptive information is permitted with evidence')

# Unresolved parent shared facts versus independent parent price.
c,o=fresh()
c['evidence']['P1.material.other']={'sku':'P1','field':'material','value':{'components':[{'material':'cotton','percent':'60'},{'material':'polyester','percent':'40'}]}}
refs=['P1.material','P1.material.other']
c['records'][0]['conflicts']=[{'field':'material','evidence':refs}]
block(o,'P1','SOURCE_CONFLICT','material',refs);block(o,'C1','PARENT_UNRESOLVED','material',refs)
add('parent-conflict-own-evidence-child-blocked',c,o,rule='Resolve shared parent material before child assignment')
bad=copy.deepcopy(o);bad['records'][1].update(status='READY',issues=[])
add('parent-conflict-independent-child-cannot-publish',c,bad,'FAIL','FALSE_READY')
# Missing inherited field produces the same dependency gate.
c['records'][1]['fields'].pop('material');c['evidence'].pop('C1.material');c['records'][1]['inherit_fields']=['material']
o['records'][1]['evidence']['material']='P1.material'
add('parent-conflict-inherited-child-blocked',c,o)
c,o=fresh();c['records'][0]['fields'].pop('price');c['evidence'].pop('P1.price')
o['records'][0]['fields'].pop('price');o['records'][0]['evidence'].pop('price');block(o,'P1','MISSING_REQUIRED','price',[])
add('parent-price-missing-child-ready',c,o,rule='Independent child attributes do not inherit parent defects')

# Owner decision 4: an unresolved conflict on an OPTIONAL field withholds that field
# and publishes the rest. It does not block the SKU. Superseded expectations that had
# it blocking are in revision_checks_historical.json.
c,o=fresh();source(c,'P1','description','Slim fit');output(o,'P1','description','Slim fit')
c['evidence']['P1.description.spec']={'sku':'P1','field':'description','value':'Relaxed fit'}
refs=['P1.description','P1.description.spec']
withhold(o,'P1','description',refs)
add('optional-description-conflict-withholds-field',c,o,
    rule='Decision 4: optional-field conflict withholds the field, publishes the record')
c['authority_registry']={'P1.description':{'evidence_id':'P1.description.spec','source_location':'supplier-master/spec-v2','supplier_approved':True}}
# An approved authority resolves the conflict, so nothing is withheld any more.
o['records'][0].update(status='READY',issues=[]);o['records'][0].pop('withheld',None)
output(o,'P1','description','Relaxed fit','P1.description.spec')
add('supplier-designated-authority-resolves-description',c,o)
bad=copy.deepcopy(o);output(bad,'P1','description','Slim fit')
add('ignored-authoritative-value',c,bad,'FAIL','WRONG_VALUE')
# Decision 3 still holds: an unapproved designation does not resolve the conflict.
# Decision 4 changes only what happens next — withhold, do not block.
c['authority_registry']['P1.description']['supplier_approved']=False
output(o,'P1','description','Slim fit')
withhold(o,'P1','description',refs)
add('unapproved-authority-withholds-not-blocks',c,o,
    rule='Decision 3 + 4: unapproved authority does not resolve; optional field is withheld, not blocking')

# Explicit edits preserve originals and bind all confirmed family updates.
c,o=fresh();updated={'components':[{'material':'cotton','percent':'60'},{'material':'polyester','percent':'40'}]}
c['evidence']['P1.material.edit']={'sku':'P1','field':'material','value':updated}
c['supplier_edits']=[{'sku':'P1','field':'material','operation':'replace','evidence_id':'P1.material.edit','approved':True,'family_wide':True}]
for sku in ('P1','C1'):output(o,sku,'material',updated,'P1.material.edit')
for r in o['records']:r['display']={'text':'60% cotton, 40% polyester'}
add('approved-family-edit-updates-children',c,o)
bad=copy.deepcopy(o);output(bad,'C1','material',BASE['candidate']['records'][1]['fields']['material'])
bad['records'][1]['display']={'text':'80% cotton, 20% polyester'}
add('stale-child-after-approved-edit',c,bad,'FAIL','WRONG_VALUE')
c,o=fresh();source(c,'P1','description','cottn blend');output(o,'P1','description','cottn blend')
c['records'][0]['proposed_corrections']=[{'field':'description','suggested':'cotton blend'}]
block(o,'P1','SUPPLIER_APPROVAL_REQUIRED','description',['P1.description'])
add('pending-correction-blocks',c,o)
c['evidence']['P1.description.edit']={'sku':'P1','field':'description','value':'cotton blend'}
c['supplier_edits']=[{'sku':'P1','field':'description','operation':'replace','evidence_id':'P1.description.edit','approved':True}]
output(o,'P1','description','cotton blend','P1.description.edit');o['records'][0].update(status='READY',issues=[])
add('supplier-approved-correction',c,o)

# Compatible partial percentages can inherit; generic labels cannot be enriched.
c,o=fresh();parent={'components':[{'material':'cotton','percent':'60'},{'material':'polyester','percent':'40'}]}
child={'components':[{'material':'cotton','percent':'60'},{'material':'polyester'}]}
source(c,'P1','material',parent);source(c,'C1','material',child)
output(o,'P1','material',parent);output(o,'C1','material',parent,'P1.material')
for r in o['records']:r['display']={'text':'60% cotton, 40% polyester'}
add('compatible-partial-child-inherits-percent',c,o)
c,o=fresh()
for sku in ('P1','C1'):source(c,sku,'material',child);output(o,sku,'material',child)
for r in o['records']:r['display']={'text':'60% cotton'}
add('partial-parent-display-preserves-unknown-internally',c,o)
bad=copy.deepcopy(o);bad['records'][0]['fields']['material']['components'].pop()
add('partial-display-is-not-permission-to-drop-source',c,bad,'FAIL','WRONG_VALUE')

# Human validation is tied to the exact claim and document in fixture input.
c,o=fresh();source(c,'P1','certification','Lab certificate X');output(o,'P1','certification','Lab certificate X')
block(o,'P1','HUMAN_VALIDATION_REQUIRED','certification',['P1.certification'])
add('certificate-needs-human-review',c,o)
c['records'][0]['claims']=[{'field':'certification','document_ref':'supplier/doc-x'}]
add('document-alone-is-not-human-approval',c,o)
c['records'][0]['claims'][0]['human_review']={'status':'approved','reviewer':'fixture-human','reviewed_at':'2026-09-18','document_ref':'supplier/doc-x','evidence_id':'P1.certification'}
o['records'][0].update(status='READY',issues=[])
add('supplied-human-attestation-allows-claim',c,o,rule='Synthetic attestation, not live document verification')
c['records'][0]['claims'][0]['human_review']['document_ref']='supplier/different-document'
block(o,'P1','HUMAN_VALIDATION_REQUIRED','certification',['P1.certification'])
add('wrong-document-review-cannot-authorize-claim',c,o)

# Ambiguous source measurements block the SKU, with supplier action.
c,o=fresh();c['records'][0]['measurements']=[{'id':'chest','type':'chest','value':'25','evidence_id':'P1.measurement.chest'}]
block(o,'P1','MEASUREMENT_INPUT','measurement:chest',[])
add('missing-measurement-unit-blocks',c,o)
c,o=fresh();c['records'][0]['measurements']=[{'id':'chest','type':'chest','value':'25','unit':'in','evidence_id':'P1.measurement.chest','bands':[
    {'size':'S','min_cm':'0','max_cm':'63.5','include_min':True,'include_max':True},
    {'size':'M','min_cm':'60','max_cm':'200','include_min':True,'include_max':True}]}]
block(o,'P1','SIZE_CHART_CONFLICT','measurement:chest',[])
add('overlapping-size-bands-block',c,o)
c['records'][0]['measurements'][0]['bands'][1]['min_cm']='63.5'
add('double-owned-size-endpoint-block',c,o)

# Existing attacks also supply legitimate guards against overstrict repairs.
for f in sorted((D/'attacks').glob('ASTRA_A*.json')):
    x=json.loads(f.read_text());add(f.stem,x['input'],x['candidate'],'FAIL',rule=x['claim'])
for x in json.loads((D/'attacks/ASTRA_false_rejections.json').read_text()):
    add(x['id'],x['input'],x['candidate'],'PASS',rule='Owner approved semantic numeric equality / alternate matching sources')

# The remainder must still be correct and explicitly derived.
x=json.loads((D/'attacks/ASTRA_false_rejections.json').read_text())[0]
c,o=copy.deepcopy(x['input']),copy.deepcopy(x['candidate']);o['records'][0]['display']['derived_remainder']='11'
add('wrong-derived-remainder-rejected',c,o,'FAIL','REMAINDER_PROVENANCE')
o['records'][0]['display'].pop('derived_remainder')
add('missing-derived-provenance-rejected',c,o,'FAIL','REMAINDER_PROVENANCE')

c,o=fresh();c['records'][0]['fields'].pop('price');c['evidence'].pop('P1.price')
c['evidence']['P1.price.authority']={'sku':'P1','field':'price','value':'1490'}
c['authority_registry']={'P1.price':{'evidence_id':'P1.price.authority','supplier_approved':True,'source_location':'supplier-master/prices'}}
o['records'][0]['evidence']['price']='P1.price.authority'
add('authority-can-supply-missing-required-fact',c,o)
c,o=fresh()
for sku in ('P1','C1'):
    source(c,sku,'material',{'label':'cottn blend'});output(o,sku,'material',{'label':'cottn blend'})
for r in o['records']:r['display']={'text':'cottn blend'}
c['profile']['known_corrections']={'material':{'cottn blend':'cotton blend'}}
block(o,'P1','SUPPLIER_APPROVAL_REQUIRED','material',['P1.material'])
block(o,'C1','PARENT_UNRESOLVED','material',['P1.material'])
block(o,'C1','SUPPLIER_APPROVAL_REQUIRED','material',['C1.material'])
add('known-typo-requires-supplier-approval',c,o)

# Boundary checks must remain strict while arithmetic tolerance remains allowed.
c=json.loads((D/'inputs/D24.json').read_text());o=json.loads((D/'candidates/sol/D24.json').read_text())
o['records'][0]['measurements'][0]['value']='63.0'
add('size-boundary-crossing-still-fails',c,o,'FAIL','SIZE_BOUNDARY')
o['records'][0]['measurements'][0]['value']='63.2'
add('owned-boundary-endpoint-still-passes',c,o)
c=json.loads((D/'inputs/D23.json').read_text());o=json.loads((D/'candidates/sol/D23.json').read_text())
o['records'][0]['measurements'][0]['value']='63.0'
add('within-tolerance-without-boundary-passes',c,o)
o['records'][0]['measurements'][0]['source_sku']='C1'
add('within-tolerance-wrong-sku-still-fails',c,o,'FAIL','MEASUREMENT_SOURCE')
(D/'revision_checks.json').write_text(json.dumps(cases,indent=2))
print('Wrote',len(cases),'explicit revision checks.')
