"""Offline v1.4 lab grader. No LLM calls and no candidate repair."""
import json
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

VERSION = 'baseline-v1'
REQUIRED = ('brand','category','subcategory','design','pattern','material','color','size','price')
SHARED = ('brand','subbrand','category','subcategory','design','pattern','material')

class SetupError(ValueError): pass

def number(x):
    if isinstance(x,bool): raise ValueError('boolean is not a number')
    d=Decimal(str(x))
    if not d.is_finite(): raise ValueError('nonfinite number')
    return d

def norm(x): return ' '.join(str(x).strip().casefold().split())

def canonical(field,value,profile):
    aliases=profile.get('aliases',{}).get(field,{})
    if isinstance(value,str): return aliases.get(value,value)
    return value

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
    if field=='material': return material_key(a)==material_key(b)
    if field=='price': return number(a)==number(b)
    return a==b

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

def effective(case):
    records={r['sku']:r for r in case['records']}
    if len(records)!=len(case['records']): raise SetupError('duplicate source SKU')
    out={}
    for sku,r in records.items():
        if r.get('record_status') not in ('existing','proposed'): raise SetupError('record status missing')
        if r.get('role') not in ('parent','child'): raise SetupError('invalid source role')
        if r['role']=='child' and r.get('parent_sku') not in records: raise SetupError('source parent absent')
        out[sku]=dict(r['fields'])
    for sku,r in records.items():
        for f in r.get('inherit_fields',[]):
            if f not in SHARED or r['role']!='child': raise SetupError('invalid inheritance fixture')
            if f not in out[r['parent_sku']]: raise SetupError('missing inherited parent fact')
            if f in out[sku] and not same(f,out[sku][f],out[r['parent_sku']][f]): raise SetupError('fixture overwrites conflict')
            out[sku][f]=out[r['parent_sku']][f]
    return records,out

def source_ref(case,sku,field):
    r=next(r for r in case['records'] if r['sku']==sku)
    owner=r['parent_sku'] if field in r.get('inherit_fields',[]) else sku
    return f'{owner}.{field}'

def band(value,bands):
    matches=[]
    for b in bands:
        lo,hi=number(b['min_cm']),number(b['max_cm'])
        if (value>lo or (value==lo and b['include_min'])) and (value<hi or(value==hi and b['include_max'])): matches.append(b['size'])
    return matches

def check_setup(case):
    if case.get('contract_version')!='1.4': raise SetupError('contract version')
    if not case.get('catalog',{}).get('currency') or not case['catalog'].get('country'): raise SetupError('catalog context')
    if not isinstance(case.get('profile'),dict): raise SetupError('profile absent')
    records,values=effective(case)
    evidence=case.get('evidence',{})
    for sku,r in records.items():
        if r['role']=='parent' and sku not in case.get('flagship_skus',[]): raise SetupError('flagship not supplier designated')
        for f,v in r['fields'].items():
            e=evidence.get(f'{sku}.{f}')
            if not e or e!={'sku':sku,'field':f,'value':v}: raise SetupError('fixture evidence mismatch')
        if 'material' in values[sku]: material_key(values[sku]['material'])
    return records,values

def expected_issues(case,records,values,sku):
    r=records[sku]; fs=values[sku]; p=case['profile']; issues=[]
    def add(code,f,refs): issues.append({'code':code,'field':f,'evidence':refs})
    required=list(REQUIRED)+(['subbrand'] if p.get('subbrand_applicable',True) else [])
    for f in required:
        if f not in fs or fs[f] is None or fs[f]=='': add('MISSING_REQUIRED',f,[])
    for f,allowed in p.get('allowed',{}).items():
        if f in fs and canonical(f,fs[f],p) not in allowed: add('UNMAPPED_VALUE',f,[source_ref(case,sku,f)])
    if 'material' in fs:
        m=fs['material']; total=material_total(m)
        if total is not None and total>101: add('COMPOSITION_EXCESS','material',[source_ref(case,sku,'material')])
        label=m.get('label','')
        if label.endswith(' blend') and m.get('components'):
            core=norm(label[:-6]); found=[c for c in m['components'] if norm(c['material'])==core]
            if found and found[0].get('percent') is not None and number(found[0]['percent'])<=50:
                add('NAMED_BLEND_MAJORITY','material',[source_ref(case,sku,'material')])
    if r['role']=='child':
        parent=r['parent_sku']
        for f in SHARED:
            if f in fs and f in values[parent] and not same(f,canonical(f,fs[f],p),canonical(f,values[parent][f],p)):
                add('FAMILY_MISMATCH',f,[source_ref(case,sku,f),source_ref(case,parent,f)])
    for c in r.get('conflicts',[]): add('SOURCE_CONFLICT',c['field'],c['evidence'])
    return issues

