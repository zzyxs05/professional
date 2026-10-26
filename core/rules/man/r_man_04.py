# -*- coding: utf-8 -*-
"""R-MAN-04 · 调试与备份风险（数据源：manifest）"""

from ..common import Hit

RULE_ID = "R-MAN-04"


def run(ctx):
    facts = ctx.manifest
    if facts is None:
        return []
    hits = []
    attrs = facts.app_attrs

    if attrs.get('debuggable') == 'true':
        hits.append(Hit(RULE_ID, 'AndroidManifest.xml [application]',
                        '<application android:debuggable="true" ...>',
                        note='应用显式开启调试标记'))

    allow_backup = attrs.get('allowBackup')
    if allow_backup == 'true':
        hits.append(Hit(RULE_ID, 'AndroidManifest.xml [application]',
                        '<application android:allowBackup="true" ...>',
                        note='允许备份（未设置限制）'))
    elif allow_backup is None:
        hits.append(Hit(RULE_ID, 'AndroidManifest.xml [application]',
                        '<application ...>（未显式声明 allowBackup）',
                        note='未显式声明 allowBackup，Android 默认值 true'))
    return hits
