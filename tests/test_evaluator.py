# -*- coding: utf-8 -*-
"""test_evaluator.py · 评价器预检与校准判例测试"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evaluator.agent import evaluate_dir_quick
from evaluator.calibration import CASES, run_calibration


class TestCalibration(unittest.TestCase):
    def test_all_cases(self):
        res = run_calibration(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                              evaluate_dir_quick)
        self.assertEqual(len(res), len(CASES))
        bad = [r for r in res if not r['ok']]
        self.assertEqual(bad, [], '校准判例未通过：%s' % bad)

    def test_missing_run_dir_fails(self):
        status, _reason = evaluate_dir_quick('C:/definitely/not/exist')
        self.assertEqual(status, 'FAIL')


if __name__ == '__main__':
    unittest.main()
