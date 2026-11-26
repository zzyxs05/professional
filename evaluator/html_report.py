# -*- coding: utf-8 -*-
"""html_report.py · 评价结果 HTML 渲染（纯函数，不改判定、不打分）

分区纪律：
- 证据审查区（verdict zone）只依赖机械结果，同快照重跑逐字节一致，带 verdict_digest；
- 评测分区单独渲染，按课程框架 S1—S4 子项给出，标注「非最终成绩」，
  分数与模型文本不进判定区、不进 digest；
- 每项给出：人话描述、判定状态、扣分原因、完整证据链、最小补查。

任何字段缺失都如实显示「未做 / 缺证据」，不补造文字。
"""

import html
import json
import os

ZONE_START = '<!-- verdict:start -->'
ZONE_END = '<!-- verdict:end -->'


def esc(value):
    return html.escape('' if value is None else str(value), quote=True)


def _plain(criterion_id, rubric_by_id):
    item = rubric_by_id.get(criterion_id, {})
    return item.get('plain') or item.get('criterion') or '（该项无描述）'


def _status_label(status):
    return {
        'PASS': '通过',
        'FAIL': '未通过',
        'INSUFFICIENT_EVIDENCE': '证据不足',
        'NOT_APPLICABLE': '不适用',
    }.get(status, status or '未判定')


def _status_class(status):
    return {
        'PASS': 'ok',
        'FAIL': 'bad',
        'INSUFFICIENT_EVIDENCE': 'warn',
        'NOT_APPLICABLE': 'na',
    }.get(status, 'na')


def _fmt_value(value):
    if value is None:
        return '读不到'
    if isinstance(value, dict):
        bits = []
        for k, v in value.items():
            if isinstance(v, list):
                shown = '、'.join(str(x) for x in v) if v else '无'
            else:
                shown = str(v)
            bits.append('%s：%s' % (k, shown))
        return '；'.join(bits) if bits else '（空）'
    if isinstance(value, bool):
        return '是' if value else '否'
    return str(value)


def _score_block(finding, rubric_by_id):
    """建议分区：分数与理由来自模型建议，缺失时如实显示，不补造。"""
    sug = finding.get('score_suggestion')
    full = rubric_by_id.get(finding.get('criterion_id'), {}).get('weight_ref', '—')
    if not isinstance(sug, dict) or sug.get('score') is None:
        note = ''
        if isinstance(sug, dict) and sug.get('reason'):
            note = esc(sug['reason'])
        return ('<div class="score"><span class="muted">建议分</span> '
                '<b>未做</b><span class="muted"> / 满分 %s</span>%s</div>'
                % (esc(full), ('<div class="why">%s</div>' % note) if note else ''))
    score = sug.get('score')
    rationale = sug.get('rationale') or sug.get('reason') or '（未给出理由）'
    refs = sug.get('evidence_ids') or []
    ref_html = ''
    if refs:
        ref_html = ('<div class="why">引用的证据：%s</div>'
                    % esc('、'.join(str(x) for x in refs)))
    return ('<div class="score"><span class="muted">建议分</span> '
            '<b>%s</b><span class="muted"> / 满分 %s</span>'
            '<div class="why">理由：%s</div>%s</div>'
            % (esc(score), esc(full), esc(rationale), ref_html))


def _chain_html(chain):
    steps = (chain or {}).get('steps') or []
    if not steps:
        return '<p class="muted">无机械核对记录（未做字段级核对）</p>'
    rows = []
    for s in steps:
        status = s.get('status') or 'missing'
        rows.append(
            '<tr class="%s"><td>%s</td><td>%s</td><td>%s</td>'
            '<td>%s</td><td>%s</td><td>%s</td></tr>'
            % (_status_class(status) if status == 'mismatch' else esc(status),
               esc(s.get('step_id')), esc(s.get('question')),
               esc(s.get('path')), esc(s.get('expectation')),
               esc(_fmt_value(s.get('observed'))), esc(s.get('status_text'))))
    return ('<table class="chain"><thead><tr><th>字段</th><th>看什么</th><th>文件</th>'
            '<th>应满足</th><th>实际读到</th><th>结果</th></tr></thead><tbody>%s'
            '</tbody></table>' % ''.join(rows))


