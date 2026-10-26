# -*- coding: utf-8 -*-
"""axml.py · 自研 AXML（Android 二进制 XML）直读

数据源：manifest（零外部依赖，见 specification.md §1）。
职责：
  1. 解析二进制 AXML（StringPool / 事件流 / 属性 typed value）
  2. 重建可读 XML 文本 + 逐元素行号（结论定位用「重建 XML 行号区间」）
  3. 提取结构化事实 ManifestFacts（package / 权限 / application 属性 / 组件）

纪律：解析失败抛 AXMLParseError，由上层转「样本级无法判定」，不吞错。
"""

import struct

# ---- chunk 类型
CHUNK_STRING_POOL = 0x0001
CHUNK_XML_START_NS = 0x0100
CHUNK_XML_END_NS = 0x0101
CHUNK_XML_START_ELEMENT = 0x0102
CHUNK_XML_END_ELEMENT = 0x0103
CHUNK_XML_CDATA = 0x0104

# ---- attribute typed value 类型
TYPE_NULL = 0x00
TYPE_REFERENCE = 0x01
TYPE_ATTRIBUTE = 0x02
TYPE_STRING = 0x03
TYPE_FLOAT = 0x04
TYPE_DIMENSION = 0x05
TYPE_INT_DEC = 0x10
TYPE_INT_HEX = 0x11
TYPE_INT_BOOLEAN = 0x12
TYPE_INT_COLOR_ARGB8 = 0x1c

NO_ENTRY = 0xFFFFFFFF


class AXMLParseError(Exception):
    pass


class _StringPool(object):
    UTF8_FLAG = 1 << 8

    def __init__(self, data, offset):
        try:
            ctype, header_size, size = struct.unpack_from('<HHI', data, offset)
            if ctype != CHUNK_STRING_POOL:
                raise AXMLParseError('chunk 0x%04x 不是 StringPool' % ctype)
            (string_count, style_count, flags, strings_start,
             styles_start) = struct.unpack_from('<IIIII', data, offset + 8)
            self.utf8 = bool(flags & self.UTF8_FLAG)
            offsets = struct.unpack_from('<%dI' % string_count, data, offset + 28)
            self.strings = []
            for off in offsets:
                pos = offset + strings_start + off
                self.strings.append(self._read_string(data, pos))
        except struct.error as e:
            raise AXMLParseError('StringPool 解析失败: %s' % e)

    def _read_string(self, data, pos):
        if self.utf8:
            # UTF-8 模式：先 utf16 长度、再 utf8 字节长度（各自 1-2 字节），然后数据
            n1 = data[pos]
            pos += 1
            if n1 & 0x80:
                pos += 1
            n = data[pos]
            pos += 1
            if n & 0x80:
                n = ((n & 0x7F) << 8) | data[pos]
                pos += 1
            raw = data[pos:pos + n]
            try:
                return raw.decode('utf-8')
            except UnicodeDecodeError:
                return raw.decode('utf-8', 'replace')
        else:
            n = struct.unpack_from('<H', data, pos)[0]
            pos += 2
            if n & 0x8000:
                n = ((n & 0x7FFF) << 16) | struct.unpack_from('<H', data, pos)[0]
                pos += 2
            raw = data[pos:pos + n * 2]
            return raw.decode('utf-16-le', 'replace')

    def get(self, idx):
        if idx is None or idx < 0 or idx >= len(self.strings):
            return ''
        return self.strings[idx]


class XmlAttr(object):
    __slots__ = ('ns', 'name', 'value', 'line')

    def __init__(self, ns, name, value, line):
        self.ns = ns
        self.name = name
        self.value = value
        self.line = line


class XmlElement(object):
    __slots__ = ('tag', 'attrs', 'children', 'parent', 'line_start', 'line_end',
                 'orig_line', 'ns_uri')

    def __init__(self, tag, line):
        self.tag = tag
        self.attrs = []          # list[XmlAttr]
        self.children = []
        self.parent = None
        self.line_start = line   # 重建文本行号（1 基）
        self.line_end = line
        self.orig_line = line    # AXML 原始源码行号
        self.ns_uri = None

    def attr(self, name):
        for a in self.attrs:
            if a.name == name:
                return a.value
        return None

    def attr_obj(self, name):
        for a in self.attrs:
            if a.name == name:
                return a
        return None

    def bool_attr(self, name):
        v = self.attr(name)
        if v is None:
            return None
        return str(v).lower() == 'true'

    def children_by_tag(self, tag):
        return [c for c in self.children if c.tag == tag]


