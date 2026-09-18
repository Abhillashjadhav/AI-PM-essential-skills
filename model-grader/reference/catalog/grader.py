"""Offline v1.4 lab grader. No LLM calls and no candidate repair."""
import json
import copy
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

VERSION = 'revised-v2.1'
REQUIRED = ('brand','category','subcategory','design','pattern','material','color','size','price')
SHARED = ('brand','subbrand','category','subcategory','design','pattern','material')
# These are private envelopes at submission/record level, never catalog fields.
# Arbitrary company metadata belongs under internal_metadata. No consumer in
# this package executes, interprets, or publishes these values.
INTERNAL_KEYS = frozenset({'internal_metadata','notes','confidence','_debug','warnings',
                           'created_at','updated_at','processed_at'})

class SetupError(ValueError): pass

def number(x):
    if isinstance(x,bool): raise ValueError('boolean is not a number')
    d=Decimal(str(x))
    if not d.is_finite(): raise ValueError('nonfinite number')
    return d

def norm(x): return ' '.join(str(x).strip().casefold().split())

def canonical(field,value,profile):
    aliases=profile.get('aliases',{}).get(field,{})
    if isinstance(value,str):
        return next((v for k,v in aliases.items() if norm(k)==norm(value)),value)
    return value

def equivalent(a,b):
    if isinstance(a,dict) and isinstance(b,dict):
        if a.keys()!=b.keys(): return False
        for k in a:
            if k in ('percent','recycled_percent') and a[k] is not None and b[k] is not None:
                if number(a[k])!=number(b[k]): return False
            elif not equivalent(a[k],b[k]): return False
        return True
    if isinstance(a,list) and isinstance(b,list):
        return len(a)==len(b) and all(equivalent(x,y) for x,y in zip(a,b))
    if isinstance(a,str) and isinstance(b,str): return norm(a)==norm(b)
    return type(a)==type(b) and a==b

def material_same(a,b):
    if material_key(a)!=material_key(b): return False
    # Compare all supplied metadata, independently of component order/numeric spelling.
    if not equivalent({k:v for k,v in a.items() if k!='components'},
                      {k:v for k,v in b.items() if k!='components'}): return False
    ac={norm(c['material']):c for c in a.get('components',[])}
    bc={norm(c['material']):c for c in b.get('components',[])}
    return all(equivalent({k:v for k,v in ac[n].items() if k not in ('material','percent')},
                          {k:v for k,v in bc[n].items() if k not in ('material','percent')}) for n in ac)

def material_key(m):
    if not isinstance(m,dict): raise ValueError('material must be object')
    cs=m.get('components',[])
    if cs:
        items=[(norm(c['material']), None if c.get('percent') is None else number(c['percent'])) for c in cs]
        if len(set(k for k,v in items))!=len(items): raise ValueError('duplicate material')
        if any(v is not None and (v<0 or v>101) for k,v in items): raise ValueError('invalid proportion')
        return ('components',tuple(sorted(items)))
    if not m.get('label'): raise ValueError('missing material')
    return ('generic',norm(m['label']))

def same(field,a,b):
    if field=='material': return material_same(a,b)
    if field=='price': return number(a)==number(b)
    return equivalent(a,b)

def material_total(m):
    cs=m.get('components',[])
    return sum((number(c['percent']) for c in cs),Decimal(0)) if cs and all(c.get('percent') is not None for c in cs) else None

def display_expected(m):
    cs=m.get('components',[])
    if not cs: return [],m['label']
    cs=[dict(c) for c in cs]
    complete=all(c.get('percent') is not None for c in cs)
    if complete:
        cs.sort(key=lambda c:number(c['percent']),reverse=True)
        if len(cs)==2 and number(cs[0]['percent'])>50 and number(cs[1]['percent'])<10: cs=cs[:1]
        elif len(cs)>=3 and material_total(m)<100:
            cs.append({'material':'others','percent':str(100-material_total(m)),'derived':True})
    elif len(cs)==2:
        known=[c for c in cs if c.get('percent') is not None]
        if len(known)==1 and number(known[0]['percent'])>50: cs=known
    return cs,None

