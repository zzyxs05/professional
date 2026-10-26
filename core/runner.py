# -*- coding: utf-8 -*-
"""runner.py · 预算、超时、熔断、状态机、子进程白名单

- 子进程白名单：仅 java（apktool 调用），名单外一律拒绝（总档 §10）
- 预算：LLM 交互数、注册补测数（总档 §2.6 试点值）
- 状态机：PENDING → DECODING → RULE_A → CHANNEL_B → FUSION → REPORT → DONE / FAILED
"""

import os
import subprocess

from . import registry


class BudgetExceeded(Exception):
    pass


class SubprocessDenied(Exception):
    pass


class StatusMachine(object):
    STEPS = ['PENDING', 'DECODING', 'RULE_A', 'CHANNEL_B', 'FUSION', 'REPORT', 'DONE']

    def __init__(self):
        self.current = 'PENDING'
        self.history = [('PENDING', None)]

    def advance(self, step, note=''):
        self.current = step
        self.history.append((step, note))

    def fail(self, reason):
        self.current = 'FAILED'
        self.history.append(('FAILED', reason))

    def as_dict(self):
        return {'state': self.current, 'history': self.history}


class Budget(object):
    def __init__(self):
        self.max_llm_calls = registry.BUDGET_MAX_LLM_CALLS_PER_RUN
        self.llm_calls = 0
        self.max_registered_tests = registry.BUDGET_MAX_REGISTERED_TESTS
        self.registered_tests = 0
        self.exhausted_notes = []

    def consume_llm(self):
        if self.llm_calls >= self.max_llm_calls:
            self.exhausted_notes.append('LLM 交互预算耗尽（%d 次）' % self.max_llm_calls)
            return False
        self.llm_calls += 1
        return True

    def as_dict(self):
        return {
            'llm_calls_used': self.llm_calls,
            'llm_calls_max': self.max_llm_calls,
            'registered_tests_used': self.registered_tests,
            'registered_tests_max': self.max_registered_tests,
            'exhausted_notes': self.exhausted_notes,
        }


class Runner(object):
    def __init__(self, project_root):
        self.project_root = project_root
        self.sm = StatusMachine()
        self.budget = Budget()
        self.notes = []          # 覆盖声明用提示
        self.decode_result = None

    # -------------------------------------------------- 子进程白名单
    def run_subprocess(self, cmd, timeout=None):
        base = os.path.basename(cmd[0]).lower()
        if base not in registry.SUBPROCESS_ALLOWED_BINARIES:
            raise SubprocessDenied('子进程白名单拒绝: %s' % cmd[0])
        return subprocess.run(cmd, capture_output=True, timeout=timeout, text=True,
                              errors='replace')

    def note(self, text):
        self.notes.append(text)
