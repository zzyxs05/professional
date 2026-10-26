# -*- coding: utf-8 -*-
"""R-PERM-01 · 定时/后台结构 × 敏感权限（数据源：smali_src）

证据两档（机械能力升级后，2026-10-15）：
  ① **调用链证据（强，已确认档）**：同一方法内存在调度原语，且该调度可解析到目标组件
     （const-class / Intent 类参数 / PendingIntent.getService|getActivity|getBroadcast 上下文），
     而目标组件内含敏感 API → 断言"存在定时/后台触发敏感组件的结构"（结构事实，非行为断言）。
  ② **样本级共存（弱，待复核档）**：调度结构与敏感 API 在样本内共存，但无可解析的调度目标
     → 疑点组合，措辞停在"疑点"，不得表述真实执行时间/实际滥用。
"""

import re

from ... import registry
from ..common import Hit, clip, smali_loc

RULE_ID = "R-PERM-01"

# const-class v2, Lcom/foo/Bar;   →  目标类描述符
_CONST_CLASS_RE = re.compile(r'const-class\s+[vp]\d+,\s*(L[\w$/.]+;)')
# .class public Lcom/foo/Bar;     →  本类描述符
_CLASS_LINE_RE = re.compile(r'^\.class\b.*?(L[\w$/.]+;)\s*$')


def _class_descriptor(lines):
    for raw in lines:
        s = raw.strip()
        if s.startswith('.class'):
            m = _CLASS_LINE_RE.match(s)
            if m:
                return m.group(1)
    return None


def _matched_primitive(s):
    for pat in registry.SCHEDULING_PRIMITIVES:
        if pat in s:
            return pat
    return '调度结构'


def run(ctx):
    if ctx.smali is None:
        return []
    app_files = ctx.smali.app_files(ctx.app_package, ctx.rule_notes)

    # 1) 敏感类表：类描述符 → [(rel, lineno, lines, 行文本, 分类)]
    sensitive = {}
    for rel in app_files:
        lines = ctx.smali.read_lines(rel)
        cls = _class_descriptor(lines)
        if not cls:
            continue
        for lineno, raw in enumerate(lines, 1):
            s = raw.strip()
            if not s or s.startswith('#'):
                continue
            if 'invoke-' not in s and 'new-instance' not in s:
                continue
            for pat, (cat, _p) in registry.SENSITIVE_APIS.items():
                if pat in s:
                    sensitive.setdefault(cls, []).append((rel, lineno, lines, s, cat))
                    break

    # 2) 按方法块扫描调度点与其可解析目标
    chain_hits = []
    sched_points = []
    for rel in app_files:
        lines = ctx.smali.read_lines(rel)
        for _sig, _name, _s_line, _e_line, body in ctx.smali.method_blocks(rel):
            sched = None
            for lineno, raw in body:
                s = raw.strip()
                if not s:
                    continue
                if (('invoke-' in s) or ('new-instance' in s)) and \
                        any(p in s for p in registry.SCHEDULING_PRIMITIVES):
                    sched = (lineno, s)
                    break
            if not sched:
                continue
            targets = []
            for lineno, raw in body:
                m = _CONST_CLASS_RE.search(raw.strip())
                if m:
                    targets.append((lineno, m.group(1), raw.strip()))
            linked = [(l, t, raw) for l, t, raw in targets if t in sensitive]
            if not linked:
                sched_points.append((rel, sched[0], lines, sched[1]))
                continue
            t_line, t_cls, t_raw = linked[0]
            s_rel, s_lineno, s_lines, s_raw, s_cat = sensitive[t_cls][0]
            chain_hits.extend([
                Hit(RULE_ID, smali_loc(rel, sched[0], lines), clip(sched[1]),
                    note='定时/后台调度点：%s' % _matched_primitive(sched[1])),
                Hit(RULE_ID, smali_loc(rel, t_line, lines), clip(t_raw),
                    note='调度目标组件：%s（该组件内存在敏感 API：%s）' % (t_cls, s_cat)),
                Hit(RULE_ID, smali_loc(s_rel, s_lineno, s_lines), clip(s_raw),
                    note='敏感 API：%s（位于被调度的组件 %s 内）' % (s_cat, t_cls)),
            ])

    # 3) 有调用链证据 → 已确认档（结构事实；仍不得断言实际执行时间/实际滥用）
    if chain_hits:
        return chain_hits

    # 4) 回退：样本级共存 → 待复核档（疑点组合）
    if not sched_points or not sensitive:
        return []
    hits = []
    for rel, lineno, lines, s in sched_points[:5]:
        hits.append(Hit(RULE_ID, smali_loc(rel, lineno, lines), clip(s),
                        note='调度原语：%s' % _matched_primitive(s),
                        max_status=registry.STATUS_REVIEW))
    for _cls, items in list(sensitive.items())[:3]:
        rel, lineno, lines, s, cat = items[0]
        hits.append(Hit(RULE_ID, smali_loc(rel, lineno, lines), clip(s),
                        note='敏感 API：%s' % cat,
                        max_status=registry.STATUS_REVIEW))
    return hits