class XmlDocument(object):
    def __init__(self, string_pool, root, ns_prefixes):
        self.string_pool = string_pool
        self.root = root              # <manifest> 元素
        self.ns_prefixes = ns_prefixes  # uri -> prefix
        self.rebuilt_xml = ''         # 重建 XML 文本
        self.lines = []               # 重建文本行表

    def to_text(self):
        return '\n'.join(self.lines)


def _format_attr_value(v):
    return (v.replace('&', '&amp;').replace('<', '&lt;')
             .replace('>', '&gt;').replace('"', '&quot;'))


def parse_axml(data):
    """解析二进制 AXML，返回 XmlDocument（含重建文本与行号）。"""
    if len(data) < 8:
        raise AXMLParseError('数据过短')
    ctype, header_size, size = struct.unpack_from('<HHI', data, 0)
    if ctype != 0x0003:
        raise AXMLParseError('不是 AXML（magic=0x%04x）' % ctype)

    pool = None
    ns_prefixes = {}
    events = []  # ('start'|'end'|'cdata', payload)
    pos = 8
    n = len(data)
    while pos + 8 <= n:
        ctype, cheader, csize = struct.unpack_from('<HHI', data, pos)
        if csize == 0:
            break
        if ctype == CHUNK_STRING_POOL:
            pool = _StringPool(data, pos)
        elif ctype == CHUNK_XML_START_NS:
            prefix_idx, uri_idx = struct.unpack_from('<II', data, pos + 16)
            ns_prefixes[pool.get(uri_idx)] = pool.get(prefix_idx)
        elif ctype == CHUNK_XML_START_ELEMENT:
            line, comment = struct.unpack_from('<II', data, pos + 8)
            ns_idx, name_idx = struct.unpack_from('<II', data, pos + 16)
            attr_start, attr_size, attr_count = struct.unpack_from('<HHH', data, pos + 24)
            attrs = []
            for i in range(attr_count):
                apos = pos + 16 + attr_start + i * attr_size
                a_ns, a_name, a_raw = struct.unpack_from('<III', data, apos)
                a_size, a_res0, a_type = struct.unpack_from('<HBB', data, apos + 12)
                a_data = struct.unpack_from('<I', data, apos + 16)[0]
                value = _resolve_value(pool, a_raw, a_type, a_data)
                attrs.append((pool.get(a_ns), pool.get(a_name), value, line))
            events.append(('start', (pool.get(name_idx), ns_idx, attrs, line)))
        elif ctype == CHUNK_XML_END_ELEMENT:
            line, comment = struct.unpack_from('<II', data, pos + 8)
            ns_idx, name_idx = struct.unpack_from('<II', data, pos + 16)
            events.append(('end', (pool.get(name_idx), line)))
        elif ctype == CHUNK_XML_CDATA:
            if pool is not None:
                data_idx = struct.unpack_from('<I', data, pos + 8)[0]
                events.append(('cdata', pool.get(data_idx)))
        pos += csize

    if pool is None:
        raise AXMLParseError('缺少 StringPool')
    if not events:
        raise AXMLParseError('无 XML 事件')

    root = _build_tree(events, ns_prefixes)
    doc = XmlDocument(pool, root, ns_prefixes)
    doc.lines = _render(root, ns_prefixes)
    doc.rebuilt_xml = doc.to_text()
    return doc


def _resolve_value(pool, raw, vtype, data):
    if raw != NO_ENTRY:
        return pool.get(raw)
    if vtype == TYPE_STRING:
        return pool.get(data)
    if vtype == TYPE_INT_BOOLEAN:
        return 'true' if data != 0 else 'false'
    if vtype == TYPE_INT_DEC:
        return str(data)
    if vtype == TYPE_INT_HEX:
        return '0x%08x' % data
    if vtype == TYPE_REFERENCE:
        return '@0x%08x' % data
    if vtype == TYPE_ATTRIBUTE:
        return '?0x%08x' % data
    if vtype == TYPE_FLOAT:
        return repr(struct.unpack('<f', struct.pack('<I', data))[0])
    if vtype == TYPE_DIMENSION:
        return '%s' % data
    if vtype == TYPE_INT_COLOR_ARGB8:
        return '#%08x' % data
    if vtype == TYPE_NULL:
        return None
    return str(data)


def _build_tree(events, ns_prefixes):
    root = None
    stack = []
    for kind, payload in events:
        if kind == 'start':
            tag, ns_idx, attrs, line = payload
            el = XmlElement(tag, line)
            for a_ns, a_name, a_value, a_line in attrs:
                el.attrs.append(XmlAttr(a_ns, a_name, a_value, a_line))
            if stack:
                el.parent = stack[-1]
                stack[-1].children.append(el)
            else:
                root = el
            stack.append(el)
        elif kind == 'end':
            if stack:
                stack.pop()
        elif kind == 'cdata':
            if stack and payload:
                el = XmlElement('#text', 0)
                el.attrs.append(XmlAttr(None, '#text', payload, 0))
                stack[-1].children.append(el)
    if root is None:
        raise AXMLParseError('未找到根元素')
    return root


