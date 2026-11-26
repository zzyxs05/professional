#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""R-1 横向评测 runner（协议见 docs/adr/0010-model-selection.md）

4 模型 × 13 样本，全部 --no-evidence，不写主仓库 evidence/。
每份 report 复制到 review/model_eval/<model>/<sample>/report.json。
指标：B 侧疑点条数、B 疑点命中（按 claim）、结论升级正确率、运行间波动。
"""
import json, os, re, shutil, subprocess, sys, tempfile, time
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, 'review', 'model_eval')
SAMPLES = (
    [('lab/apks/bad01.apk','bad01'),('lab/apks/bad02.apk','bad02'),
     ('lab/apks/bad03.apk','bad03'),('lab/apks/bad04.apk','bad04'),
     ('lab/apks/good01.apk','good01'),('lab/apks/good02.apk','good02')]
    + [('review/redteam/samples/'+f+'.apk',f) for f in
       ('a02','a04','a05','a13','a16','v2_crossmethod','v4_isolated')]
)
MODELS = ('mimo-v2.6-flash','deepseek-flash','qwen3.8-max','glm-5.3')


def find_report(run_id):
    temp = os.environ.get('TEMP') or tempfile.gettempdir()
    ps = [p for p in __import__('glob').glob(
        os.path.join(temp, 'apkaudit_trial_*', run_id, 'report.json'))]
    return max(ps, key=os.path.getmtime) if ps else None


def main():
    result = {'generated_at': datetime.now(timezone.utc).isoformat(),
              'protocol': 'docs/adr/0010-model-selection.md',
              'models': list(MODELS),
              'samples': [n for _,n in SAMPLES],
              'runs': []}
    for model in MODELS:
        mdir = os.path.join(OUT, re.sub(r'\W','_',model))
        os.makedirs(mdir, exist_ok=True)
        for rel, name in SAMPLES:
            t0 = time.time()
            p = subprocess.run([sys.executable,'cli.py','analyze',rel,'--no-evidence','--model',model],
                               cwd=ROOT, capture_output=True, text=True,
                               encoding='utf-8', errors='replace', env=dict(os.environ, PYTHONUTF8='1'))
            text=p.stdout+p.stderr
            m=re.search(r'\[run\]\s+(RUN-[0-9a-zA-Z\-]+)',text)
            run_id=m.group(1) if m else None
            src=find_report(run_id) if run_id else None
            entry={'model':model,'sample':name,'run_id':run_id,
                   'elapsed_s':round(time.time()-t0,1),'exit':p.returncode}
            if src:
                d=json.load(open(src,encoding='utf-8'))
                obs=d.get('observations',[])
                concl=d.get('conclusions',[])
                upgrade=[c for c in concl if c.get('channel')=='fusion'
                         and c.get('status')=='已确认'
                         and c.get('criterion_id','').startswith('R-B-')]
                entry.update({
                    'rule_pack':d.get('versions',{}).get('rule_pack'),
                    'model_used':d.get('versions',{}).get('channel_b_model'),
                    'obs_count':len(obs),
                    'b_claims':[o.get('claim','')[:80] for o in obs],
                    'upgraded_rules':[c['criterion_id'] for c in upgrade],
                    'confirmed':sum(1 for c in concl if c.get('status')=='已确认'),
                    'review':sum(1 for c in concl if c.get('status')=='待复核'),
                })
                shutil.copy(src, os.path.join(mdir, name+'.json'))
            else:
                entry['error']=text[-300:]
            result['runs'].append(entry)
            print('[%s] %s -> %s (obs %s)' % (model,name,run_id or 'FAIL',
                  entry.get('obs_count','-')),flush=True)
    json.dump(result, open(os.path.join(OUT,'r1_results.json'),'w',encoding='utf-8'),
              ensure_ascii=False,indent=2)
    print('DONE', len(result['runs']),'runs')

if __name__=='__main__':
    main()
