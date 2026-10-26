# APK 静态审计报告 RUN-20261015-150127

- 样本：`good02.apk`
- sha256：`710b457d51f2b960d63470001105522e5eea24d63c4d09d9696d549b3978b1f2`
- 规则包版本：`0.1.3`　｜　通道 B 模型：`mimo-v2.6-flash`
- 工具链：java=openjdk version "1.8.0_492", apktool=apktool_3.0.3.jar

> 证据层级说明：本项目只读、不执行被测 APK，全部证据层级上限为 STATIC。

## 覆盖声明

- 已检查（15 条）：R-MAN-01(manifest)；R-MAN-02(manifest)；R-MAN-03(manifest+res_decoded)；R-MAN-04(manifest)；R-MAN-05(manifest)；R-PERM-01(smali_src)；R-PERM-02(manifest/smali_src)；R-PERM-03(manifest/smali_src)；R-STR-01(dex_strings)；R-STR-02(dex_strings)；R-CODE-01(dex_strings/smali_src)；R-CODE-02(smali_src)；R-NET-01(smali_src)；R-NET-02(smali_src)；通道B(模型:mimo-v2.6-flash)
- 未覆盖（0 条）：—
- 解码状态：正常（复用缓存）

## 已确认（0 条）

（无）

## 待复核（4 条）

### 1. R-B-001 · ProtectedService 声明为 exported=True，可被外部应用访问，其访问控制完全依赖自定义权限 com.synth.good02.permission.INTERNAL

- 状态：待复核 ｜ 通道：B ｜ 人工签署：pending
- 证据：`EV-20261015-150127-002`
- 定位坐标：
    - `com.synth.good2.ProtectedService (manifest <service>)`
- 说明：B 侧疑点（LLM 提疑），未经确定性钉证据，不得升级措辞
- 缺口：钉证据未通过：断言未被机械事实证实（候选规则 R-MAN-02, R-PERM-02 均无机械命中；claim 提及实体（INTERNAL、PROTECTEDSERVICE、com.synth.good02.permission.INTERNAL）未被机械命中覆盖）

### 2. R-B-002 · 自定义权限 com.synth.good02.permission.INTERNAL 的 protectionLevel 为 signature，需确认调用方与本应用同签名才能通过鉴权；若存在同签名共享或调试签名复用场景，防护可能被绕过

- 状态：待复核 ｜ 通道：B ｜ 人工签署：pending
- 证据：`EV-20261015-150127-003`
- 定位坐标：
    - `manifest <permission android:name="com.synth.good02.permission.INTERNAL">`
- 说明：B 侧疑点（LLM 提疑），未经确定性钉证据，不得升级措辞
- 缺口：钉证据未通过：断言未被机械事实证实（候选规则 R-MAN-02, R-MAN-04 均无机械命中；claim 提及实体（INTERNAL、com.synth.good02.permission.INTERNAL）未被机械命中覆盖）

### 3. R-B-003 · 服务使用自定义权限而非系统权限进行保护，需人工确认该权限在 <permission> 中的声明先于任何使用它的组件解析，避免声明顺序导致权限降级为默认 normal 级别

- 状态：待复核 ｜ 通道：B ｜ 人工签署：pending
- 证据：`EV-20261015-150127-004`
- 定位坐标：
    - `manifest 自定义权限声明与 ProtectedService 引用处`
- 说明：B 侧疑点（LLM 提疑），未经确定性钉证据，不得升级措辞
- 缺口：钉证据未通过：断言未被机械事实证实（候选规则 R-MAN-02 均无机械命中）

### 4. R-B-004 · 应用申请了 android.permission.INTERNET 权限，且存在两个自有 HTTPS 网络端点，需核查上报数据范围与 TLS 校验实现（是否校验证书/主机名）

- 状态：待复核 ｜ 通道：B ｜ 人工签署：pending
- 证据：`EV-20261015-150127-005`
- 定位坐标：
    - `权限 INTERNET; URL https://example.com/api/profile, https://example.com/secure`
- 说明：B 侧疑点（LLM 提疑），未经确定性钉证据，不得升级措辞
- 缺口：钉证据未通过：断言未被机械事实证实（候选规则 R-MAN-02, R-NET-01 均无机械命中；claim 提及实体（ANDROID.PERMISSION.INTERNET、INTERNET、android.permission.INTERNET）未被机械命中覆盖）

## 无法判定（0 条）

（无）

## B 通道观察（非结论 · 保留模型原声）

> 以下为 LLM 复核/扫描的补充观察，**未经机械核查、不作为结论、不计入三档统计**；仅用于人工参考。

- [B2] SyncReceiver 虽为 exported=False，但监听自定义 action com.synth.good02.action.SYNC，需确认该 action 是否仅由本应用内部广播触发，是否存在隐式广播可达的动态注册接收器（位置：com.synth.good02.SyncReceiver (action=com.synth.good02.action.SYNC)）
    - LLM 观察（低置信），未经机械核查，不作为结论
- [B2] 网络端点硬编码于自有代码中（example.com 域名），需确认是否为占位/测试域名，以及是否存在后续动态下发可覆盖的配置（位置：自有代码 URL 列表）
    - LLM 观察（低置信），未经机械核查，不作为结论

---
*本报告由 apkaudit 生成（规则包 0.1.3）。复核方式：按定位坐标直达原文，比对 raw_snippet 与证据 JSONL；结论未经人工签署前不生效。*
