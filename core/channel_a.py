# -*- coding: utf-8 -*-
"""channel_a.py · 通道 A：确定性规则引擎

- 逐规则声明数据源依赖（required 为 all-of 组间 any-of）；不可用即显式跳过，进覆盖声明，不静默
- 本模块只做计算；证据落盘由流程层（cli analyze）负责
"""

import importlib
import os
import re
import zipfile

from . import registry
from .adapters import ResFacts, SmaliFacts
from .axml import parse_manifest_bytes
from .dexscan import scan_apk_dex

# (rule_id, module, required_groups)；required_groups: all-of 列表的 any-of 列表
RULES_PIPELINE = [
    ("R-MAN-01", "core.rules.man.r_man_01", [["manifest"]]),
    ("R-MAN-02", "core.rules.man.r_man_02", [["manifest"]]),
    ("R-MAN-03", "core.rules.man.r_man_03", [["manifest"]]),
    ("R-MAN-04", "core.rules.man.r_man_04", [["manifest"]]),
    ("R-MAN-05", "core.rules.man.r_man_05", [["manifest"]]),
    ("R-PERM-01", "core.rules.perm.r_perm_01", [["smali_src"]]),
    ("R-PERM-02", "core.rules.perm.r_perm_02", [["manifest", "smali_src"]]),
    ("R-PERM-03", "core.rules.perm.r_perm_03", [["manifest", "smali_src"]]),
    ("R-STR-01", "core.rules.str.r_str_01", [["dex_strings"]]),
    ("R-STR-02", "core.rules.str.r_str_02", [["dex_strings"]]),
    ("R-CODE-01", "core.rules.code.r_code_01", [["smali_src"], ["dex_strings"]]),
    ("R-CODE-02", "core.rules.code.r_code_02", [["smali_src"]]),
    ("R-NET-01", "core.rules.net.r_net_01", [["smali_src"]]),
    ("R-NET-02", "core.rules.net.r_net_02", [["smali_src"]]),
]

SOURCE_LABELS = {
    'manifest': 'manifest(自研AXML)',
    'dex_strings': 'dex_strings(自研dex)',
    'smali_src': 'smali_src(apktool)',
    'res_decoded': 'res_decoded(apktool)',
}


class RuleContext(object):
    def __init__(self):
        self.project_root = ''
        self.apk_path = ''
        self.apk_name = ''
        self.apk_sha256 = ''
        self.app_package = ''
        self.manifest = None          # ManifestFacts
        self.manifest_doc = None      # XmlDocument（重建文本坐标）
        self.dex = None               # DexFacts
        self.smali = None             # SmaliFacts
        self.res = None               # ResFacts
        self.nsc_ref = None           # networkSecurityConfig 引用名（@xml/xxx）
        self.rule_notes = []          # 规则级覆盖/限制说明


def source_available(ctx, src):
    if src == 'manifest':
        return ctx.manifest is not None
    if src == 'dex_strings':
        return (ctx.dex is not None and
                (ctx.dex.strings or ctx.dex.type_descriptors))
    if src == 'smali_src':
        return ctx.smali is not None and len(ctx.smali.files) > 0
    if src == 'res_decoded':
        return ctx.res is not None and len(ctx.res.xml_files) > 0
    return False


def build_context(project_root, apk_path, sha256, decode_dir=None):
    """构造规则上下文。manifest 直读失败会抛 AXMLParseError（样本级处理）。"""
    ctx = RuleContext()
    ctx.project_root = project_root
    ctx.apk_path = apk_path
    ctx.apk_name = os.path.basename(apk_path)
    ctx.apk_sha256 = sha256

    with zipfile.ZipFile(apk_path) as z:
        manifest_bytes = z.read('AndroidManifest.xml')
    doc, facts = parse_manifest_bytes(manifest_bytes)
    ctx.manifest = facts
    ctx.manifest_doc = doc
    ctx.app_package = facts.package

    try:
        ctx.dex = scan_apk_dex(apk_path)
    except Exception as e:  # noqa: BLE001 —— dex 完全失败进覆盖声明
        ctx.rule_notes.append('dex 扫描失败：%s' % e)
        ctx.dex = None

    if decode_dir:
        ctx.smali = SmaliFacts(decode_dir)
        ctx.res = ResFacts(decode_dir)
        mpath = os.path.join(decode_dir, 'AndroidManifest.xml')
        try:
            with open(mpath, 'r', encoding='utf-8', errors='replace') as f:
                text = f.read()
            m = re.search(r'networkSecurityConfig="@xml/([^"]+)"', text)
            if m:
                ctx.nsc_ref = m.group(1)
        except OSError:
            pass
    return ctx


def run_channel_a(ctx):
    """执行全部规则。返回 (hits_by_rule: dict, coverage: dict, notes: list)。"""
    hits_by_rule = {}
    coverage_checked = []
    coverage_not_checked = []

    for rule_id, modpath, groups in RULES_PIPELINE:
        group_ok = False
        for g in groups:
            if all(source_available(ctx, s) for s in g):
                group_ok = True
                break
        if not group_ok:
            missing = ' / '.join('+'.join(SOURCE_LABELS.get(s, s) for s in g) for g in groups)
            coverage_not_checked.append(
                '%s（数据源未覆盖：缺少 %s）' % (rule_id, missing))
            continue
        mod = importlib.import_module(modpath)
        try:
            hits = mod.run(ctx)
        except Exception as e:  # noqa: BLE001 —— 单规则异常不阻断其余；记为未判定
            coverage_not_checked.append('%s（规则执行异常：%s）' % (rule_id, e))
            continue
        hits_by_rule[rule_id] = hits
        sources_note = '/'.join(sorted({s for g in groups for s in g if source_available(ctx, s)}))
        if rule_id == 'R-MAN-03' and source_available(ctx, 'res_decoded'):
            sources_note += '+res_decoded'
        coverage_checked.append('%s(%s)' % (rule_id, sources_note))

    notes = list(ctx.rule_notes)
    if ctx.dex is not None and ctx.dex.errors:
        notes.append('dex 部分解析失败：%s' % '；'.join(ctx.dex.errors[:3]))
    return hits_by_rule, {'checked': coverage_checked, 'not_checked': coverage_not_checked}, notes
