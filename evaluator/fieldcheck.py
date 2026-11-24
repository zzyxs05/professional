# -*- coding: utf-8 -*-
"""fieldcheck.py · 字段级内容核对（T-M5-12）

把评价从「查文件是否存在」推进到「读文件里的真实字段」。只读、机械比对：
文本子串 / JSON 取值 / 目录条目数 / 文件存在。读到的内容一律当数据处理，
不执行、不升级结论、不产生分数、不代签。

三态：match=符合 / mismatch=不符（字段在但期望不满足）/ missing=缺字段（读不到）。
"""

import json
import os

STATUS_MATCH = 'match'
STATUS_MISMATCH = 'mismatch'
STATUS_MISSING = 'missing'
VALID = (STATUS_MATCH, STATUS_MISMATCH, STATUS_MISSING)

FIELDS_PATH = os.path.join(os.path.dirname(__file__), 'skills', 'evidence-review',
                           'fields.json')


def load_fields(path=None):
    with open(path or FIELDS_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def _resolve(tools, rel, run_id):
    """把 RUN-* 模板替换成具体 run_id，再走 tools 白名单校验。"""
    if not isinstance(rel, str):
        return None, rel
    expanded = rel.replace('RUN-*', run_id)
    full = tools._safe_path(expanded)
    # 白名单拒绝时不把展开路径暴露到产物/轨迹里，只记 None。
    return full, (expanded if full is not None else None)


def _read_text(full):
    if full is None or not os.path.isfile(full):
        return None
    with open(full, 'r', encoding='utf-8', errors='replace') as f:
        return f.read()


def _read_json(full):
    if full is None or not os.path.isfile(full):
        return None
    with open(full, 'r', encoding='utf-8') as f:
        return json.load(f)


def _dig(obj, dotted):
    """按点路径取 JSON 值；取不到返回 (False, None)。"""
    cur = obj
    for part in dotted.split('.'):
        if not isinstance(cur, dict) or part not in cur:
            return False, None
        cur = cur[part]
    return True, cur


def _nonempty(value):
    if value is None:
        return False
    if isinstance(value, (list, dict, str)):
        return len(value) > 0
    if isinstance(value, (int, float)):
        return value != 0
    return True


def check_field(field, tools, run_id):
    """核对单个字段定义，返回 {id, path, kind, status, observed, note}。

    tools 为 RestrictedTools 实例：路径越界一律 missing，不读取白名单外文件。
    """
    out = {'id': field.get('id'), 'path': field.get('path'),
           'kind': field.get('kind'), 'status': STATUS_MISSING,
           'observed': None, 'note': field.get('note')}
    kind = field.get('kind')
    full, expanded = _resolve(tools, field.get('path'), run_id)
    out['path_expanded'] = expanded

    try:
        if kind == 'file_exists':
            out['status'] = (STATUS_MATCH if full is not None and os.path.exists(full)
                             else STATUS_MISSING)
            out['observed'] = os.path.exists(full) if full is not None else None

        elif kind == 'text_all':
            text = _read_text(full)
            if text is None:
                out['status'] = STATUS_MISSING
            else:
                missing = [s for s in field.get('expect', []) if s not in text]
                out['observed'] = {'missing_anchors': missing,
                                   'expected_count': len(field.get('expect', []))}
                out['status'] = STATUS_MISMATCH if missing else STATUS_MATCH

        elif kind == 'dir_min':
            if full is None or not os.path.isdir(full):
                out['status'] = STATUS_MISSING
            else:
                n = len([e for e in os.listdir(full)
                         if not e.startswith('.')])
                out['observed'] = {'entries': n, 'min': field.get('min')}
                out['status'] = (STATUS_MATCH if n >= field.get('min', 0)
                                 else STATUS_MISMATCH)

        elif kind == 'json_nonempty':
            data = _read_json(full)
            if data is None:
                out['status'] = STATUS_MISSING
            else:
                ok, val = _dig(data, field.get('json_path', ''))
                out['observed'] = {'found': ok, 'nonempty': _nonempty(val) if ok else None}
                if not ok:
                    out['status'] = STATUS_MISSING
                elif not _nonempty(val):
                    out['status'] = STATUS_MISMATCH
                else:
                    out['status'] = STATUS_MATCH

        elif kind == 'json_eq':
            data = _read_json(full)
            if data is None:
                out['status'] = STATUS_MISSING
            else:
                ok_l, lhs = _dig(data, field.get('lhs', ''))
                if not ok_l:
                    out['status'] = STATUS_MISSING
                    out['observed'] = {'lhs_found': False}
                else:
                    if 'const' in field:
                        ok_r, rhs = True, field['const']
                    else:
                        rhs_spec = field.get('rhs', '')
                        if ':' not in rhs_spec:
                            out['status'] = STATUS_MISSING
                            out['observed'] = {'rhs_spec': rhs_spec}
                            return out
                        rhs_path, rhs_dotted = rhs_spec.split(':', 1)
                        rhs_full, _ = _resolve(tools, rhs_path, run_id)
                        rhs_data = _read_json(rhs_full)
                        if rhs_data is None:
                            out['status'] = STATUS_MISSING
                            out['observed'] = {'rhs_readable': False}
                            return out
                        ok_r, rhs = _dig(rhs_data, rhs_dotted)
                        if not ok_r:
                            out['status'] = STATUS_MISSING
                            out['observed'] = {'rhs_found': False}
                            return out
                    out['observed'] = {'lhs': lhs, 'rhs': rhs}
                    out['status'] = (STATUS_MATCH if lhs == rhs
                                     else STATUS_MISMATCH)
        else:
            out['observed'] = {'error': '未知 kind：%s' % kind}
            out['status'] = STATUS_MISSING
    except (OSError, ValueError, TypeError) as e:
        out['observed'] = {'error': '%s: %s' % (type(e).__name__, e)}
        out['status'] = STATUS_MISSING
    return out


def check_criterion(criterion, tools, run_id):
    """核对一项审查项，返回三态汇总。"""
    rows = [check_field(f, tools, run_id) for f in criterion.get('fields', [])]
    counts = {s: sum(1 for r in rows if r['status'] == s) for s in VALID}
    return {
        'criterion_id': criterion.get('criterion_id'),
        'note': criterion.get('note'),
        'fields': rows,
        'summary': {
            'total': len(rows),
            **counts,
            'all_match': bool(rows) and counts[STATUS_MISMATCH] == 0
                         and counts[STATUS_MISSING] == 0,
        },
    }


def check_all(spec, tools, run_id):
    """核对全部审查项；spec 为 fields.json 内容。"""
    return {
        'fields_id': spec.get('id'),
        'fields_version': spec.get('version'),
        'run_id': run_id,
        'criteria': [check_criterion(c, tools, run_id)
                     for c in spec.get('criteria', [])],
    }
