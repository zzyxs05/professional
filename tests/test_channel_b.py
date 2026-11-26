# -*- coding: utf-8 -*-
"""test_channel_b.py · B 通道响应解析鲁棒性（合成响应，不依赖模型）

背景：去禁令后模型输出更自由，可能出现尾部畸形字段（如 `, ""`）；
程序侧必须能宽容解析，避免把"确认可疑"误判为"无法判断"进而误降级结论。
"""

import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import registry
from core.channel_b import _parse_b2, _parse_verdict


class TestParseVerdict(unittest.TestCase):
    def test_normal(self):
        r = _parse_verdict('{"verdict": "确认可疑", "reason": "ok", "observation": "obs"}')
        self.assertEqual(r['verdict'], '确认可疑')
        self.assertEqual(r['observation'], 'obs')

    def test_trailing_junk_tolerated(self):
        # 模型在对象尾部附加畸形字段：仍应解析出前面的正常判定
        raw = '{"verdict": "确认可疑", "reason": "r", "observation": "o", ""}'
        r = _parse_verdict(raw)
        self.assertEqual(r['verdict'], '确认可疑')
        self.assertEqual(r['observation'], 'o')

    def test_invalid_enum_falls_back(self):
        self.assertEqual(_parse_verdict('{"verdict": "随便说的"}')['verdict'], '无法判断')

    def test_no_json_falls_back(self):
        self.assertEqual(_parse_verdict('完全没有 JSON')['verdict'], '无法判断')

    def test_b2_trailing_comma(self):
        out = _parse_b2('[{"claim": "a", "confidence": "low"},]')
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]['confidence'], 'low')


if __name__ == '__main__':
    unittest.main()


class TestModelSelection(unittest.TestCase):
    """R-1：按模型名选 key.txt 配置；默认仍取第一行；错误名字不回退。"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='model_sel_')
        with open(os.path.join(self.tmp, registry.KEY_FILE_NAME), 'w', encoding='utf-8') as f:
            f.write('first-model,https://a.example/v1,key1\n')
            f.write('second-model,https://b.example/v1,key2\n')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _ctx(self):
        class Ctx(object): pass
        c = Ctx(); c.project_root = self.tmp
        return c

    def test_load_key_config_reads_all_lines(self):
        from core.channel_b import load_key_config
        cfgs = load_key_config(self.tmp)
        self.assertEqual([c[0] for c in cfgs], ['first-model', 'second-model'])

    def test_unknown_model_does_not_fallback(self):
        from core.channel_b import run_channel_b
        res = run_channel_b(self._ctx(), {}, None, None, model_name='not-exist')
        self.assertFalse(res.ran)
        self.assertIn('not-exist', res.reason)
