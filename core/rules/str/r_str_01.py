# -*- coding: utf-8 -*-
"""R-STR-01 · 硬编码凭据（数据源：dex_strings + res_decoded）

形式匹配即事实：示例值/形式值照报（真值口径），真伪判断交给人。
"""

import re

from ... import registry
from ..common import Hit, clip

RULE_ID = "R-STR-01"


def run(ctx):
    hits = []
    compiled = [(label, re.compile(rx)) for label, rx in registry.CREDENTIAL_PATTERNS]

    if ctx.dex is not None:
        for label, rx in compiled:
            for fact, _m in ctx.dex.find_strings(rx, limit=registry.MAX_HITS_PER_RULE):
                hits.append(Hit(
                    RULE_ID, fact.location, clip(fact.value),
                    note='凭据形式匹配：%s（dex 字符串常量）' % label))

    if ctx.res is not None:
        for name, value, rel, lineno in ctx.res.iter_string_values():
            for label, rx in compiled:
                if rx.search(value):
                    hits.append(Hit(
                        RULE_ID, '%s:%d [@string/%s]' % (rel, lineno, name), clip(value),
                        note='凭据形式匹配：%s（资源字符串）' % label))
                    break

    return hits[:registry.MAX_HITS_PER_RULE]
