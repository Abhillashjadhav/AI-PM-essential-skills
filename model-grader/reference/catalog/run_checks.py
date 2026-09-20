"""Run development verification and preserve an execution receipt. No model calls."""
import subprocess
import argparse,datetime,hashlib,json,platform,sys,importlib.util
from pathlib import Path
from grader import grade,read_json,VERSION,check_setup,guided_help
D=Path(__file__).resolve().parent

def run_regressions():
    """Every fixture under reproductions/ that reproduced a real defect.

    Each exits 0 when its defect is absent, 1 when present, 2 when the fixture no
    longer reaches the state it tests. A fixture that stops being able to see its
    defect is reported as a failure, not silently counted as a pass.
    """
    folder=D/'reproductions'
    if not folder.is_dir(): return []
    rows=[]
    for f in sorted(list(folder.glob('finding*.py'))+list(folder.glob('preservation*.py'))+list(folder.glob('ruling*.py'))):
        r=subprocess.run([sys.executable,str(f)],cwd=folder,capture_output=True,text=True)
        detail={0:'defect absent',1:'DEFECT PRESENT',2:'FIXTURE BROKEN'}.get(r.returncode,
                 'exit '+str(r.returncode))
        rows.append({'case':f.stem,'matched':r.returncode==0,'detail':detail,
                     'expected':'the reproduced defect stays absent'})
    return rows

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--input');p.add_argument('--candidate');p.add_argument('--guide',action='store_true')
    a=p.parse_args()
    if a.input:
        case=read_json(a.input)
        if a.guide:
            try:
                result={'guided_help':guided_help(case)}
            except (ValueError,KeyError,TypeError) as e:
                result={'verdict':'SETUP_ERROR','action':'Correct the fixture configuration before scoring a model.','detail':str(e)}
        else:
            if not a.candidate:p.error('--candidate is required unless --guide is used')
            try:result=grade(case,read_json(a.candidate))
            except (ValueError,TypeError) as e: result={'verdict':'FAIL','errors':[{'code':'MALFORMED_JSON','detail':str(e)}]}
        print(json.dumps(result,indent=2))
        return 1 if result.get('verdict') in ('FAIL','SETUP_ERROR') else 0
    entries=[]
    for n in ('S1','S2','S3'):
        e=read_json(D/'gold'/f'{n}.json');e['name']=n;e['suite']='approved';entries.append(e)
    for e in read_json(D/'gold/faults.json'):e['suite']='fault_injection';entries.append(e)
    for e in read_json(D/'revision_checks.json'):e['suite']='revision';entries.append(e)
    spec=importlib.util.spec_from_file_location('preserved_baseline',D/'baseline_v1.py')
    baseline=importlib.util.module_from_spec(spec);spec.loader.exec_module(baseline)
    results=[]
    for e in entries:
        try:r=grade(e['input'],e['candidate'])
        except Exception as ex:r={'verdict':'CRASH','errors':[str(ex)]}
        codes=[x.get('code') for x in r['errors'] if isinstance(x,dict)]
        match=r['verdict']==e['expected'] and (not e.get('required_error') or e['required_error'] in codes)
        # New v1.5 cases include revised policies. This comparison is diagnostic,
        # never an independent measure of reliability or like-for-like accuracy.
        try:old=baseline.grade(e['input'],e['candidate'])['verdict']
        except Exception:old='CRASH'
        results.append({'suite':e['suite'],'case':e['name'],'expected':e['expected'],
                        'baseline_verdict':old,'matched':bool(match),'result':r})
    replay=[]
    for f in sorted((D/'inputs').glob('D*.json')):
        replay.append({'case':f.stem,'result':grade(read_json(f),read_json(D/'candidates/sol'/f.name))})
    from check_metadata import run as check_metadata
    metadata_checks=check_metadata()
    report={'version':VERSION,'python':sys.version,'platform':platform.platform(),
            'timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'fresh_model_calls':False,'independent_holdout':False,
            'grader_sha256':hashlib.sha256((D/'grader.py').read_bytes()).hexdigest(),
            'results':results,'saved_candidate_replay':replay,'metadata_checks':metadata_checks}
    # Regression reproductions run as part of the standard suite, not only via a
    # separate runner. Last pass this suite reported 55/55 green while three real
    # defects were live, because the only thing that could see them was a script
    # nobody was obliged to run.
    regressions=run_regressions()
    report['regressions']=regressions
    folder=D/'reports';folder.mkdir(exist_ok=True)
    target=folder/('checks_'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json')
    target.write_text(json.dumps(report,indent=2))
    for suite in ('approved','fault_injection','revision'):
        rows=[x for x in results if x['suite']==suite]
        print(suite+':',sum(x['matched'] for x in rows),'/',len(rows),'expected judgments matched')
    for row in results:
        if not row['matched']:print('MISMATCH:',row['case'],row['result'])
    print('Saved candidate replay:',sum(x['result']['verdict']=='PASS' for x in replay),'/',len(replay),'accepted; not an independent accuracy score')
    print('Internal metadata:',sum(x['matched'] for x in metadata_checks),'/',len(metadata_checks),'boundary checks matched')
    for row in metadata_checks:
        if not row['matched']:print('METADATA MISMATCH:',row)
    print('Regressions:',sum(x['matched'] for x in regressions),'/',len(regressions),
          'reproduced defects still absent')
    for row in regressions:
        if not row['matched']:print('REGRESSION:',row['case'],'->',row['detail'])
    print('Report:',target)
    return 0 if all(x['matched'] for x in results+metadata_checks+regressions) else 1

if __name__=='__main__':sys.exit(main())