def text_parts(text):
    """Bounded composition grammar: order/case/spacing and comma/semicolon/slash accepted."""
    import re
    chunks=re.split(r'\s*[,;/]\s*',text.strip())
    ans=[]
    for chunk in chunks:
        hit=re.fullmatch(r'\s*(\d+(?:\.\d+)?)\s*%\s*([A-Za-z][A-Za-z -]*)\s*',chunk)
        if hit: ans.append((norm(hit[2]),number(hit[1])))
        elif re.fullmatch(r'[A-Za-z][A-Za-z -]*',chunk): ans.append((norm(chunk),None))
        else: raise ValueError('composition text outside declared grammar')
    return sorted(ans,key=lambda x:x[0])

def authority(case,sku,field):
    entry=case.get('authority_registry',{}).get(f'{sku}.{field}')
    if entry and entry.get('supplier_approved') is True: return entry['evidence_id']
    return None

def compatible_partial(child,parent):
    a=child.get('components',[]); b=parent.get('components',[])
    if not a or not b or not any(c.get('percent') is None for c in a): return False
    if {norm(c['material']) for c in a}!={norm(c['material']) for c in b}: return False
    if any(c.get('percent') is None for c in b): return False
    target={norm(c['material']):c for c in b}
    for c in a:
        t=target[norm(c['material'])]
        if c.get('percent') is not None and number(c['percent'])!=number(t['percent']): return False
        if not equivalent({k:v for k,v in c.items() if k not in ('material','percent')},
                          {k:v for k,v in t.items() if k not in ('material','percent')}): return False
    return equivalent({k:v for k,v in child.items() if k!='components'},
                      {k:v for k,v in parent.items() if k!='components'})

def effective(case):
    records={r['sku']:r for r in case['records']}
    if len(records)!=len(case['records']): raise SetupError('duplicate source SKU')
    out={}
    for sku,r in records.items():
        if r.get('record_status') not in ('existing','proposed'): raise SetupError('record status missing')
        if r.get('role') not in ('parent','child'): raise SetupError('invalid source role')
        if r['role']=='child' and r.get('parent_sku') not in records: raise SetupError('source parent absent')
        out[sku]=copy.deepcopy(r['fields'])
        authority_fields=[e['field'] for e in case.get('evidence',{}).values()
                          if e.get('sku')==sku and authority(case,sku,e.get('field'))]
        for f in set(r['fields'])|set(authority_fields):
            ref=authority(case,sku,f)
            if ref: out[sku][f]=copy.deepcopy(case['evidence'][ref]['value'])
    # Apply only explicit, supplier-approved edits; preserve original input evidence.
    for e in case.get('supplier_edits',[]):
        if e.get('approved') is not True: continue
        value=copy.deepcopy(case['evidence'][e['evidence_id']]['value'])
        out[e['sku']][e['field']]=value
        if e.get('family_wide') and e['field'] in SHARED:
            for child,r in records.items():
                if r.get('parent_sku')==e['sku']: out[child][e['field']]=copy.deepcopy(value)
    for sku,r in records.items():
        for f in r.get('inherit_fields',[]):
            if f not in SHARED or r['role']!='child': raise SetupError('invalid inheritance fixture')
            if f not in out[r['parent_sku']]: raise SetupError('missing inherited parent fact')
            if f not in out[sku]: out[sku][f]=copy.deepcopy(out[r['parent_sku']][f])
        if r['role']=='child':
            cm=out[sku].get('material');pm=out[r['parent_sku']].get('material')
            if cm and pm and compatible_partial(cm,pm): out[sku]['material']=copy.deepcopy(pm)
    return records,out

def source_ref(case,sku,field):
    r=next(r for r in case['records'] if r['sku']==sku)
    for e in reversed(case.get('supplier_edits',[])):
        if e.get('approved') is True and e['field']==field:
            if e['sku']==sku or (e.get('family_wide') and field in SHARED and e['sku']==r.get('parent_sku')):
                return e['evidence_id']
    if r['role']=='child':
        parent=next(x for x in case['records'] if x['sku']==r['parent_sku'])
        _,values=effective(case)
        if (field in r.get('inherit_fields',[]) and field not in r['fields']) or (
            field=='material' and r['fields'].get(field) and compatible_partial(r['fields'][field],values[parent['sku']][field])):
            return source_ref(case,parent['sku'],field)
    return authority(case,sku,field) or f'{sku}.{field}'

