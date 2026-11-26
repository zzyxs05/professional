# -*- coding: utf-8 -*-
"""R-MAN-02 · 危险权限声明（数据源：manifest）"""

from ... import registry
from ..common import Hit

RULE_ID = "R-MAN-02"


def run(ctx):
    facts = ctx.manifest
    if facts is None:
        return []
    hits = []
    # CHG-005：uses-permission 与 uses-permission-sdk-23 语义等价，
    # 同一权限用两种标签各声明一次时只出一条 Hit（不重复计数），
    # 证据片段用首次出现的真实标签，保证与 manifest 原文一致。
    seen = set()
    for p in facts.permissions:
        if p.name in seen:
            continue
        if registry.is_sensitive_permission(p.name):
            seen.add(p.name)
            label = registry.SENSITIVE_PERMISSIONS.get(p.name, '敏感权限')
            tag = getattr(p, 'tag', 'uses-permission')
            loc = 'AndroidManifest.xml:%d [%s]' % (p.line, tag)
            snippet = '<%s android:name="%s"/>' % (tag, p.name)
            hits.append(Hit(RULE_ID, loc, snippet,
                            note='声明敏感权限：%s（%s）' % (p.name, label)))
    return hits
