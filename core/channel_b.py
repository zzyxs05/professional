# -*- coding: utf-8 -*-
"""channel_b.py · 通道 B：LLM 语义审查（B1 复核 + B2 敏感区扫描）

- key.txt（项目根，不入库）：一行一条、逗号分隔 `模型名,base_url,api_key`，多行按序取第一个可用
- 缺失/加载失败 → 自动降级：B 通道整体跳过并进「B 通道未运行」覆盖声明（硬要求）
- B 的结论天花板：只能到「待复核」；升级为「已确认」必须经过确定性钉证据
- 证据必须落盘：prompt 模板版本、模型标识、原始响应、输入片段哈希（M2 补全）
"""

import http.client
import json
import os
import re
import time
import urllib.error
import urllib.request

from . import registry


class BResult(object):
    def __init__(self):
        self.ran = False
        self.reason = ''
        self.model = 'none'
        self.b1 = {}      # {rule_id: {'verdict': 确认可疑/上下文无害/无法判断, 'reason': str}}
        self.b2 = []      # [{claim, location, rule_guess, note}]
        self.calls = 0


def load_key_config(project_root):
    """解析 key.txt → [(model, base_url, api_key)]，异常条目跳过。"""
    path = os.path.join(project_root, registry.KEY_FILE_NAME)
    if not os.path.isfile(path):
        return []
    cfgs = []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith('#'):
                    continue
                parts = [p.strip() for p in line.split(',')]
                if len(parts) >= 3 and parts[0] and parts[1] and parts[2]:
                    cfgs.append((parts[0], parts[1], parts[2]))
    except OSError:
        return []
    return cfgs


def _chat(cfg, messages, timeout=None, max_tokens=None):
    """OpenAI 兼容端点（标准库 HTTP，不引 SDK）。返回响应文本。"""
    model, base_url, api_key = cfg
    url = base_url.rstrip('/') + '/chat/completions'
    payload = {
        'model': model,
        'messages': messages,
        'temperature': registry.LLM_TEMPERATURE,
        'max_tokens': max_tokens or registry.LLM_MAX_TOKENS,
    }
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json',
                 'Authorization': 'Bearer %s' % api_key},
        method='POST')
    last_err = None
    for attempt in range(registry.LLM_RETRY + 1):
        try:
            with urllib.request.urlopen(
                    req, timeout=timeout or registry.LLM_TIMEOUT_SECONDS) as resp:
                body = json.loads(resp.read().decode('utf-8', 'replace'))
            return body['choices'][0]['message']['content']
        except urllib.error.HTTPError as e:
            last_err = e
            # 限流(429)/服务端错误(5xx)：退避重试，避免整轮 B 通道被跳过
            if e.code in (429, 500, 502, 503, 504) and attempt < registry.LLM_RETRY:
                time.sleep(registry.LLM_RETRY_BACKOFF_SECONDS)
                continue
            raise
        except http.client.HTTPException as e:
            # 响应截断/连接异常（实测 IncompleteRead）同样可恢复
            last_err = e
            if attempt < registry.LLM_RETRY:
                time.sleep(registry.LLM_RETRY_BACKOFF_SECONDS)
                continue
            raise
    raise last_err


B1_PROMPT_VERSION = 'b1-v0.3'
B2_PROMPT_VERSION = 'b2-v0.4'

B1_SYSTEM = (
    '你是静态审计的命中复核器。\n'
    '输入：规则 ID 与检测点、该规则的误报口径（什么不算命中）、命中片段与位置。\n'
    '任务：判定该命中是否落在该规则的误报口径内。\n'
    '输出 JSON：{"verdict": "...", "reason": "...", "observation": "..."}\n'
    'verdict 取值：\n'
    '- 确认可疑：命中构成该规则所检测的结构\n'
    '- 上下文无害：命中属于该规则的误报口径，不构成该结构\n'
    '- 无法判断：所给信息不足以裁定\n'
    'reason 为一句判定依据；observation 为不属于判定结论的补充观察（无则空字符串）。'
)

B2_SYSTEM = (
    '你是静态审计的疑点扫描器。\n'
    '输入：样本的敏感区域摘要（组件及属性、权限、自定义权限声明、URL、动态加载点）。\n'
    '任务：列出值得人工进一步核查的疑点。\n'
    '输出 JSON 数组：[{"claim": "...", "location": "...", "rule_guess": "...", "confidence": "..."}]\n'
    '- claim：你观察到的事实断言\n'
    '- rule_guess：归类的规则 ID，无法归类时为空字符串\n'
    '- confidence：high / medium / low，用于标注该疑点的置信程度\n'
    '没有可列出的内容时输出 []。'
)


