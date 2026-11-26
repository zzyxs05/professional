# -*- coding: utf-8 -*-
"""checker.py · 通用确定性审查内核（评价器与目标项目解耦）

纪律：
- 不 import core、不认 report.json / APK / 规则包结构、不内置任何项目专属路径或字段；
- 不要求目标有 run_id、evidence/ 目录或任何特定结构——路径模板里的 {{name}}
  是可选上下文变量，由 --context 提供；没提供就如实判 missing，不套默认值；
- 白名单由传入的 fields spec 数据驱动推导，字段规范没声明的路径一律拒绝；
- 输出三态 + 完整证据链 + verdict_digest；模型输出不进本模块、不进 digest。

本模块是纯内核：任何调用方（本地命令、外部 harness、脚本）都通过传入
target / fields spec / context 调用，模块不规定启动方式，也不依赖特定 CLI。
"""

import hashlib
import json
import os

from .fieldcheck import (STATUS_MATCH, STATUS_MISMATCH, STATUS_MISSING,
                         check_field, expand_template, make_context)


class CheckerError(Exception):
    """字段规范或输入不可用时抛出；不吞错、不伪造判定。"""


def load_json(path):
    if not os.path.isfile(path):
        raise CheckerError('文件不存在：%s' % path)
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError) as e:
        raise CheckerError('不可解析：%s（%s）' % (path, e))


def expand_with_context(raw, context):
    """用已展开的路径模板推导白名单；变量缺失时该路径不进白名单。"""
    expanded, missing = expand_template(raw, context)
    if expanded and 'RUN-*' in expanded and 'run_id' in context:
        expanded = expanded.replace('RUN-*', str(context['run_id']))
    return expanded


def derive_allowlist(spec, context):
    """从字段规范推导允许读取的路径集合：只认规范里出现过的路径，不认别的。"""
    exact, prefixes = set(), set()

    def add(raw):
        rel = expand_with_context(raw, context)
        if not rel:
            return
        exact.add(rel)
        parent = os.path.dirname(rel)
        if parent:
            prefixes.add(parent)
        if isinstance(raw, str) and raw.rstrip('/').endswith('*'):
            prefixes.add(os.path.dirname(rel))

    for criterion in spec.get('criteria', []):
        for field in criterion.get('fields', []):
            add(field.get('path'))
            rhs = field.get('rhs', '')
            if isinstance(rhs, str) and ':' in rhs:
                add(rhs.split(':', 1)[0])
            add(field.get('left_path'))
            add(field.get('right_path'))
    return exact, prefixes


class FieldReader(object):
    """给 fieldcheck.check_field 用的只读 reader；路径白名单由 spec 推导。"""

    def __init__(self, target_root, exact, prefixes):
        self.target_root = os.path.abspath(target_root)
        self.exact = set(exact)
        self.prefixes = tuple(sorted(prefixes))

    def _safe_path(self, rel):
        expanded, missing = expand_template(rel, {})
        if missing or not expanded:
            return None
        if (expanded not in self.exact
                and not any(expanded.startswith(p + '/') for p in self.prefixes)):
            return None
        full = os.path.normpath(os.path.join(self.target_root, expanded))
        try:
            if os.path.commonpath([full, self.target_root]) != self.target_root:
                return None
        except ValueError:
            return None
        return full


def _expectation(field):
    """把比对规则翻成人话期望，供证据链展示。不读取目标内容，不产生判断。"""
    kind = field.get('kind')
    if kind == 'text_all':
        return '应包含：%s' % '、'.join(field.get('expect', []))
    if kind == 'json_eq':
        return '%s 应等于 %s' % (field.get('lhs'), field.get('rhs') or field.get('const'))
    if kind == 'json_nonempty':
        return '%s 应有内容' % field.get('json_path')
    if kind == 'dir_min':
        return '条目数应 ≥ %s' % field.get('min')
    if kind == 'file_exists':
        return '文件应存在'
    return '未知比对方式：%s' % kind


def _status_text(status):
    return {'match': '符合', 'mismatch': '不符合', 'missing': '读不到'}.get(status, status)


def build_chain(criterion_id, criterion_spec, checked):
    """把字段三态展开成逐条可回溯的证据链；期望与实际分开写，不用结论代替事实。"""
    by_id = {f['id']: f for f in criterion_spec.get('fields', [])}
    chain = []
    for row in checked.get('fields', []):
        spec = by_id.get(row.get('id'), {})
        chain.append({
            'step_id': row.get('id'),
            'question': spec.get('note') or row.get('note') or '字段核对',
            'path': row.get('path_expanded') or row.get('path'),
            'method': row.get('kind'),
            'expectation': _expectation(spec),
            'observed': row.get('observed'),
            'status': row.get('status'),
            'status_text': _status_text(row.get('status')),
        })
    return {'criterion_id': criterion_id, 'steps': chain}


def verdict_digest(payload):
    """判定区指纹：同快照重跑必须一致。不含时间、模型文本、eval_id。"""
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True,
                           separators=(',', ':'), default=str)
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()


