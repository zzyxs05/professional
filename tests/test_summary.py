# -*- coding: utf-8 -*-
"""test_summary.py · B3 汇总的判点全量化适配回归（第二次审查 M-1）

判点全量化后每条规则都有结论——无命中但已执行的是一条「无法判定」占位。
汇总模块判定「干净样本」不能再看结论条数，必须看有没有非 UNDECIDED 的实结论。
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import fusion, registry
from core.summary import build_summary_input, substantive_conclusions


def _clean_conclusions():
    """14 条规则全部已执行、全部未命中的占位结论（干净样本）。"""
    hits = {rid: [] for rid in registry.ALL_RULE_IDS}
    return fusion.build_conclusions(hits, {}, None, None)[0]


def _report(conclusions, sample='clean'):
    return {
        'sample': sample, 'run_id': 'RUN-X',
        'report': {
            'versions': {'rule_pack': registry.RULE_PACK_VERSION},
            'conclusions': conclusions,
            'coverage': {'checked': [], 'not_checked': []},
            'target': {'apk_name': sample + '.apk', 'apk_sha256': '0' * 64},
        },
    }


class TestSubstantiveConclusions(unittest.TestCase):

    def test_clean_sample_has_no_substantive_conclusion(self):
        self.assertEqual(substantive_conclusions(_clean_conclusions()), [])

    def test_confirmed_and_review_are_substantive(self):
        conclusions = [
            {'criterion_id': 'R-MAN-01', 'status': registry.STATUS_CONFIRMED},
            {'criterion_id': 'R-MAN-02', 'status': registry.STATUS_REVIEW},
            {'criterion_id': 'R-MAN-03', 'status': registry.STATUS_UNDECIDED},
            {'criterion_id': 'R-B-001', 'status': registry.STATUS_REVIEW},  # B 侧疑点不算
        ]
        got = [c['criterion_id'] for c in substantive_conclusions(conclusions)]
        self.assertEqual(got, ['R-MAN-01', 'R-MAN-02'])


class TestSummaryCleanSample(unittest.TestCase):

    def test_clean_sample_counted_as_no_detection(self):
        """回归：干净样本必须计入 n_quiet，不能因 14 条占位结论被当'有结论'。"""
        bundle = [_report(_clean_conclusions())]
        text = build_summary_input(os.getcwd(), bundle)
        self.assertIn('规则侧无检出的样本 1 个（clean）', text)
        self.assertIn('本样本规则结论 0 条', text)

    def test_detected_sample_not_counted_as_clean(self):
        conclusions = _clean_conclusions()
        conclusions[0]['status'] = registry.STATUS_CONFIRMED
        bundle = [_report(conclusions, sample='bad')]
        text = build_summary_input(os.getcwd(), bundle)
        self.assertIn('规则侧无检出的样本 0 个', text)
        self.assertIn('本样本规则结论 1 条（已确认 1、待复核 0）', text)


if __name__ == '__main__':
    unittest.main()