def _deduction_html(finding):
    """扣分原因：只从机械缺口事实生成，不用模型措辞替代事实。"""
    reasons = []
    fc = finding.get('field_check') or {}
    for f in fc.get('fields') or []:
        if f.get('status') == 'missing':
            obs = f.get('observed') or {}
            if 'missing_context' in obs:
                reasons.append('%s：缺上下文变量 %s，未核对'
                               % (f.get('id'), '、'.join(obs['missing_context'])))
            else:
                reasons.append('%s：文件读不到（%s）'
                               % (f.get('id'), f.get('path')))
        elif f.get('status') == 'mismatch':
            obs = f.get('observed') or {}
            miss = obs.get('missing_anchors')
            if miss:
                reasons.append('%s：缺少 %s' % (f.get('id'), '、'.join(miss)))
            else:
                reasons.append('%s：读到的值与期望不一致（%s）'
                               % (f.get('id'), _fmt_value(obs)))
    if not reasons:
        finding_text = finding.get('finding') or '（未记录原因）'
        reasons.append(str(finding_text))
    return '<ul>%s</ul>' % ''.join('<li>%s</li>' % esc(r) for r in reasons)


def render_verdict_zone(result, rubric=None):
    """只渲染判定区：输入只含机械字段，同快照重跑逐字节一致。"""
    rubric_by_id = {c.get('id'): c for c in (rubric or {}).get('criteria', [])}
    findings = result.get('findings') or []
    parts = []
    for i, finding in enumerate(findings, 1):
        cid = finding.get('criterion_id')
        status = finding.get('status')
        chain = finding.get('evidence_chain')
        if not chain:
            fc = finding.get('field_check') or {}
            chain = {'steps': []}
            for row in fc.get('fields') or []:
                spec = row.get('note') or '字段核对'
                chain['steps'].append({
                    'step_id': row.get('id'), 'question': spec,
                    'path': row.get('path_expanded'), 'expectation': '见字段规范',
                    'observed': row.get('observed'), 'status': row.get('status'),
                    'status_text': row.get('status'),
                })
        parts.append(
            '<section class="item"><div class="item-head">'
            '<span class="no">%d</span><span class="cid">%s</span>'
            '<span class="badge %s">%s</span></div>'
            '<p class="desc">%s</p>'
            '<div class="why"><b>扣分或未通过原因</b>%s</div>'
            '<details open><summary>完整证据链（%d 步）</summary>%s</details>'
            '<div class="why"><b>最小补查</b><span>%s</span></div>'
            '</section>'
            % (i, esc(cid), _status_class(status), esc(_status_label(status)),
               esc(_plain(cid, rubric_by_id)), _deduction_html(finding),
               len((chain or {}).get('steps') or []), _chain_html(chain),
               esc(finding.get('suggested_check') or '无')))
    digest = result.get('verdict_digest') or result.get('checker', {}).get('verdict_digest')
    head = ('<div class="digest">判定指纹：<code>%s</code>'
            '<span class="muted">（只含机械判定；同快照重跑应一致）</span></div>'
            % esc(digest or '未生成'))
    return ZONE_START + head + ''.join(parts) + ZONE_END


def render_score_header(result):
    """报告开头的醒目评分区：总分大字 + S1—S4 分组卡片 + 评分状态。"""
    scores = result.get('evaluation_scores') or []
    status = result.get('scoring_status') or 'pending_harness'
    groups = (
        ('S1', '项目工程成果', 45), ('S2', '工程实验与取舍', 15),
        ('S3', '评价 Agent 与交叉审查', 15), ('S4', '个人能力证明', 25),
    )
    cards = []
    for gid, gname, gmax in groups:
        items = [s for s in scores if str(s.get('subcriterion_id', '')).startswith(gid + '.')]
        got = sum(s['score'] for s in items if isinstance(s.get('score'), int))
        n = len(items)
        filled = sum(1 for s in items if isinstance(s.get('score'), int))
        pct = int(100 * got / gmax) if gmax else 0
        label = ('%d / %d' % (got, gmax)) if status == 'scored' else '待评'
        cards.append(
            '<div class="gcard"><div class="gname">%s</div>'
            '<div class="gnum">%s</div><div class="gbar"><span style="width:%d%%"></span></div>'
            '<div class="gsub">%s · %d 项</div></div>'
            % (esc(gname), esc(label), pct if status == 'scored' else 0,
               ('已评 %d/%d' % (filled, n)) if n else '无子项', n))
    known = [s['score'] for s in scores if isinstance(s.get('score'), int)]
    total = sum(known)
    if status == 'scored':
        big = ('<div class="big-score">%d<span>/100</span></div>' % total
               + '<div class="score-state">已评分 · %d/%d 项 · harness 依据证据满足度给出</div>'
               % (len(known), len(scores)))
    else:
        big = ('<div class="big-score pending">待评<span>/100</span></div>'
               '<div class="score-state">证据已备齐，等待 harness 逐项判断打分；本页不含分数</div>')
    return ('<section class="score-hero"><div class="hero-left">'
            '<h2>分项评测分</h2>%s'
            '<div class="hero-note">非课程最终成绩 · </div>'
            '</div><div class="hero-right">%s</div></section>'
            % (big, ''.join(cards)))


