# -*- coding: utf-8 -*-
"""R-STR-02 · 内网/明文端点（数据源：dex_strings + res_decoded）"""

import re

from ... import registry
from ..common import Hit, clip

RULE_ID = "R-STR-02"


def run(ctx):
    hits = []
    rx = re.compile(registry.INTERNAL_URL_PATTERN)

    if ctx.dex is not None:
        for fact, _m in ctx.dex.find_strings(rx, limit=registry.MAX_HITS_PER_RULE):
            hits.append(Hit(
                RULE_ID, fact.location, clip(fact.value),
                note='内网/明文端点（dex 字符串常量）'))

    if ctx.res is not None:
        for name, value, rel, lineno in ctx.res.iter_string_values():
            if rx.search(value):
                hits.append(Hit(
                    RULE_ID, '%s:%d [@string/%s]' % (rel, lineno, name), clip(value),
                    note='内网/明文端点（资源字符串）'))

    return hits[:registry.MAX_HITS_PER_RULE]
