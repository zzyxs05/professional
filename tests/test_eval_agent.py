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
                             evaluate_run, run_agent)
from evaluator.tools import RestrictedTools

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUN = 'RUN-20261015-145536'
SCHEMA_KEYS = ('criterion_id', 'status', 'evidence_level', 'evidence_ids',
               'finding', 'scope', 'missing_evidence', 'suggested_check',
               'score_suggestion')


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
        # 纯 harness：先产出证据包，分数待 harness 看过证据后主观给出；
        # 机械层不猜分，不调用 API。
        self.assertIsNone(res['score_suggestion'])
        self.assertEqual(res['evaluation_scores'], [])
        self.assertEqual(res['scoring_status'], 'pending_harness')
        pack = res['evidence_pack']
        self.assertEqual(len(pack['subcriteria']), 15)
        self.assertTrue(all(s['evidence'] for s in pack['subcriteria']))
        self.assertIn('S1-S4', res['scoring_framework'])
        # 评价产物不含签署字段；项目治理台账的签署另行维护，不在此产物中
        self.assertNotIn('human_signoff', res)
        self.assertNotIn('signoff_chain', res)
        self.assertEqual(res['contract']['approved_by'], 'pending')
        self.assertTrue(os.path.isfile(res['out_path']))
        self.assertTrue(os.path.isfile(res['trace_path']))
        self.assertTrue(res['verdict_digest'])
        self.assertTrue(os.path.isfile(res['html_path']))
        for f in res['findings']:
            for key in SCHEMA_KEYS:
                self.assertIn(key, f)
            self.assertIsNone(f['score_suggestion'])
        with open(res['out_path'], 'r', encoding='utf-8') as fh:
            self.assertEqual(json.load(fh)['eval_id'], res['eval_id'])
        with open(res['trace_path'], 'r', encoding='utf-8') as fh:
            trace = fh.read()
        # 纯 harness：不调 API、不产生 tool_call；轨迹记录评分与判定
        self.assertNotIn('tool_call', trace)
        self.assertIn('evidence_pack_ready', trace)
        self.assertIn('verdict', trace)
        self.assertIn('field_check', trace)
        self.assertIn('verdict', trace)

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

    def test_run_id_traversal_rejected_in_tools(self):
        # run_dir 由 run_id 拼接，必须白名单校验（第四次审查 U1）
        from core.evidence import BadRunId
        for bad in ('../evil', 'RUN-..-..', 'RUN-a/b', 'RUN-1\\x'):
            with self.assertRaises(BadRunId, msg=bad):
                RestrictedTools(ROOT, ROOT, bad, {}, 'self', Budget())
        with self.assertRaises(BadRunId):
            evaluate_run(ROOT, '../../etc')

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
