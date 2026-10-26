# -*- coding: utf-8 -*-
"""R-CODE-02 · WebView 危险组合（数据源：smali_src）

三要素齐备才构成危险组合（缺一不算，good02 口径：仅启用 JS 不算）。
已知限制：不解析布尔实参（setJavaScriptEnabled(false) 亦计要素），记 changes.md 观察项。
"""

from ..common import Hit, clip, smali_loc

RULE_ID = "R-CODE-02"

ELEMENTS = {
    'addJavascriptInterface': 'Landroid/webkit/WebView;->addJavascriptInterface(',
    'setJavaScriptEnabled': 'Landroid/webkit/WebSettings;->setJavaScriptEnabled(',
    'setAllowFileAccess': 'Landroid/webkit/WebSettings;->setAllowFileAccess(',
}


def run(ctx):
    if ctx.smali is None:
        return []
    found = {}
    for rel in ctx.smali.app_files(ctx.app_package, ctx.rule_notes):
        lines = ctx.smali.read_lines(rel)
        for lineno, raw in enumerate(lines, 1):
            s = raw.strip()
            if not s or s.startswith('#'):
                continue
            if 'invoke-' not in s:
                continue
            for key, pat in ELEMENTS.items():
                if key not in found and pat in s:
                    found[key] = (rel, lineno, lines, s)
    if len(found) < 3:
        return []
    hits = []
    for key in ('addJavascriptInterface', 'setJavaScriptEnabled', 'setAllowFileAccess'):
        rel, lineno, lines, s = found[key]
        hits.append(Hit(
            RULE_ID, smali_loc(rel, lineno, lines), clip(s),
            note='WebView 危险组合要素：%s' % key))
    return hits
