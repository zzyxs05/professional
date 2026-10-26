# APK 静态审计报告 RUN-20261015-150236

- 样本：`bad04.apk`
- sha256：`e11522640317bad12bafb2aecd880d348343b66234a42b1b28e206e7c846dab7`
- 规则包版本：`0.1.3`　｜　通道 B 模型：`mimo-v2.6-flash`
- 工具链：java=openjdk version "1.8.0_492", apktool=apktool_3.0.3.jar

> 证据层级说明：本项目只读、不执行被测 APK，全部证据层级上限为 STATIC。

## 覆盖声明

- 已检查（15 条）：R-MAN-01(manifest)；R-MAN-02(manifest)；R-MAN-03(manifest+res_decoded)；R-MAN-04(manifest)；R-MAN-05(manifest)；R-PERM-01(smali_src)；R-PERM-02(manifest/smali_src)；R-PERM-03(manifest/smali_src)；R-STR-01(dex_strings)；R-STR-02(dex_strings)；R-CODE-01(dex_strings/smali_src)；R-CODE-02(smali_src)；R-NET-01(smali_src)；R-NET-02(smali_src)；通道B(模型:mimo-v2.6-flash)
- 未覆盖（0 条）：—
- 解码状态：正常（复用缓存）

## 已确认（2 条）

### 1. R-MAN-01 · 导出组件无权限保护

- 状态：已确认 ｜ 通道：fusion ｜ 人工签署：pending
- 证据：`EV-20261015-150236-001`
- 定位坐标：
    - `AndroidManifest.xml:5-5 [activity com.synth.bad04.MainActivity]`
- 说明：导出组件 com.synth.bad04.MainActivity 无权限保护（android:exported="true"）

### 2. R-STR-01 · 硬编码凭据

- 状态：已确认 ｜ 通道：fusion ｜ 人工签署：pending
- 证据：`EV-20261015-150236-002`, `EV-20261015-150236-003`
- 定位坐标：
    - `classes.dex#str[3276]`
    - `classes.dex#str[11052]`
- 说明：凭据形式匹配：AWS Access Key（dex 字符串常量）
- 说明：凭据形式匹配：AWS Access Key（dex 字符串常量）

## 待复核（0 条）

（无）

## 无法判定（0 条）

（无）

## B 通道观察（非结论 · 保留模型原声）

> 以下为 LLM 复核/扫描的补充观察，**未经机械核查、不作为结论、不计入三档统计**；仅用于人工参考。

- [B2] 敏感区域摘要中未列出任何权限调用点、自定义权限声明、网络入口或动态加载点，样本的敏感行为线索极少，可能是扫描覆盖不全或样本本身仅暴露了导出组件（位置：(全样本摘要)）
    - LLM 观察（低置信），未经机械核查，不作为结论
- [B1·R-MAN-01] 命中位于 AndroidManifest.xml 第5行，导出组件为 com.synth.bad04.MainActivity，缺少权限声明；若该组件另有 intent-filter 或需结合用途评估风险等级，可进一步核查
    - B1 复核的补充观察（不构成判定），未经机械核查
- [B1·R-STR-01] AKIAIOSFODNN7EXAMPLE 是 AWS 官方文档惯用的示例 key（后缀 EXAMPLE 为文档占位惯例），第二处命中还带日志上下文 /storage access key in use:，更像演示或日志输出代码；但按本规则口径这类值仍须上报，真伪与用途不在裁定范围内。
    - B1 复核的补充观察（不构成判定），未经机械核查

---
*本报告由 apkaudit 生成（规则包 0.1.3）。复核方式：按定位坐标直达原文，比对 raw_snippet 与证据 JSONL；结论未经人工签署前不生效。*
