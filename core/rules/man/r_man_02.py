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
    for p in facts.permissions:
        if registry.is_sensitive_permission(p.name):
            label = registry.SENSITIVE_PERMISSIONS.get(p.name, '敏感权限')
            loc = 'AndroidManifest.xml:%d [uses-permission]' % p.line
            snippet = '<uses-permission android:name="%s"/>' % p.name
            hits.append(Hit(RULE_ID, loc, snippet,
                            note='声明敏感权限：%s（%s）' % (p.name, label)))
    return hits
