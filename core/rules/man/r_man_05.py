# -*- coding: utf-8 -*-
"""R-MAN-05 · 敏感广播监听（数据源：manifest）"""

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
        if facts.doc is not None and 0 < c.line_start <= len(facts.doc.lines):
            # 取元素完整文本区间（含 intent-filter 子元素），保证复核片段自含判定要素
            snippet = clip('\n'.join(
                facts.doc.lines[c.line_start - 1:c.line_end]), limit=500)
        labels = '、'.join('%s（%s）' % (a, registry.SENSITIVE_ACTIONS[a]) for a in found)
        hits.append(Hit(RULE_ID, loc, snippet,
                        note='静态注册监听敏感事件：%s' % labels))
    return hits
