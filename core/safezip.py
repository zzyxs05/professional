# -*- coding: utf-8 -*-
"""safezip.py · zip 成员读取的安全上限

审计对象是敌对样本：高压缩比成员（zip bomb）会在 z.read() 时一次性展开进内存，
把审计进程直接打挂。这里按中央目录声明的 file_size 先行拒绝，不做任何解压。

依据（第 5 次审查核实）：CPython zipfile 以中央目录声明的 file_size 作为读取
边界（读满即做 CRC 核对，谎报头会抛 BadZipFile 而非无限解压），因此「声明值
预检」在本运行时下是完备的，不需要额外的流式硬上限。

纪律：只做上限判断，不改变正常样本的读取结果（上限见 registry.ZIP_MEMBER_MAX_BYTES）。
若未来更换 zip 实现（非 CPython zipfile），需复查该实现是否同样强制声明边界。
"""

from . import registry


class ZipMemberTooLarge(ValueError):
    """成员解压后体积超限（疑似 zip bomb）。"""


def read_member(z, name, limit=None):
    """读取 zip 成员；声明体积超过上限即拒绝，否则行为等同 z.read(name)。"""
    limit = limit or registry.ZIP_MEMBER_MAX_BYTES
    info = z.getinfo(name)          # 不存在则抛 KeyError，由调用方按原语义处理
    if info.file_size > limit:
        raise ZipMemberTooLarge(
            '%s 解压后 %d 字节，超过上限 %d（疑似 zip bomb）'
            % (name, info.file_size, limit))
    return z.read(name)
