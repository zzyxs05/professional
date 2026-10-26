#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""cli.py · 唯一入口：analyze / register / evaluate / reset

用法（总档 §6.1）：
    python cli.py analyze <apk> [--out <dir>] [--force-decode]
    python cli.py register <apk>
    python cli.py evaluate --run <run_id> [--llm]
    python cli.py reset
"""

import argparse
import json
import os
import shutil
import sys
import tempfile

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core import fusion, registry
from core import report as report_mod
from core.adapters import decode_with_apktool, probe_toolchain
from core.axml import AXMLParseError
from core.channel_a import build_context, run_channel_a
from core.channel_b import run_channel_b
from core.evidence import EvidenceStore, local_stamp, sha256_file, utc_now_iso
from core.runner import Runner


# ------------------------------------------------------------------ analyze
def cmd_analyze(args):
    apk_path = os.path.abspath(args.apk)
    if not os.path.isfile(apk_path):
        print('[error] 样本不存在：%s' % apk_path)
        return 2

    sha = sha256_file(apk_path)
    run_id = 'RUN-' + local_stamp()
    runner = Runner(PROJECT_ROOT)
    if args.no_evidence:
        # 演练模式：完整跑链路（含通道 B），但证据写临时区，不进 evidence/ 正本
        import tempfile
        ev_root = tempfile.mkdtemp(prefix='apkaudit_trial_')
        print('[run] %s（演练模式 · 不写入 evidence，sha256=%s…）' % (run_id, sha[:16]))
    else:
        ev_root = os.path.join(PROJECT_ROOT, 'evidence')
        print('[run] %s（sha256=%s…）' % (run_id, sha[:16]))
    store = EvidenceStore(ev_root, run_id)

    # ---- 解码（失败不阻断：M/S 类照跑，语义类进覆盖声明）
    runner.sm.advance('DECODING')
    tc = probe_toolchain(PROJECT_ROOT)
    decode = decode_with_apktool(tc, apk_path, sha, PROJECT_ROOT,
                                 runner=runner, force=args.force_decode)
    if decode.ok:
        print('[toolchain] %s' % tc.describe())
        print('[decode] %s%s' % (decode.out_dir, '（复用缓存）' if decode.reused else ''))
    else:
        print('[toolchain] %s' % tc.describe())
        print('[decode] 降级：%s' % decode.error)

    # ---- 通道 A
    runner.sm.advance('RULE_A')
    hits_by_rule = {}
    ev_map = {}
    observations = []
    sample_failed = False
    fail_reason = ''
    try:
        ctx = build_context(PROJECT_ROOT, apk_path, sha,
                            decode.out_dir if decode.ok else None)
    except AXMLParseError as e:
        sample_failed = True
        fail_reason = 'AndroidManifest.xml 解析失败：%s' % e
        ctx = None
    except Exception as e:  # noqa: BLE001 —— 兜底：样本级失败如实报告
        sample_failed = True
        fail_reason = '样本预处理失败：%s' % e
        ctx = None

    if sample_failed:
        print('[channel A] 样本级失败：%s' % fail_reason)
        conclusions = []
        for rid in registry.ALL_RULE_IDS:
            conclusions.append({
                'criterion_id': rid,
                'status': registry.STATUS_UNDECIDED,
                'channel': 'A',
                'location': '',
                'evidence_ids': [],
                'scope': registry.RULE_META[rid]['name'],
                'missing_evidence': [fail_reason],
                'human_signoff': 'pending',
                'notes': [],
            })
        coverage = {
            'checked': [],
            'not_checked': ['全部规则（manifest 数据源不可用）'],
            'decode_failed': True,
            'decode_note': fail_reason,
            'notes': [],
        }
        b_result = None
    else:
        hits_by_rule, coverage, notes = run_channel_a(ctx)
        coverage['decode_failed'] = False
        coverage['decode_note'] = decode.error if not decode.ok else ''
        coverage['decode_reused'] = bool(decode.ok and decode.reused)
        coverage['notes'] = notes
        rel_apk = os.path.relpath(apk_path, PROJECT_ROOT).replace('\\', '/')
        total = 0
        for rule_id, hits in hits_by_rule.items():
            ev_map[rule_id] = []
            for h in hits:
                ev = store.add_record(
                    rule_id, h.location, h.raw_snippet, kind='rule_hit',
                    source_file=rel_apk, source_sha256=sha,
                    rule_pack=registry.RULE_PACK_VERSION,
                    extra={'note': h.note})
                ev_map[rule_id].append(ev)
                total += 1
        hit_summary = ' '.join('%s(%d)' % (r, len(h))
                               for r, h in sorted(hits_by_rule.items()) if h)
        print('[channel A] 命中 %d 处：%s' % (total, hit_summary or '（无）'))
        if ctx.manifest_doc is not None:
            store.write_text('decode/AndroidManifest.rebuilt.xml',
                             ctx.manifest_doc.rebuilt_xml)

        # ---- 通道 B
        runner.sm.advance('CHANNEL_B')
        b_result = run_channel_b(ctx, hits_by_rule, runner, store)
        if b_result.ran:
            print('[channel B] 运行（模型：%s，调用 %d 次）' % (b_result.model, b_result.calls))
            coverage['checked'].append('通道B(模型:%s)' % b_result.model)
        else:
            print('[channel B] 未运行：%s' % b_result.reason)
            coverage['not_checked'].append('通道 B（%s）' % b_result.reason)

    # ---- 融合 + 报告
    runner.sm.advance('FUSION')
    if not sample_failed:
        def _pin_fn(guess, pt):
            res = fusion.pin_evidence(ctx, pt.get('claim', ''), pt.get('location', ''), guess)
            if res['status'] == 'pinned':
                for rinfo in res.get('rules', []):
                    evs = []
                    for loc in rinfo.get('locations', [])[:5]:
                        evs.append(store.add_record(
                            rinfo['rule_id'], loc,
                            (rinfo.get('note', '') + '；' + rinfo.get('facts', ''))[:300],
                            kind='pin_evidence', source_file=rel_apk, source_sha256=sha,
                            rule_pack=registry.RULE_PACK_VERSION, origin='b_channel_pin'))
                    rinfo['evidence_ids'] = evs
            else:
                ev = store.add_record(
                    'B2 疑点', (pt.get('location', '') or 'B2 claim')[:200],
                    ('未钉：' + pt.get('claim', '') + '｜原因：' + res.get('detail', ''))[:400],
                    kind='b2_point', source_file=rel_apk, source_sha256=sha,
                    rule_pack=registry.RULE_PACK_VERSION, origin='b_channel',
                    extra={'pin_detail': res.get('detail', '')})
                res['evidence_ids'] = [ev]
            return res

        conclusions, observations = fusion.build_conclusions(hits_by_rule, ev_map, b_result,
                                                             pin_fn=_pin_fn)
    runner.sm.advance('REPORT')

    versions = {
        'rule_pack': registry.RULE_PACK_VERSION,
        'channel_b_model': (b_result.model if (b_result and b_result.ran) else 'none'),
    }
    rep = report_mod.build_report_json(
        run_id, os.path.basename(apk_path), sha, versions, conclusions, coverage,
        state_history=runner.sm.history, budget=runner.budget.as_dict(),
        observations=observations)
    md = report_mod.render_md(rep, meta_extra={'工具链': tc.describe()})

    meta = {
        'run_id': run_id,
        'apk_name': os.path.basename(apk_path),
        'apk_path': os.path.relpath(apk_path, PROJECT_ROOT).replace('\\', '/'),
        'apk_sha256': sha,
        'rule_pack': registry.RULE_PACK_VERSION,
        'channel_b_model': versions['channel_b_model'],
        'toolchain': tc.describe(),
        'decode': {
            'ok': decode.ok,
            'reused': bool(decode.ok and decode.reused),
            'dir': decode.out_dir,
            'error': decode.error,
        },
        'created': utc_now_iso(),
        'budget': runner.budget.as_dict(),
        'state': runner.sm.as_dict(),
    }
    store.write_json('meta.json', meta)
    store.write_jsonl('channel_a/hits.jsonl', store.records)
    store.write_text('report.md', md)
    store.write_json('report.json', rep)

    if args.out:
        out_dir = os.path.abspath(args.out)
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, 'report.md'), 'w', encoding='utf-8', newline='\n') as f:
            f.write(md)
        with open(os.path.join(out_dir, 'report.json'), 'w', encoding='utf-8', newline='\n') as f:
            json.dump(rep, f, ensure_ascii=False, indent=2)
        print('[out] %s' % out_dir)

    runner.sm.advance('DONE')
    # 状态机终稿更新
    meta['state'] = runner.sm.as_dict()
    store.write_json('meta.json', meta)

    counts = {registry.STATUS_CONFIRMED: 0, registry.STATUS_REVIEW: 0, registry.STATUS_UNDECIDED: 0}
    for c in conclusions:
        counts[c['status']] = counts.get(c['status'], 0) + 1
    print('[summary] 已确认 %d / 待复核 %d / 无法判定 %d'
          % (counts.get(registry.STATUS_CONFIRMED, 0),
             counts.get(registry.STATUS_REVIEW, 0),
             counts.get(registry.STATUS_UNDECIDED, 0)))
    print('[report] %s' % os.path.join(store.root, 'report.md'))
    if args.no_evidence:
        print('  （演练模式：产物仅在临时区，未写入 evidence/ 正本）')
    return 0


# ------------------------------------------------------------------ register
def cmd_register(args):
    apk_path = os.path.abspath(args.apk)
    if not os.path.isfile(apk_path):
        print('[error] 样本不存在：%s' % apk_path)
        return 2
    sha = sha256_file(apk_path)
    try:
        rel = os.path.relpath(apk_path, PROJECT_ROOT).replace('\\', '/')
    except ValueError:
        rel = apk_path
    template = {
        'apk': rel,
        'sha256': sha,
        'designed_by': '',
        'reviewed_by': '',
        'expected': {rid: 'TODO（EXPECTED_HIT:CONFIRMED / EXPECTED_HIT:REVIEW / EXPECTED_SILENT）'
                     for rid in registry.ALL_RULE_IDS},
        'criteria_used': ['K-2'],
        'evidence_note': '',
    }
    print('# 登记条目（粘贴到 lab/truth/<name>.json 并人工标定，不自动写 registry）：')
    print(json.dumps(template, ensure_ascii=False, indent=2))
    return 0


# ------------------------------------------------------------------ evaluate
def cmd_evaluate(args):
    from evaluator.agent import evaluate_run
    result = evaluate_run(PROJECT_ROOT, args.run, use_llm=args.llm)
    print(result['text'])
    out_path = os.path.join(PROJECT_ROOT, 'evidence', args.run, 'evaluation.json')
    with open(out_path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print('[evaluation] %s' % out_path)
    return 0


# ------------------------------------------------------------------ summary（B3）
def cmd_summary(args):
    from core.summary import generate_summary
    res = generate_summary(PROJECT_ROOT, out_path=args.out, no_llm=args.no_llm)
    if not res.get('ok'):
        print('[summary] 失败：%s' % res.get('error', ''))
        if res.get('missing'):
            print('  缺少报告的样本：%s（请先运行 analyze）' % ', '.join(res['missing']))
        return 2
    mode_desc = ('模型生成（%s）' % res['model']) if res['mode'] == 'llm' \
        else ('模板渲染降级（%s）' % (res.get('note') or '未运行模型'))
    print('[summary] 六合一汇总报告已生成：%s' % mode_desc)
    print('  样本 %d 个%s' % (res['samples'],
                             '，缺失：%s' % ', '.join(res['missing']) if res['missing'] else ''))
    if res.get('batch_note'):
        print('  ⚠ %s' % res['batch_note'])
    print('  正文：%s' % res['out_path'])
    print('  生成记录（prompt/响应/哈希）：%s' % res['record_path'])
    print('  注：汇总件为 review 类材料，未经人工签署不改变任何审计结论。')
    return 0


# ------------------------------------------------------------------ reset
def cmd_reset(args):
    decode_root = os.path.join(tempfile.gettempdir(), registry.DECODE_TMP_DIRNAME)
    removed = []
    if os.path.isdir(decode_root):
        shutil.rmtree(decode_root, ignore_errors=True)
        removed.append(decode_root)
    print('[reset] 已清理可重建产物：')
    for r in removed:
        print('  - %s' % r)
    print('[reset] evidence/ 与已签署运行正本未触碰。')
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog='apkaudit', description='APK 通用静态审计')
    sub = parser.add_subparsers(dest='cmd')

    p_an = sub.add_parser('analyze', help='完整审计（双通道+融合+报告）')
    p_an.add_argument('apk', help='样本 APK 路径')
    p_an.add_argument('--out', default=None, help='报告副本输出目录（可选）')
    p_an.add_argument('--force-decode', action='store_true', help='强制重新解码')
    p_an.add_argument('--no-evidence', action='store_true',
                      help='演练模式：跑完整链路但不写入 evidence/（调准则/实验用，避免污染运行正本）')

    p_rg = sub.add_parser('register', help='登记样本（打印待粘贴条目，不写 registry）')
    p_rg.add_argument('apk')

    p_ev = sub.add_parser('evaluate', help='运行评价器')
    p_ev.add_argument('--run', required=True, help='run_id（如 RUN-20261014-223700）')
    p_ev.add_argument('--llm', action='store_true', help='启用模型判读（默认确定性）')

    p_sm = sub.add_parser('summary', help='B3：六样本汇总报告（模型生成，失败自动降级模板）')
    p_sm.add_argument('--out', default=None, help='输出路径（默认 review/summary.md）')
    p_sm.add_argument('--no-llm', action='store_true', help='禁用模型，直接模板渲染')

    sub.add_parser('reset', help='清理可重建产物')

    args = parser.parse_args(argv)
    if args.cmd == 'analyze':
        return cmd_analyze(args)
    if args.cmd == 'register':
        return cmd_register(args)
    if args.cmd == 'evaluate':
        return cmd_evaluate(args)
    if args.cmd == 'summary':
        return cmd_summary(args)
    if args.cmd == 'reset':
        return cmd_reset(args)
    parser.print_help()
    return 1


if __name__ == '__main__':
    sys.exit(main())
