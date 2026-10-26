# -*- coding: utf-8 -*-
"""R-NET-02 · WebView SSL 错误忽略（数据源：smali_src）

命中：onReceivedSslError 方法体内调用 SslErrorHandler;->proceed()。
正确实现（handler.cancel()）不算（good02 口径）。
"""

from ..common import Hit, clip, smali_loc

RULE_ID = "R-NET-02"


def run(ctx):
    if ctx.smali is None:
        return []
    hits = []
    for rel in ctx.smali.app_files(ctx.app_package, ctx.rule_notes):
        lines = ctx.smali.read_lines(rel)
        for sig, name, _s_line, _e_line, body in ctx.smali.method_blocks(rel):
            if name != 'onReceivedSslError':
                continue
            for lineno, raw in body:
                s = raw.strip()
                if 'SslErrorHandler;->proceed()V' in s and 'invoke-' in s:
                    hits.append(Hit(
                        RULE_ID, smali_loc(rel, lineno, lines), clip(s),
                        note='onReceivedSslError 忽略 SSL 错误（proceed）'))
    return hits
