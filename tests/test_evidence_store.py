# -*- coding: utf-8 -*-
"""evidence store 的纪律回归（C-2 / M-4）

- 同一 run_id 不得静默复用目录（否则证据 ID 重号 + hits.jsonl 互相覆盖）
- B 通道原始响应必须完整落盘（JSONL 只留指针与哈希）
"""

import shutil
import tempfile
import unittest

from core.evidence import BadRunId, EvidenceStore, RunDirExists


class TestEvidenceStore(unittest.TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix='evtest_')

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_duplicate_run_id_rejected(self):
        run_id = 'RUN-20261123-000000-abcd1234'
        EvidenceStore(self.root, run_id).add_record('R-MAN-01', 'a:1', 'x')
        with self.assertRaises(RunDirExists):
            EvidenceStore(self.root, run_id)

    def test_fresh_run_id_accepted(self):
        s1 = EvidenceStore(self.root, 'RUN-20261123-000000-aaaaaaaa')
        s2 = EvidenceStore(self.root, 'RUN-20261123-000000-bbbbbbbb')
        self.assertNotEqual(s1.root, s2.root)
        self.assertNotEqual(s1.add_record('R-MAN-01', 'a:1', 'x'),
                            s2.add_record('R-MAN-01', 'a:1', 'x'))

    def test_evidence_ids_do_not_collide_across_runs(self):
        a = EvidenceStore(self.root, 'RUN-20261123-000000-aaaaaaaa')
        b = EvidenceStore(self.root, 'RUN-20261123-000000-bbbbbbbb')
        eid_a = a.add_record('R-MAN-01', 'a:1', 'x')
        eid_b = b.add_record('R-MAN-01', 'a:1', 'x')
        self.assertNotEqual(eid_a, eid_b)

    def test_raw_response_persisted_fully(self):
        s = EvidenceStore(self.root, 'RUN-20261123-000000-deadbeef')
        raw = '模型原始响应' * 800          # 远超 400 字展示截断
        eid = s.add_record('B1 复核', 'x', raw[:400], kind='b1_response',
                           raw_response=raw)
        rec = [r for r in s.records if r['evidence_id'] == eid][0]
        self.assertIn('raw_response_path', rec)
        self.assertEqual(len(rec['raw_response_sha256']), 64)
        with open(s.path(rec['raw_response_path']), 'r', encoding='utf-8') as f:
            self.assertEqual(f.read(), raw)

    def test_path_traversal_run_id_rejected(self):
        # run_id 参与路径拼接，只拒危险字符；不规定命名前缀（那是项目约定）。
        # 第四次审查 U1 的路径穿越防护保留：斜杠、..、绝对路径、空壳、控制字符。
        for bad in ('../evil', 'RUN-..-..', 'RUN-a/b', 'RUN-a\\b',
                    '/etc/passwd', '', 'RUN-', 'RUN-1\0', '-', 'a-'):
            with self.assertRaises(BadRunId, msg=bad):
                EvidenceStore(self.root, bad)

    def test_run_id_prefix_not_required(self):
        # 通用内核不认 RUN- 前缀：换项目后 K1 / calib-2026 等也能当 run_id。
        for good in ('K1', 'calib-2026', 'xRUN-1'):
            store = EvidenceStore(self.root, good, allow_existing=True)
            self.assertEqual(store.run_id, good)


if __name__ == '__main__':
    unittest.main()
