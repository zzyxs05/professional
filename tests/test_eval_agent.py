# -*- coding: utf-8 -*-
"""test_eval_agent.py · 评价 Agent 离线回归（不调用模型、不联网、不写 evidence/）"""

import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evaluator.agent import (Budget, _parse_model_output, evaluate_dir_quick,
                             run_agent)
from evaluator.tools import RestrictedTools

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUN = 'RUN-20261015-145536'
SCHEMA_KEYS = ('criterion_id', 'status', 'evidence_level', 'evidence_ids',
               'finding', 'scope', 'missing_evidence', 'suggested_check',
               'score_suggestion', 'human_signoff')


class TestAgentOffline(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='apkaudit_eval_agent_')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_self_review_deterministic(self):
        res = run_agent(ROOT, ROOT, RUN, mode='self', use_llm=False,
                        out_dir=self.tmp)
        self.assertEqual(res['model']['mode'], 'deterministic')
        # 历史 RUN 为 0.1.3 正本、当前契约 0.1.4：版本错配必须报待复核
        self.assertEqual(res['status'], 'INSUFFICIENT_EVIDENCE')
        self.assertTrue(res['version_check']['mismatch'])
        self.assertTrue(res['coverage_note'])
        self.assertTrue(res['not_checked'])
        self.assertEqual(len(res['findings']), 10)
        self.assertIsNone(res['score_suggestion'])
        self.assertEqual(res['human_signoff'], 'pending')
        self.assertEqual(res['contract']['approved_by'], 'pending')
        self.assertTrue(os.path.isfile(res['out_path']))
        self.assertTrue(os.path.isfile(res['trace_path']))
        for f in res['findings']:
            for key in SCHEMA_KEYS:
                self.assertIn(key, f)
            self.assertIsNone(f['score_suggestion'])
        with open(res['out_path'], 'r', encoding='utf-8') as fh:
            self.assertEqual(json.load(fh)['eval_id'], res['eval_id'])
        with open(res['trace_path'], 'r', encoding='utf-8') as fh:
            trace = fh.read()
        self.assertIn('tool_call', trace)
        self.assertIn('verdict', trace)
        self.assertIn('verify_claims', trace)

    def test_peer_without_contract_is_insufficient(self):
        res = run_agent(ROOT, ROOT, RUN, mode='peer', use_llm=False,
                        out_dir=self.tmp)
        self.assertFalse(res['contract']['present'])
        self.assertEqual(res['status'], 'INSUFFICIENT_EVIDENCE')
        for f in res['findings']:
            self.assertEqual(f['status'], 'INSUFFICIENT_EVIDENCE')
            self.assertTrue(f['missing_evidence'])

    def test_path_whitelist_is_enforced(self):
        tools = RestrictedTools(ROOT, ROOT, RUN, {}, 'self', Budget())
        self.assertIsNone(tools._safe_path('../key.txt'))
        self.assertIsNone(tools._safe_path('/etc/passwd'))
        self.assertIsNone(tools._safe_path('key.txt'))
        self.assertIsNone(tools._safe_path('docs/../../key.txt'))
        self.assertIsNotNone(tools._safe_path('docs/specification.md'))
        self.assertIsNotNone(tools._safe_path('.gitignore'))

    def test_unregistered_test_rejected(self):
        tools = RestrictedTools(ROOT, ROOT, RUN, {}, 'self', Budget())
        out = tools.request_registered_test(RUN, 'rm_rf_everything')
        self.assertFalse(out['ok'])
        self.assertIn('未注册', out['error'])

    def test_verify_claims_is_wired_as_registered_test(self):
        tools = RestrictedTools(ROOT, ROOT, RUN, {}, 'self', Budget())
        out = tools.request_registered_test(RUN, 'verify_claims')
        self.assertTrue(out['ok'])
        self.assertEqual(out['runner'], 'deterministic_precheck')
        self.assertEqual(out['evidence_level'], 'STATIC')
        self.assertTrue(out['report_present'])

    def test_model_output_parsing(self):
        self.assertEqual(_parse_model_output('```json\n{"final": true}\n```'),
                         {'final': True})
        self.assertEqual(_parse_model_output('说明文字 {"tool": "list_evidence"}'),
                         {'tool': 'list_evidence'})
        self.assertIsNone(_parse_model_output('这里没有结构化输出'))

    def test_calibration_quick_path_still_works(self):
        status, _ = evaluate_dir_quick('C:/definitely/not/exist')
        self.assertEqual(status, 'FAIL')


if __name__ == '__main__':
    unittest.main()
