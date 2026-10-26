# -*- coding: utf-8 -*-
"""fusion.py · 融合层：分歧呈现 + 钉证据机制

融合规则（确定性执行，逐条可审计，总档 §3.5）：
  A 命中 + B1 确认可疑 → 维持档位（通道标 fusion）
  A 命中 + B1 上下文无害 → 复核降级（记录降级理由，人工可推翻）
  A 命中 + B1 无法判断 → 待复核
  未命中 + B2 提疑 → 钉证据 → 成功则补盲（档位不超规则上限）；失败则保留疑点

钉证据（ADR-0004，v2 严格化）：语义疑点 → 规则映射（PIN_RULE_MAP）→ 机械规则验证。
钉成功三条件（全部满足）：
  1. claim 能映射到至少一条规则（关键词组）；
  2. 映射规则在当前样本上有机械命中（复用通道 A 规则判定）；
  3. claim 中若含可核查强实体（权限/动作/URL/类名），命中内容必须触及其中至少一个。
钉出的结论档位 = 该规则 max_status（不得越过规则上限）；推测型、不可核查的 claim 一律拒绝升级。
"""

import importlib
import re

from . import registry
from .channel_a import RULES_PIPELINE

STATUS_RANK = {registry.STATUS_CONFIRMED: 2, registry.STATUS_REVIEW: 1, registry.STATUS_UNDECIDED: 0}

_MODULE_BY_RULE = {rid: mod for rid, mod, _groups in RULES_PIPELINE}

_URL_RE = re.compile(r'https?://[^\s"\'<>、，。；]+')
_CLASS_RE = re.compile(r'(?:[a-z][a-zA-Z0-9_]*\.){1,}[A-Z][a-zA-Z0-9_]*')


def min_status(a, b):
    if b is None:
        return a
    return a if STATUS_RANK.get(a, 0) <= STATUS_RANK.get(b, 0) else b


# ------------------------------------------------------------------ 钉证据
def _sample_entity_pool(ctx):
    """样本内已知实体池（权限/组件/广播动作的全名与短名，均大写存放）。"""
    pool = set()
    if ctx.manifest is not None:
        for p in ctx.manifest.permissions:
            pool.add(p.name.upper())
            pool.add(p.name.split('.')[-1].upper())
        for c in ctx.manifest.components:
            pool.add(c.name.upper())
            pool.add(c.name.split('.')[-1].upper())
            for a in c.actions:
                pool.add(a.upper())
                pool.add(a.split('.')[-1].upper())
    return pool


def _claim_entities(ctx, claim):
    """claim 中的可核查硬实体：
    权限全名/敏感权限短名/样本实体池中的大写 token/URL/含点类名（全名+短名）。
    硬实体必须被机械命中内容覆盖，否则不升级（防"实体存在≠断言成立"的假证据）。"""
    ents = set()
    upper = claim.upper()
    for m in re.finditer(r'ANDROID\.PERMISSION\.[A-Z_]+', upper):
        ents.add(m.group(0))
    for perm in registry.SENSITIVE_PERMISSIONS:
        short = perm.split('.')[-1]
        if re.search(r'(?<![A-Z_])%s(?![A-Z_])' % re.escape(short), upper):
            ents.add('ANDROID.PERMISSION.' + short)
    pool = _sample_entity_pool(ctx)
    for m in re.finditer(r'[A-Z][A-Z_]{5,}', upper):
        if m.group(0) in pool:
            ents.add(m.group(0))
    for m in _URL_RE.finditer(claim):
        # 剥离尾随标点（中文括号/逗号等），避免"http://x）"这类误提取导致实体比对失败
        u = m.group(0).rstrip('）。，、；：！？）」』】】,.;:!?)]')
        if u:
            ents.add(u)
    for m in _CLASS_RE.finditer(claim):
        ents.add(m.group(0))
        ents.add(m.group(0).split('.')[-1])
    return ents