def run_channel_b(ctx, hits_by_rule, runner, store, force_off=False):
    """B1 复核 + B2 敏感区扫描。无模型配置时返回 ran=False（进覆盖声明）。"""
    res = BResult()
    cfgs = [] if force_off else load_key_config(ctx.project_root)
    if not cfgs:
        res.reason = '未配置模型（key.txt 缺失或不可解析）——B 通道未运行'
        return res

    cfg = cfgs[0]
    res.model = cfg[0]
    available = True
    # 轻量连通性探测记入首次调用；失败即降级
    try:
        _chat(cfg, [{'role': 'user', 'content': 'ping'}], max_tokens=4)
    except Exception as e:  # noqa: BLE001 —— 任何网络/协议失败都降级
        res.reason = '模型端点不可用（%s）——B 通道未运行' % e
        return res

    # ---- B1 上下文复核
    for rule_id, hits in hits_by_rule.items():
        if not hits or not available:
            continue
        if not runner.budget.consume_llm():
            available = False
            break
        meta = registry.RULE_META[rule_id]
        snippet = _hits_with_context(ctx, hits[:5])
        messages = [
            {'role': 'system', 'content': B1_SYSTEM},
            {'role': 'user',
             'content': '规则 %s（%s）\n误报口径（什么不算）：%s\n命中片段：\n%s'
                        % (rule_id, meta['name'], meta.get('fp_notes', '未定义'), snippet)},
        ]
        raw = ''
        try:
            raw = _chat(cfg, messages)
            verdict = _parse_verdict(raw)
        except Exception as e:  # noqa: BLE001
            verdict = {'verdict': '无法判断', 'reason': '复核调用失败：%s' % e}
        res.calls += 1
        res.b1[rule_id] = verdict
        store.add_record(rule_id, 'B1 复核', raw[:400], kind='b1_response',
                         source_file=ctx.apk_name, source_sha256=ctx.apk_sha256,
                         rule_pack=registry.RULE_PACK_VERSION, origin='b_channel',
                         extra={'prompt_version': B1_PROMPT_VERSION, 'model': cfg[0],
                                'verdict': verdict.get('verdict'),
                                'observation': verdict.get('observation', '')})

    # ---- B2 敏感区扫描（固定清单，独立审查）
    if available and runner.budget.consume_llm():
        b2_input = _collect_sensitive_area(ctx)
        if b2_input:
            messages = [
                {'role': 'system', 'content': B2_SYSTEM},
                {'role': 'user',
                 'content': '以下是样本敏感区域摘要（权限调用点/动态加载/导出组件/网络入口/调度结构）：\n'
                            + b2_input},
            ]
            raw = ''
            try:
                raw = _chat(cfg, messages)
                res.b2 = _parse_b2(raw)
            except Exception as e:  # noqa: BLE001
                raw = 'B2 失败：%s' % e
            res.calls += 1
            store.add_record('B2', '敏感区扫描', raw[:2000], kind='b2_response',
                             source_file=ctx.apk_name, source_sha256=ctx.apk_sha256,
                             rule_pack=registry.RULE_PACK_VERSION, origin='b_channel',
                             extra={'prompt_version': B2_PROMPT_VERSION, 'model': cfg[0]})

    res.ran = True
    return res


_SMALI_LOC_RE = re.compile(r'^(smali[^:]*\.smali):(\d+)')


def _context_around(ctx, location, span=3):
    """取命中点上下若干行作为上下文——模型常因"片段不足"判"无法判断"，
    给全信息是对症的机械改进（不改变判定标准，只补齐输入）。"""
    m = _SMALI_LOC_RE.match(location or '')
    if not m or ctx.smali is None:
        return ''
    rel, lineno = m.group(1), int(m.group(2))
    if rel not in ctx.smali.files:
        return ''
    lines = ctx.smali.read_lines(rel)
    lo = max(1, lineno - span)
    hi = min(len(lines), lineno + span)
    return '\n'.join('%d: %s' % (i, lines[i - 1].strip()) for i in range(lo, hi + 1))


def _hits_with_context(ctx, hits):
    blocks = []
    for h in hits:
        block = '- %s :: %s' % (h.location, h.raw_snippet)
        ctx_text = _context_around(ctx, h.location)
        if ctx_text:
            block += '\n  上下文:\n' + '\n'.join('    ' + ln for ln in ctx_text.split('\n'))
        mech = getattr(h, 'context', '') or ''
        if mech:
            block += '\n  机械层检索说明: %s' % mech
        blocks.append(block)
    return '\n'.join(blocks)


def _tolerant_json(text, opener='{'):
    """宽容解析模型响应：容忍尾随逗号（`},]`）、尾部孤立键（`, ""}`）、尾部附加文本。
    只取第一个完整对象/数组，解析不出则抛异常由调用方兜底。"""
    start = text.find(opener)
    if start < 0:
        raise ValueError('响应中无 %s' % opener)
    s = text[start:]
    s = re.sub(r',\s*([}\]])', r'\1', s)            # 尾随逗号
    s = re.sub(r',\s*"[^"]*"\s*([}\]])', r'\1', s)  # 尾部孤立字符串键
    obj, _end = json.JSONDecoder().raw_decode(s)
    return obj


