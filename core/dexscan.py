# -*- coding: utf-8 -*-
"""dexscan.py · 自研 dex 字符串 / 引用扫描

数据源：dex_strings（零外部依赖）。
职责：
  1. 直读 APK 内 classes*.dex（不落盘、不执行）
  2. 提取全部字符串（带 classesN.dex#str[索引] 定位）、类型描述符、方法引用
  3. 供 R-STR-01/02（字符串）与 R-CODE-01 弱模式（类型引用）使用
"""

import re
import struct
import zipfile

from . import registry


class DexFact(object):
    __slots__ = ('dex_file', 'index', 'value')

    def __init__(self, dex_file, index, value):
        self.dex_file = dex_file
        self.index = index
        self.value = value

    @property
    def location(self):
        return '%s#str[%d]' % (self.dex_file, self.index)


class DexFacts(object):
    def __init__(self):
        self.strings = []          # list[DexFact]
        self.type_descriptors = set()
        self.method_refs = set()
        self.dex_files = []
        self.errors = []           # list[str]，单 dex 解析失败不阻断其余

    def find_strings(self, pattern, limit=None):
        """返回 [(DexFact, match)]；pattern 预编译或用字符串。"""
        rx = re.compile(pattern) if isinstance(pattern, str) else pattern
        out = []
        for f in self.strings:
            m = rx.search(f.value)
            if m:
                out.append((f, m))
                if limit and len(out) >= limit:
                    break
        return out

    def find_type_refs(self, descriptor):
        return descriptor in self.type_descriptors


def _decode_mutf8(raw):
    # MUTF-8：内嵌 NUL 编码为 0xC0 0x80；其余与 UTF-8 兼容
    if b'\xc0\x80' in raw:
        raw = raw.replace(b'\xc0\x80', b'\x00')
    return raw.decode('utf-8', 'replace')


def _read_string_at(data, pos):
    end = data.find(b'\x00', pos)
    if end < 0:
        end = len(data)
    return _decode_mutf8(data[pos:end]), end + 1


def parse_dex(data, dex_name):
    """解析单个 dex 字节流 → dict{strings, type_descriptors, method_refs}。"""
    if len(data) < 112 or data[:4] != b'dex\n':
        raise ValueError('不是合法 dex：%s' % dex_name)
    string_ids_size, string_ids_off = struct.unpack_from('<II', data, 0x38)
    type_ids_size, type_ids_off = struct.unpack_from('<II', data, 0x40)
    method_ids_size, method_ids_off = struct.unpack_from('<II', data, 0x58)

    # 字符串表
    strings = []
    count = min(string_ids_size, registry.DEX_SCAN_MAX_STRINGS)
    for i in range(count):
        if string_ids_off + 4 * i + 4 > len(data):
            break
        off = struct.unpack_from('<I', data, string_ids_off + 4 * i)[0]
        if off >= len(data):
            strings.append('')
            continue
        s, _ = _read_string_at(data, off)
        strings.append(s)

    def str_at(idx):
        if 0 <= idx < len(strings):
            return strings[idx]
        return ''

    # 类型描述符
    type_descriptors = set()
    for i in range(min(type_ids_size, registry.DEX_SCAN_MAX_STRINGS)):
        if type_ids_off + 4 * i + 4 > len(data):
            break
        d_idx = struct.unpack_from('<I', data, type_ids_off + 4 * i)[0]
        d = str_at(d_idx)
        if d:
            type_descriptors.add(d)

    # 方法引用：class_idx(u2) proto_idx(u2) name_idx(u4)
    method_refs = set()
    for i in range(min(method_ids_size, registry.DEX_SCAN_MAX_STRINGS)):
        if method_ids_off + 8 * i + 8 > len(data):
            break
        class_idx, proto_idx, name_idx = struct.unpack_from('<HHI', data, method_ids_off + 8 * i)
        cls = str_at(class_idx)
        if not cls.startswith('L'):
            continue
        name = str_at(name_idx)
        if cls and name:
            method_refs.add('%s;->%s' % (cls, name))

    return {'strings': strings, 'type_descriptors': type_descriptors, 'method_refs': method_refs}


def scan_apk_dex(apk_path):
    """扫描 APK 内全部 classes*.dex。单个 dex 失败记入 errors 不阻断。"""
    facts = DexFacts()
    with zipfile.ZipFile(apk_path) as z:
        dex_names = sorted(
            [n for n in z.namelist() if re.match(r'^classes\d*\.dex$', n)],
            key=lambda n: (0 if n == 'classes.dex' else int(re.search(r'\d+', n).group()) if re.search(r'\d+', n) else 0),
        )
        for name in dex_names:
            facts.dex_files.append(name)
            try:
                parsed = parse_dex(z.read(name), name)
            except Exception as e:  # noqa: BLE001 —— 单文件失败不阻断整体，如实记录
                facts.errors.append('%s: %s' % (name, e))
                continue
            for i, s in enumerate(parsed['strings']):
                facts.strings.append(DexFact(name, i, s))
            facts.type_descriptors |= parsed['type_descriptors']
            facts.method_refs |= parsed['method_refs']
    return facts