def evidence_matches(case,ref,expected_ref):
    actual=case.get('evidence',{}).get(ref)
    expected=case.get('evidence',{}).get(expected_ref)
    if not actual or not expected: return False
    return (actual.get('sku')==expected.get('sku') and actual.get('field')==expected.get('field')
            and same(expected['field'],actual.get('value'),expected.get('value')))

def band(value,bands):
    matches=[]
    for b in bands:
        lo,hi=number(b['min_cm']),number(b['max_cm'])
        if (value>lo or (value==lo and b['include_min'])) and (value<hi or(value==hi and b['include_max'])): matches.append(b['size'])
    return matches

def check_setup(case):
    if case.get('contract_version') not in ('1.4','1.5','1.5.1'): raise SetupError('contract version')
    if not case.get('catalog',{}).get('currency') or not case['catalog'].get('country'): raise SetupError('catalog context')
    if not isinstance(case.get('profile'),dict): raise SetupError('profile absent')
    evidence=case.get('evidence',{})
    source_records={r['sku']:r for r in case['records']}
    for ref,e in evidence.items():
        if not isinstance(e,dict) or set(e)!={'sku','field','value'} or e['sku'] not in source_records or not isinstance(e['field'],str):
            raise SetupError('invalid evidence entry: '+ref)
        if e['field']=='material': material_key(e['value'])
        if e['field']=='price': number(e['value'])
    for key,a in case.get('authority_registry',{}).items():
        e=evidence.get(a.get('evidence_id'))
        if not e or key!=f"{e['sku']}.{e['field']}" or not a.get('source_location'):
            raise SetupError('authority needs a matching evidence entry and source_location: '+key)
    seen=set()
    for e in case.get('supplier_edits',[]):
        fact=evidence.get(e.get('evidence_id'))
        if not fact or fact['sku']!=e.get('sku') or fact['field']!=e.get('field') or e.get('operation')!='replace':
            raise SetupError('invalid supplier edit evidence')
        if e.get('approved') is True:
            key=(e['sku'],e['field'])
            if key in seen: raise SetupError('multiple active supplier edits: select the current edit')
            seen.add(key)
        if e.get('family_wide') and source_records[e['sku']]['role']!='parent': raise SetupError('family edit needs flagship parent')
    records,values=effective(case)
    for sku,r in records.items():
        if r['role']=='parent' and sku not in case.get('flagship_skus',[]): raise SetupError('flagship not supplier designated')
        if r['role']=='child' and records[r['parent_sku']]['role']!='parent': raise SetupError('child must link directly to flagship parent')
        for f,v in r['fields'].items():
            e=evidence.get(f'{sku}.{f}')
            if not e or e!={'sku':sku,'field':f,'value':v}: raise SetupError('fixture evidence mismatch')
        for c in r.get('conflicts',[]):
            refs=c.get('evidence',[])
            if len(refs)<2 or any(ref not in evidence or evidence[ref]['sku']!=sku or evidence[ref]['field']!=c.get('field') for ref in refs):
                raise SetupError('conflict must cite source evidence for this SKU and field')
            if all(same(c['field'],evidence[refs[0]]['value'],evidence[ref]['value']) for ref in refs[1:]):
                raise SetupError('conflict flag cites equal values')
        if 'material' in values[sku]: material_key(values[sku]['material'])
    return records,values

def required_fields(p):
    """The COMPUTED required set, not the static REQUIRED tuple.

    subbrand is required only when the profile says it applies. Partitioning
    blocking from withholding against the static tuple would treat a subbrand
    conflict as optional and publish a record that must block — a false accept.
    """
    return list(REQUIRED)+(['subbrand'] if p.get('subbrand_applicable',True) else [])

def withholds(issue,p):
    """Owner decision 4: an unresolved conflict on a non-required field withholds
    that field instead of blocking the SKU."""
    return issue['code']=='SOURCE_CONFLICT' and issue['field'] not in required_fields(p)

def partition_issues(issues,p):
    """(blocking, withholding). Blocking decides status; withholding decides fields."""
    return [i for i in issues if not withholds(i,p)],[i for i in issues if withholds(i,p)]

def conflict_resolved(case,sku,field):
    """A conflict is resolved only by a supplier-approved authority or an approved edit."""
    return bool(authority(case,sku,field)) or any(
        e.get('approved') is True and e['sku']==sku and e['field']==field
        for e in case.get('supplier_edits',[]))

