# -*- coding: utf-8 -*-
"""R-MAN-01 · 导出组件无权限保护（数据源：manifest）"""

from ..common import Hit, clip

RULE_ID = "R-MAN-01"


def run(ctx):
    facts = ctx.manifest
    if facts is None:
        return []
    hits = []
    for c in facts.components:
        explicit_exported = c.exported is True
        implicit_exported = (c.exported is None and c.has_intent_filter)
        if not explicit_exported and not implicit_exported:
            continue
        protection = c.permission or c.read_permission or c.write_permission
        if protection:
            continue  # 有权限保护的导出组件不算（good02 口径）
        if explicit_exported:
            why = 'android:exported="true"'
        else:
            why = '含 intent-filter 且未声明 exported（隐式导出）'
        loc = 'AndroidManifest.xml:%d-%d [%s %s]' % (
            c.line_start, c.line_end, c.ctype, c.name)
        snippet = ''
        if facts.doc is not None and 0 < c.line_start <= len(facts.doc.lines):
            # 取元素完整文本区间（子元素可能承载 permission 相关信息的场景），500 字截断
            snippet = clip('\n'.join(
                facts.doc.lines[c.line_start - 1:c.line_end]), limit=500)
        hits.append(Hit(
            RULE_ID, loc, snippet,
            note='导出组件 %s 无权限保护（%s）' % (c.name, why)))
        if len(hits) >= 50:
            break
    return hits
