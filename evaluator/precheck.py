# -*- coding: utf-8 -*-
"""precheck.py · 评价器确定性预检（引用存在性、版本匹配、结构）"""

import json
import os

from core import registry

VALID_STATUS = {registry.STATUS_CONFIRMED, registry.STATUS_REVIEW, registry.STATUS_UNDECIDED}
VALID_CHANNEL = {'A', 'B', 'fusion'}


def _load_jsonl_ids(path):
    ids = set()
    records = {}
    if not os.path.isfile(path):
        return ids, records
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            eid = obj.get('evidence_id')
            if eid:
                ids.add(eid)
                records[eid] = obj
    return ids, records


def precheck(run_dir):
    """返回 (findings, report, evidence_records)。findings 每项 {level, code, msg}。"""
    findings = []
    report_path = os.path.join(run_dir, 'report.json')
    if not os.path.isfile(report_path):
        findings.append({'level': 'FAIL', 'code': 'E-NO-REPORT',
                         'msg': 'report.json 缺失，无法评价'})
        return findings, None, {}

    with open(report_path, 'r', encoding='utf-8') as f:
        report = json.load(f)

    ids, records = _load_jsonl_ids(os.path.join(run_dir, 'channel_a', 'hits.jsonl'))
    # B 通道证据（若存在）
    b_ids, b_records = _load_jsonl_ids(os.path.join(run_dir, 'channel_b', 'records.jsonl'))
    ids |= b_ids
    records.update(b_records)

    # 结构完整性
    for key in ('run_id', 'target', 'versions', 'conclusions', 'coverage'):
        if key not in report:
            findings.append({'level': 'FAIL', 'code': 'E-STRUCT',
                             'msg': 'report.json 缺少字段 %s' % key})
    if report.get('versions', {}).get('rule_pack') is None:
        findings.append({'level': 'FAIL', 'code': 'E-VERSION',
                         'msg': 'report 未绑定规则包版本'})

    # 版本与 meta 匹配
    meta_path = os.path.join(run_dir, 'meta.json')
    if os.path.isfile(meta_path):
        try:
            with open(meta_path, 'r', encoding='utf-8') as f:
                meta = json.load(f)
            if meta.get('rule_pack') != report.get('versions', {}).get('rule_pack'):
                findings.append({'level': 'FAIL', 'code': 'E-VERSION-MISMATCH',
                                 'msg': 'meta.json 与 report.json 规则包版本不一致'})
            if meta.get('apk_sha256') != report.get('target', {}).get('apk_sha256'):
                findings.append({'level': 'FAIL', 'code': 'E-TARGET-MISMATCH',
                                 'msg': 'meta.json 与 report.json 样本指纹不一致'})
        except json.JSONDecodeError:
            findings.append({'level': 'FAIL', 'code': 'E-META-PARSE',
                             'msg': 'meta.json 不可解析'})
    else:
        findings.append({'level': 'FAIL', 'code': 'E-NO-META', 'msg': 'meta.json 缺失'})

    conclusions = report.get('conclusions', [])
    if not isinstance(conclusions, list):
        findings.append({'level': 'FAIL', 'code': 'E-STRUCT',
                         'msg': 'conclusions 不是列表'})
        conclusions = []

    for c in conclusions:
        cid = c.get('criterion_id', '?')
        if c.get('status') not in VALID_STATUS:
            findings.append({'level': 'FAIL', 'code': 'E-STATUS',
                             'msg': '%s 状态值非法：%s' % (cid, c.get('status'))})
        if c.get('channel') not in VALID_CHANNEL:
            findings.append({'level': 'FAIL', 'code': 'E-CHANNEL',
                             'msg': '%s 通道值非法：%s' % (cid, c.get('channel'))})
        evs = c.get('evidence_ids', [])
        for eid in evs:
            if eid not in ids:
                findings.append({'level': 'FAIL', 'code': 'E-DANGLING',
                                 'msg': '%s 引用悬空证据 %s' % (cid, eid)})
        if c.get('status') == registry.STATUS_CONFIRMED and not evs:
            findings.append({'level': 'FAIL', 'code': 'E-CLAIM-ONLY',
                             'msg': '%s 为「已确认」但无证据引用（自述）' % cid})
        if c.get('status') == registry.STATUS_CONFIRMED and not c.get('location'):
            findings.append({'level': 'FAIL', 'code': 'E-NO-LOCATION',
                             'msg': '%s 为「已确认」但无定位坐标' % cid})

    cov = report.get('coverage', {})
    if not cov.get('checked') and not cov.get('not_checked'):
        findings.append({'level': 'FAIL', 'code': 'E-NO-COVERAGE',
                         'msg': '覆盖声明为空'})
    if not cov.get('checked') and not cov.get('decode_failed'):
        findings.append({'level': 'INSUFFICIENT', 'code': 'W-NO-CHECKED',
                         'msg': '无任何已检查项（可能全部未覆盖）'})

    return findings, report, records