def unresolved_conflicts(case,fs,r,sku):
    """{field: evidence refs} for every field on THIS record whose sources disagree.

    Two ways a conflict arrives: declared in the record, or implied by two
    evidence entries for the same field holding different values. Both feed the
    SOURCE_CONFLICT issues, and both must be visible to the family check so it
    can tell a withheld field from a real family disagreement.
    """
    out={}
    for c in r.get('conflicts',[]):
        if not conflict_resolved(case,sku,c['field']): out.setdefault(c['field'],c['evidence'])
    for f in fs:
        refs=[key for key,e in case['evidence'].items() if e['sku']==sku and e['field']==f]
        if len(refs)>1 and any(not same(f,case['evidence'][refs[0]]['value'],case['evidence'][x]['value']) for x in refs[1:]):
            if not conflict_resolved(case,sku,f): out.setdefault(f,refs)
    return out

def expected_issues(case,records,values,sku):
    r=records[sku]; fs=values[sku]; p=case['profile']; issues=[]
    def add(code,f,refs): issues.append({'code':code,'field':f,'evidence':refs})
    required=required_fields(p)
    # Fields THIS record withholds: an unresolved conflict on a non-required field.
    # Scoped to this SKU only — a sibling that is not withholding the same field is
    # unaffected, and required fields are never in here.
    conflicts_here=unresolved_conflicts(case,fs,r,sku)
    withheld_here={f for f in conflicts_here if f not in required}
    for f in required:
        if f not in fs or fs[f] is None or fs[f]=='': add('MISSING_REQUIRED',f,[])
    for f,allowed in p.get('allowed',{}).items():
        if f in fs and not any(equivalent(canonical(f,fs[f],p),a) for a in allowed): add('UNMAPPED_VALUE',f,[source_ref(case,sku,f)])
    if 'material' in fs:
        m=fs['material']; total=material_total(m)
        if total is not None and total>101: add('COMPOSITION_EXCESS','material',[source_ref(case,sku,'material')])
        label=norm(m.get('label',''))
        if label.endswith(' blend') and m.get('components'):
            core=norm(label[:-6]); found=[c for c in m['components'] if norm(c['material'])==core]
            if (not found) or (found[0].get('percent') is not None and number(found[0]['percent'])<=50):
                add('NAMED_BLEND_MAJORITY','material',[source_ref(case,sku,'material')])
    if r['role']=='child':
        parent=r['parent_sku']
        for f in SHARED:
            # A field this record is withholding has no settled value to compare, so a
            # family difference on it is not established. Narrow on purpose: only this
            # field, only on this SKU, and never a required one — withheld_here cannot
            # contain a required field.
            if f in withheld_here: continue
            if f in fs and f in values[parent] and not same(f,canonical(f,fs[f],p),canonical(f,values[parent][f],p)):
                add('FAMILY_MISMATCH',f,[source_ref(case,sku,f),source_ref(case,parent,f)])
        for problem in expected_issues(case,records,values,parent):
            if problem['field'] in SHARED and not any(i['field']==problem['field'] for i in issues):
                # Decision 4: an optional-field conflict blocks nothing else, and a child
                # is something else. A parent problem that only withholds propagates as a
                # withholding conflict on the child's inherited copy, not as a blocker.
                if withholds(problem,p): add('SOURCE_CONFLICT',problem['field'],problem['evidence'])
                else: add('PARENT_UNRESOLVED',problem['field'],problem['evidence'])
    # A supplied conflict is resolved only by the selected authority or explicit approved edit.
    for f,refs in conflicts_here.items():
        if not any(x['code']=='SOURCE_CONFLICT' and x['field']==f for x in issues): add('SOURCE_CONFLICT',f,refs)
    for correction in r.get('proposed_corrections',[]):
        f=correction['field']
        if not any(e.get('approved') is True and e['sku']==sku and e['field']==f for e in case.get('supplier_edits',[])):
            add('SUPPLIER_APPROVAL_REQUIRED',f,[source_ref(case,sku,f)] if f in fs else [])
    for f,mappings in p.get('known_corrections',{}).items():
        current=fs.get(f)
        if f=='material' and isinstance(current,dict): current=current.get('label')
        if isinstance(current,str) and any(norm(current)==norm(k) for k in mappings):
            add('SUPPLIER_APPROVAL_REQUIRED',f,[source_ref(case,sku,f)])
    # These are input attestations in this offline lab, not document authentication.
    for requirement in r.get('claims',[]):
        f=requirement['field']; review=requirement.get('human_review',{})
        if (not requirement.get('document_ref') or review.get('status')!='approved' or not review.get('reviewer') or not review.get('reviewed_at')
            or review.get('document_ref')!=requirement['document_ref']
            or not evidence_matches(case,review.get('evidence_id'),source_ref(case,sku,f))):
            add('HUMAN_VALIDATION_REQUIRED',f,[source_ref(case,sku,f)] if f in fs else [])
    review_fields={'certification','certificate','compliance','safety_claim','organic_certified'} | set(p.get('human_review_fields',[]))
    declared={x['field'] for x in r.get('claims',[])}
    for f in fs.keys() & review_fields - declared:
        add('HUMAN_VALIDATION_REQUIRED',f,[source_ref(case,sku,f)])
    for m in r.get('measurements',[]):
        if m.get('unit') not in ('in','cm'):
            add('MEASUREMENT_INPUT','measurement:'+m.get('id','unknown'),[])
        bs=m.get('bands',[])
        try:
            for b in bs:
                if number(b['min_cm'])>=number(b['max_cm']) or not isinstance(b['include_min'],bool) or not isinstance(b['include_max'],bool): raise ValueError()
            ordered=sorted(bs,key=lambda b:number(b['min_cm']))
            for a,b in zip(ordered,ordered[1:]):
                if number(a['max_cm'])!=number(b['min_cm']) or a['include_max']==b['include_min']: raise ValueError()
            if bs:
                ref=number(m['value'])*(Decimal('2.54') if m.get('unit')=='in' else 1)
                if len(band(ref,bs))!=1: raise ValueError()
        except (KeyError,TypeError,ValueError,InvalidOperation):
            add('SIZE_CHART_CONFLICT','measurement:'+m['id'],[])
    unique={(x['code'],x['field']):x for x in issues}
    issues=list(unique.values())
    return issues

