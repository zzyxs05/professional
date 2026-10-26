# APK 静态审计报告 RUN-20261015-145503

- 样本：`bad02.apk`
- sha256：`232666b8c0bf411dd454f5ec0922a5795a5c594e0eff56cbecce9f376a4f0d4c`
- 规则包版本：`0.1.3`　｜　通道 B 模型：`mimo-v2.6-flash`
- 工具链：java=openjdk version "1.8.0_492", apktool=apktool_3.0.3.jar

> 证据层级说明：本项目只读、不执行被测 APK，全部证据层级上限为 STATIC。

## 覆盖声明

- 已检查（15 条）：R-MAN-01(manifest)；R-MAN-02(manifest)；R-MAN-03(manifest+res_decoded)；R-MAN-04(manifest)；R-MAN-05(manifest)；R-PERM-01(smali_src)；R-PERM-02(manifest/smali_src)；R-PERM-03(manifest/smali_src)；R-STR-01(dex_strings)；R-STR-02(dex_strings)；R-CODE-01(dex_strings/smali_src)；R-CODE-02(smali_src)；R-NET-01(smali_src)；R-NET-02(smali_src)；通道B(模型:mimo-v2.6-flash)
- 未覆盖（0 条）：—
- 解码状态：正常（复用缓存）

## 已确认（2 条）

### 1. R-STR-01 · 硬编码凭据

- 状态：已确认 ｜ 通道：fusion ｜ 人工签署：pending
- 证据：`EV-20261015-145503-001`, `EV-20261015-145503-002`, `EV-20261015-145503-003`, `EV-20261015-145503-004`, `EV-20261015-145503-005`, `EV-20261015-145503-006`
- 定位坐标：
    - `classes.dex#str[3275]`
    - `classes.dex#str[7293]`
    - `classes.dex#str[8841]`
    - `classes.dex#str[8939]`
    - `res/values/strings.xml:4 [@string/backup_access_key]`
    - `res/values/strings.xml:6 [@string/payment_gateway_key]`
- 说明：凭据形式匹配：AWS Access Key（dex 字符串常量）
- 说明：凭据形式匹配：AWS Access Key（dex 字符串常量）
- 说明：凭据形式匹配：GitHub Token（dex 字符串常量）
- 说明：凭据形式匹配：GitHub Token（dex 字符串常量）
- 说明：凭据形式匹配：AWS Access Key（资源字符串）
- 说明：凭据形式匹配：Stripe Key（资源字符串）

### 2. R-STR-02 · 内网/明文端点

- 状态：已确认 ｜ 通道：fusion ｜ 人工签署：pending
- 证据：`EV-20261015-145503-007`, `EV-20261015-145503-008`, `EV-20261015-145503-009`
- 定位坐标：
    - `classes.dex#str[8938]`
    - `classes.dex#str[8939]`
    - `res/values/strings.xml:5 [@string/internal_api_base]`
- 说明：内网/明文端点（dex 字符串常量）
- 说明：内网/明文端点（dex 字符串常量）
- 说明：内网/明文端点（资源字符串）

## 待复核（1 条）

### 1. R-B-001 · API 请求使用明文 HTTP 协议传输，令牌与用户 profile 数据未加密，易被中间人窃听或篡改

- 状态：待复核 ｜ 通道：B ｜ 人工签署：pending
- 证据：`EV-20261015-145503-018`
- 定位坐标：
    - `http://10.0.0.8:8080/api/profile`
- 说明：B 侧疑点（LLM 提疑），未经确定性钉证据，不得升级措辞
- 缺口：钉证据未通过：断言未被机械事实证实（候选规则 R-MAN-03 均无机械命中）

## 无法判定（0 条）

（无）

## B 通道观察（非结论 · 保留模型原声）

> 以下为 LLM 复核/扫描的补充观察，**未经机械核查、不作为结论、不计入三档统计**；仅用于人工参考。

- [B2] 应用声明 INTERNET 权限，而唯一可见网络入口是上述携带令牌的 API 调用，需核实该权限是否被用于其他未列出的外联行为（位置：AndroidManifest: android.permission.INTERNET / com.synth.bad02.MainActivity）
    - LLM 观察（低置信），未经机械核查，不作为结论
- [B1·R-STR-02] 其中一处 URL 附带 ghp_ 开头的 token 占位串，可能涉及凭据经明文传输；字符串前缀的单字符（如 'M'）疑为 dex 字符串表相邻数据的截取噪声。
    - B1 复核的补充观察（不构成判定），未经机械核查

---
*本报告由 apkaudit 生成（规则包 0.1.3）。复核方式：按定位坐标直达原文，比对 raw_snippet 与证据 JSONL；结论未经人工签署前不生效。*
