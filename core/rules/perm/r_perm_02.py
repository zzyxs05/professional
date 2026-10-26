# -*- coding: utf-8 -*-
"""R-PERM-02 · 非交互组件使用敏感 API（数据源：manifest + smali_src）"""

from ... import registry
from ..common import Hit, clip, smali_loc

RULE_ID = "R-PERM-02"


def run(ctx):
    facts = ctx.manifest
    smali = ctx.smali
    if facts is None or smali is None:
        return []
    hits = []
    for c in facts.components:
        if c.ctype not in ('service', 'receiver', 'provider'):
            continue
        rel = smali.class_index.get(c.name.replace('.', '/'))
        if not rel:
            continue
        lines = smali.read_lines(rel)
        for lineno, raw in enumerate(lines, 1):
            s = raw.strip()
            if not s or s.startswith('#'):
                continue
            if 'invoke-' not in s and 'new-instance' not in s:
                continue
            for pat, (cat, _p) in registry.SENSITIVE_APIS.items():
                if pat in s:
                    hits.append(Hit(
                        RULE_ID, smali_loc(rel, lineno, lines), clip(s),
                        note='非交互组件 %s（%s）中调用敏感 API：%s' % (c.name, c.ctype, cat)))
                    break
    return hits
