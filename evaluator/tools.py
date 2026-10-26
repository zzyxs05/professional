# -*- coding: utf-8 -*-
"""tools.py · 评价器四个受限工具

不提供任意 Shell / 任意 URL —— 是权限边界，不是 Prompt 禁令（总档 §2.6）。
"""

import json
import os
import subprocess
import sys

from core import registry


class RestrictedTools(object):
    def __init__(self, project_root, run_id):
        self.project_root = project_root
        self.run_id = run_id
        self.run_dir = os.path.join(project_root, 'evidence', run_id)
        self.tests_used = 0
        self.tests_max = registry.BUDGET_MAX_REGISTERED_TESTS

    # 工具 1：get_approved_contract
    def get_approved_contract(self):
        return {
            'rule_pack_version': registry.RULE_PACK_VERSION,
            'rules': {rid: meta['name'] for rid, meta in registry.RULE_META.items()},
            'spec': 'docs/specification.md',
            'acceptance': 'docs/acceptance-matrix.md',
        }

    # 工具 2：list_evidence
    def list_evidence(self):
        out = []
        for rel in ('channel_a/hits.jsonl', 'channel_b/records.jsonl', 'meta.json'):
            p = os.path.join(self.run_dir, rel)
            if os.path.isfile(p):
                out.append({'file': rel, 'size': os.path.getsize(p)})
        return out

    # 工具 3：read_evidence
    def read_evidence(self, evidence_id):
        for rel in ('channel_a/hits.jsonl', 'channel_b/records.jsonl'):
            p = os.path.join(self.run_dir, rel)
            if not os.path.isfile(p):
                continue
            with open(p, 'r', encoding='utf-8', errors='replace') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if obj.get('evidence_id') == evidence_id:
                        return obj
        return None

    # 工具 4：request_registered_test（白名单：仅注册过的测试）
    REGISTERED_TESTS = {
        'rerun_analyze': '对样本重跑 cli.py analyze（注册补测）',
        'truth_check': '对 lab 靶场重跑真值一致性检查',
    }

    def request_registered_test(self, target_id, test_id):
        if test_id not in self.REGISTERED_TESTS:
            return {'ok': False, 'error': '未注册的测试：%s' % test_id}
        if self.tests_used >= self.tests_max:
            return {'ok': False, 'error': '补测预算耗尽（%d/%d）' % (self.tests_used, self.tests_max)}
        self.tests_used += 1
        if test_id == 'truth_check':
            proc = subprocess.run(
                [sys.executable, os.path.join(self.project_root, 'scripts', 'truth_check.py')],
                capture_output=True, text=True, timeout=600,
                cwd=self.project_root, errors='replace')
            return {'ok': proc.returncode == 0, 'output': (proc.stdout or '')[-4000:] +
                    (proc.stderr or '')[-2000:]}
        return {'ok': False, 'error': 'target 未注册：%s' % target_id}