def _map_claim_to_rules(claim, rule_guess=''):
    """关键词组映射；合法的 rule_guess 一并作为候选（仍需机械核对）。"""
    claim_l = claim.lower()
    matched = []
    for rid, spec in registry.PIN_RULE_MAP.items():
        groups = spec.get('all_of', [])
        if groups and all(any(kw.lower() in claim_l for kw in grp) for grp in groups):
            matched.append(rid)
    if rule_guess in registry.RULE_META and rule_guess not in matched:
        matched.append(rule_guess)
    return matched


def _rule_hits_for(ctx, rule_id):
    mod_path = _MODULE_BY_RULE.get(rule_id)
    if not mod_path:
        return []
    try:
        mod = importlib.import_module(mod_path)
        return mod.run(ctx)
    except Exception:  # noqa: BLE001 —— 单规则核对失败不阻断（视为无命中）
        return []


def pin_evidence(ctx, claim, location='', rule_guess=''):
    """钉证据主入口。返回：
    {'status': 'pinned'|'unpinned', 'detail', 'rules': [{rule_id, locations, note, facts}],
     'locations': [...]}
    """
    candidates = _map_claim_to_rules(claim, rule_guess)
    findings = []
    for rid in candidates:
        hits = _rule_hits_for(ctx, rid)
        if hits:
            findings.append({'rule_id': rid, 'hits': hits})

    ents = _claim_entities(ctx, claim)
    if ents and findings:
        def touched(h):
            blob = ('%s %s %s' % (h.location, h.raw_snippet, h.note)).lower()
            return any(e.lower() in blob for e in ents)
        findings = [{'rule_id': f['rule_id'],
                     'hits': [h for h in f['hits'] if touched(h)]}
                    for f in findings]
        findings = [f for f in findings if f['hits']]

    if findings:
        rules_out = []
        all_locs = []
        for f in findings:
            locs = []
            for h in f['hits'][:5]:
                if h.location not in locs:
                    locs.append(h.location)
            spec = registry.PIN_RULE_MAP.get(f['rule_id'], {})
            rules_out.append({
                'rule_id': f['rule_id'],
                'locations': locs,
                'note': spec.get('note') or registry.RULE_META[f['rule_id']]['name'],
                'facts': next((h.note for h in f['hits'] if h.note), ''),
            })
            all_locs.extend(locs)
        return {
            'status': 'pinned',
            'detail': '；'.join('%s 机械命中 %d 处（%s）'
                                % (r['rule_id'], len(r['locations']),
                                   registry.RULE_META[r['rule_id']]['name'])
                                for r in rules_out),
            'rules': rules_out,
            'locations': all_locs,
        }

    if not candidates:
        detail = '未识别到可核查断言（claim 无法映射到任何规则）'
    else:
        ent_note = ''
        if ents:
            ent_note = '；claim 提及实体（%s）未被机械命中覆盖' % '、'.join(sorted(ents)[:3])
        detail = '断言未被机械事实证实（候选规则 %s 均无机械命中%s）' % (
            ', '.join(candidates), ent_note)
    return {'status': 'unpinned', 'detail': detail, 'rules': [], 'locations': []}