def render(result, rubric=None):
    """渲染整份 HTML。开头是评分区，其后是证据审查区与评分明细。"""
    rubric_by_id = {c.get('id'): c for c in (rubric or {}).get('criteria', [])}
    findings = result.get('findings') or []
    counts = {}
    for f in findings:
        counts[f.get('status')] = counts.get(f.get('status'), 0) + 1
    summary = '、'.join('%s %d' % (_status_label(k), v)
                        for k, v in sorted(counts.items()))
    model_note = ''
    obs = result.get('observations') or []
    if obs:
        model_note = ('<section class="model"><h2>模型观察（非最终成绩，不进判定）</h2><ul>%s</ul></section>'
                      % ''.join('<li>%s</li>' % esc(x) for x in obs[:20]))
    # 评测分区：按课程评分框架 S1—S4 子项列出，带满分、扣分理由、证据引用与层级。
    # 与证据审查区分离；分数不是课程最终成绩。
    scores = result.get('evaluation_scores') or []
    if scores:
        rows = []
        for s in scores:
            score = s.get('score')
            shown = '未评' if score is None else esc(score)
            level = s.get('evidence_level') or 'CLAIM_ONLY'
            level_label = {'STATIC': '静态证据', 'OBSERVED': '已观察',
                           'REPRODUCED': '已复现',
                           'CLAIM_ONLY': '仅自述'}.get(level, level)
            level_note = '（自述待核）' if level == 'CLAIM_ONLY' else ''
            rows.append('<tr><td>%s</td><td>%s / %s</td><td>%s</td>'
                        '<td>%s</td><td>%s %s</td></tr>'
                        % (esc(s.get('subcriterion_id')),
                           shown, esc(s.get('max', '—')),
                           esc(s.get('rationale') or '（未给出理由）'),
                           esc('、'.join(str(x) for x in (s.get('evidence_ids') or [])) or '无'),
                           esc(level_label), level_note))
        total_known = sum(s['score'] for s in scores if isinstance(s.get('score'), int))
        sug_html = (
            '<section><h2>分项评测分（S1—S4，非课程最终成绩）</h2>'
            '<p class="muted">共 %d 个子项，已评合计 %d / 100；未评项如实标「未评」，不猜分。<br>'
            '这是 <b>harness 看过证据后给的主观分</b>：按证据对该评分项的满足程度判断，'
            '扣分理由指到具体缺口；不是课程最终成绩。</p>'
            '<table class="summary"><thead><tr><th>子项</th><th>得分</th>'
            '<th>扣分理由</th><th>证据引用</th><th>证据层级</th></tr></thead>'
            '<tbody>%s</tbody></table></section>'
            % (len(scores), total_known, ''.join(rows)))
    else:
        sug_html = ('<section><h2>分项评测分</h2><p class="muted">'
                    '未做语义评分（确定性路径或模型降级）；不猜分、不编造。</p></section>')
    css = """
body{font-family:system-ui,-apple-system,"Segoe UI",sans-serif;color:#2c2c2a;background:#fff;line-height:1.6;margin:0;padding:24px;max-width:1080px;margin:0 auto}
h1{font-size:20px;font-weight:500;margin:0 0 4px}h2{font-size:15px;font-weight:500;margin:24px 0 8px}
.meta{color:#5f5e5a;font-size:13px;margin-bottom:16px}
.top{background:#f1efe8;border:1px solid #d3d1c7;padding:12px 16px;border-radius:8px;margin-bottom:16px}
.item{border:1px solid #d3d1c7;border-radius:8px;padding:14px 16px;margin-bottom:12px}
.item-head{display:flex;align-items:center;gap:10px}.no{color:#888780;font-size:12px}
.cid{font-weight:500;font-size:14px}.badge{font-size:12px;padding:2px 8px;border-radius:10px}
.badge.ok{background:#eaf3de;color:#3b6d11}.badge.bad{background:#fcebeb;color:#a32d2d}
.badge.warn{background:#faeeda;color:#854f0b}.badge.na{background:#f1efe8;color:#5f5e5a}
.desc{font-size:13px;margin:8px 0 12px;color:#2c2c2a}
.why{font-size:13px;margin:8px 0;color:#444441}.why b{font-weight:500}
.muted{color:#888780;font-size:12px}
.score{font-size:13px;background:#e6f1fb;border-radius:6px;padding:8px 10px;margin:8px 0}
.score b{font-size:16px;font-weight:500;color:#0c447c}
table{border-collapse:collapse;width:100%;font-size:12px;margin-top:6px}
th,td{border:1px solid #d3d1c7;padding:6px 8px;text-align:left;vertical-align:top}
th{background:#f1efe8;font-weight:500}td.mismatch{background:#fcebeb}
details summary{cursor:pointer;font-size:13px;font-weight:500;padding:6px 0}
.digest{font-size:12px;color:#5f5e5a;margin-bottom:12px}code{font-family:monospace}
.model{background:#f1efe8;border-radius:8px;padding:10px 16px}
.score-hero{display:flex;gap:20px;align-items:stretch;background:#e6f1fb;border:1px solid #b5d4f4;border-radius:12px;padding:18px 20px;margin-bottom:18px}
.hero-left{min-width:230px}.hero-left h2{margin:0 0 6px}.hero-note{font-size:12px;color:#5f5e5a;margin-top:8px}
.big-score{font-size:52px;font-weight:500;color:#0c447c;line-height:1.1}.big-score span{font-size:20px;color:#5f5e5a}
.big-score.pending{font-size:36px;color:#888780}
.score-state{font-size:12px;color:#185fa5;margin-top:4px}
.hero-right{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;flex:1}
.gcard{background:#fff;border:1px solid #b5d4f4;border-radius:8px;padding:10px 12px}
.gname{font-size:12px;color:#5f5e5a}.gnum{font-size:22px;font-weight:500;color:#0c447c;margin:2px 0}
.gbar{height:4px;background:#e6f1fb;border-radius:2px;overflow:hidden}.gbar span{display:block;height:100%;background:#378add}
.gsub{font-size:11px;color:#888780;margin-top:4px}
"""
    return ('<!DOCTYPE html>\n<html lang="zh-CN">\n<head><meta charset="utf-8">'
            '<title>评价报告 · %s</title><style>%s</style></head><body>'
            '<h1>工程证据审查报告</h1>'
            '<div class="meta">评价编号 %s ｜ 目标 %s ｜ 模式 %s ｜ 规则版本 %s</div>'
            '%s'
            '<div class="top">证据审查：%s ｜ 审查项 %d ｜ 结论状态 %s<br>'
            '执行方式 %s ｜ 模型交互 %s</div>'
            '%s%s%s%s</body></html>'
            % (esc(result.get('eval_id') or '未编号'), css,
               esc(result.get('eval_id') or '未编号'),
               esc(result.get('target') or '未提供'),
               esc(result.get('mode') or '未知'),
               esc((result.get('versions') or {}).get('rule_pack') or '未绑定'),
               render_score_header(result),
               esc(summary or '无审查项'), len(findings),
               esc(_status_label(result.get('status'))),
               esc((result.get('model') or {}).get('mode') or '未知'),
               esc((result.get('budget') or {}).get('model_calls_used', '—')),
               render_verdict_zone(result, rubric), sug_html, model_note,
               '<p class="muted">本报告为工程证据审查，不是成绩单；评价器不产出最终成绩。'
               '证据审查区由机械核对收口；分项评测分按课程框架逐项给出。</p>'))


def write_html(result, rubric, path):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(render(result, rubric))
    return path