def grade(case,candidate):
    errors=[]; warnings=[]; per=[]
    def err(code,sku=None,field=None,detail=''): errors.append(dict(code=code,sku=sku,field=field,detail=detail))
    try: records,values=check_setup(case)
    except (KeyError,TypeError,ValueError,InvalidOperation) as e: return {'verdict':'SETUP_ERROR','errors':[str(e)],'warnings':[]}
    if not isinstance(candidate,dict) or not isinstance(candidate.get('records'),list):
        return {'verdict':'FAIL','errors':[{'code':'EMPTY_OR_REFUSAL','detail':'Required record list absent'}],'warnings':[]}
    out={}
    for row in candidate['records']:
        if not isinstance(row,dict) or not isinstance(row.get('sku'),str): err('MALFORMED_RECORD'); continue
        sku=row['sku']
        if sku in out: err('DUPLICATE_SKU',sku)
        out[sku]=row
    for sku in out.keys()-records.keys(): err('INVENTED_SKU',sku)
    for sku in records.keys()-out.keys(): err('OMITTED_SKU',sku)
    for sku,r in records.items():
        if sku not in out: continue
        o=out[sku]; fs=values[sku]; before=len(errors)
        try:
            expected=expected_issues(case,records,values,sku)
            wanted='BLOCKED' if expected else 'READY'
            if o.get('status')!=wanted: err('FALSE_BLOCK' if wanted=='READY' else 'FALSE_READY',sku,detail=f'Expected {wanted}')
            if o.get('role')!=r['role'] or o.get('parent_sku')!=r.get('parent_sku'): err('FAMILY_LINK',sku)
            supplied=o.get('fields',{})
            if not isinstance(supplied,dict): raise ValueError('fields must be object')
            for f,v in fs.items():
                if f not in supplied: err('OMITTED_FACT',sku,f); continue
                if not same(f,canonical(f,v,case['profile']),supplied[f]): err('WRONG_VALUE',sku,f)
                ref=o.get('evidence',{}).get(f)
                if ref!=source_ref(case,sku,f): err('WRONG_EVIDENCE',sku,f)
            for f in supplied.keys()-fs.keys(): err('UNSUPPORTED_VALUE',sku,f)
            oi=o.get('issues',[])
            if not isinstance(oi,list): raise ValueError('issues must be list')
            expected_keys={(x['code'],x['field']):x for x in expected}
            actual_keys=set()
            for i in oi:
                key=(i['code'],i['field']); actual_keys.add(key)
                if key not in expected_keys: err('SPURIOUS_ISSUE',sku,i['field']); continue
                if set(i.get('evidence',[]))!=set(expected_keys[key]['evidence']): err('ISSUE_EVIDENCE',sku,i['field'])
                if not isinstance(i.get('action'),str) or not i['action'].strip(): err('MISSING_ACTION',sku,i['field'])
            if actual_keys!=set(expected_keys): err('ISSUE_COVERAGE',sku)
            if 'material' in fs:
                exp,label=display_expected(fs['material']); d=o.get('display',{})
                if label:
                    if norm(d.get('text',''))!=norm(label): err('DISPLAY_VALUE',sku,'material')
                else:
                    ek=sorted([(norm(c['material']),None if c.get('percent') is None else number(c['percent'])) for c in exp],key=lambda x:x[0])
                    if text_parts(d.get('text',''))!=ek: err('DISPLAY_VALUE',sku,'material')
                    others=[c for c in exp if c.get('derived')]
                    if others and d.get('derived_remainder')!=others[0]['percent']: err('REMAINDER_PROVENANCE',sku,'material')
                total=material_total(fs['material'])
                if total is not None and total!=100 and total<=101: warnings.append({'sku':sku,'code':'COMPOSITION_ROUNDING' if total>=Decimal('99.9') else 'COMPOSITION_INCOMPLETE'})
            ms=r.get('measurements',[]); mo=o.get('measurements',[])
            if len(ms)!=len(mo): err('MEASUREMENT_COVERAGE',sku)
            byid={x['id']:x for x in mo}
            if len(byid)!=len(mo): err('DUPLICATE_MEASUREMENT',sku)
            for m in ms:
                c=byid.get(m['id'])
                if c is None: err('MISSING_MEASUREMENT',sku);continue
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
    return {'verdict':'FAIL' if errors else 'PASS','errors':errors,'warnings':warnings,'records':per,'correctly_handled':sum(x['handling']=='PASS' for x in per),'publishable':sum(x['handling']=='PASS' and x['expected_status']=='READY' for x in per),'incomplete':sum(x['handling']=='PASS' and x['expected_status']=='BLOCKED' for x in per)}

def read_json(path):
    def unique(pairs):
        d={}
        for k,v in pairs:
            if k in d: raise ValueError('duplicate JSON key: '+k)
            d[k]=v
        return d
    return json.loads(Path(path).read_text(),object_pairs_hook=unique,parse_constant=lambda x:(_ for _ in ()).throw(ValueError(x)))
