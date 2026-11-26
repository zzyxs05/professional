# -*- coding: utf-8 -*-
"""fieldcheck.py · 字段级机械核对（通用内核，与目标项目无关）

字段规范决定「看什么文件、什么字段」，本模块只实现通用比对方式：
text_all / json_eq / json_nonempty / dir_min / file_exists。

路径中的 {{name}} 是可选上下文变量（如 {{snapshot}}），由调用方提供；
变量缺失如实判 missing，不套默认值、不假设任何项目结构。

三态：match=符合 / mismatch=不符（字段在但期望不满足）/ missing=缺字段或缺变量。
读到的内容一律当数据处理，不执行、不升级结论、不产生分数、不代签。
"""

import json
import os
import re

STATUS_MATCH = 'match'
STATUS_MISMATCH = 'mismatch'
STATUS_MISSING = 'missing'
VALID = (STATUS_MATCH, STATUS_MISMATCH, STATUS_MISSING)

FIELDS_PATH = os.path.join(os.path.dirname(__file__), 'skills', 'evidence-review',
                           'fields.json')

_VAR_RE = re.compile(r'\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}')


def load_fields(path=None):
    with open(path or FIELDS_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def expand_template(rel, context=None):
    """展开 {{name}} 占位符，返回 (展开路径, 缺失变量名列表)。

    无占位符时原样返回；变量缺失返回 (None, 缺失名)，由调用方判 missing。
    绝对路径与 .. 穿越同样返回 None，不读取白名单外内容。
    """
    if not isinstance(rel, str) or not rel:
        return None, []
    ctx = context or {}
    missing = []

    def sub(m):
        name = m.group(1)
        if name in ctx and ctx[name] not in (None, ''):
            return str(ctx[name])
        missing.append(name)
        return ''

    expanded = _VAR_RE.sub(sub, rel)
    if missing:
        return None, missing
    # 兼容存量字段规范里的 RUN-* 占位符（等价于 {{run_id}}），
    # 不强制所有旧规范立刻改写；新规范统一用 {{name}}。
    if 'RUN-*' in expanded and 'run_id' in ctx:
        expanded = expanded.replace('RUN-*', str(ctx['run_id']))
    expanded = expanded.replace('\\', '/').lstrip('/')
    if expanded.startswith('/') or '..' in expanded.split('/'):
        return None, ['路径越界']
    return expanded, []


def make_context(run_id=None, context=None):
    """兼容旧调用：run_id 只是可注入的变量之一，不是本模块的前提。"""
    ctx = dict(context or {})
    if run_id is not None:
        ctx.setdefault('run_id', run_id)
    return ctx


def _resolve(tools, rel, context):
    """返回 (绝对路径, 展开后的相对路径, 缺失变量名)。"""
    expanded, missing = expand_template(rel, context)
    if expanded is None:
        return None, None, missing
    full = tools._safe_path(expanded)
    return full, (expanded if full is not None else None), []


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


def check_field(field, tools, run_id=None, context=None):
    """核对单字段，返回 {id, path, kind, status, observed, note}。

    tools 为受限 reader：路径越界一律 missing，不读取白名单外文件。
    run_id 仅为兼容旧调用保留，等价于注入 {{run_id}} 变量；不传也能工作。
    """
    out = {'id': field.get('id'), 'path': field.get('path'),
           'kind': field.get('kind'), 'status': STATUS_MISSING,
           'observed': None, 'note': field.get('note')}
    kind = field.get('kind')
    ctx = make_context(run_id, context)
    full, expanded, missing_vars = _resolve(tools, field.get('path'), ctx)
    out['path_expanded'] = expanded
    if missing_vars:
        out['observed'] = {'missing_context': missing_vars}
        return out

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
                n = len([e for e in os.listdir(full) if not e.startswith('.')])
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
                        rhs_full, _, rhs_missing = _resolve(tools, rhs_path, ctx)
                        if rhs_missing:
                            out['observed'] = {'rhs_missing_context': rhs_missing}
                            return out
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
                    out['status'] = (STATUS_MATCH if lhs == rhs else STATUS_MISMATCH)
        else:
            out['observed'] = {'error': '未知 kind：%s' % kind}
            out['status'] = STATUS_MISSING
    except (OSError, ValueError, TypeError) as e:
        out['observed'] = {'error': '%s: %s' % (type(e).__name__, e)}
        out['status'] = STATUS_MISSING
    return out


def check_criterion(criterion, tools, run_id=None, context=None):
    ctx = make_context(run_id, context)
    rows = [check_field(f, tools, context=ctx) for f in criterion.get('fields', [])]
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


def check_all(spec, tools, run_id=None, context=None):
    ctx = make_context(run_id, context)
    return {
        'fields_id': spec.get('id'),
        'fields_version': spec.get('version'),
        'context': ctx,
        'criteria': [check_criterion(c, tools, context=ctx)
                     for c in spec.get('criteria', [])],
    }
