# -*- coding: utf-8 -*-
"""test_channel_b.py · B 通道响应解析鲁棒性（合成响应，不依赖模型）

背景：去禁令后模型输出更自由，可能出现尾部畸形字段（如 `, ""`）；
程序侧必须能宽容解析，避免把"确认可疑"误判为"无法判断"进而误降级结论。
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