def _parse_verdict(raw):
    try:
        obj = _tolerant_json(raw, '{')
        v = str(obj.get('verdict', '无法判断')).strip()
        if v not in ('确认可疑', '上下文无害', '无法判断'):
            v = '无法判断'
        return {'verdict': v, 'reason': str(obj.get('reason', ''))[:200],
                'observation': str(obj.get('observation', ''))[:300]}
    except Exception:  # noqa: BLE001
        return {'verdict': '无法判断', 'reason': '响应解析失败', 'observation': ''}


def _parse_b2(raw):
    try:
        arr = _tolerant_json(raw, '[')
        if not isinstance(arr, list):
            raise ValueError('响应不是数组')
        out = []
        for item in arr[:10]:
            if isinstance(item, dict) and item.get('claim'):
                conf = str(item.get('confidence', 'medium')).strip().lower()
                if conf not in ('high', 'medium', 'low'):
                    conf = 'medium'
                out.append({
                    'claim': str(item.get('claim', ''))[:200],
                    'location': str(item.get('location', ''))[:200],
                    'rule_guess': str(item.get('rule_guess', ''))[:32],
                    'confidence': conf,
                })
        return out
    except Exception:  # noqa: BLE001
        return []


# protectionLevel 数值 → 符号名（自研 AXML 直读输出为数值，避免摘要让模型误判）
_PROTECTION_LEVEL_NAMES = {
    0x0: 'normal', 0x1: 'dangerous', 0x2: 'signature', 0x3: 'signatureOrSystem',
}


def _fmt_protection_level(v):
    if v is None:
        return '未声明'
    try:
        iv = int(v, 16) if str(v).lower().startswith('0x') else int(v)
    except (ValueError, TypeError):
        return str(v)
    base = _PROTECTION_LEVEL_NAMES.get(iv & 0xF)
    if base:
        return base if iv == (iv & 0xF) else '%s(0x%x)' % (base, iv)
    return str(v)


def _collect_sensitive_area(ctx):
    """固定敏感区域摘要（导出组件+属性 / 权限 / 网络入口 / 动态加载点）。
    原则：给完整属性，避免模型在残缺信息上产出事实性错误的疑点。"""
    parts = []
    if ctx.manifest is not None:
        comp_lines = []
        for c in ctx.manifest.components[:20]:
            attrs = []
            if c.exported is not None:
                attrs.append('exported=%s' % c.exported)
            if c.permission:
                attrs.append('permission=%s' % c.permission)
            if c.read_permission:
                attrs.append('readPermission=%s' % c.read_permission)
            if c.write_permission:
                attrs.append('writePermission=%s' % c.write_permission)
            if c.actions:
                attrs.append('actions=[%s]' % ', '.join(c.actions[:6]))
            comp_lines.append('%s (%s%s)' % (
                c.name, c.ctype, ('; ' + '; '.join(attrs)) if attrs else ''))
        parts.append('组件：\n  ' + '\n  '.join(comp_lines))
        perms = ', '.join(p.name for p in ctx.manifest.permissions[:25])
        parts.append('权限：%s' % perms)
        # 自定义权限声明（含 protectionLevel）——避免模型因信息缺失怀疑取值
        declared = []
        if ctx.manifest.doc is not None:
            for el in ctx.manifest.doc.root.children:
                if el.tag == 'permission':
                    nm = el.attr('name')
                    lvl = _fmt_protection_level(el.attr('protectionLevel'))
                    if nm:
                        declared.append('%s (protectionLevel=%s)' % (nm, lvl))
        if declared:
            parts.append('自定义权限声明：%s' % '；'.join(declared[:10]))
    if ctx.smali is not None:
        urls = []
        dyn = []
        for rel in ctx.smali.app_files(ctx.app_package, ctx.rule_notes)[:80]:
            for lineno, raw in enumerate(ctx.smali.read_lines(rel), 1):
                if 'const-string' in raw:
                    m = re.search(r'"(https?://[^"]+)"', raw)
                    if m and m.group(1) not in urls:
                        urls.append(m.group(1))
                for pat in ('DexClassLoader', 'PathClassLoader', 'InMemoryDexClassLoader'):
                    if pat in raw and ('invoke-' in raw or 'new-instance' in raw):
                        dyn.append('%s:%d' % (rel, lineno))
        if urls:
            parts.append('自有代码中的 URL（前 15 条）：%s' % '; '.join(urls[:15]))
        if dyn:
            parts.append('动态加载点：%s' % ', '.join(dyn[:10]))
    text = '\n'.join(parts)
    return text[:6000]
