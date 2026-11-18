#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""eval_calibrate.py · 评价 Agent 的 K-1~K-6 校准记录

用确定性快路径跑六个已知判例，落盘 JSON 到 review/evaluation/。
小校准包不证明总体准确率；记录错误类型比正确率有价值。
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.evidence import utc_now_iso              # noqa: E402
from evaluator.agent import evaluate_dir_quick    # noqa: E402
from evaluator.calibration import CASES, run_calibration  # noqa: E402


def main():
    rows = run_calibration(ROOT, evaluate_dir_quick)
    out = {
        'generated_at': utc_now_iso(),
        'evaluator': 'evidence-review-agent v1.0',
        'path': 'deterministic_quick_path',
        'rubric': 'evaluator/skills/evidence-review/rubric.json',
        'cases': rows,
        'summary': {
            'total': len(rows),
            'passed': sum(1 for r in rows if r['ok']),
            'failed': sum(1 for r in rows if not r['ok']),
        },
        'note': ('小校准包不证明总体准确率或安全；仪表板不显示总准确率。'
                 '记录错误类型（误放行、错引、不必要弃权、分歧）比正确率有价值。'),
        'case_expectations': {k: v['expect'] for k, v in CASES.items()},
    }
    path = os.path.join(ROOT, 'review', 'evaluation', 'calibration_k1_k6.json')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print('=== 评价 Agent 校准 ===')
    for r in rows:
        print('[%s] expect=%s got=%s ok=%s %s'
              % (r['case'], r['expect'], r['got'], r['ok'], r['error_type']))
    print('汇总：%d/%d 通过' % (out['summary']['passed'], out['summary']['total']))
    print('[out] %s' % path)
    return 0 if out['summary']['failed'] == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