# ------------------------------------------------------------------ 融合
def build_conclusions(hits_by_rule, ev_map=None, b_result=None, pin_fn=None):
    """hits_by_rule: {rule_id: [Hit]}；ev_map: {rule_id: [evidence_id]}；
    pin_fn(rule_guess, point) → pin_evidence 结果（含 rules[].evidence_ids）。

    返回 (conclusions, observations)：
      - conclusions：审计结论（三档，须有证据）
      - observations：B 通道观察（低置信、未经机械核查）——保留 B 的原始声音，不作为结论
    """
    ev_map = ev_map or {}
    b1_by_rule = {}
    b2_points = []
    if b_result is not None and getattr(b_result, 'ran', False):
        b1_by_rule = getattr(b_result, 'b1', {}) or {}
        b2_points = getattr(b_result, 'b2', []) or []

    conclusions = []
    hit_rule_ids = set()
    for rule_id in registry.ALL_RULE_IDS:
        hits = hits_by_rule.get(rule_id, [])
        meta = registry.RULE_META[rule_id]

        if hits:
            hit_rule_ids.add(rule_id)
            status = meta['max_status']
            for h in hits:
                if h.max_status:
                    status = min_status(status, h.max_status)

            channel = 'A'
            degrade_note = None
            b1 = b1_by_rule.get(rule_id)
            if b1:
                verdict = b1.get('verdict')
                channel = 'fusion'
                if verdict == '上下文无害':
                    new_status = min_status(status, registry.STATUS_REVIEW)
                    if STATUS_RANK[new_status] < STATUS_RANK[status]:
                        degrade_note = ('B1 复核判定「上下文无害」，降级为待复核（人工可推翻）：%s'
                                        % b1.get('reason', ''))
                        status = new_status
                elif verdict == '无法判断':
                    status = min_status(status, registry.STATUS_REVIEW)

            conclusions.append({
                'criterion_id': rule_id,
                'status': status,
                'channel': channel,
                'location': ' | '.join(h.location for h in hits),
                'evidence_ids': list(ev_map.get(rule_id, [])),
                'scope': meta['name'],
                'missing_evidence': [],
                'human_signoff': 'pending',
                'notes': [h.note for h in hits if h.note] + ([degrade_note] if degrade_note else []),
            })

    # ---- B2 侧疑点：低置信进观察区，其余走钉证据
    observations = []
    b_seq = 0
    for pt in b2_points:
        guess = pt.get('rule_guess', '') or ''
        claim = pt.get('claim', '')
        if pt.get('confidence', 'medium') == 'low':
            observations.append({
                'source': 'B2',
                'claim': claim[:200],
                'location': (pt.get('location', '') or '')[:200],
                'confidence': 'low',
                'note': 'LLM 观察（低置信），未经机械核查，不作为结论',
            })
            continue
        pin = pin_fn(guess, pt) if pin_fn else {
            'status': 'unpinned', 'detail': '未执行钉证据', 'rules': [], 'locations': []}

        if pin['status'] == 'pinned':
            # 补盲：只对"未被 A 覆盖"的规则出结论（避免重复）
            new_infos = [r for r in pin.get('rules', [])
                         if r['rule_id'] in registry.RULE_META and r['rule_id'] not in hit_rule_ids]
            for rinfo in new_infos:
                rid = rinfo['rule_id']
                cap = registry.RULE_META[rid]['max_status']
                conclusions.append({
                    'criterion_id': rid,
                    'status': cap,
                    'channel': 'fusion',
                    'location': ' | '.join(rinfo.get('locations', [])[:8]),
                    'evidence_ids': list(rinfo.get('evidence_ids', [])),
                    'scope': 'B2 提疑 + 钉证据补齐（%s）' % registry.RULE_META[rid]['name'],
                    'missing_evidence': [],
                    'human_signoff': 'pending',
                    'notes': ['钉证据通过：%s' % rinfo.get('note', ''),
                              '来源：B2 疑点「%s」' % claim[:120]],
                })
                hit_rule_ids.add(rid)
            continue

        # 未钉成功：保留疑点（待复核），不冒充任何规则结论
        if guess in registry.RULE_META and guess in hit_rule_ids:
            continue
        b_seq += 1
        conclusions.append({
            'criterion_id': 'R-B-%03d' % b_seq,
            'status': registry.STATUS_REVIEW,
            'channel': 'B',
            'location': pt.get('location', '')[:300],
            'evidence_ids': list(pin.get('evidence_ids', [])),
            'scope': claim[:200],
            'missing_evidence': ['钉证据未通过：%s' % pin.get('detail', '')],
            'human_signoff': 'pending',
            'notes': ['B 侧疑点（LLM 提疑），未经确定性钉证据，不得升级措辞'],
        })

    # ---- B1 的补充观察（判定之外的事实陈述）同样进观察区，保留其原始声音
    for rule_id, b1 in b1_by_rule.items():
        obs = (b1 or {}).get('observation', '') or ''
        if obs.strip():
            observations.append({
                'source': 'B1',
                'rule_id': rule_id,
                'claim': obs[:200],
                'location': '',
                'confidence': 'n/a',
                'note': 'B1 复核的补充观察（不构成判定），未经机械核查',
            })
    return conclusions, observations
