# -*- coding: utf-8 -*-
"""adapters.py · apktool 封装（probe + decode smali / 资源 + 降级路径）

- 工具链查找顺序：项目内 .tools/ → 环境变量（JAVA_HOME） → PATH（总档 §10）
- apktool 调用固定 `-p <framework 目录>`（项目可控路径 .tools/framework）
- 解码产物放工作区外临时区（%TEMP%/apkaudit_decode/<sha256前16>/），可重建、不入库（总档 §10）
- 工具缺席时返回明确降级状态：M/S 类照跑，语义类规则声明覆盖缺口（不静默）
"""

import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile

from . import registry


class Toolchain(object):
    def __init__(self):
        self.java = None
        self.apktool_jar = None
        self.java_version = ''
        self.errors = []

    @property
    def available(self):
        return bool(self.java and self.apktool_jar)

    def describe(self):
        if self.available:
            return 'java=%s, apktool=%s' % (
                self.java_version or self.java,
                os.path.basename(self.apktool_jar))
        return '不可用（%s）' % '；'.join(self.errors) if self.errors else '不可用'


def _probe_java(project_root):
    tools_dir = os.path.join(project_root, '.tools')
    if os.path.isdir(tools_dir):
        for name in sorted(os.listdir(tools_dir)):
            low = name.lower()
            if low.startswith('jre') or low.startswith('jdk'):
                for exe in ('java.exe', 'java'):
                    cand = os.path.join(tools_dir, name, 'bin', exe)
                    if os.path.isfile(cand):
                        return cand
    java_home = os.environ.get('JAVA_HOME')
    if java_home:
        for exe in ('java.exe', 'java'):
            cand = os.path.join(java_home, 'bin', exe)
            if os.path.isfile(cand):
                return cand
    found = shutil.which('java')
    return found


def _probe_apktool(project_root):
    tools_dir = os.path.join(project_root, '.tools')
    if not os.path.isdir(tools_dir):
        return None
    jars = [n for n in os.listdir(tools_dir)
            if n.lower().startswith(registry.APKTOOL_JAR_PREFIX) and n.lower().endswith('.jar')]
    if not jars:
        return None
    jars.sort()
    return os.path.join(tools_dir, jars[-1])


def probe_toolchain(project_root):
    tc = Toolchain()
    tc.java = _probe_java(project_root)
    if not tc.java:
        tc.errors.append('未找到 java（.tools/JRE、JAVA_HOME、PATH 均无）')
    else:
        try:
            out = subprocess.run([tc.java, '-version'], capture_output=True,
                                 timeout=30, text=True)
            line = (out.stderr or out.stdout or '').strip().splitlines()
            tc.java_version = line[0] if line else ''
        except Exception as e:  # noqa: BLE001
            tc.errors.append('java 探测失败: %s' % e)
    tc.apktool_jar = _probe_apktool(project_root)
    if not tc.apktool_jar:
        tc.errors.append('未找到 .tools/apktool_*.jar')
    return tc


class DecodeResult(object):
    def __init__(self, out_dir):
        self.out_dir = out_dir
        self.ok = False
        self.error = ''
        self.stdout = ''
        self.stderr = ''
        self.reused = False


def decode_with_apktool(toolchain, apk_path, sha256, project_root, timeout=None,
                        force=False, runner=None):
    """解码 APK → 临时区目录。返回 DecodeResult。"""
    if not toolchain.available:
        res = DecodeResult('')
        res.error = '工具链不可用：%s' % toolchain.describe()
        return res

    timeout = timeout or registry.APKTOOL_DECODE_TIMEOUT_SECONDS
    out_dir = os.path.join(tempfile.gettempdir(), registry.DECODE_TMP_DIRNAME, sha256[:16])
    framework_dir = os.path.join(project_root, '.tools', 'framework')
    os.makedirs(framework_dir, exist_ok=True)
    res = DecodeResult(out_dir)

    if not force and os.path.isfile(os.path.join(out_dir, 'AndroidManifest.xml')):
        res.ok = True
        res.reused = True
        return res

    if os.path.isdir(out_dir):
        shutil.rmtree(out_dir, ignore_errors=True)
    os.makedirs(out_dir, exist_ok=True)

    cmd = [toolchain.java, '-jar', toolchain.apktool_jar, 'd', '-f',
           '-o', out_dir, '-p', framework_dir, apk_path]
    try:
        if runner is not None:
            proc = runner.run_subprocess(cmd, timeout=timeout)
        else:
            proc = subprocess.run(cmd, capture_output=True, timeout=timeout, text=True,
                                  errors='replace')
    except subprocess.TimeoutExpired:
        res.error = 'apktool 解码超时（%ss）' % timeout
        return res
    except Exception as e:  # noqa: BLE001
        res.error = 'apktool 调用失败: %s' % e
        return res

    res.stdout = (proc.stdout or '')[-4000:]
    res.stderr = (proc.stderr or '')[-4000:]
    manifest = os.path.join(out_dir, 'AndroidManifest.xml')
    smali_dirs = [d for d in os.listdir(out_dir) if re.match(r'^smali(_classes\d+)?$', d)]
    if proc.returncode == 0 and os.path.isfile(manifest) and smali_dirs:
        res.ok = True
    else:
        res.error = 'apktool 返回码 %s；manifest=%s smali_dirs=%s' % (
            proc.returncode, os.path.isfile(manifest), smali_dirs)
    return res


