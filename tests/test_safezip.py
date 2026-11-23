# -*- coding: utf-8 -*-
"""tests/test_safezip.py · safezip 上限行为与运行时边界假设

第 5 次审查核实的运行时假设（有测试钉住，若未来换 zip 实现会在这里报警）：
CPython zipfile 以中央目录声明的 file_size 作为读取边界——谎报头的成员
读满声明长度即触发 Bad CRC-32，不会无限解压打挂内存。
"""

import io
import os
import sys
import unittest
import zipfile

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.safezip import ZipMemberTooLarge, read_member


def _make_zip(data, name='member.bin'):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr(name, data)
    buf.seek(0)
    return zipfile.ZipFile(buf)


class TestSafezip(unittest.TestCase):

    def test_normal_read_unchanged(self):
        """正常成员读取结果等同 z.read。"""
        z = _make_zip(b'hello world')
        self.assertEqual(read_member(z, 'member.bin'), b'hello world')

    def test_declared_oversize_rejected(self):
        """声明体积超限：不启动解压直接拒绝。"""
        data = b'x' * 100
        z = _make_zip(data)
        z.getinfo('member.bin').file_size = 10 ** 9  # 模拟超大声明
        with self.assertRaises(ZipMemberTooLarge):
            read_member(z, 'member.bin', limit=1024)

    def test_lying_header_raises_badzipfile(self):
        """谎报头（声明 1 字节、实际 100 字节）：CPython zipfile 读满声明
        长度即做 CRC 核对，抛 BadZipFile——不会以无限解压打挂内存。
        这钉住了 safezip「声明值预检即完备」所依赖的运行时行为。"""
        data = b'x' * 100
        z = _make_zip(data)
        z.getinfo('member.bin').file_size = 1  # 谎报
        with self.assertRaises(zipfile.BadZipFile):
            read_member(z, 'member.bin', limit=16)

    def test_missing_member_raises_keyerror(self):
        """成员不存在：保持 z.read 的 KeyError 语义。"""
        z = _make_zip(b'abc')
        with self.assertRaises(KeyError):
            read_member(z, 'no_such_member')


if __name__ == '__main__':
    unittest.main()
