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


# 0.1.8（CHG-006 / V-1）：跨方法 Runnable 链解析。
# 只追"静态可解析"的调用，最多两跳；invoke-interface / 反射 / 动态类名一律停。
_NEW_INSTANCE_RE = re.compile(r'new-instance\s+[vp]\d+,\s*(L[\w$/.]+;)')
_INVOKE_METHOD_RE = re.compile(r'invoke-(?:static|direct|virtual)\s+[^,]*,\s*L[\w$/.]+;\->([\-A-Za-z0-9_$]+)')


def _nest_plain(name):
    """ shed synthetic bridge 前缀： -$$Nest$mstartRecordingService → startRecordingService """
    if name.startswith('-$'):
        m = re.search(r'\$(m|s?)?([A-Za-z0-9_]+)$', name)
        return m.group(2) if m else name
    return name


def _method_index(app_files, ctx):
    """全 app 方法索引：方法名 → [(rel, sig, body)]；类名 → rel。"""
    by_name = {}
    by_cls = {}
    for rel in app_files:
        blocks = ctx.smali.method_blocks(rel)
        for _sig, name, _s, _e, body in blocks:
            by_name.setdefault(name, []).append((rel, _sig, body))
            plain = _nest_plain(name)
            if plain != name:
                by_name.setdefault(plain, []).append((rel, _sig, body))
        cls = _class_descriptor(ctx.smali.read_lines(rel))
        if cls:
            by_cls[cls] = rel
    return by_name, by_cls


def _resolve_cross_method(ctx, body, by_name, by_cls, sensitive, max_hops=2):
    """从调度方法体里解析 Runnable → run() → 目标方法 → const-class 组件。

    返回 (目标类, 证据行列表) 或 (None, [])。只追静态可解析调用，限 max_hops 跳。
    """
    for _lineno, raw in body:
        s = raw.strip()
        if 'invoke-interface' in s:
            return None, []  # 动态分派：能力边界，停
    # 第一跳：从调度行（postDelayed 等）往上找它实际传入的匿名 Runnable 类。
    # 不能简单取第一个含 $ 的 new-instance——onCreate 里可能有多个（JsBridge 等）。
    sched_idx = None
    for i, (_lineno, raw) in enumerate(body):
        if any(p in raw for p in registry.SCHEDULING_PRIMITIVES):
            sched_idx = i
            break
    runnable = None
    if sched_idx is not None:
        for _lineno, raw in reversed(body[max(0, sched_idx - 8):sched_idx + 1]):
            m = _NEW_INSTANCE_RE.search(raw.strip())
            if m and '$' in m.group(1):
                runnable = m.group(1)
                break
    if not runnable or runnable not in by_cls:
        return None, []
    rel = by_cls[runnable]
    run_blocks = [b for b in ctx.smali.method_blocks(rel) if b[1] == 'run']
    if not run_blocks:
        return None, []
    chain = [(rel, run_blocks[0][2], 'Runnable.run()：%s' % runnable)]

    # 第二跳：run() 里 invoke- 的目标方法（剥 bridge 前缀）
    target_name = None
    for lineno, raw in run_blocks[0][4]:
        m = _INVOKE_METHOD_RE.search(raw.strip())
        if m:
            target_name = _nest_plain(m.group(1))
            break
    if not target_name:
        return None, []
    targets = by_name.get(target_name, [])
    if not targets or max_hops < 2:
        return None, []

    for t_rel, _sig, t_body in targets:
        for lineno, raw in t_body:
            m = _CONST_CLASS_RE.search(raw.strip())
            if not m or m.group(1) not in sensitive:
                continue
            chain.append((t_rel, t_body, '跨方法链：%s → %s → %s'
                          % (runnable, target_name, m.group(1))))
            return m.group(1), chain
    return None, []



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

    # 2a) 0.1.8：建全 app 方法索引，供跨方法链解析（V-1）
    by_name, by_cls = _method_index(app_files, ctx)

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
                # 0.1.8（V-1）：同方法无目标时，试跨方法 Runnable 链；
                # 静态可解析且目标类含敏感 API 才升档，否则保留待复核并记边界。
                cls, cross_chain = _resolve_cross_method(ctx, body, by_name, by_cls, sensitive)
                if cls:
                    s_rel, s_lineno, s_lines, s_raw, s_cat = sensitive[cls][0]
                    chain_hits.extend([
                        Hit(RULE_ID, smali_loc(rel, sched[0], lines), clip(sched[1]),
                            note='定时/后台调度点：%s' % _matched_primitive(sched[1])),
                        Hit(RULE_ID, smali_loc(s_rel, s_lineno, s_lines), clip(s_raw),
                            note='跨方法链目标组件：%s（存在敏感 API：%s）' % (cls, s_cat)),
                    ])
                    for c_rel, c_body, c_note in cross_chain[1:]:
                        chain_hits.append(Hit(
                            RULE_ID, smali_loc(c_rel, c_body[0][0] if c_body else 1,
                                               ctx.smali.read_lines(c_rel)),
                            clip(c_body[0][1]) if c_body else '', note=c_note))
                    continue
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
    # 0.1.7（F-05）：无链回退时声明能力边界——复核者要能分清
    # "查过但接口/回调目标未解析" 与 "根本没查"。
    unresolved_targets = []
    for rel, lineno, lines, s in sched_points:
        if any(tok in s for tok in ('->', 'invoke-interface')):
            unresolved_targets.append(smali_loc(rel, lineno, lines))
    boundary = None
    if unresolved_targets:
        boundary = ('存在不可直接解析的调度目标（%s 等），'
                    'Runnable/接口回调/动态类名的跨方法链未解析'
                    % unresolved_targets[0])

    for rel, lineno, lines, s in sched_points[:5]:
        hits.append(Hit(RULE_ID, smali_loc(rel, lineno, lines), clip(s),
                        note='调度原语：%s' % _matched_primitive(s),
                        max_status=registry.STATUS_REVIEW,
                        context=boundary or ''))
    for _cls, items in list(sensitive.items())[:3]:
        rel, lineno, lines, s, cat = items[0]
        hits.append(Hit(RULE_ID, smali_loc(rel, lineno, lines), clip(s),
                        note='敏感 API：%s' % cat,
                        max_status=registry.STATUS_REVIEW))
    return hits
