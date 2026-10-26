# -*- coding: utf-8 -*-
"""R-CODE-01 · 动态代码加载（数据源：smali_src 强模式 / dex_strings 弱模式）

- smali 自有代码中检出调用上下文（invoke/new-instance）→ 已确认
- 仅 dex 类型引用（smali 不可用时的降级）→ 待复核（弱证据）
"""

from ... import registry
from ..common import Hit, clip, smali_loc

RULE_ID = "R-CODE-01"

LOADER_PATTERNS = (
    'Ldalvik/system/DexClassLoader;',
    'Ldalvik/system/PathClassLoader;',
    'Ldalvik/system/InMemoryDexClassLoader;',
)
SYSTEM_LOAD_PATTERNS = (
    'Ljava/lang/System;->load(',
    'Ljava/lang/System;->loadLibrary(',
)


def run(ctx):
    hits = []
    if ctx.smali is not None:
        for rel in ctx.smali.app_files(ctx.app_package, ctx.rule_notes):
            lines = ctx.smali.read_lines(rel)
            for lineno, raw in enumerate(lines, 1):
                s = raw.strip()
                if not s or s.startswith('#'):
                    continue
                if 'invoke-' not in s and 'new-instance' not in s:
                    continue
                matched = None
                for pat in LOADER_PATTERNS + SYSTEM_LOAD_PATTERNS:
                    if pat in s:
                        matched = pat
                        break
                if matched:
                    hits.append(Hit(
                        RULE_ID, smali_loc(rel, lineno, lines), clip(s),
                        note='动态代码加载调用：%s' % matched,
                        max_status=registry.STATUS_CONFIRMED))
        if hits:
            return hits

    # 降级弱模式：仅 dex 类型引用（无调用上下文 → 待复核）
    if ctx.smali is None and ctx.dex is not None:
        for pat in LOADER_PATTERNS:
            if pat in ctx.dex.type_descriptors:
                hits.append(Hit(
                    RULE_ID, 'classes.dex#type[%s]' % pat, pat,
                    note='dex 类型引用（弱证据：无调用上下文）',
                    max_status=registry.STATUS_REVIEW))
    return hits
