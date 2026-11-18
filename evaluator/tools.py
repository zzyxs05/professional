# -*- coding: utf-8 -*-
"""tools.py · 评价 Agent 的四个受限工具（真正接入主循环）

与旧版差别：工具不再是摆设——AgentLoop 按模型输出调用它们；目标仓库参数化；
路径白名单由程序强制（不是提示词禁令）；确定性预检 precheck 降级为注册测试
verify_claims，成为 Agent 可调用的机械核对工具。
"""

import hashlib
import json
import os
import subprocess
import sys

from .precheck import precheck

ALLOWED_PREFIXES = (
    'docs/', 'review/', 'evidence/', 'core/', 'evaluator/',
    'scripts/', 'tests/', 'lab/truth/', 'handoff/',
)
ALLOWED_ROOT_FILES = frozenset({
    'AGENTS.md', 'HARNESS.md', 'GLOBAL.md', 'PLAN.md', 'TASKS.md',
    '总档.md', 'cli.py', '.gitignore',
})
TEXT_EXT = ('.md', '.json', '.jsonl', '.py', '.txt', '.xml', '.yml', '.yaml')


def _sha256(path):
    h = hashlib.sha256()
    try:
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b''):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


class RestrictedTools(object):
    """四个受限工具；不提供任意 Shell / 任意 URL / 任意文件写。"""

    REGISTERED_TESTS = {
        'verify_claims': '机械核对：引用存在性、版本匹配、结构、覆盖声明（调用 precheck）',
        'truth_check': '仅自评：复算本仓库靶场真值一致性',
        'rerun_analyze': '需受控 runner；未提供时只读既有结果并标注验证层级',
    }

    def __init__(self, owner_root, target_root, run_id, contract, mode, budget):
        self.owner_root = owner_root
        self.target_root = target_root
        self.run_id = run_id
        self.run_dir = os.path.join(target_root, 'evidence', run_id)
        self.contract = contract
        self.mode = mode
        self.budget = budget

    # ------------------------------------------------------------ 权限边界
    def _safe_path(self, rel):
        """路径白名单：拒绝绝对路径、.. 穿越、白名单外前缀。"""
        if not isinstance(rel, str) or not rel:
            return None
        rel = rel.replace('\\', '/').lstrip('/')
        if '..' in rel.split('/'):
            return None
        if rel.startswith('.') and rel not in ALLOWED_ROOT_FILES:
            return None
        if '/' not in rel and rel not in ALLOWED_ROOT_FILES:
            return None
        if '/' in rel and not rel.startswith(ALLOWED_PREFIXES):
            return None
        full = os.path.normpath(os.path.join(self.target_root, rel))
        try:
            if os.path.commonpath([full, self.target_root]) != self.target_root:
                return None
        except ValueError:
            return None
        return full

    # 工具 1 ---------------------------------------------------------------
    def get_approved_contract(self):
        if self.contract is None:
            return {'ok': False, 'error': '批准契约缺失，不得继续评价'}
        return {'ok': True, 'contract': self.contract}

    # 工具 2 ---------------------------------------------------------------
    def list_evidence(self, paths=None):
        """列出目标仓库证据/交付物。paths 为空时给出 RUN 正本与常见锚点。"""
        if paths is None:
            paths = [
                'docs/requirements.md', 'docs/specification.md',
                'docs/acceptance-matrix.md', 'docs/decision-log.md',
                'docs/experiments.md', 'docs/experiment-protocol.md',
                'docs/changes.md', 'docs/release.md', 'docs/signoff.md',
                'HARNESS.md', 'GLOBAL.md', 'PLAN.md', 'TASKS.md',
                'AGENTS.md', 'handoff/README.md',
                'evidence/%s/report.json' % self.run_id,
                'evidence/%s/meta.json' % self.run_id,
                'evidence/%s/channel_a/hits.jsonl' % self.run_id,
            ]
        out = []
        for rel in paths:
            full = self._safe_path(rel)
            if full is None:
                out.append({'path': rel, 'allowed': False, 'exists': False,
                            'note': '路径不在白名单，已拒绝'})
                continue
            if os.path.isfile(full):
                out.append({'path': rel, 'allowed': True, 'exists': True,
                            'size': os.path.getsize(full), 'sha256': _sha256(full)})
            elif os.path.isdir(full):
                out.append({'path': rel, 'allowed': True, 'exists': True,
                            'is_dir': True, 'entries': sorted(os.listdir(full))[:20]})
            else:
                out.append({'path': rel, 'allowed': True, 'exists': False})
        return {'ok': True, 'items': out}

    # 工具 3 ---------------------------------------------------------------
    def read_evidence(self, path=None, evidence_id=None, limit=4000):
        """读取白名单文件内容，或按 evidence_id 查 RUN 的 JSONL 证据。"""
        if evidence_id:
            for rel in ('channel_a/hits.jsonl', 'channel_b/records.jsonl',
                        'fusion/records.jsonl'):
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
                        except ValueError:
                            continue
                        if obj.get('evidence_id') == evidence_id:
                            return {'ok': True, 'kind': 'evidence_record',
                                    'path': rel, 'record': obj}
            return {'ok': False, 'error': 'evidence_id 未找到：%s' % evidence_id}

        full = self._safe_path(path)
        if full is None:
            return {'ok': False, 'error': '路径不在白名单，已拒绝：%s' % path}
        if not os.path.isfile(full):
            return {'ok': False, 'error': '文件不存在：%s' % path}
        if full.endswith(TEXT_EXT):
            try:
                with open(full, 'r', encoding='utf-8', errors='replace') as f:
                    text = f.read(limit)
                return {'ok': True, 'kind': 'text', 'path': path,
                        'sha256': _sha256(full), 'truncated': len(text) >= limit,
                        'content': text}
            except OSError as e:
                return {'ok': False, 'error': str(e)}
        return {'ok': True, 'kind': 'binary', 'path': path,
                'size': os.path.getsize(full), 'sha256': _sha256(full),
                'note': '二进制文件只返回指纹，不作为文本证据'}

    # 工具 4 ---------------------------------------------------------------
    def request_registered_test(self, target_id, test_id):
        """白名单注册测试；每次消耗补测预算；执行由受控 runner 处理。"""
        if test_id not in self.REGISTERED_TESTS:
            return {'ok': False, 'error': '未注册的测试：%s' % test_id}
        if not self.budget.consume_test():
            return {'ok': False, 'error': '补测预算耗尽（%d/%d）'
                    % (self.budget.tests_used, self.budget.tests_max)}
        if test_id == 'verify_claims':
            findings, report, records = precheck(self.run_dir)
            return {
                'ok': True, 'test_id': test_id,
                'runner': 'deterministic_precheck', 'evidence_level': 'STATIC',
                'findings': findings, 'report_present': report is not None,
                'evidence_records': len(records),
                'conclusions': len(report.get('conclusions', [])) if report else 0,
            }
        if test_id == 'truth_check':
            if (self.mode != 'self' or
                    os.path.normpath(self.target_root) != os.path.normpath(self.owner_root)):
                return {'ok': False, 'error': 'truth_check 仅限本仓库自评，不得用于互评目标'}
            script = os.path.join(self.owner_root, 'scripts', 'truth_check.py')
            if not os.path.isfile(script):
                return {'ok': False, 'error': '真值脚本缺失'}
            proc = subprocess.run([sys.executable, script, '--no-run'],
                                  capture_output=True, text=True, timeout=120,
                                  cwd=self.owner_root, errors='replace')
            return {'ok': proc.returncode == 0, 'test_id': test_id,
                    'runner': 'controlled_local_runner',
                    'evidence_level': 'OBSERVED',
                    'output': (proc.stdout or '')[-2000:]}
        return {'ok': False, 'test_id': test_id,
                'error': '受控 runner 未接入，未执行重跑；证据层级维持 STATIC',
                'evidence_level': 'STATIC', 'not_independently_verified': True}

    def dispatch(self, name, args):
        """统一分派入口；工具名白名单由程序强制。"""
        table = {
            'get_approved_contract': lambda a: self.get_approved_contract(),
            'list_evidence': lambda a: self.list_evidence(a.get('paths')),
            'read_evidence': lambda a: self.read_evidence(
                a.get('path'), a.get('evidence_id'), a.get('limit', 4000)),
            'request_registered_test': lambda a: self.request_registered_test(
                a.get('target_id'), a.get('test_id')),
        }
        fn = table.get(name)
        if fn is None:
            return {'ok': False, 'error': '工具不在白名单：%s' % name}
        try:
            return fn(args or {})
        except Exception as e:  # noqa: BLE001 —— 工具异常记入轨迹，不中断 Agent
            return {'ok': False, 'error': '%s: %s' % (type(e).__name__, e)}