class SmaliFacts(object):
    """解码产物的 smali 索引（smali_src 数据源）。"""

    def __init__(self, decode_dir):
        self.root = decode_dir
        self.smali_dirs = []
        self.files = []            # 相对 decode_dir 的路径
        self.class_index = {}      # 'com/foo/Bar' → 相对路径
        self._lines_cache = {}
        if os.path.isdir(decode_dir):
            for name in sorted(os.listdir(decode_dir)):
                if re.match(r'^smali(_classes\d+)?$', name):
                    self.smali_dirs.append(name)
            for d in self.smali_dirs:
                base = os.path.join(decode_dir, d)
                for dirpath, _dirnames, filenames in os.walk(base):
                    for fn in filenames:
                        if fn.endswith('.smali'):
                            full = os.path.join(dirpath, fn)
                            rel = os.path.relpath(full, decode_dir).replace('\\', '/')
                            self.files.append(rel)
                            cls = fn[:-len('.smali')]
                            pkg_rel = os.path.relpath(dirpath, os.path.join(decode_dir, d))
                            if pkg_rel != '.':
                                cls = pkg_rel.replace('\\', '/') + '/' + cls
                            self.class_index[cls] = rel

    def read_lines(self, rel_path):
        if rel_path not in self._lines_cache:
            full = os.path.join(self.root, rel_path.replace('/', os.sep))
            try:
                with open(full, 'r', encoding='utf-8', errors='replace') as f:
                    self._lines_cache[rel_path] = f.read().splitlines()
            except OSError:
                self._lines_cache[rel_path] = []
        return self._lines_cache[rel_path]

    def class_name_of(self, rel_path):
        """从 .class 行读全限定名（Lcom/foo/Bar; → com/foo/Bar）。"""
        for line in self.read_lines(rel_path)[:20]:
            if line.startswith('.class '):
                m = re.search(r'L([A-Za-z0-9_/$]+);', line)
                if m:
                    return m.group(1)
        return ''

    def app_files(self, package, notes=None):
        """自有代码文件列表。

        主判定：manifest package 前缀匹配。
        兜底（换样本泛化性）：若包名前缀**一个都没匹配到**（多进程/插件化/包名与代码路径
        不一致的情形），退化为"排除已知库前缀"法，并记入 notes 说明判定方式已退化。
        """
        pkg_path = package.replace('.', '/') + '/' if package else ''
        by_pkg = []
        by_exclusion = []
        for rel in self.files:
            # rel = 'smali[/classesN]/<pkg 路径>/<类>.smali'
            m = re.match(r'^smali(?:_classes\d+)?/(.+)$', rel)
            if not m:
                continue
            inner = m.group(1)
            if pkg_path and inner.startswith(pkg_path):
                by_pkg.append(rel)
            elif not inner.startswith(registry.LIBRARY_PREFIXES):
                by_exclusion.append(rel)
        if pkg_path and not by_pkg and by_exclusion:
            if notes is not None:
                notes.append(
                    '自有代码判定退化：包名前缀 %s 无匹配，改用"排除已知库前缀"法（%d 个文件）'
                    % (pkg_path, len(by_exclusion)))
            return by_exclusion
        return by_pkg

    def method_blocks(self, rel_path):
        """切分方法块：[(sig, name, start_line, end_line, body_lines)]，行号 1 基。"""
        lines = self.read_lines(rel_path)
        blocks = []
        i = 0
        n = len(lines)
        while i < n:
            line = lines[i]
            if line.startswith('.method'):
                start = i + 1
                sig = line[len('.method'):].strip()
                name = ''
                m = re.search(r'([A-Za-z0-9_$\-<>]+)\(', sig)
                if m:
                    name = m.group(1)
                body = []
                j = i + 1
                while j < n and not lines[j].startswith('.end method'):
                    body.append((j + 1, lines[j]))
                    j += 1
                blocks.append((sig, name, start, j + 1, body))
                i = j + 1
            else:
                i += 1
        return blocks


class ResFacts(object):
    """res_decoded 数据源：资源字符串（res/values/strings.xml 等）。"""

    def __init__(self, decode_dir):
        self.root = decode_dir
        self.xml_files = []   # [(相对路径, 行列表)]
        res_dir = os.path.join(decode_dir, 'res')
        if os.path.isdir(res_dir):
            for dirpath, _dirnames, filenames in os.walk(res_dir):
                for fn in filenames:
                    if fn.endswith('.xml') and os.path.basename(dirpath) in ('values', 'xml'):
                        full = os.path.join(dirpath, fn)
                        rel = os.path.relpath(full, decode_dir).replace('\\', '/')
                        try:
                            with open(full, 'r', encoding='utf-8', errors='replace') as f:
                                self.xml_files.append((rel, f.read().splitlines()))
                        except OSError:
                            pass

    def find_xml(self, name_hint):
        """按文件名（如 network_security_config）查找 XML。"""
        for rel, lines in self.xml_files:
            if name_hint in os.path.basename(rel):
                return rel, lines
        return None, None

    def iter_string_values(self):
        """产出 (资源名, 值, 相对路径, 行号)：仅字符串资源的文本值。"""
        rx = re.compile(r'<string\s+name="([^"]*)"[^>]*>([^<]*)</string>')
        for rel, lines in self.xml_files:
            for idx, line in enumerate(lines, 1):
                m = rx.search(line)
                if m:
                    yield m.group(1), m.group(2), rel, idx
