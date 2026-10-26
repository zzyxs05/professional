# -*- coding: utf-8 -*-
"""R-PERM-03 · 声明与使用不一致（过度声明）（数据源：manifest + smali_src）

分档（按"静态排除力"，与 R-PERM-01 同构）：
  ① 无隐藏调用通道：样本未使用反射/JNI/动态加载 → "代码内未发现使用"的可信度提高
     → **已确认**，措辞限定为"在当前 APK 自有代码范围内未发现使用"（不断言绝对无使用）。
  ② 存在隐藏调用通道：运行时可绕过静态扫描 → **待复核**，并在结论中列明具体通道。
"""

from ... import registry

RULE_ID = "R-PERM-03"


def _hidden_channels(text):
    found = []
    for label, pat in registry.HIDDEN_CHANNEL_PATTERNS.items():
        if pat in text:
            found.append(label)
    return found


def run(ctx):
    facts = ctx.manifest
    smali = ctx.smali
    if facts is None or smali is None:
        return []
    app_files = smali.app_files(ctx.app_package, ctx.rule_notes)
    chunks = []
    for rel in app_files:
        chunks.extend(smali.read_lines(rel))
    text = '\n'.join(chunks)

    unused = []
    unchecked = []
    for p in facts.permissions:
        if not registry.is_sensitive_permission(p.name):
            continue
        if p.name in registry.BROADCAST_TYPE_PERMISSIONS:
            continue
        if p.name in registry.DECLARATION_ONLY_PERMISSIONS:
            continue  # 声明即生效，无对应 API 调用点，不参与"未发现使用"判定
        patterns = registry.PERMISSION_USAGE_PATTERNS.get(p.name)
        if not patterns:
            unchecked.append(p.name)
            continue
        if not any(pat in text for pat in patterns):
            unused.append(p)

    if unchecked:
        ctx.rule_notes.append(
            '%s: %d 项敏感权限无使用模式定义，未参与比对（%s）'
            % (RULE_ID, len(unchecked), ', '.join(unchecked)))

    if not unused:
        return []

    channels = _hidden_channels(text)
    loc = 'AndroidManifest.xml:%d-%d [uses-permission × %d]' % (
        unused[0].line, unused[-1].line, len(unused))
    snippet = '; '.join(p.name for p in unused)

    # 机械层已完成的检索（事实陈述，供 B 通道复核时参考，不含判定倾向）
    example = registry.PERMISSION_USAGE_PATTERNS.get(unused[0].name, [])[:2]
    context = ('机械层已完成：扫描自有代码 %d 个文件；'
               '检索 %d 项权限对应的 API 使用模式（例：%s）均无命中；'
               '隐藏调用通道检测（反射/JNI/动态加载）：%s'
               % (len(app_files), len(unused),
                  '、'.join(example) or '无模式定义',
                  ('无' if not channels else '、'.join(channels))))

    from ..common import Hit
    if channels:
        return [Hit(
            RULE_ID, loc, snippet,
            note='敏感权限声明后在自有代码中未发现使用；样本存在隐藏调用通道（%s），'
                 '运行时可能绕过静态扫描，故停在待复核' % '、'.join(channels[:5]),
            max_status=registry.STATUS_REVIEW, context=context)]
    return [Hit(
        RULE_ID, loc, snippet,
        note='敏感权限声明后未发现使用：在当前 APK 自有代码范围内检索无对应调用，'
             '且样本未使用反射/JNI/动态加载等可隐藏调用的机制'
             '（不排除运行时动态下发的代码调用）',
        context=context)]
