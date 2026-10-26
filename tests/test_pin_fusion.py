# -*- coding: utf-8 -*-
"""test_pin_fusion.py · 钉证据与融合层测试（合成事实）"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import fusion, registry
from core.rules.common import Hit
from tests.fixtures.axml_builder import ANDROID_NS, Attr, AxmlBuilder, Node
from core.axml import parse_manifest_bytes


class FakeCtx(object):
    def __init__(self, manifest=None, package='com.test.app', dex=None, smali=None, res=None):
        self.manifest = manifest
        self.app_package = package
        self.dex = dex
        self.smali = smali
        self.res = res


def build_manifest_facts():
    b = AxmlBuilder()
    root = Node('manifest', line=1, attrs=[Attr('package', ('string', 'com.test.app'))])
    perm1 = Node('uses-permission', line=3, attrs=[
        Attr('name', ('string', 'android.permission.RECORD_AUDIO'), ns=ANDROID_NS)])
    perm2 = Node('uses-permission', line=4, attrs=[
        Attr('name', ('string', 'android.permission.INTERNET'), ns=ANDROID_NS)])
    app = Node('application', line=5, attrs=[
        Attr('usesCleartextTraffic', ('bool', True), ns=ANDROID_NS)])
    act = Node('activity', line=7, attrs=[
        Attr('name', ('string', 'com.test.app.LeakyActivity'), ns=ANDROID_NS),
        Attr('exported', ('bool', True), ns=ANDROID_NS),
    ])
    app.children = [act]
    root.children = [perm1, perm2, app]
    _doc, facts = parse_manifest_bytes(b.build(root))
    return facts


class TestPinEvidence(unittest.TestCase):
    def setUp(self):
        self.ctx = FakeCtx(manifest=build_manifest_facts())

    def test_pin_component(self):
        # 组件导出且无权限 + 机械命中（R-MAN-01）→ 钉成功
        r = fusion.pin_evidence(self.ctx, 'LeakyActivity 组件导出且无权限保护', '', 'R-MAN-01')
        self.assertEqual(r['status'], 'pinned')
        self.assertEqual(r['rules'][0]['rule_id'], 'R-MAN-01')

    def test_pin_attr(self):
        r = fusion.pin_evidence(self.ctx, '应用开启了明文流量', '', 'R-MAN-03')
        self.assertEqual(r['status'], 'pinned')

    def test_pin_fail_vague(self):
        # 推测型、无法映射 → 钉失败（不得升级）
        r = fusion.pin_evidence(self.ctx, '该应用可能存在后门行为', '', '')
        self.assertEqual(r['status'], 'unpinned')

    def test_pin_rejects_unrelated_entity(self):
        # bad02 场景回归：claim 谈 INTERNET（样本存在但非本条断言对象），
        # 机械命中却是 RECORD_AUDIO → 实体不被覆盖 → 拒绝钉证
        r = fusion.pin_evidence(
            self.ctx, '应用仅申请 INTERNET 权限，存在隐藏网络外联/数据外发风险', '', 'R-042')
        self.assertEqual(r['status'], 'unpinned')
        self.assertIn('实体', r['detail'])

    def test_pin_sensitive_entity_matched(self):
        claim = '声明了 RECORD_AUDIO 录音权限，存在环境窃听风险'
        r = fusion.pin_evidence(self.ctx, claim, '', '')
        self.assertEqual(r['status'], 'pinned')
        self.assertEqual(r['rules'][0]['rule_id'], 'R-MAN-02')

    def test_pin_rule_guess_requires_mechanical_hit(self):
        # guess 合法但机械未命中 → 钉失败
        r = fusion.pin_evidence(self.ctx, '某个内网地址 http://192.168.9.9 被使用', '', 'R-STR-02')
        self.assertEqual(r['status'], 'unpinned')  # fixture 无该字符串，检索不命中


class TestBuildConclusions(unittest.TestCase):
    def test_tier_cap_by_rule(self):
        # 融合层档位 = 该规则的 max_status（不越权；动态取值，档位调整不会让测试假失败）
        rid = 'R-PERM-03'
        hits = {rid: [Hit(rid, 'x.smali:1', 'snippet')]}
        concl, _obs = fusion.build_conclusions(hits)
        self.assertEqual(concl[0]['status'], registry.RULE_META[rid]['max_status'])

    def test_hit_level_cap_below_rule(self):
        # hit 标注低于规则上限时，取更低档（弱证据不得被规则上限拉高）
        rid = 'R-PERM-03'
        hits = {rid: [Hit(rid, 'x.smali:1', 'snippet', max_status=registry.STATUS_REVIEW)]}
        concl, _obs = fusion.build_conclusions(hits)
        self.assertEqual(concl[0]['status'], registry.STATUS_REVIEW)

    def test_tier_min_with_hit_override(self):
        hits = {'R-CODE-01': [Hit('R-CODE-01', 'classes.dex#type', 'x',
                                  max_status=registry.STATUS_REVIEW)]}
        concl, _obs = fusion.build_conclusions(hits)
        code01 = [c for c in concl if c['criterion_id'] == 'R-CODE-01'][0]
        self.assertEqual(code01['status'], registry.STATUS_REVIEW)

    def test_b2_unpinned_stays_review(self):
        class BRes(object):
            ran = True
            b1 = {}
            b2 = [{'claim': '某处存在可疑行为但无具体对象', 'location': '', 'rule_guess': 'R-FAKE'}]
        concl, obs = fusion.build_conclusions({}, {}, BRes())
        self.assertEqual(obs, [])
        self.assertEqual(len(concl), 1)
        self.assertEqual(concl[0]['status'], registry.STATUS_REVIEW)
        self.assertTrue(concl[0]['missing_evidence'])

    def test_b2_pinned_backfill_respects_cap(self):
        # 钉成功补盲：档位取规则上限（R-PERM-01 仍为待复核，不越权）
        def pin_fn(guess, pt):
            return {'status': 'pinned', 'detail': 'ok', 'locations': ['x'],
                    'rules': [{'rule_id': 'R-PERM-03', 'locations': ['x.smali:9'],
                               'note': '权限声明与使用不一致', 'evidence_ids': ['EV-X-1']}]}

        class BRes(object):
            ran = True
            b1 = {}
            b2 = [{'claim': '声明了权限但代码中未发现使用', 'location': 'x', 'rule_guess': 'R-PERM-03'}]

        concl, _obs = fusion.build_conclusions({}, {}, BRes(), pin_fn=pin_fn)
        self.assertEqual(len(concl), 1)
        self.assertEqual(concl[0]['criterion_id'], 'R-PERM-03')
        # 补盲结论档位取该规则上限（不得越权升到上限之上）
        self.assertEqual(concl[0]['status'], registry.RULE_META['R-PERM-03']['max_status'])
        self.assertEqual(concl[0]['channel'], 'fusion')


if __name__ == '__main__':
    unittest.main()
