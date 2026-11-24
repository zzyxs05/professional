#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""field_check.py · 对 6 个 RUN 正本批量做字段级核对（T-M5-12）

只读：读仓库文件与 evidence/RUN-* 正本，不写 evidence/。
产出 review/evaluation/field_check.json：每项三态 + 6 样本矩阵 + 人工抽验留空位。
不代签、不判分、不改四状态。
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core.evidence import utc_now_iso  # noqa: E402
from evaluator.agent import Budget  # noqa: E402
from evaluator.fieldcheck import check_all, load_fields  # noqa: E402
from evaluator.tools import RestrictedTools  # noqa: E402

RUNS = [
    ('RUN-20261124-140458-21cf5a06', 'bad03'),
    ('RUN-20261124-141033-3356097a', 'bad01'),
    ('RUN-20261124-141327-232666b8', 'bad02'),
    ('RUN-20261124-141435-e1152264', 'bad04'),
    ('RUN-20261124-141502-4cbacbdd', 'good01'),
    ('RUN-20261124-141518-710b457d', 'good02'),
]
OUT = os.path.join(ROOT, 'review', 'evaluation', 'field_check.json')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=OUT, help='输出路径（默认正本；演练请指向临时文件）')
    args = ap.parse_args()

    spec = load_fields()
    per_run = {}
    for run_id, sample in RUNS:
        run_dir = os.path.join(ROOT, 'evidence', run_id)
        if not os.path.isdir(run_dir):
            print('[跳过] %s 目录不存在' % run_id)
            continue
        tools = RestrictedTools(ROOT, ROOT, run_id, {}, 'self', Budget())
        per_run[run_id] = {'sample': sample, 'check': check_all(spec, tools, run_id)}

    # 矩阵：审查项 × 样本，取三态汇总
    matrix = {}
    for crit in spec['criteria']:
        cid = crit['criterion_id']
        matrix[cid] = {}
        for run_id, entry in per_run.items():
            c = next((x for x in entry['check']['criteria']
                      if x['criterion_id'] == cid), None)
            matrix[cid][entry['sample']] = (
                c['summary'] if c else {'all_match': False, 'missing': -1})

    result = {
        'generated_at': utc_now_iso(),
        'task': 'T-M5-12 字段级内容核对',
        'fields_id': spec.get('id'),
        'fields_version': spec.get('version'),
        'discipline': '只读、机械三态、不代签不判分；字段未全符合不得仅凭存在性判 PASS',
        'runs': list(RUNS),
        'per_run': per_run,
        'matrix': matrix,
        'human_spot_check': {
            'required': 5,
            'note': '人工抽 5 条，按坐标/字段打开原文核对程序三态结论；签名与日期由本人填写',
            'items': [
                {'index': i, 'run_id': '', 'criterion_id': '', 'field_id': '',
                 'program_status': '', 'human_result': '', 'checker': '', 'date': ''}
                for i in range(1, 6)
            ],
        },
    }
    with open(args.out, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # 摘要
    for cid, by_sample in matrix.items():
        cells = ['%s:%s' % (s, '✓' if v.get('all_match') else 'X')
                 for s, v in by_sample.items()]
        print('%-5s %s' % (cid, ' '.join(cells)))
    print('[out] %s' % args.out)


if __name__ == '__main__':
    main()
