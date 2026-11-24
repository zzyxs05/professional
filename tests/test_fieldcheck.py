# -*- coding: utf-8 -*-
"""test_fieldcheck.py · 字段级内容核对回归（T-M5-12）

只读临时目录，不写 evidence/、不调用模型。覆盖三态、白名单、JSON 取值与加严。
"""

import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evaluator.agent import Budget
from evaluator.fieldcheck import (STATUS_MATCH, STATUS_MISMATCH, STATUS_MISSING,
                                  check_field, check_criterion, check_all, load_fields)
from evaluator.tools import RestrictedTools

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUN = 'RUN-20261015-145536'


class TestFieldCheck(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='apkaudit_fieldcheck_')
        # 造最小目标仓库结构：白名单前缀 docs/ 与 evidence/<RUN>/
        os.makedirs(os.path.join(self.tmp, 'docs'))
        os.makedirs(os.path.join(self.tmp, 'evidence', RUN))
        with open(os.path.join(self.tmp, 'docs', 'a.md'), 'w', encoding='utf-8') as f:
            f.write('# 角色\n## 场景\n不服务批量扫描\nUN-01\n')
        with open(os.path.join(self.tmp, 'evidence', RUN, 'report.json'),
                  'w', encoding='utf-8') as f:
            json.dump({'versions': {'rule_pack': '0.1.6'},
                       'target': {'apk_sha256': 'abc'},
                       'conclusions': [{'x': 1}],
                       'coverage': {'checked': ['R-MAN-01']}}, f)
        with open(os.path.join(self.tmp, 'evidence', RUN, 'meta.json'),
                  'w', encoding='utf-8') as f:
            json.dump({'rule_pack': '0.1.6', 'apk_sha256': 'abc'}, f)
        self.tools = RestrictedTools(ROOT, self.tmp, RUN, {}, 'self', Budget())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_text_all_three_states(self):
        base = {'id': 'F1', 'path': 'docs/a.md', 'kind': 'text_all'}
        self.assertEqual(check_field(dict(base, expect=['UN-01', '场景']),
                                     self.tools, RUN)['status'], STATUS_MATCH)
        miss = check_field(dict(base, expect=['UN-01', '不存在的锚点']),
                           self.tools, RUN)
        self.assertEqual(miss['status'], STATUS_MISMATCH)
        self.assertIn('不存在的锚点', miss['observed']['missing_anchors'])
        self.assertEqual(check_field(dict(base, path='docs/none.md',
                                          expect=['UN-01']),
                                     self.tools, RUN)['status'], STATUS_MISSING)

    def test_json_eq_and_nonempty(self):
        eq = {'id': 'F2', 'path': 'evidence/RUN-*/report.json', 'kind': 'json_eq',
              'lhs': 'versions.rule_pack',
              'rhs': 'evidence/RUN-*/meta.json:rule_pack'}
        self.assertEqual(check_field(eq, self.tools, RUN)['status'], STATUS_MATCH)
        bad = dict(eq, rhs='evidence/RUN-*/meta.json:missing_key')
        self.assertEqual(check_field(bad, self.tools, RUN)['status'], STATUS_MISSING)
        self.assertEqual(check_field({'id': 'F3', 'path': 'evidence/RUN-*/report.json',
                                      'kind': 'json_nonempty', 'json_path': 'conclusions'},
                                     self.tools, RUN)['status'], STATUS_MATCH)
        self.assertEqual(check_field({'id': 'F4', 'path': 'evidence/RUN-*/report.json',
                                      'kind': 'json_nonempty', 'json_path': 'no_such'},
                                     self.tools, RUN)['status'], STATUS_MISSING)

    def test_const_equality_and_mismatch(self):
        eq = {'id': 'F5', 'path': 'evidence/RUN-*/meta.json', 'kind': 'json_eq',
              'lhs': 'apk_sha256', 'const': 'abc'}
        self.assertEqual(check_field(eq, self.tools, RUN)['status'], STATUS_MATCH)
        self.assertEqual(check_field(dict(eq, const='xyz'), self.tools,
                                     RUN)['status'], STATUS_MISMATCH)

    def test_whitelist_reject_is_missing(self):
        out = check_field({'id': 'F6', 'path': '../key.txt', 'kind': 'text_all',
                           'expect': ['x']}, self.tools, RUN)
        self.assertEqual(out['status'], STATUS_MISSING)
        self.assertIsNone(out['path_expanded'])

    def test_dir_min_and_file_exists(self):
        # _safe_path 要求目录路径带斜杠前缀（'docs' 单段不在白名单）
        self.assertEqual(check_field({'id': 'F7', 'path': 'docs/', 'kind': 'dir_min',
                                      'min': 1}, self.tools, RUN)['status'], STATUS_MATCH)
        self.assertEqual(check_field({'id': 'F8', 'path': 'docs/', 'kind': 'dir_min',
                                      'min': 99}, self.tools, RUN)['status'], STATUS_MISMATCH)
        self.assertEqual(check_field({'id': 'F9', 'path': 'docs/a.md',
                                      'kind': 'file_exists'}, self.tools, RUN)['status'],
                         STATUS_MATCH)

    def test_criterion_summary_all_match(self):
        crit = {'criterion_id': 'E-X', 'fields': [
            {'id': 'a', 'path': 'docs/a.md', 'kind': 'text_all', 'expect': ['UN-01']},
            {'id': 'b', 'path': 'docs/a.md', 'kind': 'file_exists'}]}
        r = check_criterion(crit, self.tools, RUN)
        self.assertTrue(r['summary']['all_match'])
        self.assertEqual(r['summary']['total'], 2)

    def test_real_spec_has_two_fields_each_and_three_states(self):
        spec = load_fields()
        self.assertEqual(len(spec['criteria']), 10)
        for c in spec['criteria']:
            self.assertGreaterEqual(len(c['fields']), 2, c['criterion_id'])
        # 真实仓库：用本仓库 tools 跑一遍，确认三态都能出现、无异常
        real_tools = RestrictedTools(ROOT, ROOT, RUN, {}, 'self', Budget())
        res = check_all(spec, real_tools, RUN)
        states = {f['status'] for c in res['criteria'] for f in c['fields']}
        self.assertIn(STATUS_MATCH, states)
        self.assertIn(STATUS_MISSING, states)  # brief.md 等历史文件如实 missing


if __name__ == '__main__':
    unittest.main()
