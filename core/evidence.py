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


class EvidenceStore(object):
    """一个 RUN 的证据目录。"""

    def __init__(self, evidence_root, run_id):
        self.run_id = run_id
        self.root = os.path.join(evidence_root, run_id)
        self.seq = 0
        self.records = []
        self._short = run_id.replace('RUN-', '')
        os.makedirs(self.root, exist_ok=True)

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
                   origin='static_inspection', extra=None):
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