class Checker(object):
    def __init__(self, target_root, fields_path, schema_path=None,
                 contract=None, context=None, version_checks=None):
        self.target_root = os.path.abspath(target_root)
        self.context = dict(context or {})
        self.fields_spec = load_json(fields_path)
        self.schema = load_json(schema_path) if schema_path else {}
        self.contract = contract
        self.version_checks = version_checks or []
        exact, prefixes = derive_allowlist(self.fields_spec, self.context)
        self.reader = FieldReader(self.target_root, exact, prefixes)

    def _check_versions(self):
        """数据驱动的版本核对：路径与取值键都来自契约，内核不认任何项目字段名。"""
        results = []
        for item in self.version_checks:
            left = self._read_binding(item.get('left'))
            right = self._read_binding(item.get('right'))
            results.append({
                'name': item.get('name') or '版本核对',
                'left': item.get('left'), 'right': item.get('right'),
                'left_value': left, 'right_value': right,
                'status': ('missing' if left is None or right is None
                           else ('match' if left == right else 'mismatch')),
                'status_text': None,
            })
            results[-1]['status_text'] = _status_text(results[-1]['status'])
        return results

    def _read_binding(self, binding):
        if not isinstance(binding, str):
            return None
        if binding.startswith('contract:'):
            cur = self.contract or {}
            for part in binding.split(':', 1)[1].split('.'):
                if not isinstance(cur, dict) or part not in cur:
                    return None
                cur = cur[part]
            return cur
        if ':' in binding:
            rel, dotted = binding.split(':', 1)
        else:
            rel, dotted = binding, None
        full = self.reader._safe_path(rel)
        if full is None or not os.path.isfile(full):
            return None
        try:
            with open(full, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (OSError, ValueError):
            return None
        if dotted:
            for part in dotted.split('.'):
                if not isinstance(data, dict) or part not in data:
                    return None
                data = data[part]
        return data

    def check(self):
        """返回通用审查结果：逐项三态 + 证据链 + 判定指纹。不打分。"""
        known_kinds = set((self.schema.get('kinds') or {}).keys())
        criteria = []
        spec_by_id = {c.get('criterion_id'): c
                      for c in self.fields_spec.get('criteria', [])}
        for cid, criterion_spec in spec_by_id.items():
            rows = [check_field(f, self.reader, context=self.context)
                    for f in criterion_spec.get('fields', [])]
            for row in rows:
                if row.get('kind') not in known_kinds and known_kinds:
                    row['status'] = STATUS_MISSING
                    row['observed'] = {'error': '未知比对方式：%s' % row.get('kind')}
            counts = {s: sum(1 for r in rows if r['status'] == s)
                      for s in (STATUS_MATCH, STATUS_MISMATCH, STATUS_MISSING)}
            summary = dict(counts, total=len(rows),
                           all_match=bool(rows) and counts[STATUS_MISMATCH] == 0
                           and counts[STATUS_MISSING] == 0)
            chain = build_chain(cid, criterion_spec, {'fields': rows})
            if rows and summary['all_match']:
                status = 'PASS'
            elif rows and counts[STATUS_MISSING]:
                status = 'INSUFFICIENT_EVIDENCE'
            elif rows and counts[STATUS_MISMATCH]:
                status = 'FAIL'
            else:
                status = 'INSUFFICIENT_EVIDENCE'
            criteria.append({
                'criterion_id': cid,
                'status': status,
                'summary': summary,
                'fields': rows,
                'evidence_chain': chain,
                'missing_evidence': [r['id'] for r in rows
                                     if r['status'] == STATUS_MISSING],
            })
        versions = self._check_versions()
        if any(v['status'] == 'mismatch' for v in versions):
            for item in criteria:
                item['status'] = 'INSUFFICIENT_EVIDENCE'
        digest_payload = {
            'fields_id': self.fields_spec.get('id'),
            'fields_version': self.fields_spec.get('version'),
            'context': self.context,
            'criteria': [{'criterion_id': c['criterion_id'],
                          'status': c['status'],
                          'fields': [{'id': f['id'], 'status': f['status'],
                                      'path': f.get('path_expanded')}
                                     for f in c['fields']]}
                         for c in criteria],
            'version_checks': versions,
        }
        return {
            'fields_id': self.fields_spec.get('id'),
            'fields_version': self.fields_spec.get('version'),
            'target': self.target_root,
            'context': self.context,
            'contract_present': self.contract is not None,
            'criteria': criteria,
            'version_checks': versions,
            'verdict_digest': verdict_digest(digest_payload),
            'scope_note': ('机械层只做字段比对与版本核对；只读、不执行、不打分。'
                           '模型建议分独立复核时决定采纳与否。'),
        }


def check_files(target_root, fields_path, schema_path=None,
                contract_path=None, context=None, version_checks=None):
    """便捷入口；契约与上下文都是可选的，缺失时只报告缺口，不套用本项目规则。"""
    contract = load_json(contract_path) if contract_path else None
    return Checker(target_root, fields_path, schema_path,
                   contract, context, version_checks).check()


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(
        description='通用确定性审查内核（harness 可直接调用，输出 JSON）')
    parser.add_argument('--target', required=True, help='目标仓库根目录')
    parser.add_argument('--fields', required=True, help='字段规范 JSON（由目标或契约提供）')
    parser.add_argument('--schema', default=None, help='比对方式定义 JSON（可选）')
    parser.add_argument('--contract', default=None, help='已批准契约 JSON（可选）')
    parser.add_argument('--context', default=None,
                        help='上下文变量 JSON；路径模板 {{name}} 从这里取值（可选）')
    parser.add_argument('--versions', default=None,
                        help='版本核对定义 JSON（可选，数据驱动）')
    parser.add_argument('--out', default=None, help='输出 JSON 路径；不写则打印到 stdout')
    args = parser.parse_args(argv)
    try:
        context = load_json(args.context) if args.context else {}
        version_checks = (load_json(args.versions).get('version_checks')
                          if args.versions else None)
        result = check_files(args.target, args.fields, args.schema,
                             args.contract, context, version_checks)
    except CheckerError as e:
        parser.exit(2, '[checker] %s\n' % e)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        with open(args.out, 'w', encoding='utf-8', newline='\n') as f:
            f.write(text + '\n')
        print('[checker] %s' % args.out)
    else:
        print(text)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
