# -*- coding: utf-8 -*-
"""test_eval_generic.py · 通用评价内核回归（不调用模型、不联网、不写 evidence/）

覆盖三件事：
1. checker 评一个完全没有 run_id / evidence/ / report.json 的异题项目；
2. 路径变量缺失时如实判 missing，不崩溃、不套默认值；
3. HTML 判定区同快照重跑逐字节一致，模型分数不进判定指纹。
"""

import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evaluator.checker import (CheckerError, check_files, derive_allowlist,
                               verdict_digest)
from evaluator.fieldcheck import expand_template
from evaluator.html_report import (ZONE_END, ZONE_START, render,
                                   render_verdict_zone)
from evaluator.agent import _validate_scores

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _write(path, content):
    full = os.path.join(path[0], path[1])
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, 'w', encoding='utf-8') as f:
        f.write(content)


class TestGenericChecker(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='apkaudit_eval_generic_')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _web_project(self):
        """一个和 APK 毫无关系的项目：无 run_id、无 evidence、无 report.json。"""
        _write((self.tmp, 'README.md'), '# Orders API\n\n## Scope\n\n## Limits\n')
        _write((self.tmp, 'src/config.json'), json.dumps({'auth': {'enabled': True}}))
        _write((self.tmp, 'tests/test_api.py'), 'def test_ok(): pass\n')
        spec = {'id': 'fields-web-demo', 'version': '1.0', 'criteria': [
            {'criterion_id': 'W-01', 'fields': [
                {'id': 'W-01-F1', 'path': 'README.md', 'kind': 'text_all',
                 'expect': ['## Scope', '## Limits'], 'note': '范围与限制'},
                {'id': 'W-01-F2', 'path': 'src/config.json', 'kind': 'json_eq',
                 'lhs': 'auth.enabled', 'const': True, 'note': '鉴权开关'}]},
            {'criterion_id': 'W-02', 'fields': [
                {'id': 'W-02-F1', 'path': 'tests', 'kind': 'dir_min',
                 'min': 1, 'note': '有测试目录'}]}]}
        _write((self.tmp, 'fields.json'), json.dumps(spec))
        return os.path.join(self.tmp, 'fields.json')

    def test_evaluates_project_without_run_id(self):
        fields = self._web_project()
        result = check_files(self.tmp, fields)
        self.assertEqual(result['context'], {})
        self.assertEqual([c['status'] for c in result['criteria']],
                         ['PASS', 'PASS'])
        self.assertTrue(result['verdict_digest'])
        self.assertTrue(result['criteria'][0]['evidence_chain']['steps'])

    def test_missing_context_reported_not_guessed(self):
        spec = {'id': 'f-ctx', 'version': '1.0', 'criteria': [
            {'criterion_id': 'W-03', 'fields': [
                {'id': 'W-03-F1', 'path': 'results/{{snapshot}}/summary.json',
                 'kind': 'file_exists', 'note': '快照摘要'}]}]}
        path = os.path.join(self.tmp, 'fields_ctx.json')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(spec, f)
        result = check_files(self.tmp, path)   # 不提供 snapshot
        row = result['criteria'][0]['fields'][0]
        self.assertEqual(row['status'], 'missing')
        self.assertEqual(row['observed']['missing_context'], ['snapshot'])
        self.assertEqual(result['criteria'][0]['status'], 'INSUFFICIENT_EVIDENCE')

    def test_context_supplied_path_is_readable(self):
        _write((self.tmp, 'results/2026/summary.json'), json.dumps({'ok': True}))
        spec = {'id': 'f-ctx2', 'version': '1.0', 'criteria': [
            {'criterion_id': 'W-04', 'fields': [
                {'id': 'W-04-F1', 'path': 'results/{{snapshot}}/summary.json',
                 'kind': 'json_nonempty', 'json_path': 'ok', 'note': '摘要'}]}]}
        path = os.path.join(self.tmp, 'fields_ctx2.json')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(spec, f)
        result = check_files(self.tmp, path, context={'snapshot': '2026'})
        self.assertEqual(result['criteria'][0]['status'], 'PASS')

    def test_allowlist_never_includes_undeclared_paths(self):
        spec = {'id': 'f-sec', 'version': '1.0', 'criteria': [
            {'criterion_id': 'W-05', 'fields': [
                {'id': 'W-05-F1', 'path': 'README.md', 'kind': 'file_exists'}]}]}
        exact, prefixes = derive_allowlist(spec, {})
        self.assertIn('README.md', exact)
        self.assertNotIn('key.txt', exact)
        self.assertFalse(any(p in prefixes for p in ('..', '/etc')))

    def test_traversal_rejected(self):
        expanded, missing = expand_template('../secret.txt', {})
        self.assertIsNone(expanded)
        self.assertEqual(missing, ['路径越界'])

    def test_bad_fields_spec_raises(self):
        with self.assertRaises(CheckerError):
            check_files(self.tmp, os.path.join(self.tmp, 'nope.json'))


