# -*- coding: utf-8 -*-
"""agent.py · 评价器编排：预检 → 判读 → 四状态输出

链条（总档 §2.6）：Agent 审查 → 学生签署 → 教师复评，最终成绩只在教师层。
四状态：PASS（带范围）/ FAIL（带反例）/ INSUFFICIENT_EVIDENCE（带最小补查）/ NOT_APPLICABLE（仅教师预先批准）。
"""

import os

from core import registry
from .llm import judge
from .precheck import precheck


def _decide(findings, report):
    fails = [f for f in findings if f['level'] == 'FAIL']
    if fails:
        return 'FAIL', '确定性预检发现 %d 项阻断问题' % len(fails)
    if report is None:
        return 'FAIL', 'report.json 缺失'
    concl = report.get('conclusions', [])
    cov = report.get('coverage', {})
    checked = cov.get('checked', [])
    if not concl:
        # 干净样本的合法空报告：必须带完整覆盖声明（否则不合格）
        if checked and not cov.get('decode_failed'):
            return 'PASS', '无命中结论（干净样本），覆盖声明完整（%d 项已检查）' % len(checked)
        return 'INSUFFICIENT_EVIDENCE', '报告无任何结论且覆盖声明不完整（无法区分"干净"与"未覆盖"）'
    if all(c.get('status') == registry.STATUS_UNDECIDED for c in concl):
        return 'INSUFFICIENT_EVIDENCE', '全部结论为「无法判定」（数据源缺口）'
    insuff = [f for f in findings if f['level'] == 'INSUFFICIENT']
    if insuff:
        return 'INSUFFICIENT_EVIDENCE', insuff[0]['msg']
    return 'PASS', '引用、版本、结构检查通过（范围：%d 条结论）' % len(concl)


def evaluate_dir_quick(run_dir):
    """轻量接口：仅确定性预检（供校准判例使用）。返回 (status, reason)。"""
    findings, report, _records = precheck(run_dir)
    return _decide(findings, report)


def evaluate_run(project_root, run_id, use_llm=False):
    run_dir = os.path.join(project_root, 'evidence', run_id)
    if not os.path.isdir(run_dir):
        return {
            'run_id': run_id,
            'status': 'FAIL',
            'mode': 'deterministic',
            'findings': [{'level': 'FAIL', 'code': 'E-NO-RUN',
                          'msg': 'run 目录不存在：%s' % run_dir}],
            'text': '评价失败：run 目录不存在（%s）' % run_dir,
        }

    findings, report, records = precheck(run_dir)
    status, reason = _decide(findings, report)

    mode = 'deterministic'
    llm_note = ''
    if use_llm and report is not None:
        summary_lines = []
        for c in report.get('conclusions', [])[:15]:
            summary_lines.append('%s | %s | ch=%s | ev=%s'
                                 % (c.get('criterion_id'), c.get('status'),
                                    c.get('channel'), ','.join(c.get('evidence_ids', [])[:3])))
        ok, text = judge(
            project_root,
            '你是工程证据审查器：只依据给定结论与引用判断是否存在引用悬空、'
            '无证据自述、版本错配。输出 JSON：{"issues": ["..."]}，无问题输出 {"issues": []}。',
            '\n'.join(summary_lines) or '（无结论）')
        if ok:
            mode = 'llm'
            llm_note = text[:800]
        else:
            llm_note = 'LLM 判读降级（%s），已回退确定性模式' % text

    lines = []
    lines.append('评价器输出 · %s' % run_id)
    lines.append('- 状态：**%s**（%s）' % (status, reason))
    lines.append('- 模式：%s%s' % (mode, ('；%s' % llm_note) if llm_note else ''))
    if report is not None:
        concl = report.get('conclusions', [])
        counts = {}
        for c in concl:
            counts[c.get('status')] = counts.get(c.get('status'), 0) + 1
        lines.append('- 审查范围：结论 %d 条（%s）'
                     % (len(concl), '、'.join('%s %d' % (k, v) for k, v in counts.items())))
        ev_total = sum(len(c.get('evidence_ids', [])) for c in concl)
        lines.append('- 引用校验：%d 个 evidence_id，可回溯 %d 个'
                     % (ev_total, sum(1 for c in concl for e in c.get('evidence_ids', []) if e in records)))
    if findings:
        lines.append('- findings：')
        for f in findings:
            lines.append('    - [%s] %s：%s' % (f['level'], f['code'], f['msg']))
    else:
        lines.append('- findings：无阻断问题')
    lines.append('- 签署栏：本组（　　）｜对抗组（　　）｜教师（　　）')
    text = '\n'.join(lines)

    return {
        'run_id': run_id,
        'status': status,
        'mode': mode,
        'reason': reason,
        'llm_note': llm_note,
        'findings': findings,
        'text': text,
    }
