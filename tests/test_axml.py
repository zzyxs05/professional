# -*- coding: utf-8 -*-
"""test_axml.py · AXML 直读解析测试（合成夹具，不依赖真实 APK）"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.fixtures.axml_builder import ANDROID_NS, Attr, AxmlBuilder, Node
from core.axml import parse_manifest_bytes


def build_sample():
    b = AxmlBuilder()
    root = Node('manifest', line=1, attrs=[
        Attr('package', ('string', 'com.test.app')),
    ])
    perm = Node('uses-permission', line=3, attrs=[
        Attr('name', ('string', 'android.permission.CAMERA'), ns=ANDROID_NS),
    ])
    perm2 = Node('uses-permission', line=4, attrs=[
        Attr('name', ('string', 'android.permission.INTERNET'), ns=ANDROID_NS),
    ])
    app = Node('application', line=5, attrs=[
        Attr('debuggable', ('bool', True), ns=ANDROID_NS),
        Attr('allowBackup', ('bool', False), ns=ANDROID_NS),
        Attr('usesCleartextTraffic', ('bool', True), ns=ANDROID_NS),
    ])
    act = Node('activity', line=7, attrs=[
        Attr('name', ('string', 'com.test.app.MainActivity'), ns=ANDROID_NS),
        Attr('exported', ('bool', True), ns=ANDROID_NS),
    ])
    svc = Node('service', line=8, attrs=[
        Attr('name', ('string', '.SyncService'), ns=ANDROID_NS),
        Attr('exported', ('bool', True), ns=ANDROID_NS),
        Attr('permission', ('string', 'com.test.app.PERM'), ns=ANDROID_NS),
    ])
    rcv = Node('receiver', line=9, attrs=[
        Attr('name', ('string', '.BootReceiver'), ns=ANDROID_NS),
        Attr('exported', ('bool', True), ns=ANDROID_NS),
    ])
    flt = Node('intent-filter', line=10)
    act_el = Node('action', line=11, attrs=[
        Attr('name', ('string', 'android.intent.action.BOOT_COMPLETED'), ns=ANDROID_NS),
    ])
    flt.children = [act_el]
    rcv.children = [flt]
    app.children = [act, svc, rcv]
    root.children = [perm, perm2, app]
    return b.build(root)


class TestAxml(unittest.TestCase):
    def setUp(self):
        self.data = build_sample()
        self.doc, self.facts = parse_manifest_bytes(self.data)

    def test_package(self):
        self.assertEqual(self.facts.package, 'com.test.app')

    def test_permissions(self):
        names = [p.name for p in self.facts.permissions]
        self.assertEqual(names, ['android.permission.CAMERA', 'android.permission.INTERNET'])

    def test_app_attrs(self):
        self.assertEqual(self.facts.app_attrs.get('debuggable'), 'true')
        self.assertEqual(self.facts.app_attrs.get('allowBackup'), 'false')
        self.assertEqual(self.facts.app_attrs.get('usesCleartextTraffic'), 'true')

    def test_components(self):
        comps = {c.name: c for c in self.facts.components}
        self.assertIn('com.test.app.MainActivity', comps)
        self.assertIn('com.test.app.SyncService', comps)   # .SyncService 展开
        self.assertIn('com.test.app.BootReceiver', comps)
        main = comps['com.test.app.MainActivity']
        self.assertTrue(main.exported)
        self.assertIsNone(main.permission)
        svc = comps['com.test.app.SyncService']
        self.assertEqual(svc.permission, 'com.test.app.PERM')
        rcv = comps['com.test.app.BootReceiver']
        self.assertEqual(rcv.actions, ['android.intent.action.BOOT_COMPLETED'])
        self.assertTrue(rcv.has_intent_filter)

    def test_rebuilt_xml_lines(self):
        text = self.doc.rebuilt_xml
        self.assertIn('<manifest', text)
        rcv_line = None
        for i, line in enumerate(self.doc.lines, 1):
            if 'BootReceiver' in line:
                rcv_line = i
                break
        self.assertIsNotNone(rcv_line)
        rcv = [c for c in self.facts.components if c.name.endswith('BootReceiver')][0]
        self.assertEqual(rcv.line_start, rcv_line)
        self.assertLess(rcv.line_start, rcv.line_end)  # 含 intent-filter 子元素

    def test_rules_on_fixture(self):
        from core.rules.man import r_man_01, r_man_04, r_man_05
        from core.rules.man import r_man_02

        class Ctx(object):
            manifest = self.facts
            res = None
            rule_notes = []

        ctx = Ctx()
        hits01 = r_man_01.run(ctx)
        names = ' '.join(h.location for h in hits01)
        self.assertIn('MainActivity', names)
        self.assertNotIn('SyncService', names)   # 有 permission 保护 → 安静
        hits02 = r_man_02.run(ctx)
        self.assertEqual(len(hits02), 1)          # 仅 CAMERA 敏感，INTERNET 不算
        hits04 = r_man_04.run(ctx)
        self.assertEqual(len(hits04), 1)          # debuggable=true；allowBackup=false 不算
        hits05 = r_man_05.run(ctx)
        self.assertEqual(len(hits05), 1)


if __name__ == '__main__':
    unittest.main()
