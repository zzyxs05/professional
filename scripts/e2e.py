#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""e2e.py · 端到端契约验收脚本（覆盖 A-01 全输入受理、A-09 确定性复现）

步骤：
  1. 对 lab/apks 全部样本跑 cli.py analyze，检查退出码 / report 结构 / 三档 / 覆盖声明（A-01）
  2. 对指定样本重复运行两次，归一化 run_id/证据 ID 后逐字段比较（A-09）
  3. 输出汇总；退出码 0 = 通过

用法：python scripts/e2e.py [--app-dir <目录>] [--repro bad02]
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLI = os.path.join(PROJECT_ROOT, 'cli.py')
VALID_STATUS = ('已确认', '待复核', '无法判定')


def run_analyze(apk, out_dir, no_evidence=False):
    cmd = [sys.executable, CLI, 'analyze', apk, '--out', out_dir]
    if no_evidence:
        cmd.append('--no-evidence')
    return subprocess.run(cmd, capture_output=True, text=True, cwd=PROJECT_ROOT,
                          timeout=900, errors='replace')


def check_report(rp):
    issues = []
    if not os.path.isfile(rp):
        return ['report.json 缺失']
    with open(rp, 'r', encoding='utf-8') as f:
        d = json.load(f)
    cov = d.get('coverage')
    if not cov:
        issues.append('缺 coverage')
    else:
        if not (cov.get('checked') or cov.get('not_checked')):
            issues.append('覆盖声明为空')
        if cov.get('decode_failed'):
            issues.append('decode_failed=true（合法路径，本样本仅作结构容忍检查）')
    for c in d.get('conclusions', []):
        if c.get('status') not in VALID_STATUS:
            issues.append('%s 状态非法' % c.get('criterion_id'))
        if c.get('status') == '已确认' and not c.get('location'):
            issues.append('%s 已确认但无定位' % c.get('criterion_id'))
    if not os.path.isfile(os.path.join(os.path.dirname(rp), 'report.md')):
        issues.append('report.md 缺失')
    return issues


def normalize_report(d):
    """归一化：run_id / 证据 ID 重排；B1 降级理由文本收敛为哨兵（细节在证据层）；
    标准规则结论与 B 侧疑点分离（B 侧波动属已声明特性，见 release.md I-6）。"""
    d = json.loads(json.dumps(d))
    d['run_id'] = 'RUN-X'
    mapping = {}

    def remap(eid):
        if eid not in mapping:
            mapping[eid] = 'EV-X-%03d' % (len(mapping) + 1)
        return mapping[eid]

    std, rb = [], []
    for c in d.get('conclusions', []):
        c['evidence_ids'] = [remap(e) for e in c.get('evidence_ids', [])]
        c['notes'] = ['[B1 复核降级]' if str(n).startswith('B1 复核判定') else n
                      for n in c.get('notes', [])]
        (rb if c.get('criterion_id', '').startswith('R-B-') else std).append(c)
    d['conclusions'] = std
    d['_b_side_count'] = len(rb)
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--app-dir', default=os.path.join(PROJECT_ROOT, 'lab', 'apks'))
    ap.add_argument('--no-evidence', action='store_true',
                    help='演练模式：重跑时不写入 evidence/（避免实验污染运行正本）')
    ap.add_argument('--repro', default='bad02', help='复现检查的样本名（空串跳过）')
    args = ap.parse_args()

    tmp = tempfile.mkdtemp(prefix='apkaudit_e2e_')
    failed = 0

    print('== A-01 全输入受理 ==')
    apks = sorted(n for n in os.listdir(args.app_dir) if n.endswith('.apk'))
    for name in apks:
        apk = os.path.join(args.app_dir, name)
        out = os.path.join(tmp, name)
        proc = run_analyze(apk, out, no_evidence=args.no_evidence)
        issues = check_report(os.path.join(out, 'report.json'))
        hard = [i for i in issues if '合法路径' not in i]
        if proc.returncode != 0 or hard:
            failed += 1
            print('[FAIL] %s 退出码=%s 问题=%s' % (name, proc.returncode, hard))
        else:
            note = '（含 decode_failed 容忍）' if issues else ''
            print('[OK] %s%s' % (name, note))

    if args.repro:
        print('')
        print('== A-09 确定性复现（%s × 2）==' % args.repro)
        apk = os.path.join(args.app_dir, args.repro + '.apk')
        if not os.path.isfile(apk):
            print('[SKIP] 样本不存在：%s' % apk)
        else:
            d1 = os.path.join(tmp, 'repro1')
            d2 = os.path.join(tmp, 'repro2')
            run_analyze(apk, d1, no_evidence=args.no_evidence)   # 预热解码缓存
            run_analyze(apk, d1, no_evidence=args.no_evidence)
            run_analyze(apk, d2, no_evidence=args.no_evidence)
            with open(os.path.join(d1, 'report.json'), 'r', encoding='utf-8') as f:
                r1 = normalize_report(json.load(f))
            with open(os.path.join(d2, 'report.json'), 'r', encoding='utf-8') as f:
                r2 = normalize_report(json.load(f))
            b_open = r1.get('versions', {}).get('channel_b_model', 'none') != 'none'
            if b_open:
                print('[mode] 通道 B 已开启：标准规则结论需逐字段一致；B 侧疑点波动按已声明特性（I-6）单列')
            b1_count = r1.pop('_b_side_count', 0)
            b2_count = r2.pop('_b_side_count', 0)
            if r1 == r2:
                print('[OK] 两次运行的标准规则结论一致（归一化后逐字段相同）')
                if b_open and b1_count != b2_count:
                    print('[WARN] B 侧疑点数量波动：%d vs %d（LLM 生成特性，已声明 release.md I-6，不计失败）'
                          % (b1_count, b2_count))
            else:
                failed += 1
                print('[FAIL] 两次运行的标准规则结论不一致')
                for c1, c2 in zip(r1.get('conclusions', []), r2.get('conclusions', [])):
                    if c1 != c2:
                        print('  差异:', c1.get('criterion_id'), c1.get('status'), 'vs', c2.get('status'))
                if len(r1.get('conclusions', [])) != len(r2.get('conclusions', [])):
                    print('  差异: 结论数 %d vs %d'
                          % (len(r1.get('conclusions', [])), len(r2.get('conclusions', []))))

    print('')
    print('== e2e 汇总：%s ==' % ('PASS' if failed == 0 else 'FAIL（%d 项）' % failed))
    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
