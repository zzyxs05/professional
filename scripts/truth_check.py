#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""truth_check.py · 真值一致性检查（A-02 的判定脚本）

对 lab 靶场全样本跑 cli.py analyze，与 lab/truth/*.json 逐点核对。
判罚口径见 docs/specification.md §6：
  EXPECTED_HIT:CONFIRMED → 必须「已确认」
  EXPECTED_HIT:REVIEW    → 「已确认」或「待复核」均算发现
  EXPECTED_SILENT        → 不得「已确认」（FP）；「待复核」记噪声（NOISE）
硬错 = FP + MISS + TIER（目标 0）。

用法：
    python scripts/truth_check.py [--only bad03] [--no-run] [--out review/truth_result.json]
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core import registry

STATUS = registry


def compare_sample(report, truth):
    concl = {}
    for c in report.get('conclusions', []):
        concl[c.get('criterion_id')] = c
    points = []
    for rid in registry.ALL_RULE_IDS:
        exp = truth.get('expected', {}).get(rid, 'TODO')
        c = concl.get(rid)
        status = c.get('status') if c else None
        result = 'SKIP'
        if exp.startswith('EXPECTED_HIT'):
            want = exp.split(':', 1)[1] if ':' in exp else 'REVIEW'
            if c is None:
                result = 'MISS'
            elif want == 'CONFIRMED':
                result = 'PASS' if status == registry.STATUS_CONFIRMED else 'TIER'
            else:
                result = 'PASS' if status in (registry.STATUS_CONFIRMED, registry.STATUS_REVIEW) else 'TIER'
        elif exp == 'EXPECTED_SILENT':
            if c is None:
                result = 'PASS'
            elif status == registry.STATUS_CONFIRMED:
                result = 'FP'
            elif status == registry.STATUS_REVIEW:
                result = 'NOISE'
            else:
                result = 'PASS'
        elif exp.startswith('EXPECTED_NA'):
            result = 'PASS' if c is None else 'FP'
        points.append({'rule': rid, 'expected': exp, 'status': status, 'result': result})
    return points


def run_analyze(apk_path, out_dir, no_evidence=False):
    cmd = [sys.executable, os.path.join(PROJECT_ROOT, 'cli.py'),
           'analyze', apk_path, '--out', out_dir]
    if no_evidence:
        cmd.append('--no-evidence')
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=PROJECT_ROOT,
                          timeout=900, errors='replace')
    return proc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', default=None, help='只检查单个样本名（如 bad03）')
    ap.add_argument('--no-run', action='store_true', help='不重跑，读取最近一次的 report')
    ap.add_argument('--no-evidence', action='store_true',
                    help='演练模式：重跑时不写入 evidence/（避免实验污染运行正本）')
    ap.add_argument('--out', default=os.path.join(PROJECT_ROOT, 'review', 'truth_result.json'))
    args = ap.parse_args()

    truth_dir = os.path.join(PROJECT_ROOT, 'lab', 'truth')
    apks_dir = os.path.join(PROJECT_ROOT, 'lab', 'apks')
    tmp_root = tempfile.mkdtemp(prefix='apkaudit_truth_')

    names = sorted(n[:-len('.json')] for n in os.listdir(truth_dir) if n.endswith('.json'))
    if args.only:
        names = [n for n in names if n == args.only]

    summary = {'samples': {}, 'total': 0, 'pass': 0, 'fp': 0, 'noise': 0,
               'miss': 0, 'tier': 0, 'skip': 0, 'hard_errors': 0}
    all_points = []

    for name in names:
        apk = os.path.join(apks_dir, name + '.apk')
        if not os.path.isfile(apk):
            print('[skip] %s：缺少 %s' % (name, apk))
            continue
        with open(os.path.join(truth_dir, name + '.json'), 'r', encoding='utf-8') as f:
            truth = json.load(f)

        out_dir = os.path.join(tmp_root, name)
        report = None
        if args.no_run:
            runs = sorted([d for d in os.listdir(os.path.join(PROJECT_ROOT, 'evidence'))
                           if d.startswith('RUN-')])
            for run in reversed(runs):
                rp = os.path.join(PROJECT_ROOT, 'evidence', run, 'report.json')
                if os.path.isfile(rp):
                    with open(rp, 'r', encoding='utf-8') as f:
                        cand = json.load(f)
                    if cand.get('target', {}).get('apk_name') == name + '.apk':
                        report = cand
                        break
            if report is None:
                print('[skip] %s：未找到 report（--no-run）' % name)
                continue
        else:
            proc = run_analyze(apk, out_dir, no_evidence=args.no_evidence)
            rp = os.path.join(out_dir, 'report.json')
            if not os.path.isfile(rp):
                print('[error] %s: analyze 未产出 report.json' % name)
                print(proc.stdout[-2000:])
                print(proc.stderr[-2000:])
                continue
            with open(rp, 'r', encoding='utf-8') as f:
                report = json.load(f)

        points = compare_sample(report, truth)
        stat = {'PASS': 0, 'FP': 0, 'NOISE': 0, 'MISS': 0, 'TIER': 0, 'SKIP': 0}
        for p in points:
            stat[p['result']] = stat.get(p['result'], 0) + 1
        summary['samples'][name] = stat
        summary['total'] += len(points)
        summary['pass'] += stat['PASS']
        summary['fp'] += stat['FP']
        summary['noise'] += stat['NOISE']
        summary['miss'] += stat['MISS']
        summary['tier'] += stat['TIER']
        summary['skip'] += stat['SKIP']
        all_points.append({'sample': name, 'points': points})

        detail = ' '.join('%s=%s' % (p['rule'], p['result'])
                          for p in points if p['result'] not in ('PASS', 'SKIP'))
        line = '[%s] %d/%d 一致' % (name, stat['PASS'], len(points))
        if detail:
            line += '　偏差: %s' % detail
        print(line)

    summary['hard_errors'] = summary['fp'] + summary['miss'] + summary['tier']
    print('')
    print('=== 汇总：%d 点 · 一致 %d · 硬错 %d（FP %d / 漏检 %d / 档位错 %d）· 噪声 %d · 未标定 %d ==='
          % (summary['total'], summary['pass'], summary['hard_errors'],
             summary['fp'], summary['miss'], summary['tier'], summary['noise'], summary['skip']))

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, 'w', encoding='utf-8', newline='\n') as f:
        json.dump({'summary': summary, 'details': all_points}, f,
                  ensure_ascii=False, indent=2)
    print('[out] %s' % args.out)
    return 0 if summary['hard_errors'] == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
