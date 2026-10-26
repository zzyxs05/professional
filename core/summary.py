# -*- coding: utf-8 -*-
"""summary.py · B 通道第三类任务（B3）：跨样本汇总报告（六合一）

- 输入：lab 全部样本的【最新 RUN】报告（report.json），组装为结构化摘要
- 用模型生成"简洁、观点明确"的人读汇总（≤900 字）；无模型/失败 → 降级为确定性模板渲染
- 证据落盘：prompt 版本 / 模型 / 原始响应 / 输入摘要哈希 → review/summary_gen_record.json
- 纪律：产物为 review 类材料（供评审/对抗组），生成记录与正文分离；未经人工签署不改变任何审计结论
"""

import hashlib
import json
import os

from . import registry
from .channel_b import _chat, load_key_config
from .evidence import utc_now_iso


def _batch_span_note(bundle):
    """批次一致性检查：各样本最新 RUN 的时间跨度过大时提示（防混合轮次快照）。"""
    stamps = sorted(b['meta'].get('created', '') for b in bundle if b['meta'].get('created'))
    if len(stamps) < 2:
        return '', ''
    try:
        import datetime
        first = datetime.datetime.fromisoformat(stamps[0].replace('Z', '+00:00'))
        last = datetime.datetime.fromisoformat(stamps[-1].replace('Z', '+00:00'))
        span_min = (last - first).total_seconds() / 60.0
    except ValueError:
        return '', ''
    span = '%s → %s（跨度 %.0f 分钟）' % (stamps[0], stamps[-1], span_min)
    note = ''
    if span_min > 120:
        note = ('注意：批次时间跨度 %.0f 分钟 > 120，可能混合了不同轮次的运行；'
                '建议先全量重跑再生成汇总' % span_min)
    return span, note

B3_PROMPT_VERSION = 'b3-v0.2'

B3_SYSTEM = (
    '你是静态审计报告撰写者。\n'
    '输入：六个 APK 样本的结构化审计结果，含【汇总统计】行（程序统计的总数）、'
    '每样本的结论与档位、覆盖声明。\n'
    '任务：为评审人写一份中文汇总报告（Markdown，≤900 字）。\n'
    '输出要求：\n'
    '- 统计数字取自【汇总统计】行（该行由程序统计，直接引用）\n'
    '- 文中档位与输入一致：输入为"待复核"的，文中仍写"待复核"\n'
    '- 无检出样本沿用输入的无检出语义表述\n'
    '- 结构：① 总评（1 段，观点明确） ② 六样本速览（表格：样本 | 检出要点 | 无检出语义） '
    '③ 值得复核的点 ④ 诚实边界（通道 B 状态、覆盖缺口、静态分析上限） ⑤ 给复核人的动作项（≤4 条）'
)


# ------------------------------------------------------------------ 收集
def collect_latest_reports(project_root):
    """lab 全样本 → 各样本最新 RUN 的 (report, meta)。返回 (bundle, missing)。"""
    truth_dir = os.path.join(project_root, 'lab', 'truth')
    ev_root = os.path.join(project_root, 'evidence')
    if not os.path.isdir(truth_dir):
        return [], ['lab/truth 目录不存在']
    names = sorted(n[:-5] for n in os.listdir(truth_dir) if n.endswith('.json'))

    latest = {}
    if os.path.isdir(ev_root):
        for run in sorted(os.listdir(ev_root), reverse=True):
            base = os.path.join(ev_root, run)
            rp = os.path.join(base, 'report.json')
            mp = os.path.join(base, 'meta.json')
            if not os.path.isfile(rp):
                continue
            try:
                with open(rp, 'r', encoding='utf-8') as f:
                    rep = json.load(f)
            except (json.JSONDecodeError, OSError):
                continue
            apk = rep.get('target', {}).get('apk_name', '')
            key = apk[:-4] if apk.endswith('.apk') else apk
            if key and key not in latest:
                meta = {}
                if os.path.isfile(mp):
                    try:
                        with open(mp, 'r', encoding='utf-8') as f:
                            meta = json.load(f)
                    except (json.JSONDecodeError, OSError):
                        pass
                latest[key] = {'run_id': run, 'report': rep, 'meta': meta}

    bundle = []
    missing = []
    for name in names:
        if name in latest:
            bundle.append(dict(sample=name, **latest[name]))
        else:
            missing.append(name)
    return bundle, missing


