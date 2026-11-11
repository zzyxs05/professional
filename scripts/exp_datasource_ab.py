#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""exp_datasource_ab.py · 数据源实现 A/B 对照实验（EXP-6 / EXP-7 复测）

技术决策锚点：ADR-0002（四层数据源分层、各自独立降级）。
对照对象：R-CODE-01「动态代码加载」的两条独立实现路径——
  A · smali_src 强模式：apktool 反汇编 + 调用上下文，档位上限「已确认」
  B · dex_strings 弱模式：自研 dex 类型引用，零外部依赖，档位上限「待复核」

控制变量见 docs/experiment-protocol.md。本脚本只采集真实运行数据，不写结论、
不启用通道 B、不联网、不产生 RUN、不改写 evidence/。

计时范围：build_context() 调用前 → r_code_01.run(ctx) 返回后；
每方法预热 1 次（不计时）+ 正式计时 N 次。apktool 解码为一次性前置处理，
产物复用缓存，不计入计时。

用法：
    python scripts/exp_datasource_ab.py --runs 5
    python scripts/exp_datasource_ab.py --runs 5 --samples bad01,bad03

产物：review/exp_datasource_ab.json
"""

import argparse
import json
import os
import platform
import statistics
import sys
import tempfile
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core import registry                       # noqa: E402
from core.channel_a import build_context        # noqa: E402
from core.rules.code import r_code_01           # noqa: E402
from core.evidence import sha256_file, utc_now_iso  # noqa: E402

ALL_SAMPLES = ['bad01', 'bad02', 'bad03', 'bad04', 'good01', 'good02']
RULE_ID = 'R-CODE-01'


def decode_dir_for(sha):
    return os.path.join(tempfile.gettempdir(),
                        registry.DECODE_TMP_DIRNAME, sha[:16])


def serialize_hits(hits):
    return [{'rule_id': h.rule_id,
             'location': h.location,
             'raw_snippet': (h.raw_snippet or '')[:200],
             'note': h.note,
             'max_status': h.max_status} for h in hits]


def one_run(apk_path, sha, ddir):
    """一次完整采集：构造上下文 + 执行单条规则，返回 (耗时 ms, 命中明细)。"""
    t0 = time.perf_counter()
    ctx = build_context(PROJECT_ROOT, apk_path, sha, ddir)
    hits = r_code_01.run(ctx)
    t1 = time.perf_counter()
    return (t1 - t0) * 1000.0, serialize_hits(hits)


def weak_mode_diagnostic(apk_path, sha):
    """只读诊断：记录弱模式匹配口径的事实，不改变规则行为。

    dex 扫描产出的类型描述符带 MUTF-8 长度前缀，规则侧用精确集合成员判断；
    本函数把「精确匹配」与「子串可见」两个事实都落盘，供结论归因使用。
    """
    ctx = build_context(PROJECT_ROOT, apk_path, sha, None)
    if ctx.dex is None:
        return {'error': 'dex 数据源不可用'}
    patterns = r_code_01.LOADER_PATTERNS
    return {
        'type_descriptors_count': len(ctx.dex.type_descriptors),
        'patterns': {
            pat: {
                'exact_membership': pat in ctx.dex.type_descriptors,
                'substring_present': any(pat in t for t in ctx.dex.type_descriptors),
            } for pat in patterns
        },
        'note': '仅记录匹配口径事实；未修改任何规则、阈值或规则包版本。',
    }


def run_method(apk_path, sha, ddir, rounds, external_dep, label):
    out = {'label': label, 'external_dep': external_dep, 'rounds': [],
           'warmup': '1 次（不计时）'}
    try:
        one_run(apk_path, sha, ddir)          # 预热：消除首次 IO / 缓存影响
    except Exception as e:                    # noqa: BLE001 —— 失败如实记录，不中断全实验
        out['error'] = '%s: %s' % (type(e).__name__, e)
        return out

    for i in range(1, rounds + 1):
        try:
            ms, hits = one_run(apk_path, sha, ddir)
            out['rounds'].append({'round': i, 'elapsed_ms': round(ms, 3),
                                  'hit_count': len(hits), 'hits': hits})
        except Exception as e:                # noqa: BLE001
            out.setdefault('errors', []).append(
                {'round': i, 'error': '%s: %s' % (type(e).__name__, e)})

    times = [r['elapsed_ms'] for r in out['rounds']]
    if times:
        out['median_ms'] = round(statistics.median(times), 3)
        out['min_ms'] = round(min(times), 3)
        out['max_ms'] = round(max(times), 3)
    counts = [r['hit_count'] for r in out['rounds']]
    out['hit_count'] = counts[-1] if counts else None
    out['hits_stable_across_rounds'] = bool(counts) and len(set(counts)) == 1
    out['hits'] = out['rounds'][-1]['hits'] if out['rounds'] else []
    out['status_ceiling'] = (out['hits'][0]['max_status']
                             if out['hits'] else None)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--runs', type=int, default=5, help='每方法正式计时轮次（建议 ≥5）')
    ap.add_argument('--samples', default=None, help='逗号分隔的样本名，默认全部 6 个')
    ap.add_argument('--out', default=os.path.join(PROJECT_ROOT, 'review',
                                                  'exp_datasource_ab.json'))
    args = ap.parse_args()

    names = ([s.strip() for s in args.samples.split(',') if s.strip()]
             if args.samples else ALL_SAMPLES)
    apks_dir = os.path.join(PROJECT_ROOT, 'lab', 'apks')

    result = {
        'experiment': 'EXP-6 / datasource-ab',
        'decision_anchor': 'ADR-0002',
        'rule': RULE_ID,
        'protocol': 'docs/experiment-protocol.md',
        'generated_at': utc_now_iso(),
        'environment': {
            'python': platform.python_version(),
            'platform': platform.platform(),
            'rule_pack': registry.RULE_PACK_VERSION,
            'channel_b': '未启用（不调用模型）',
            'network': '无',
        },
        'fixed_conditions': {
            'input_dataset': 'lab/apks/ 6 个自建样本（sha256 见 lab/sha256.txt）',
            'preprocessing': 'apktool 解码产物复用 %s/<sha前16位>，不重复解码；'
                             '解码耗时为一次性前置成本，不计入计时' % registry.DECODE_TMP_DIRNAME,
            'scope': '只执行 %s 一条规则，避免其他规则引入变量' % RULE_ID,
            'timing': 'build_context() 前 → 规则返回后；perf_counter；预热 1 次 + 计时 %d 次'
                      % args.runs,
            'excluded': '报告渲染、证据落盘、模型调用、apktool 解码',
        },
        'metrics': [
            '每样本命中数与命中明细（坐标 + 档位上限）',
            '样本级检出一致性：两方法是否都发现目标（不做坐标级比对，两路径坐标格式不同）',
            '解析 + 规则执行耗时中位数 / 最小 / 最大（ms）',
            '轮次间命中稳定性',
            '外部依赖：A 需 Java + apktool，B 零依赖',
        ],
        'samples': {},
    }

    print('=== EXP-6 数据源实现 A/B 对照（%s）===' % RULE_ID)
    print('规则包=%s  轮次=%d  样本=%d  通道B=未启用' %
          (registry.RULE_PACK_VERSION, args.runs, len(names)))
    print('')

    for name in names:
        apk_path = os.path.join(apks_dir, name + '.apk')
        if not os.path.isfile(apk_path):
            print('[skip] %s：样本缺失' % name)
            result['samples'][name] = {'error': '样本文件缺失'}
            continue
        sha = sha256_file(apk_path)
        ddir = decode_dir_for(sha)
        cache_ok = (os.path.isfile(os.path.join(ddir, 'AndroidManifest.xml'))
                    and os.path.isdir(os.path.join(ddir, 'smali')))
        entry = {
            'apk_sha256': sha,
            'decode_cache': ddir,
            'decode_cache_available': cache_ok,
        }

        if cache_ok:
            entry['A_smali'] = run_method(apk_path, sha, ddir, args.runs,
                                          'java + apktool', 'smali_src 强模式')
        else:
            entry['A_smali'] = {'error': '解码缓存不可用，A 组未运行（不构造假数据）'}
        entry['B_dex'] = run_method(apk_path, sha, None, args.runs,
                                    '无（仅标准库）', 'dex_strings 弱模式')
        entry['B_dex']['weak_mode_diagnostic'] = weak_mode_diagnostic(apk_path, sha)

        a_n = entry['A_smali'].get('hit_count')
        b_n = entry['B_dex'].get('hit_count')
        if isinstance(a_n, int) and isinstance(b_n, int):
            entry['both_detected'] = bool(a_n and b_n)
            entry['detection_agreement'] = (bool(a_n) == bool(b_n))
            a_ms = entry['A_smali'].get('median_ms')
            b_ms = entry['B_dex'].get('median_ms')
            entry['median_ms_ratio_A_over_B'] = (round(a_ms / b_ms, 3)
                                                 if a_ms and b_ms else None)
        result['samples'][name] = entry

        a_desc = ('%s 命中 / %s ms' % (a_n, entry['A_smali'].get('median_ms'))
                  if isinstance(a_n, int) else '未运行')
        b_desc = ('%s 命中 / %s ms' % (b_n, entry['B_dex'].get('median_ms'))
                  if isinstance(b_n, int) else '未运行')
        print('[%-6s] A: %-22s B: %-22s 一致=%s' %
              (name, a_desc, b_desc, entry.get('detection_agreement', 'n/a')))

    a_detect = sum(1 for e in result['samples'].values()
                   if isinstance(e.get('A_smali', {}).get('hit_count'), int)
                   and e['A_smali']['hit_count'] > 0)
    b_detect = sum(1 for e in result['samples'].values()
                   if isinstance(e.get('B_dex', {}).get('hit_count'), int)
                   and e['B_dex']['hit_count'] > 0)
    agree = sum(1 for e in result['samples'].values()
                if e.get('detection_agreement') is True)
    a_ms_all = [e['A_smali']['median_ms'] for e in result['samples'].values()
                if 'median_ms' in e.get('A_smali', {})]
    b_ms_all = [e['B_dex']['median_ms'] for e in result['samples'].values()
                if 'median_ms' in e.get('B_dex', {})]
    result['summary'] = {
        'samples': len(result['samples']),
        'A_detected_samples': a_detect,
        'B_detected_samples': b_detect,
        'agreement_samples': agree,
        'A_median_ms_across_samples': round(statistics.median(a_ms_all), 3) if a_ms_all else None,
        'B_median_ms_across_samples': round(statistics.median(b_ms_all), 3) if b_ms_all else None,
        'note': '统计由脚本对真实运行结果计算；结论与边界见 docs/experiments.md（EXP-6 / EXP-7）。',
    }

    print('')
    print('=== 汇总：样本 %d · A 检出 %d · B 检出 %d · 检出一致 %d ===' %
          (len(result['samples']), a_detect, b_detect, agree))

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print('[out] %s' % args.out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