def grade(case,candidate):
    errors=[]; warnings=[]; per=[]
    def err(code,sku=None,field=None,detail=''): errors.append(dict(code=code,sku=sku,field=field,detail=detail))
    try: records,values=check_setup(case)
    except (KeyError,TypeError,ValueError,InvalidOperation) as e: return {'verdict':'SETUP_ERROR','errors':[str(e)],'warnings':[]}
    if not isinstance(candidate,dict) or not isinstance(candidate.get('records'),list):
        return {'verdict':'FAIL','errors':[{'code':'EMPTY_OR_REFUSAL','detail':'Required record list absent'}],'warnings':[]}
    if candidate.get('case_id')!=case.get('case_id'): err('CASE_ID','',detail='Submission belongs to a different test input.')
    for key in candidate.keys()-{'case_id','records','catalog'}-INTERNAL_KEYS: err('UNSUPPORTED_OUTPUT_FIELD',field=key)
    if 'catalog' in candidate:
        context=candidate['catalog']
        if not isinstance(context,dict) or any(k not in case['catalog'] or not equivalent(v,case['catalog'][k]) for k,v in context.items()):
            err('CATALOG_CONTEXT',detail='Country/currency must match the supplied destination; no automatic FX or repricing.')
    out={}
    for row in candidate['records']:
        if not isinstance(row,dict) or not isinstance(row.get('sku'),str): err('MALFORMED_RECORD'); continue
        sku=row['sku']
        if sku in out: err('DUPLICATE_SKU',sku)
        out[sku]=row
    for sku in out.keys()-records.keys(): err('INVENTED_SKU',sku)
    for sku in records.keys()-out.keys(): err('OMITTED_SKU',sku)
    withheld_fields={}
    for sku,r in records.items():
        if sku not in out: continue
        o=out[sku]; fs=values[sku]; before=len(errors)
        try:
            expected=expected_issues(case,records,values,sku)
            blocking,withholding=partition_issues(expected,case['profile'])
            withheld_fields[sku]={i['field'] for i in withholding}
            wanted='BLOCKED' if blocking else 'READY'
            if o.get('status')!=wanted: err('FALSE_BLOCK' if wanted=='READY' else 'FALSE_READY',sku,detail=f'Expected {wanted}')
            if o.get('role')!=r['role'] or o.get('parent_sku')!=r.get('parent_sku'): err('FAMILY_LINK',sku)
            for key in o.keys()-{'sku','role','parent_sku','fields','evidence','status','issues','display','measurements','record_status'}-INTERNAL_KEYS:
                err('UNSUPPORTED_OUTPUT_FIELD',sku,key,detail='Place supported product descriptions/claims in fields with their evidence.')
            if 'record_status' in o and o['record_status']!=r['record_status']: err('RECORD_STATUS',sku)
            supplied=o.get('fields',{})
            if not isinstance(supplied,dict): raise ValueError('fields must be object')
            for f,v in fs.items():
                if f in withheld_fields[sku]:
                    # Decision 4: the field is withheld, so its absence is required and
                    # its presence is a defect. Publishing a value whose sources disagree
                    # is the failure withholding exists to prevent.
                    if f in supplied: err('WITHHELD_FIELD_PUBLISHED',sku,f,
                        detail='Sources disagree on this field; it is withheld, not published.')
                    continue
                if f not in supplied: err('OMITTED_FACT',sku,f); continue
                if not same(f,canonical(f,v,case['profile']),supplied[f]): err('WRONG_VALUE',sku,f)
                ref=o.get('evidence',{}).get(f)
                if not evidence_matches(case,ref,source_ref(case,sku,f)): err('WRONG_EVIDENCE',sku,f)
            for f in supplied.keys()-fs.keys(): err('UNSUPPORTED_VALUE',sku,f)
            oi=o.get('issues',[])
            if not isinstance(oi,list): raise ValueError('issues must be list')
            expected_keys={(x['code'],x['field']):x for x in blocking}
            permitted_keys={(x['code'],x['field']):x for x in withholding}
            known=dict(expected_keys); known.update(permitted_keys)
            actual_keys=set()
            for i in oi:
                key=(i['code'],i['field']); actual_keys.add(key)
                if key not in known: err('SPURIOUS_ISSUE',sku,i['field']); continue
                # A permitted issue is optional in BOTH directions: the candidate may
                # report it or stay silent, and neither is penalised. Reporting one can
                # therefore never be worse than saying nothing, so no check below applies
                # to it. Expected issues are still held to evidence and action.
                if key in permitted_keys and key not in expected_keys: continue
                actual_refs=i.get('evidence',[]);expected_refs=known[key]['evidence']
                if not (all(any(evidence_matches(case,a,b) for b in expected_refs) for a in actual_refs)
                        and all(any(evidence_matches(case,a,b) for a in actual_refs) for b in expected_refs)):
                    err('ISSUE_EVIDENCE',sku,i['field'])
                if not isinstance(i.get('action'),str) or not i['action'].strip(): err('MISSING_ACTION',sku,i['field'])
            if not set(expected_keys)<=actual_keys: err('ISSUE_COVERAGE',sku)
            if 'material' in fs:
                exp,label=display_expected(fs['material']); d=o.get('display',{})
                for key in d.keys()-{'text','derived_remainder'}: err('UNSUPPORTED_OUTPUT_FIELD',sku,'display.'+key)
                if label:
                    if norm(d.get('text',''))!=norm(label): err('DISPLAY_VALUE',sku,'material')
                else:
                    ek=sorted([(norm(c['material']),None if c.get('percent') is None else number(c['percent'])) for c in exp],key=lambda x:x[0])
                    if text_parts(d.get('text',''))!=ek: err('DISPLAY_VALUE',sku,'material')
                    others=[c for c in exp if c.get('derived')]
                    if others:
                        try:
                            if number(d.get('derived_remainder'))!=number(others[0]['percent']): err('REMAINDER_PROVENANCE',sku,'material')
                        except (ValueError,InvalidOperation,TypeError): err('REMAINDER_PROVENANCE',sku,'material')
                    elif 'derived_remainder' in d: err('REMAINDER_PROVENANCE',sku,'material')
                total=material_total(fs['material'])
                if total is not None and total!=100 and total<=101: warnings.append({'sku':sku,'code':'COMPOSITION_ROUNDING' if total>=Decimal('99.9') else 'COMPOSITION_INCOMPLETE'})
            invalid={x['field'].split(':',1)[1] for x in expected if x['code'] in ('MEASUREMENT_INPUT','SIZE_CHART_CONFLICT')}
            ms=[m for m in r.get('measurements',[]) if m['id'] not in invalid]; mo=o.get('measurements',[])
            if len(ms)!=len(mo): err('MEASUREMENT_COVERAGE',sku)
            byid={x['id']:x for x in mo}
            if len(byid)!=len(mo): err('DUPLICATE_MEASUREMENT',sku)
            for m in ms:
                c=byid.get(m['id'])
                if c is None: err('MISSING_MEASUREMENT',sku);continue
                for key in c.keys()-{'id','source_sku','source_ref','measurement_type','source_value','source_unit','value','unit'}:
                    err('UNSUPPORTED_OUTPUT_FIELD',sku,'measurement.'+key)
                if c.get('source_sku')!=sku or c.get('source_ref')!=m['evidence_id'] or c.get('measurement_type')!=m['type'] or c.get('source_unit')!=m['unit'] or number(c.get('source_value'))!=number(m['value']):
                    err('MEASUREMENT_SOURCE',sku);continue
                if c.get('unit')!='cm': err('MEASUREMENT_UNIT',sku);continue
                ref=number(m['value'])*(Decimal('2.54') if m['unit']=='in' else 1)
                rounded=ref.quantize(Decimal('0.1'),rounding=ROUND_HALF_UP); val=number(c['value'])
                if val!=val.quantize(Decimal('0.1')): err('MEASUREMENT_PRECISION',sku)
                delta=abs(val-rounded)
                if delta>Decimal('0.5'): err('CONVERSION_ERROR',sku)
                elif delta: warnings.append({'sku':sku,'code':'CONVERSION_P2'})
                if m.get('bands') and band(val,m['bands'])!=band(ref,m['bands']): err('SIZE_BOUNDARY',sku)
            per.append({'sku':sku,'expected_status':wanted,'candidate_status':o.get('status'),'handling':'PASS' if before==len(errors) else 'FAIL'})
        except (KeyError,TypeError,ValueError,InvalidOperation,AttributeError) as e: err('MALFORMED_RECORD',sku,detail=str(e))
    guided=guided_help(case,records,values)
    status_by_sku={x['sku']:x['expected_status'] for x in per}
    warnings_for_seller=seller_warnings(case,records,values,status_by_sku)
    # Global identity/context errors invalidate the batch; do not advertise publishable SKUs.
    global_error=any(not x.get('sku') for x in errors)
    ready={x['sku'] for x in per if x['handling']=='PASS' and x['expected_status']=='READY'} if not global_error else set()
    # Explicit projection: never forward the raw candidate, metadata, model
    # confidence, proposed actions, or debug text to a publication consumer.
    payload={'catalog':copy.deepcopy(case['catalog']), 'records':[]}
    for sku in records:
        if sku in ready:
            row=out[sku]
            parent=records[sku].get('parent_sku')
            # D2: never point a published record at a parent absent from this payload.
            # The relationship stays in `records`; link it when the parent is ready.
            published_parent=parent if parent in ready else None
            fields={k:v for k,v in row['fields'].items() if k not in withheld_fields.get(sku,set())}
            payload['records'].append({
                'sku':sku,'role':records[sku]['role'],'parent_sku':published_parent,
                'fields':copy.deepcopy(fields), 'display':copy.deepcopy(row['display']),
                'measurements':[{'id':m['id'],'measurement_type':m['measurement_type'],
                                 'value':m['value'],'unit':m['unit']} for m in row.get('measurements',[])]})
    return {'verdict':'FAIL' if errors else 'PASS','errors':errors,'warnings':warnings,'records':per,'guided_help':guided,'seller_warnings':warnings_for_seller,'withheld':{k:sorted(v) for k,v in withheld_fields.items() if v},'publication_payload':payload,'correctly_handled':sum(x['handling']=='PASS' for x in per) if not global_error else 0,'publishable':sum(x['handling']=='PASS' and x['expected_status']=='READY' for x in per) if not global_error else 0,'incomplete':sum(x['handling']=='PASS' and x['expected_status']=='BLOCKED' for x in per)}