# ------------------------------------------------------------------ 输入组装
def build_summary_input(project_root, bundle, truth_summary=None):
    lines = []
    lines.append('规则包版本：%s' % registry.RULE_PACK_VERSION)
    models = sorted({b['report'].get('versions', {}).get('channel_b_model', 'none') for b in bundle})
    lines.append('通道 B 模型：%s' % ('、'.join(models)))
    if truth_summary:
        lines.append('真值一致性（自评质量门）：%s 点中一致 %s，硬错 %s（FP %s / 漏检 %s / 档位错 %s），噪声 %s'
                     % (truth_summary.get('total'), truth_summary.get('pass'),
                        truth_summary.get('hard_errors'), truth_summary.get('fp'),
                        truth_summary.get('miss'), truth_summary.get('tier'), truth_summary.get('noise')))
    # 汇总统计：程序计算，模型只许引用（防止自行加总出错）
    n_conf = n_rev = n_rb = n_quiet = 0
    quiet_names = []
    for b in bundle:
        concl = b['report'].get('conclusions', [])
        std = [c for c in concl if not c['criterion_id'].startswith('R-B-')]
        n_rb += len([c for c in concl if c['criterion_id'].startswith('R-B-')])
        if not std:
            n_quiet += 1
            quiet_names.append(b['sample'])
        for c in std:
            if c['status'] == registry.STATUS_CONFIRMED:
                n_conf += 1
            elif c['status'] == registry.STATUS_REVIEW:
                n_rev += 1
    lines.append('【汇总统计】样本 %d 个：规则侧无检出的样本 %d 个（%s）；其余样本共 %d 条规则结论'
                 '（已确认 %d、待复核 %d）；B 侧疑点条目 %d。'
                 % (len(bundle), n_quiet, '、'.join(quiet_names) or '无',
                    n_conf + n_rev, n_conf, n_rev, n_rb))
    lines.append('【口径说明】R-PERM-01 / R-PERM-03 的「待复核」为规则设计上限'
                 '（静态只能给疑点组合/排除性结论），不是通道间分歧；'
                 '「未发现」仅指在已声明覆盖范围内未命中，不等于安全。')
    lines.append('')
    lines.append('样本数据：')
    for b in bundle:
        rep = b['report']
        cov = rep.get('coverage', {})
        concl = rep.get('conclusions', [])
        std = [c for c in concl if not c['criterion_id'].startswith('R-B-')]
        rb = [c for c in concl if c['criterion_id'].startswith('R-B-')]
        lines.append('### %s.apk（run=%s，sha256 前缀 %s）'
                     % (b['sample'], b['run_id'], rep.get('target', {}).get('apk_sha256', '')[:12]))
        conf = len([c for c in std if c['status'] == registry.STATUS_CONFIRMED])
        rev = len([c for c in std if c['status'] == registry.STATUS_REVIEW])
        lines.append('- 本样本规则结论 %d 条（已确认 %d、待复核 %d），B 侧疑点 %d 条'
                     % (len(std), conf, rev, len(rb)))
        if not std and not rb:
            lines.append('- 结论：无（未发现可检出违规）')
        for c in std:
            lines.append('- %s [%s] %s（定位 %d 处）'
                         % (c['criterion_id'], c['status'], c.get('scope', ''),
                            len([p for p in (c.get('location') or '').split(' | ') if p])))
        for c in rb:
            lines.append('- %s [%s，B 侧疑点·未钉] %s'
                         % (c['criterion_id'], c['status'], (c.get('scope') or '')[:80]))
        obs = rep.get('observations', [])
        if obs:
            lines.append('- B 通道观察（非结论）：%d 条，例如 %s'
                         % (len(obs),
                            '；'.join((o.get('claim') or '')[:60] for o in obs[:2])))
        lines.append('- 覆盖：已检查 %d 项；未覆盖 %s；解码%s'
                     % (len(cov.get('checked', [])),
                        '、'.join(cov.get('not_checked', [])) or '无',
                        '失败' if cov.get('decode_failed') else '正常'))
    return '\n'.join(lines)


