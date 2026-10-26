# -*- coding: utf-8 -*-
"""R-MAN-03 · 明文流量许可（数据源：manifest + res_decoded）"""

from ..common import Hit

RULE_ID = "R-MAN-03"


def run(ctx):
    facts = ctx.manifest
    if facts is None:
        return []
    hits = []
    attrs = facts.app_attrs

    if attrs.get('usesCleartextTraffic') == 'true':
        loc = 'AndroidManifest.xml [application]'
        hits.append(Hit(RULE_ID, loc,
                        '<application android:usesCleartextTraffic="true" ...>',
                        note='显式开启明文流量许可'))

    nsc_present = 'networkSecurityConfig' in attrs
    if nsc_present:
        checked = False
        if ctx.res is not None and ctx.nsc_ref:
            rel, lines = ctx.res.find_xml(ctx.nsc_ref)
            if lines is not None:
                checked = True
                for idx, line in enumerate(lines, 1):
                    if 'cleartextTrafficPermitted="true"' in line:
                        hits.append(Hit(
                            RULE_ID, '%s:%d [base-config]' % (rel, idx),
                            line.strip(),
                            note='networkSecurityConfig 允许明文流量'))
        if not checked:
            ctx.rule_notes.append(
                '%s: networkSecurityConfig 已设置但内容未检查（res_decoded 不可用）' % RULE_ID)
    return hits
