# -*- coding: utf-8 -*-
"""common.py · 规则公共设施（Hit、方法体清洗、定位格式化）"""


class Hit(object):
    """规则命中三元组 + 附注。max_status 为规则级档位覆盖（None=用 registry 默认）。

    context：规则在机械层"已完成哪些检索/检测"的事实说明（不含判定倾向），
    用于向 B 通道补齐输入信息——信息不全会让模型判"无法判断"。
    """
    __slots__ = ('rule_id', 'location', 'raw_snippet', 'note', 'max_status', 'context')

    def __init__(self, rule_id, location, raw_snippet, note='', max_status=None, context=''):
        self.rule_id = rule_id
        self.location = location
        self.raw_snippet = raw_snippet
        self.note = note
        self.max_status = max_status
        self.context = context


def effective_ops(body):
    """清洗 smali 方法体 → [(lineno, insn)]。

    过滤：空行/注释/#、.annotation 块（含块内行）、.line/.locals/.param/.catch*/.end*、
    label（: 开头）。保留：真实指令行。
    """
    ops = []
    in_annotation = False
    for lineno, raw in body:
        s = raw.strip()
        if not s or s.startswith('#'):
            continue
        if s.startswith('.annotation'):
            in_annotation = True
            continue
        if s.startswith('.end annotation'):
            in_annotation = False
            continue
        if in_annotation:
            continue
        if (s.startswith('.line') or s.startswith('.locals') or s.startswith('.param')
                or s.startswith('.catch') or s.startswith('.end') or s == '.prologue'):
            continue
        if s.startswith(':'):
            continue
        ops.append((lineno, s))
    return ops


def origin_line(lines, smali_lineno):
    """1 基 smali 行号 → 最近（含本行）向前 .line N 的值；无则 None。"""
    idx = min(smali_lineno - 1, len(lines) - 1)
    for i in range(idx, -1, -1):
        s = lines[i].strip()
        if s.startswith('.line '):
            try:
                return int(s[6:].strip())
            except ValueError:
                return None
    return None


def smali_loc(rel, smali_lineno, lines):
    """smali 定位：文件:行号（原始行 N）。"""
    orig = origin_line(lines, smali_lineno)
    return '%s:%d（原始行 %s）' % (rel, smali_lineno, orig if orig is not None else '?')


def clip(text, limit=200):
    text = text.strip()
    if len(text) > limit:
        return text[:limit] + '…'
    return text


def ops_have_invoke(ops):
    return any('invoke-' in op for _, op in ops)


def is_empty_method_body(ops):
    """无校验实现：没有实质校验逻辑的方法体（0.1.7 扩宽，F-01）。

    除 return-void / nop 外，允许常量装配与日志/无返回值的调用
    （Log.d、打印等只做记录、不做校验），但不放过真正的校验动作：
    - 任何 throw / move-exception（抛异常型校验）
    - 任何返回非 void（有判定结果）
    - 对 TrustManager/证书/主机名相关对象的 invoke（实质校验委托）
    - 条件跳转（if-*，做了判断）

    这样"空方法体 + 一行 Log.d"仍判为空实现（对抗组 F-01 漏报），
    而真实实现（委托校验、抛异常、条件判断）不会被误判。
    """
    if not ops:
        return False
    insns = [op for _, op in ops]
    if not any(op.startswith('return-void') for op in insns):
        return False
    benign_call_tokens = (
        'Landroid/util/Log;->', 'Ljava/io/PrintStream;->',
        'Ljava/lang/System;->out', 'Ljava/lang/StringBuilder;->',
    )
    for op in insns:
        s = op.strip()
        if s.startswith('return') and not s.startswith('return-void'):
            return False
        if 'throw' in s or 'move-exception' in s:
            return False
        if s.startswith('if-') or s.startswith('goto'):
            return False
        if 'invoke-' in s:
            # 只放行记录类调用；涉及证书/校验对象的调用视为实质校验
            if not any(tok in s for tok in benign_call_tokens):
                return False
            if any(tok in s for tok in ('TrustManager', 'X509', 'Certificate',
                                        'checkServerTrusted', 'checkClientTrusted')):
                return False
        # const / new-instance / move-result 等装配指令允许
    return True


def is_empty_array_return(ops):
    """返回空数组：指令精简（≤5）且含 new-array 或 const 0，无 invoke/iget/sget。"""
    insns = [op for _, op in ops]
    if not insns or len(insns) > 6:
        return False
    if any(k in op for op in insns for k in ('invoke-', 'iget', 'sget', 'aget')):
        return False
    has_new_array = any(op.startswith('new-array') for op in insns)
    return has_new_array


def is_const_true_return(ops):
    """方法体无 invoke 且返回常量真（const vX, 0x1 + return vX 形态）。"""
    insns = [op for _, op in ops]
    if not insns:
        return False
    if any('invoke-' in op for op in insns):
        return False
    has_true = any(op.startswith('const') and op.rstrip().endswith('0x1') for op in insns)
    has_return = any(op.startswith('return') for op in insns)
    return has_true and has_return


def class_interfaces(lines, limit=40):
    """读 smali 文件头部的 .implements / .super 行。"""
    out = []
    for line in lines[:limit]:
        s = line.strip()
        if s.startswith('.implements') or s.startswith('.super'):
            out.append(s)
        if s.startswith('.method'):
            break
    return out