class TestVerdictStability(unittest.TestCase):
    def _result(self, score=None):
        finding = {
            'criterion_id': 'W-01', 'status': 'PASS',
            'field_check': {'summary': {'all_match': True}, 'fields': [
                {'id': 'F1', 'path': 'README.md', 'kind': 'text_all',
                 'status': 'match', 'observed': {'missing_anchors': []}}]},
            'finding': 'ok', 'suggested_check': '抽验',
            'score_suggestion': None,
        }
        scores = [{'subcriterion_id': 'S1.需求', 'score': score, 'max': 6,
                   'rationale': '理由', 'evidence_ids': ['README.md'],
                   'evidence_level': 'STATIC'}] if score is not None else []
        return {'eval_id': 'EVAL-x', 'target': '/x', 'mode': 'self',
                'status': 'PASS', 'verdict_digest': 'abc123',
                'findings': [finding], 'evaluation_scores': scores,
                'observations': ['模型说了一句话']}

    def test_verdict_zone_ignores_model_score(self):
        rubric = {'criteria': [{'id': 'W-01', 'plain': '写没写清', 'weight_ref': 6}]}
        a = render_verdict_zone(self._result(5), rubric)
        b = render_verdict_zone(self._result(2), rubric)
        self.assertEqual(a, b)
        self.assertIn(ZONE_START, a)
        self.assertIn(ZONE_END, a)

    def test_full_html_shows_scores(self):
        rubric = {'criteria': [{'id': 'W-01', 'plain': '写没写清', 'weight_ref': 6}]}
        html = render(self._result(5), rubric)
        self.assertIn('分项评测分', html)
        self.assertIn('S1.需求', html)
        self.assertIn('非课程最终成绩', html)
        self.assertIn('写没写清', html)

    def test_digest_changes_with_verdict_only(self):
        base = {'run_id': 'R', 'criteria': [{'id': 'W', 'status': 'PASS'}]}
        self.assertNotEqual(verdict_digest(base),
                            verdict_digest(dict(base, observations=['x'])))

    def test_score_validation_drops_bogus(self):
        # 越界分数单独出现：丢弃为 None，不裁剪成假分
        bad = _validate_scores(
            [{'subcriterion_id': 'S1.需求', 'score': 999, 'rationale': 'x'}],
            {'S1.需求': 6}, {'README.md'})
        self.assertIsNone(bad['S1.需求']['score'])
        self.assertEqual(bad['S1.需求']['max'], 6)
        # 合法条目可覆盖同项的非法条目；证据引用只保留真实存在的；层级非法降到 CLAIM_ONLY
        good = _validate_scores(
            [{'subcriterion_id': 'S1.需求', 'score': 999, 'rationale': 'x'},
             {'subcriterion_id': 'S1.需求', 'score': 3, 'rationale': 'ok',
              'evidence_ids': ['README.md', 'nope'], 'evidence_level': 'BOGUS'}],
            {'S1.需求': 6}, {'README.md'})
        self.assertEqual(good['S1.需求']['score'], 3)
        self.assertEqual(good['S1.需求']['evidence_ids'], ['README.md'])
        self.assertEqual(good['S1.需求']['evidence_level'], 'CLAIM_ONLY')
        # 未定义的子项一律丢弃，不猜分
        self.assertNotIn('S9.不存在', _validate_scores(
            [{'subcriterion_id': 'S9.不存在', 'score': 5}], {'S1.需求': 6}, set()))


if __name__ == '__main__':
    unittest.main()