def designated_but_unapproved(case,sku,field):
    """A designation is not an approval (decision 3).

    Returns the designated evidence id when a registry entry names one for this
    field but the supplier has not approved it. authority() returns None in that
    case, so the conflict is still unresolved and the field stays withheld — but
    the seller can be told which value the designation points at.
    """
    entry=case.get('authority_registry',{}).get(f'{sku}.{field}')
    if entry and entry.get('supplier_approved') is not True: return entry.get('evidence_id')
    return None

def warning_branch(status,designated):
    """The one place a warning's outcome is decided. Three branches, from the
    status the grader already computed — never re-derived here."""
    if status!='READY': return 'blocked'
    return 'awaiting_approval' if designated else 'eligible_for_publication'

def seller_warnings(case,records,values,status_by_sku):
    """Deterministic seller guidance for every withheld field. Owner decision 4.

    Generated by the grader from the detected conflict, never written by the
    candidate. Each warning carries the SKU, the field, the conflicting source
    values, the branch, and the required action.

    `branch` is a pure function of the SKU's computed status and whether a
    designated-but-unapproved source exists. status_by_sku is passed in from
    grade() so the wording cannot drift from the verdict: there is one status,
    computed once, and the template follows it.

    Fully deterministic and fully checkable. No judge is involved.
    """
    p=case['profile']; out=[]
    for sku in records:
        _,withholding=partition_issues(expected_issues(case,records,values,sku),p)
        for i in withholding:
            f=i['field']
            conflicting=[{'evidence_id':ref,'value':case['evidence'][ref]['value']}
                         for ref in i['evidence'] if ref in case['evidence']]
            designated=designated_but_unapproved(case,sku,f)
            has_designation=bool(designated and designated in case['evidence'])
            status=status_by_sku.get(sku,'BLOCKED')
            branch=warning_branch(status,has_designation)
            w={'sku':sku,'field':f,'branch':branch,'conflicting_values':conflicting}
            if branch=='blocked':
                w['action']=('Sources disagree on '+f+', so it is withheld. This product is '
                             'not published for other reasons; resolve those first, then '
                             'confirm the correct '+f+'.')
            elif branch=='awaiting_approval':
                w['recommended_value']=case['evidence'][designated]['value']
                w['recommended_from']=designated
                w['action']=('Sources disagree on '+f+'. The designated source gives '
                             +repr(case['evidence'][designated]['value'])+', but it is not '
                             'supplier-approved, so '+f+' stays withheld while the rest of this '
                             'product is published. Approve that source to publish '+f+'.')
            else:
                w['action']=('Sources disagree on '+f+'. It is withheld and the rest of this '
                             'product is published. Confirm the correct value to publish '+f+'.')
            out.append(w)
    return out

