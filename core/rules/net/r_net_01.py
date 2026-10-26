# -*- coding: utf-8 -*-
"""R-NET-01 · 证书校验绕过结构（数据源：smali_src）

危险结构（任一）：
  ① X509TrustManager 实现的 checkClientTrusted / checkServerTrusted 为空方法体（无实质指令）
  ② getAcceptedIssuers 返回空数组
  ③ HostnameVerifier 实现 verify 恒 true（无 invoke，返回常量真）
  ④ 自定义 SSLSocketFactory 子类
判据基础：smali 方法体指令级（正确实现必有委托 invoke，good02 口径）。
"""

from ... import registry
from ..common import (Hit, class_interfaces, clip, effective_ops,
                      is_const_true_return, is_empty_array_return,
                      is_empty_method_body, smali_loc)

RULE_ID = "R-NET-01"


def run(ctx):
    if ctx.smali is None:
        return []
    hits = []
    install_sites = []

    for rel in ctx.smali.app_files(ctx.app_package, ctx.rule_notes):
        lines = ctx.smali.read_lines(rel)
        top = class_interfaces(lines)
        is_trustmgr_class = any('Ljavax/net/ssl/X509TrustManager;' in l for l in top)
        is_hostverifier_class = any('Ljavax/net/ssl/HostnameVerifier;' in l for l in top)
        is_sslfactory_sub = any(
            l.startswith('.super') and 'Ljavax/net/ssl/SSLSocketFactory;' in l for l in top)

        if is_sslfactory_sub:
            hits.append(Hit(RULE_ID, '%s:1 [class]' % rel,
                            top and clip('; '.join(top)) or '',
                            note='自定义 SSLSocketFactory 子类（替换系统实现）'))

        if is_trustmgr_class or is_hostverifier_class:
            for sig, name, _s_line, _e_line, body in ctx.smali.method_blocks(rel):
                ops = effective_ops(body)
                if not ops:
                    continue
                if name in ('checkClientTrusted', 'checkServerTrusted') and is_trustmgr_class:
                    if is_empty_method_body(ops):
                        hits.append(Hit(
                            RULE_ID, smali_loc(rel, ops[0][0], lines), clip(sig),
                            note='X509TrustManager.%s 空实现（证书校验被跳过）' % name))
                elif name == 'getAcceptedIssuers' and is_trustmgr_class:
                    if is_empty_array_return(ops):
                        hits.append(Hit(
                            RULE_ID, smali_loc(rel, ops[0][0], lines), clip(sig),
                            note='X509TrustManager.getAcceptedIssuers 返回空数组'))
                elif name == 'verify' and is_hostverifier_class and 'Ljavax/net/ssl/SSLSession;' in sig:
                    if is_const_true_return(ops):
                        hits.append(Hit(
                            RULE_ID, smali_loc(rel, ops[0][0], lines), clip(sig),
                            note='HostnameVerifier.verify 返回恒真（域名校验被跳过）'))

        for lineno, raw in enumerate(lines, 1):
            s = raw.strip()
            if 'Ljavax/net/ssl/SSLContext;->init(' in s and 'invoke-' in s:
                install_sites.append((rel, lineno, lines))

    if hits and install_sites:
        r0, l0, ln0 = install_sites[0]
        hits[0].note += '；检测到安装点 %s' % smali_loc(r0, l0, ln0)
    return hits
