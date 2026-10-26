#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""b_stability.py · B 通道稳定性实验（有协议、有记录、可复算）

背景（2026-10-15 项目负责人指出）：此前对 B 通道的改进方式是"跑一次 → 看输出 → 改提示词 → 再跑"，
属**无协议、无重复、无统计**的试错，无法区分"真实改进"与"单次运气"。
本脚本把改进过程改成可复算的实验：

  固定样本 × 固定提示词版本 × N 次重复 → 统计 B1 verdict 分布 / B2 疑点数分布 → 落盘 JSON

用法：
    python scripts/b_stability.py --sample bad03 --runs 3
    python scripts/b_stability.py --sample bad01 --runs 5 --rules R-PERM-03,R-MAN-01
    python scripts/b_stability.py --sample bad03 --runs 5 --no-b2

产物：review/b_stability_<sample>_<runs>.json（含每次原始响应摘要，可复算）
"""

import argparse
import json
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core import registry
from core.channel_b import (B1_PROMPT_VERSION, B2_PROMPT_VERSION, B2_SYSTEM,
                            B1_SYSTEM, _chat, _collect_sensitive_area,
                            _hits_with_context, _parse_b2, _parse_verdict,
                            load_key_config)
from core.adapters import decode_with_apktool, probe_toolchain
from core.channel_a import build_context, run_channel_a
from core.evidence import sha256_file, utc_now_iso


def _b1_call(cfg, ctx, rule_id, hits):
    meta = registry.RULE_META[rule_id]
    messages = [
        {'role': 'system', 'content': B1_SYSTEM},
        {'role': 'user',
         'content': '规则 %s（%s）\n误报口径（什么不算）：%s\n命中片段：\n%s'
                    % (rule_id, meta['name'], meta.get('fp_notes', '未定义'),
                       _hits_with_context(ctx, hits[:5]))},
    ]
    raw = _chat(cfg, messages, max_tokens=1200)
    return _parse_verdict(raw), raw


def _b2_call(cfg, ctx):
    area = _collect_sensitive_area(ctx)
    if not area:
        return [], ''
    raw = _chat(cfg, [{'role': 'system', 'content': B2_SYSTEM},
                      {'role': 'user', 'content': '以下是样本敏感区域摘要：\n' + area}],
                max_tokens=2000)
    return _parse_b2(raw), raw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--sample', required=True, help='样本名（如 bad03）')
    ap.add_argument('--runs', type=int, default=3, help='重复次数（建议 ≥5 有统计意义）')
    ap.add_argument('--rules', default=None, help='只测指定规则（逗号分隔），默认全部命中规则')
    ap.add_argument('--no-b2', action='store_true', help='跳过 B2')
    ap.add_argument('--apks', default=os.path.join(PROJECT_ROOT, 'lab', 'apks'))
    args = ap.parse_args()

    apk_path = os.path.join(args.apks, args.sample + '.apk')
    if not os.path.isfile(apk_path):
        print('样本不存在：%s' % apk_path)
        return 2
    cfgs = load_key_config(PROJECT_ROOT)
    if not cfgs:
        print('未配置模型（key.txt 缺失），无法运行稳定性实验')
        return 2

    sha = sha256_file(apk_path)
    tc = probe_toolchain(PROJECT_ROOT)
    dec = decode_with_apktool(tc, apk_path, sha, PROJECT_ROOT)
    if not dec.ok:
        print('解码失败：%s（smali 类规则将无法参与）' % dec.error)
    ctx = build_context(PROJECT_ROOT, apk_path, sha, dec.out_dir if dec.ok else None)
    hits_by_rule, _cov, _notes = run_channel_a(ctx)
    if not hits_by_rule:
        print('该样本无规则命中，无法测 B1 稳定性')
        return 0
    only = [r.strip() for r in args.rules.split(',')] if args.rules else None
    targets = [r for r in hits_by_rule if (not only or r in only)]

    print('=== B 通道稳定性实验 ===')
    print('样本=%s  规则包=%s  B1=%s  B2=%s  重复=%d 次'
          % (args.sample, registry.RULE_PACK_VERSION, B1_PROMPT_VERSION,
             B2_PROMPT_VERSION, args.runs))
    print('待测规则：%s' % ', '.join(targets))
    print('')

    records = {'b1': {}, 'b2': []}
    for rid in targets:
        records['b1'][rid] = []
    for i in range(1, args.runs + 1):
        print('--- 第 %d/%d 轮 ---' % (i, args.runs))
        for rid in targets:
            try:
                v, raw = _b1_call(cfgs[0], ctx, rid, hits_by_rule[rid])
                records['b1'][rid].append(
                    {'verdict': v['verdict'], 'reason': v['reason'][:80],
                     'has_observation': bool((v.get('observation') or '').strip())})
                print('  %-10s %s%s' % (rid, v['verdict'],
                                        '  [有观察]' if records['b1'][rid][-1]['has_observation'] else ''))
            except Exception as e:  # noqa: BLE001 —— 限流等异常记录为 error，不中断实验
                records['b1'][rid].append({'verdict': 'error', 'reason': str(e)[:80],
                                           'has_observation': False})
                print('  %-10s 调用失败：%s' % (rid, str(e)[:60]))
        if not args.no_b2:
            pts, raw = _b2_call(cfgs[0], ctx)
            conf = {}
            for p in pts:
                conf[p.get('confidence', 'medium')] = conf.get(p.get('confidence', 'medium'), 0) + 1
            records['b2'].append({'count': len(pts), 'confidence': conf,
                                  'claims': [p['claim'][:60] for p in pts[:5]]})
            print('  B2 疑点 %d 条 %s' % (len(pts), conf))

    # 统计
    print('')
    print('=== 统计（一致率 = 众数次数 / 总次数）===')
    summary = {}
    for rid, items in records['b1'].items():
        dist = {}
        for it in items:
            dist[it['verdict']] = dist.get(it['verdict'], 0) + 1
        errs = dist.get('error', 0)
        valid = [it for it in items if it['verdict'] != 'error']
        if not valid:
            summary[rid] = {'dist': dist, 'consistency': 0.0, 'fully_stable': False,
                            'all_failed': True}
            print('  %-10s ⚠ 全部调用失败（%d/%d），无有效数据' % (rid, errs, len(items)))
            continue
        vdist = {}
        for it in valid:
            vdist[it['verdict']] = vdist.get(it['verdict'], 0) + 1
        top = max(vdist.items(), key=lambda kv: kv[1])
        stable = (top[1] == len(valid))
        summary[rid] = {'dist': dist, 'valid_dist': vdist,
                        'consistency': round(top[1] / float(len(valid)), 3),
                        'fully_stable': stable, 'errors': errs}
        print('  %-10s 分布=%s  一致率=%.2f  %s%s'
              % (rid, vdist, top[1] / float(len(valid)),
                 '✅ 稳定' if stable else '⚠ 存在浮动',
                 '  （%d 次调用失败已剔除）' % errs if errs else ''))
        obs_rate = sum(1 for it in items if it['has_observation']) / float(len(items))
        print('             观察字段出现率=%.2f' % obs_rate)
    if records['b2']:
        counts = [r['count'] for r in records['b2']]
        print('  B2 疑点数：%s  波动幅度=%d'
              % (counts, (max(counts) - min(counts)) if counts else 0))

    out = {
        'generated_at': utc_now_iso(),
        'sample': args.sample,
        'apk_sha256': sha,
        'rule_pack': registry.RULE_PACK_VERSION,
        'b1_prompt': B1_PROMPT_VERSION,
        'b2_prompt': B2_PROMPT_VERSION,
        'runs': args.runs,
        'records': records,
        'summary': summary,
    }
    out_path = os.path.join(PROJECT_ROOT, 'review',
                            'b_stability_%s_%d.json' % (args.sample, args.runs))
    with open(out_path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print('')
    print('[out] %s' % out_path)
    return 0


if __name__ == '__main__':
    sys.exit(main())
