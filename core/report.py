# -*- coding: utf-8 -*-
"""report.py · 双渲染：report.md（人读主交付物）+ report.json（机器读支撑件）"""

import json

from . import registry

STATUS_TO_MD_TITLE = {
    registry.STATUS_CONFIRMED: '已确认',
    registry.STATUS_REVIEW: '待复核',
    registry.STATUS_UNDECIDED: '无法判定',
}


def build_report_json(run_id, apk_name, apk_sha256, versions, conclusions, coverage,
                      state_history=None, budget=None, observations=None):
    return {
        'run_id': run_id,
        'target': {'apk_name': apk_name, 'apk_sha256': apk_sha256},
        'versions': versions,
        'conclusions': conclusions,
        'observations': observations or [],
        'coverage': coverage,
        'state': state_history,
        'budget': budget,
    }


def render_md(report, meta_extra=None):
    lines = []
    tgt = report['target']
    lines.append('# APK 静态审计报告 %s' % report['run_id'])
    lines.append('')
    lines.append('- 样本：`%s`' % tgt['apk_name'])
    lines.append('- sha256：`%s`' % tgt['apk_sha256'])
    lines.append('- 规则包版本：`%s`　｜　通道 B 模型：`%s`'
                 % (report['versions'].get('rule_pack'),
                    report['versions'].get('channel_b_model', 'none')))
    if meta_extra:
        for k, v in meta_extra.items():
            lines.append('- %s：%s' % (k, v))
    lines.append('')
    lines.append('> 证据层级说明：本项目只读、不执行被测 APK，全部证据层级上限为 STATIC。')
    lines.append('')

    cov = report['coverage']
    lines.append('## 覆盖声明')
    lines.append('')
    lines.append('- 已检查（%d 条）：%s' % (len(cov.get('checked', [])), '；'.join(cov.get('checked', [])) or '—'))
    not_checked = cov.get('not_checked', [])
    lines.append('- 未覆盖（%d 条）：%s' % (len(not_checked), '；'.join(not_checked) or '—'))
    if cov.get('decode_failed'):
        lines.append('- 解码状态：**失败** —— %s' % cov.get('decode_note', ''))
    else:
        lines.append('- 解码状态：正常%s' % ('（复用缓存）' if cov.get('decode_reused') else ''))
    for note in cov.get('notes', []):
        lines.append('- 附注：%s' % note)
    lines.append('')

    groups = {registry.STATUS_CONFIRMED: [], registry.STATUS_REVIEW: [], registry.STATUS_UNDECIDED: []}
    for c in report['conclusions']:
        groups.setdefault(c['status'], []).append(c)

    for status in (registry.STATUS_CONFIRMED, registry.STATUS_REVIEW, registry.STATUS_UNDECIDED):
        items = groups.get(status, [])
        lines.append('## %s（%d 条）' % (status, len(items)))
        lines.append('')
        if not items:
            lines.append('（无）')
            lines.append('')
            continue
        for i, c in enumerate(items, 1):
            lines.append('### %d. %s · %s' % (i, c['criterion_id'], c.get('scope', '')))
            lines.append('')
            lines.append('- 状态：%s ｜ 通道：%s ｜ 人工签署：%s'
                         % (c['status'], c['channel'], c.get('human_signoff', 'pending')))
            if c.get('evidence_ids'):
                lines.append('- 证据：%s' % ', '.join('`%s`' % e for e in c['evidence_ids']))
            loc = c.get('location', '')
            lines.append('- 定位坐标：')
            for part in loc.split(' | '):
                if part:
                    lines.append('    - `%s`' % part)
            for note in c.get('notes', []):
                if note:
                    lines.append('- 说明：%s' % note)
            if c.get('missing_evidence'):
                lines.append('- 缺口：%s' % '；'.join(c['missing_evidence']))
            lines.append('')

    obs = report.get('observations') or []
    if obs:
        lines.append('## B 通道观察（非结论 · 保留模型原声）')
        lines.append('')
        lines.append('> 以下为 LLM 复核/扫描的补充观察，**未经机械核查、不作为结论、不计入三档统计**；'
                     '仅用于人工参考。')
        lines.append('')
        for o in obs:
            tag = o.get('source', 'B')
            rid = o.get('rule_id', '')
            loc = o.get('location', '')
            lines.append('- [%s%s] %s%s' % (
                tag, ('·' + rid) if rid else '', o.get('claim', ''),
                ('（位置：%s）' % loc) if loc else ''))
            if o.get('note'):
                lines.append('    - %s' % o['note'])
        lines.append('')

    lines.append('---')
    lines.append('*本报告由 apkaudit 生成（规则包 %s）。复核方式：按定位坐标直达原文，'
                 '比对 raw_snippet 与证据 JSONL；结论未经人工签署前不生效。*'
                 % report['versions'].get('rule_pack'))
    return '\n'.join(lines) + '\n'


def dump_json(report):
    return json.dumps(report, ensure_ascii=False, indent=2)
