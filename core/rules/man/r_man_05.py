# -*- coding: utf-8 -*-
"""R-MAN-05 · 敏感广播监听（数据源：manifest）"""

import re

from ... import registry
from ..common import Hit, clip

RULE_ID = "R-MAN-05"


def run(ctx):
    facts = ctx.manifest
    if facts is None:
        return []
    hits = []
    for c in facts.components_by_type('receiver'):
        found = [a for a in c.actions if a in registry.SENSITIVE_ACTIONS]
        if not found:
            continue
        loc = 'AndroidManifest.xml:%d-%d [receiver %s]' % (
            c.line_start, c.line_end, c.name)
        snippet = ''
        element_text = ''
        if facts.doc is not None and 0 < c.line_start <= len(facts.doc.lines):
            # 取元素完整文本区间（含 intent-filter 子元素），保证复核片段自含判定要素
            element_text = '\n'.join(
                facts.doc.lines[c.line_start - 1:c.line_end])
            snippet = clip(element_text, limit=500)
        labels = '、'.join('%s（%s）' % (a, registry.SENSITIVE_ACTIONS[a]) for a in found)

        # 0.1.7（F-03）：enabled="false" 的组件不接收任何广播，
        # 报"已确认"是误报；降为待复核并在 notes 里写明禁用状态。
        disabled = bool(re.search(
            r'android:enabled\s*=\s*["\']false["\']', element_text, re.I))
        if disabled:
            hits.append(Hit(
                RULE_ID, loc, snippet,
                note=('静态注册监听敏感事件：%s；但 android:enabled="false" '
                      '（组件禁用，不接收广播，仅结构共存）' % labels),
                max_status=registry.STATUS_REVIEW))
        else:
            hits.append(Hit(RULE_ID, loc, snippet,
                            note='静态注册监听敏感事件：%s' % labels))
    return hits
