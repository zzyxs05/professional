# -*- coding: utf-8 -*-
"""scoring.py · 评分证据包生成器（不打分）

纪律：
- 机械层只负责把证据原文片段摆到 harness 面前，不计算分数、不判断质量；
- 分数由执行评价的 harness（agent）看过证据后主观给出，按「证据满足度」判断；
- 每个子项附：字段核对结果 + 原文片段 + 期望，让判断有据可查；
- S4 个人能力只有文档自述时标 CLAIM_ONLY，提示 harness 不能当已确认。

证据包写入评价 JSON 的 evidence_pack 字段；harness 据此评分后，
按评价输出 next_action.submit 描述的接口把分数回填到同一份 JSON。
模块不规定回填的命令行或工具。
"""

import json
import os

from .fieldcheck import check_field
from .checker import FieldReader, derive_allowlist, load_json

SCORING_FIELDS_PATH = os.path.join(os.path.dirname(__file__), 'skills',
                                   'evidence-review', 'scoring-fields.json')
EXCERPT_LIMIT = 1200


def load_scoring_fields(path=None):
    return load_json(path or SCORING_FIELDS_PATH)


def _excerpt(full, expect=None, limit=EXCERPT_LIMIT):
    """取原文片段：优先包含锚点的段落，否则取文件开头。只读，不改内容。"""
    if full is None or not os.path.isfile(full):
        return None
    try:
        with open(full, 'r', encoding='utf-8', errors='replace') as f:
            text = f.read()
    except OSError:
        return None
    if expect:
        for anchor in expect:
            i = text.find(anchor)
            if i >= 0:
                start = max(0, i - 200)
                return text[start:start + limit]
    return text[:limit]


def build_evidence_pack(spec, target_root, context=None, rubric=None):
    """为每个评分子项收集证据原文片段，返回证据包；不含任何分数。"""
    context = dict(context or {})
    exact, prefixes = derive_allowlist({'criteria': [
        {'fields': sc.get('fields', [])}
        for sc in spec.get('subcriteria', [])
    ]}, context)
    reader = FieldReader(target_root, exact, prefixes)

    rubric_sc = ((rubric or {}).get('evaluation_scoring') or {})
    declared = {s['id']: s for s in rubric_sc.get('subcriteria', [])}
    subcriteria = []
    for sc in spec.get('subcriteria', []):
        sid = sc.get('subcriterion_id')
        max_score = int(declared.get(sid, {}).get('max', sc.get('max', 0)))
        evidence = []
        for f in sc.get('fields', []):
            row = check_field(f, reader, context=context)
            full = reader._safe_path(row.get('path_expanded') or f.get('path', ''))
            excerpt = _excerpt(full, f.get('expect'))
            evidence.append({
                'field_id': f.get('id'),
                'question': f.get('note') or '字段核对',
                'path': row.get('path_expanded') or f.get('path'),
                'kind': f.get('kind'),
                'expect': f.get('expect') or f.get('json_path')
                          or f.get('lhs') or '见字段规范',
                'status': row.get('status'),
                'observed': row.get('observed'),
                'excerpt': excerpt,
            })
        subcriteria.append({
            'subcriterion_id': sid,
            'max': max_score,
            'evidence_refs': sc.get('evidence_refs', []),
            'evidence_level': sc.get('evidence_level') or 'STATIC',
            'note': sc.get('note'),
            'evidence': evidence,
        })
    return {
        'id': spec.get('id'),
        'version': spec.get('version'),
        'target': os.path.abspath(target_root),
        'context': context,
        'scoring_framework': rubric_sc.get('framework'),
        'subcriteria': subcriteria,
        'instruction': (
            '这是证据包，不是评分。harness 请逐子项阅读 evidence 里的原文片段，'
            '按「证据对该项的满足程度」主观打分（0..max），写清扣分理由与引用的证据路径。'
            '证据不足不猜分，给 null 并说明缺什么。S4 自述只到 CLAIM_ONLY，不能当已确认。'),
    }


def build_from_project(target_root, context=None, rubric=None, fields_path=None):
    return build_evidence_pack(load_scoring_fields(fields_path), target_root,
                               context, rubric)


def validate_scores(scores, pack):
    """校验 harness 提交的分数：只接受已知子项、0..max 整数或 null、带理由。"""
    max_by_id = {s['subcriterion_id']: s['max']
                 for s in pack.get('subcriteria', [])}
    out = []
    for sid, item in (scores or {}).items():
        if sid not in max_by_id or not isinstance(item, dict):
            continue
        score = item.get('score')
        if score is not None:
            try:
                score = int(score)
            except (TypeError, ValueError):
                score = None
            if score is not None and not (0 <= score <= max_by_id[sid]):
                score = None
        rationale = str(item.get('rationale') or '')[:800]
        if not rationale:
            rationale = '未给出理由（harness 提交时遗漏）'
        refs = [str(x) for x in (item.get('evidence_ids') or [])][:12]
        out.append({
            'subcriterion_id': sid,
            'score': score,
            'max': max_by_id[sid],
            'rationale': rationale,
            'evidence_ids': refs,
            'evidence_level': str(item.get('evidence_level') or 'STATIC'),
            'note': 'harness 依据证据满足度给出；非课程最终成绩',
        })
    order = {s['subcriterion_id']: i for i, s in
             enumerate(pack.get('subcriteria', []))}
    out.sort(key=lambda x: order.get(x['subcriterion_id'], 999))
    return out
