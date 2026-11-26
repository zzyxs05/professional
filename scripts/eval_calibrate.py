#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""eval_calibrate.py · 评价 Agent 的 K-1~K-6 校准记录

默认用确定性快路径；--llm 走完整 AgentLoop（模型判读 + 机械收口）。
两种模式各自落盘 JSON 到 review/evaluation/，互不覆盖。
小校准包不证明总体准确率；记录错误类型比正确率有价值。
"""

import argparse
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.evidence import utc_now_iso              # noqa: E402
from evaluator.agent import evaluate_dir_quick, run_agent  # noqa: E402
from evaluator.calibration import CASES, run_calibration  # noqa: E402


def llm_evaluate_fn(run_dir):
    """适配 run_calibration 的 evaluate_fn 签名：合成 RUN 目录 → llm 评价。"""
    case = os.path.basename(run_dir)  # K1 / K2 ...
    case_id = 'RUN-CALIB-' + case  # 满足 check_run_id 的 RUN- 前缀约束
    out_dir = tempfile.mkdtemp(prefix='calib_llm_')
    result = run_agent(
        owner_root=ROOT, target_root=ROOT, run_id=case_id,
        mode='self', use_llm=True, max_model_calls=4,
        out_dir=out_dir, want_html=False, run_dir=run_dir)
    return result.get('status'), result.get('reason', '')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--llm', action='store_true',
                    help='用完整 AgentLoop（模型判读）跑校准；默认确定性快路径')
    args = ap.parse_args()
    mode = 'llm' if args.llm else 'deterministic_quick_path'
    rows = run_calibration(ROOT, llm_evaluate_fn if args.llm else evaluate_dir_quick)
    out = {
        'generated_at': utc_now_iso(),
        'evaluator': 'evidence-review-agent v1.0',
        'path': mode,
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
    name = 'calibration_k1_k6_llm.json' if args.llm else 'calibration_k1_k6.json'
    path = os.path.join(ROOT, 'review', 'evaluation', name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print('=== 评价 Agent 校准（%s）===' % mode)
    for r in rows:
        print('[%s] expect=%s got=%s ok=%s %s'
              % (r['case'], r['expect'], r['got'], r['ok'], r['error_type']))
    print('汇总：%d/%d 通过' % (out['summary']['passed'], out['summary']['total']))
    print('[out] %s' % path)
    return 0 if out['summary']['failed'] == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
