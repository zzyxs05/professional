# -*- coding: utf-8 -*-
"""test_dex_weak_mode.py · OBS-5 回归测试

验证 DEX string_data_item 的 uleb128 长度前缀被正确剥离，以及 R-CODE-01
弱模式（smali 不可用时）能据类型描述符给出「待复核」命中。

全部使用合成 dex 字节流，不依赖真实 APK、不联网、不写 evidence/。
"""

import os
import struct
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import registry
from core.dexscan import DexFacts, _read_string_at, parse_dex
from core.rules.code import r_code_01


LOADER = b'Ldalvik/system/DexClassLoader;'


def _uleb128(n):
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def make_min_dex(strings):
    """构造最小合法 dex：header + string_data + string_ids + type_ids。"""
    header = bytearray(112)
    header[0:8] = b'dex\n035\x00'

    blob = bytearray()
    offsets = []
    base = 112
    for s in strings:
        offsets.append(base + len(blob))
        blob += _uleb128(len(s)) + s + b'\x00'
    string_ids_off = base + len(blob)
    ids = b''.join(struct.pack('<I', off) for off in offsets)
    type_ids_off = string_ids_off + len(ids)
    tids = b''.join(struct.pack('<I', i) for i in range(len(strings)))

    struct.pack_into('<II', header, 0x38, len(strings), string_ids_off)
    struct.pack_into('<II', header, 0x40, len(strings), type_ids_off)
    struct.pack_into('<II', header, 0x58, 0, 0)   # method_ids 空
    return bytes(header) + bytes(blob) + ids + tids


class FakeCtx(object):
    def __init__(self, dex, smali=None):
        self.dex = dex
        self.smali = smali
        self.app_package = 'com.test.app'
        self.rule_notes = []


class TestStringDataPrefix(unittest.TestCase):
    def test_single_byte_length_is_skipped(self):
        raw = b'\x1e' + LOADER + b'\x00'
        s, _ = _read_string_at(raw, 0)
        self.assertEqual(s, LOADER.decode('utf-8'))

    def test_multibyte_length_is_skipped(self):
        payload = b'L' + b'x' * 199 + b';'          # 201 字节，uleb128 需 2 字节
        raw = _uleb128(len(payload)) + payload + b'\x00'
        s, _ = _read_string_at(raw, 0)
        self.assertEqual(s, payload.decode('utf-8'))

    def test_mutf8_embedded_nul(self):
        raw = b'\x04a\xc0\x80b\x00'
        s, _ = _read_string_at(raw, 0)
        self.assertEqual(s, 'a\x00b')

    def test_truncated_prefix_does_not_crash(self):
        s, _ = _read_string_at(b'\x80', 0)
        self.assertEqual(s, '')

    def test_parse_dex_returns_clean_descriptors(self):
        parsed = parse_dex(make_min_dex([LOADER]), 'classes.dex')
        self.assertEqual(parsed['type_descriptors'], {LOADER.decode('utf-8')})
        self.assertEqual(parsed['strings'], [LOADER.decode('utf-8')])


class TestWeakModeAfterFix(unittest.TestCase):
    def _ctx_from_dex(self, strings):
        parsed = parse_dex(make_min_dex(strings), 'classes.dex')
        dex = DexFacts()
        dex.type_descriptors = parsed['type_descriptors']
        dex.strings = []
        return FakeCtx(dex)

    def test_detects_loader_type_without_smali(self):
        ctx = self._ctx_from_dex([LOADER])
        hits = r_code_01.run(ctx)
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].max_status, registry.STATUS_REVIEW)
        self.assertIn('dex#type', hits[0].location)
        self.assertIn('弱证据', hits[0].note)

    def test_find_type_refs_is_usable(self):
        ctx = self._ctx_from_dex([LOADER])
        self.assertTrue(ctx.dex.find_type_refs('Ldalvik/system/DexClassLoader;'))

    def test_quiet_when_no_loader_type(self):
        ctx = self._ctx_from_dex([b'Ljava/lang/String;', b'Landroid/app/Activity;'])
        self.assertEqual(r_code_01.run(ctx), [])


if __name__ == '__main__':
    unittest.main()