def _attr_display_name(attr, ns_prefixes):
    if attr.ns:
        prefix = ns_prefixes.get(attr.ns, '')
        if prefix:
            return '%s:%s' % (prefix, attr.name)
    return attr.name


def _render(root, ns_prefixes):
    """重建 XML 文本；同时写回每个元素的 line_start / line_end（1 基行号）。"""
    lines = ['<?xml version="1.0" encoding="utf-8"?>']

    def walk(el, depth):
        indent = '    ' * depth
        if el.tag == '#text':
            lines.append(indent + _format_attr_value(str(el.attrs[0].value)))
            el.line_start = el.line_end = len(lines)
            return
        parts = ['<' + el.tag]
        for a in el.attrs:
            name = _attr_display_name(a, ns_prefixes)
            if a.value is not None:
                parts.append(' %s="%s"' % (name, _format_attr_value(str(a.value))))
            else:
                parts.append(' %s' % name)
        header = indent + ''.join(parts)
        if not el.children:
            lines.append(header + '/>')
            el.line_start = el.line_end = len(lines)
        else:
            lines.append(header + '>')
            el.line_start = len(lines)
            for c in el.children:
                walk(c, depth + 1)
            lines.append(indent + '</%s>' % el.tag)
            el.line_end = len(lines)

    walk(root, 0)
    return lines


# ------------------------------------------------------------------ 事实提取
class PermissionDecl(object):
    __slots__ = ('name', 'line')

    def __init__(self, name, line):
        self.name = name
        self.line = line


class ComponentFacts(object):
    __slots__ = ('ctype', 'name', 'exported', 'permission', 'read_permission',
                 'write_permission', 'actions', 'has_intent_filter',
                 'line_start', 'line_end', 'authorities')

    def __init__(self, ctype, name):
        self.ctype = ctype
        self.name = name
        self.exported = None
        self.permission = None
        self.read_permission = None
        self.write_permission = None
        self.actions = []
        self.has_intent_filter = False
        self.line_start = 0
        self.line_end = 0
        self.authorities = None


class ManifestFacts(object):
    def __init__(self):
        self.package = ''
        self.permissions = []          # list[PermissionDecl]
        self.declared_permissions = []  # <permission> 自定义声明
        self.app_attrs = {}            # name -> value
        self.components = []           # list[ComponentFacts]
        self.doc = None                # XmlDocument

    def components_by_type(self, ctype):
        return [c for c in self.components if c.ctype == ctype]

    def has_permission(self, name):
        return any(p.name == name for p in self.permissions)


def extract_manifest_facts(doc):
    root = doc.root
    if root.tag != 'manifest':
        raise AXMLParseError('根元素不是 <manifest>（实际 %s）' % root.tag)
    facts = ManifestFacts()
    facts.doc = doc
    facts.package = root.attr('package') or ''

    def qualify(name):
        if not name:
            return ''
        if name.startswith('.'):
            return facts.package + name
        if '.' not in name:
            return facts.package + '.' + name
        return name

    for child in root.children:
        if child.tag == 'uses-permission':
            nm = child.attr('name')
            if nm:
                facts.permissions.append(PermissionDecl(nm, child.line_start))
        elif child.tag == 'permission':
            nm = child.attr('name')
            if nm:
                facts.declared_permissions.append(nm)
        elif child.tag == 'application':
            for a in child.attrs:
                facts.app_attrs[a.name] = a.value
            for comp in child.children:
                if comp.tag not in ('activity', 'service', 'receiver', 'provider'):
                    continue
                cf = ComponentFacts(comp.tag, qualify(comp.attr('name')))
                cf.exported = comp.bool_attr('exported')
                cf.permission = comp.attr('permission')
                cf.read_permission = comp.attr('readPermission')
                cf.write_permission = comp.attr('writePermission')
                cf.authorities = comp.attr('authorities')
                cf.line_start = comp.line_start
                cf.line_end = comp.line_end
                for flt in comp.children_by_tag('intent-filter'):
                    cf.has_intent_filter = True
                    for act in flt.children_by_tag('action'):
                        an = act.attr('name')
                        if an:
                            cf.actions.append(an)
                facts.components.append(cf)
    return facts


def parse_manifest_bytes(data):
    """入口：字节 → (XmlDocument, ManifestFacts)。"""
    doc = parse_axml(data)
    facts = extract_manifest_facts(doc)
    return doc, facts
