# -*- coding: utf-8 -*-
"""llm.py · 评价器模型客户端（独立于产品；失败自动降级确定性判读）

与产品隔离纪律（总档 §8.3）：本模块不继承产品执行能力，只做文本判读。
"""

import json
import os
import urllib.request

from core import registry


def _load_cfg(project_root):
    path = os.path.join(project_root, registry.KEY_FILE_NAME)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith('#'):
                    continue
                parts = [p.strip() for p in line.split(',')]
                if len(parts) >= 3 and all(parts[:3]):
                    return tuple(parts[:3])
    except OSError:
        return None
    return None


def judge(project_root, system, user, timeout=None):
    """返回 (ok, text_or_error)。任何失败都返回 ok=False 由调用方降级。"""
    cfg = _load_cfg(project_root)
    if not cfg:
        return False, '未配置模型（key.txt 缺失）'
    model, base_url, api_key = cfg
    url = base_url.rstrip('/') + '/chat/completions'
    payload = {
        'model': model,
        'messages': [{'role': 'system', 'content': system},
                     {'role': 'user', 'content': user}],
        'temperature': 0,
        'max_tokens': registry.LLM_MAX_TOKENS,
    }
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json',
                 'Authorization': 'Bearer %s' % api_key},
        method='POST')
    try:
        with urllib.request.urlopen(req, timeout=timeout or registry.LLM_TIMEOUT_SECONDS) as resp:
            body = json.loads(resp.read().decode('utf-8', 'replace'))
        return True, body['choices'][0]['message']['content']
    except Exception as e:  # noqa: BLE001
        return False, '模型调用失败：%s' % e
