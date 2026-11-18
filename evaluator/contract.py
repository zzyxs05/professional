# -*- coding: utf-8 -*-
"""contract.py · 批准契约加载（评价 Agent 的目标参数化基础）

纪律：评价 Agent 不得用本仓库的规则去判异题项目。互评必须有目标方提供、
教师批准的契约；自评可以使用本仓库规格层生成的内部快照，但须显式标注未批准。
"""

import json
import os

from core import registry

CONTRACT_REL_CANDIDATES = (
    'evaluation/contract.json',
    'review/evaluation/contract.json',
    'docs/contract.json',
)


def internal_snapshot(owner_root):
    """自评专用：从本仓库规格层生成机器可读快照（未批准，不构成正式契约）。"""
    spec = os.path.join(owner_root, 'docs', 'specification.md')
    acc = os.path.join(owner_root, 'docs', 'acceptance-matrix.md')
    return {
        'contract_id': 'internal-snapshot-%s' % registry.RULE_PACK_VERSION,
        'source': 'static_inspection',
        'approved_by': 'pending',
        'scope': 'internal_self_review_only',
        'level_ceiling': 'STATIC',
        'rule_pack_version': registry.RULE_PACK_VERSION,
        'rules': {rid: meta['name'] for rid, meta in registry.RULE_META.items()},
        'spec': 'docs/specification.md' if os.path.isfile(spec) else None,
        'acceptance': 'docs/acceptance-matrix.md' if os.path.isfile(acc) else None,
        'note': '程序生成的内部快照，未经人批准；只用于自评，不用于互评，不可引作已批准契约。',
    }


def load_contract(owner_root, target_root, mode, contract_path=None):
    """返回 (contract_dict_or_None, note)。"""
    if contract_path:
        path = (contract_path if os.path.isabs(contract_path)
                else os.path.join(owner_root, contract_path))
        if not os.path.isfile(path):
            return None, '契约文件不存在：%s' % path
        try:
            with open(path, 'r', encoding='utf-8') as f:
                contract = json.load(f)
        except (OSError, ValueError) as e:
            return None, '契约不可解析：%s' % e
        contract.setdefault('source', 'target_claim')
        return contract, '使用显式契约：%s' % path

    for rel in CONTRACT_REL_CANDIDATES:
        path = os.path.join(target_root, rel)
        if os.path.isfile(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    contract = json.load(f)
            except (OSError, ValueError) as e:
                return None, '目标契约不可解析：%s' % e
            contract.setdefault('source', 'target_claim')
            return contract, '使用目标仓库契约：%s' % rel

    if mode == 'self':
        return internal_snapshot(owner_root), '使用内部契约快照（未批准，仅自评）'

    return None, ('互评缺少目标批准契约：请提供 --contract，或让对方在仓库内提供 '
                  'evaluation/contract.json；不得用本仓库规则代替。')