# ------------------------------------------------------------------ 渲染
def _template_render(project_root, bundle, truth_summary, note):
    lines = ['# APK 审计 · 六样本汇总报告', '']
    lines.append('> 生成方式：模板渲染（%s）｜ 规则包 %s ｜ 未经人工签署' % (note, registry.RULE_PACK_VERSION))
    lines.append('')
    lines.append('## 样本速览')
    lines.append('')
    lines.append('| 样本 | 已确认 | 待复核 | B 侧疑点 | 运行 |')
    lines.append('|------|--------|--------|----------|------|')
    for b in bundle:
        rep = b['report']
        concl = rep.get('conclusions', [])
        std = [c for c in concl if not c['criterion_id'].startswith('R-B-')]
        rb = [c for c in concl if c['criterion_id'].startswith('R-B-')]
        conf = len([c for c in std if c['status'] == registry.STATUS_CONFIRMED])
        rev = len([c for c in std if c['status'] == registry.STATUS_REVIEW])
        lines.append('| %s | %d | %d | %d | %s |'
                     % (b['sample'], conf, rev, len(rb), b['run_id']))
    lines.append('')
    if truth_summary:
        lines.append('- 真值一致性：%s/%s 一致，硬错 %s，噪声 %s'
                     % (truth_summary.get('pass'), truth_summary.get('total'),
                        truth_summary.get('hard_errors'), truth_summary.get('noise')))
    lines.append('')
    lines.append('## 逐样本要点')
    for b in bundle:
        lines.append('')
        lines.append('### %s' % b['sample'])
        std = [c for c in b['report'].get('conclusions', [])
               if not c['criterion_id'].startswith('R-B-')]
        if std:
            for c in std:
                lines.append('- %s：%s（%s）' % (c['criterion_id'], c.get('scope', ''), c['status']))
        else:
            lines.append('- 未发现可检出违规（覆盖范围见该样本 report.md 的覆盖声明）')
    lines.append('')
    lines.append('## 诚实边界')
    lines.append('')
    lines.append('- 证据层级上限 STATIC（只读、不执行被测 APK）；')
    lines.append('- 无检出 ≠ 安全：仅在已声明的规则集与覆盖范围内"未发现"；')
    lines.append('- 通道 B（LLM）结论天花板为待复核，升级仅经确定性钉证据；')
    lines.append('- 本文件不含对真实第三方应用的结论（样本为自建靶场）。')
    return '\n'.join(lines) + '\n'


# ------------------------------------------------------------------ 主入口
def generate_summary(project_root, out_path=None, no_llm=False):
    """生成六合一汇总。返回 dict（含 ok/mode/out_path/record_path）。"""
    bundle, missing = collect_latest_reports(project_root)
    if not bundle:
        return {'ok': False, 'mode': 'none', 'error': '没有可用样本报告（先跑 analyze）',
                'missing': missing}
    batch_span, batch_note = _batch_span_note(bundle)

    truth_summary = None
    tr_path = os.path.join(project_root, 'review', 'truth_result.json')
    if os.path.isfile(tr_path):
        try:
            with open(tr_path, 'r', encoding='utf-8') as f:
                truth_summary = json.load(f).get('summary')
        except (json.JSONDecodeError, OSError):
            pass

    summary_input = build_summary_input(project_root, bundle, truth_summary)
    input_hash = hashlib.sha256(summary_input.encode('utf-8')).hexdigest()

    out_path = out_path or os.path.join(project_root, 'review', 'summary.md')
    record_path = os.path.join(project_root, 'review', 'summary_gen_record.json')

    model = 'none'
    raw = ''
    mode = 'template'
    note = ''
    cfg = [] if no_llm else load_key_config(project_root)
    if cfg:
        try:
            raw = _chat(cfg[0], [{'role': 'system', 'content': B3_SYSTEM},
                                 {'role': 'user', 'content': summary_input}],
                        max_tokens=2400)
            if raw and raw.strip():
                mode = 'llm'
                model = cfg[0][0]
            else:
                note = '模型返回为空'
        except Exception as e:  # noqa: BLE001 —— 任何失败均降级
            note = '模型调用失败：%s' % str(e)[:200]
    else:
        note = '未配置模型（key.txt 缺失）' if not no_llm else '按参数禁用模型'

    if mode == 'llm':
        content = raw.strip()
        # 生成声明由程序附加（与模型输出分离，保证纪律声明不依赖模型自觉）
        content += ('\n\n---\n*本报告由 B3 汇总任务生成（模型 %s，prompt %s），数据源为六份 RUN 报告快照；'
                    '**未经人工签署**，不改变任何审计结论；生成记录（prompt/响应/哈希）见 '
                    'review/summary_gen_record.json。*' % (model, B3_PROMPT_VERSION))
    else:
        content = _template_render(project_root, bundle, truth_summary, note)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(content + ('\n' if not content.endswith('\n') else ''))

    record = {
        'generated_at': utc_now_iso(),
        'mode': mode,
        'note': note,
        'model': model,
        'prompt_version': B3_PROMPT_VERSION,
        'input_sha256': input_hash,
        'input_preview': summary_input[:3000],
        'raw_response': raw[:6000],
        'samples': [{'sample': b['sample'], 'run_id': b['run_id']} for b in bundle],
        'missing': missing,
        'batch_span': batch_span,
        'batch_note': batch_note,
        'human_signoff': 'pending',
    }
    with open(record_path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(record, f, ensure_ascii=False, indent=2)

    return {'ok': True, 'mode': mode, 'model': model, 'out_path': out_path,
            'record_path': record_path, 'samples': len(bundle), 'missing': missing,
            'note': note, 'batch_note': batch_note}
