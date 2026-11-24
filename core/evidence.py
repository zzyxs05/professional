# -*- coding: utf-8 -*-
"""evidence.py · 证据库：run 目录、JSONL、哈希、证据 ID 生成

纪律（总档 §4/§10）：
- 证据 ID 全局唯一；报告只能引用已落盘证据（编不出来）
- 证据层级本项目上限 = STATIC（只读、不执行被测 APK）
- evidence/ 存运行事实；已签署的运行正本不改写
"""

import datetime
import hashlib
import json
import os
import re


def utc_now_iso():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def local_stamp():
    return datetime.datetime.now().strftime('%Y%m%d-%H%M%S')


def sha256_file(path, block=1 << 20):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while True:
            b = f.read(block)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


class RunDirExists(RuntimeError):
    """RUN 目录已存在：拒绝覆盖已落盘正本（总档 §4「已签署的运行正本不改写」）。"""


class BadRunId(ValueError):
    """run_id 含路径穿越/非法字符：拒绝参与路径拼接（第四次审查 U1）。"""


# run_id 会拼进 evidence/ 路径。只允许 RUN- 前缀 + 字母数字/连字符/下划线：
# 拒绝 `..`、路径分隔符、绝对路径等一切可改变拼接落点的字符（白名单而非黑名单）。
_RUN_ID_RE = re.compile(r'^RUN-[A-Za-z0-9][A-Za-z0-9_-]*$')


def check_run_id(run_id):
    """校验 run_id 格式；不合法抛 BadRunId。返回 run_id 便于链式使用。"""
    if not isinstance(run_id, str) or not _RUN_ID_RE.match(run_id):
        raise BadRunId('run_id 含非法字符（只允许 RUN- 前缀 + 字母数字/-/_）：%r'
                       % (run_id,))
    return run_id


class EvidenceStore(object):
    """一个 RUN 的证据目录。

    纪律：目录已存在即拒绝（不做静默合并）。run_id 冲突曾导致两次运行写同一目录、
    证据 ID 从 -001 重号并互相覆盖 hits.jsonl，直接破坏「证据 ID 全局唯一」。
    """

    def __init__(self, evidence_root, run_id, allow_existing=False):
        self.run_id = check_run_id(run_id)
        self.root = os.path.join(evidence_root, run_id)
        self.seq = 0
        self.records = []
        self._short = run_id[4:] if run_id.startswith('RUN-') else run_id
        if not allow_existing:
            try:
                os.makedirs(self.root, exist_ok=False)
            except FileExistsError:
                raise RunDirExists(
                    'RUN 目录已存在，拒绝覆盖正本：%s'
                    '（如需重跑请换 run_id，或人工归档后重试）' % self.root)
            except OSError as e:
                raise RunDirExists('无法创建 RUN 目录 %s：%s' % (self.root, e))

    # -------------------------------------------------- 目录
    def path(self, *parts):
        return os.path.join(self.root, *parts)

    def subdir(self, name):
        d = self.path(name)
        os.makedirs(d, exist_ok=True)
        return d

    # -------------------------------------------------- ID
    def new_id(self):
        self.seq += 1
        return 'EV-%s-%03d' % (self._short, self.seq)

    # -------------------------------------------------- 记录
    def add_record(self, rule_id, location, raw_snippet, kind='rule_hit',
                   source_file='', source_sha256='', rule_pack='',
                   origin='static_inspection', raw_response=None, extra=None):
        ev = {
            'evidence_id': self.new_id(),
            'run_id': self.run_id,
            'rule_id': rule_id,
            'kind': kind,
            'layer': 'STATIC',
            'origin': origin,
            'location': location,
            'raw_snippet': (raw_snippet or '')[:400],
            'source_file': source_file,
            'source_sha256': source_sha256,
            'rule_pack': rule_pack,
            'created': utc_now_iso(),
        }
        if raw_response is not None:
            # 完整原始响应单独落盘，JSONL 只留指针与哈希：
            # 模型的判定理由要能被事后复核，不能被 400 字展示截断。
            full = raw_response or ''
            rel = 'raw/%s.txt' % ev['evidence_id']
            self.write_text(rel, full)
            ev['raw_response_path'] = rel
            ev['raw_response_sha256'] = hashlib.sha256(full.encode('utf-8')).hexdigest()
        if extra:
            ev.update(extra)
        self.records.append(ev)
        return ev['evidence_id']

    # -------------------------------------------------- 落盘
    def write_json(self, rel_path, obj):
        p = self.path(rel_path)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w', encoding='utf-8') as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
        return p

    def write_text(self, rel_path, text):
        p = self.path(rel_path)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w', encoding='utf-8', newline='\n') as f:
            f.write(text)
        return p

    def write_jsonl(self, rel_path, records):
        p = self.path(rel_path)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w', encoding='utf-8', newline='\n') as f:
            for r in records:
                f.write(json.dumps(r, ensure_ascii=False) + '\n')
        return p