def guided_help(case,records=None,values=None):
    if records is None: records,values=check_setup(case)
    actions={
        'MISSING_REQUIRED':'Supply the missing fact for this SKU.',
        'SOURCE_CONFLICT':'Resolve the conflicting sources. Designate the supplier-approved authoritative evidence and its location, or supply an explicit approved edit.',
        'PARENT_UNRESOLVED':'Resolve the parent shared-field problem before publishing this child. Do not copy disputed values.',
        'FAMILY_MISMATCH':'Ask the supplier to resolve parent/child specifications or confirm a different family.',
        'SUPPLIER_APPROVAL_REQUIRED':'Obtain supplier approval for the proposed correction. Publication remains blocked.',
        'HUMAN_VALIDATION_REQUIRED':'Supply the supporting document and a human validation record for this claim. Publication remains blocked.',
        'SIZE_CHART_CONFLICT':'Ask the supplier for non-overlapping size ranges with explicit boundary ownership.',
        'MEASUREMENT_INPUT':'Ask the supplier for the missing or supported measurement unit (in or cm).',
        'UNMAPPED_VALUE':'Ask the supplier to correct the value or supply an approved mapping.',
        'COMPOSITION_EXCESS':'Ask the supplier to correct composition exceeding 101%; do not rebalance it.',
        'NAMED_BLEND_MAJORITY':'Ask the supplier to resolve the named-blend claim against its proportions.'}
    return [dict(sku=sku,code=i['code'],field=i['field'],evidence=i['evidence'],
                 action=actions.get(i['code'],'Ask the supplier to resolve this field.'))
            for sku in records for i in expected_issues(case,records,values,sku)]

def read_json(path):
    def unique(pairs):
        d={}
        for k,v in pairs:
            if k in d: raise ValueError('duplicate JSON key: '+k)
            d[k]=v
        return d
    return json.loads(Path(path).read_text(),object_pairs_hook=unique,parse_constant=lambda x:(_ for _ in ()).throw(ValueError(x)))
