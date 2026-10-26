# -*- coding: utf-8 -*-
"""axml_builder.py · 合成 AXML 二进制构造器（测试夹具，不依赖真实 APK）

支持 axml.py 所需子集：StringPool(UTF-8) / StartNamespace / StartElement(+attrs) /
EndElement。属性值支持 string / bool / int / reference 四种 typed value。
"""

import struct

UTF8_FLAG = 0x100
TYPE_REFERENCE = 0x01
TYPE_STRING = 0x03
TYPE_INT_DEC = 0x10
TYPE_INT_BOOLEAN = 0x12


class Attr(object):
    def __init__(self, name, value, ns=None):
        """value: ('string', s) | ('bool', True/False) | ('int', n) | ('ref', id)"""
        self.name = name
        self.value = value
        self.ns = ns


class Node(object):
    def __init__(self, tag, line=1, attrs=None, children=None):
        self.tag = tag
        self.line = line
        self.attrs = attrs or []
        self.children = children or []


ANDROID_NS = 'http://schemas.android.com/apk/res/android'


class AxmlBuilder(object):
    def __init__(self):
        self._index = {}
        self._strings = []

    def _s(self, s):
        if s not in self._index:
            self._index[s] = len(self._strings)
            self._strings.append(s)
        return self._index[s]

    def build(self, root, namespaces=(('android', ANDROID_NS),)):
        self._index = {}
        self._strings = []

        # 1) 收集字符串
        for prefix, uri in namespaces:
            self._s(prefix)
            self._s(uri)

        def visit(n):
            self._s(n.tag)
            for a in n.attrs:
                if a.ns:
                    self._s(a.ns)
                self._s(a.name)
                kind, val = a.value
                if kind == 'string':
                    self._s(val)
            for c in n.children:
                visit(c)

        visit(root)

        # 2) StringPool chunk
        offsets = []
        data = bytearray()
        for s in self._strings:
            offsets.append(len(data))
            b = s.encode('utf-8')
            assert len(s) < 0x80 and len(b) < 0x80, '夹具只支持短字符串'
            data += bytes([len(s), len(b)]) + b + b'\x00'
        header_size = 28
        strings_start = header_size + 4 * len(self._strings)
        sp_size = strings_start + len(data)
        sp = bytearray()
        sp += struct.pack('<HHI', 0x0001, header_size, sp_size)
        sp += struct.pack('<IIIII', len(self._strings), 0, UTF8_FLAG, strings_start, 0)
        for o in offsets:
            sp += struct.pack('<I', o)
        sp += bytes(data)

        # 3) 命名空间
        ns_uri_idx = {uri: self._s(uri) for _p, uri in namespaces}
        events = bytearray()
        for prefix, uri in namespaces:
            events += struct.pack('<HHIIIII', 0x0100, 16, 24, 1, 0xFFFFFFFF,
                                  self._s(prefix), self._s(uri))

        # 4) 元素
        def attr_bytes(a):
            ns_i = ns_uri_idx.get(a.ns, 0xFFFFFFFF) if a.ns else 0xFFFFFFFF
            name_i = self._s(a.name)
            kind, val = a.value
            if kind == 'string':
                raw = self._s(val)
                dtype, ddata = TYPE_STRING, raw
            elif kind == 'bool':
                raw = 0xFFFFFFFF
                dtype, ddata = TYPE_INT_BOOLEAN, (0xFFFFFFFF if val else 0)
            elif kind == 'int':
                raw = 0xFFFFFFFF
                dtype, ddata = TYPE_INT_DEC, val
            elif kind == 'ref':
                raw = 0xFFFFFFFF
                dtype, ddata = TYPE_REFERENCE, val
            else:
                raise ValueError(kind)
            return struct.pack('<IIIHBBI', ns_i, name_i, raw, 8, 0, dtype, ddata)

        def emit(n):
            buf = bytearray()
            attr_count = len(n.attrs)
            size = 36 + 20 * attr_count
            buf += struct.pack('<HHI', 0x0102, 16, size)
            buf += struct.pack('<II', n.line, 0xFFFFFFFF)
            buf += struct.pack('<II', 0xFFFFFFFF, self._s(n.tag))
            buf += struct.pack('<HHHHHH', 20, 20, attr_count, 0, 0, 0)
            for a in n.attrs:
                buf += attr_bytes(a)
            for c in n.children:
                buf += emit(c)
            buf += struct.pack('<HHI', 0x0103, 16, 24)
            buf += struct.pack('<II', n.line, 0xFFFFFFFF)
            buf += struct.pack('<II', 0xFFFFFFFF, self._s(n.tag))
            return bytes(buf)

        events += emit(root)
        for prefix, uri in namespaces:
            events += struct.pack('<HHIIIII', 0x0101, 16, 24, 1, 0xFFFFFFFF,
                                  self._s(prefix), self._s(uri))

        total = 8 + len(sp) + len(events)
        head = struct.pack('<HHI', 0x0003, 8, total)
        return head + bytes(sp) + bytes(events)
