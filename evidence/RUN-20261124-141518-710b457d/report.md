# APK 静态审计报告 RUN-20261124-141518-710b457d

- 样本：`good02.apk`
- sha256：`710b457d51f2b960d63470001105522e5eea24d63c4d09d9696d549b3978b1f2`
- 规则包版本：`0.1.6`　｜　通道 B 模型：`mimo-v2.6-flash`
- 工具链：java=openjdk version "1.8.0_492", apktool=apktool_3.0.3.jar

> 证据层级说明：本项目只读、不执行被测 APK，全部证据层级上限为 STATIC。

## 覆盖声明

- 已检查（15 条）：R-MAN-01(manifest)；R-MAN-02(manifest)；R-MAN-03(manifest+res_decoded)；R-MAN-04(manifest)；R-MAN-05(manifest)；R-PERM-01(smali_src)；R-PERM-02(manifest/smali_src)；R-PERM-03(manifest/smali_src)；R-STR-01(dex_strings)；R-STR-02(dex_strings)；R-CODE-01(dex_strings/smali_src)；R-CODE-02(smali_src)；R-NET-01(smali_src)；R-NET-02(smali_src)；通道B(模型:mimo-v2.6-flash)
- 未覆盖（0 条）：—
- 解码状态：正常（复用缓存）

## 已确认（0 条）

（无）

## 待复核（3 条）

### 1. R-B-001 · ProtectedService 对外导出（exported=True），仅依赖自定义签名级权限 com.synth.good02.permission.INTERNAL 挡在外部调用之前；摘要中未见该服务在运行时 enforceCallingPermission/checkCallingPermission 的调用点证据。

- 状态：待复核 ｜ 通道：B ｜ 人工签署：pending
- 证据：`EV-20261124-141518-710b457d-002`
- 定位坐标：
    - `com.synth.good02.ProtectedService (service; exported=True)`
- 说明：B 侧疑点（LLM 提疑），未经确定性钉证据，不得升级措辞
- 缺口：钉证据未通过：断言未被机械事实证实（候选规则 R-MAN-01, R-MAN-02, R-PERM-02 均无机械命中；claim 提及实体（INTERNAL、PROTECTEDSERVICE、com.synth.good02.permission.INTERNAL）未被机械命中覆盖）

### 2. R-B-002 · 自定义权限声明 com.synth.good02.permission.INTERNAL 的 protectionLevel 为 signature，需确认 Manifest 中实际声明值与之一致，且未被降级为 normal/debuggable，也未与系统或其他应用的同名权限产生覆盖冲突。

- 状态：待复核 ｜ 通道：B ｜ 人工签署：pending
- 证据：`EV-20261124-141518-710b457d-003`
- 定位坐标：
    - `AndroidManifest.xml 自定义权限声明 com.synth.good02.permission.INTERNAL`
- 说明：B 侧疑点（LLM 提疑），未经确定性钉证据，不得升级措辞
- 缺口：钉证据未通过：断言未被机械事实证实（候选规则 R-MAN-02, R-MAN-04 均无机械命中；claim 提及实体（INTERNAL、com.synth.good02.permission.INTERNAL）未被机械命中覆盖）

### 3. R-B-003 · 样本声明 INTERNET 权限并存在自有代码 URL（https://example.com/api/profile、https://example.com/secure），需核查请求是否仅走 HTTPS、是否禁用 cleartextTraffic、证书校验是否被放宽（如自定义 TrustManager/HostnameVerifier）。

- 状态：待复核 ｜ 通道：B ｜ 人工签署：pending
- 证据：`EV-20261124-141518-710b457d-004`
- 定位坐标：
    - `自有代码 URL 列表: https://example.com/api/profile; https://example.com/secure`
- 说明：B 侧疑点（LLM 提疑），未经确定性钉证据，不得升级措辞
- 缺口：钉证据未通过：断言未被机械事实证实（候选规则 R-MAN-02, R-MAN-03, R-NET-01 均无机械命中；claim 提及实体（INTERNET、https://example.com/api/profile、https://example.com/secure）未被机械命中覆盖）

## 无法判定（14 条）

> 其中：规则已执行、机械未命中 14 条（不构成安全结论）｜规则未执行 0 条（覆盖缺口）

### 1. R-MAN-01 · 导出组件无权限保护

- 状态：无法判定 ｜ 通道：A ｜ 人工签署：pending
- 定位坐标：
- 说明：机械规则已执行、未命中。仅代表本规则集范围内未发现问题，不构成「安全」结论。

### 2. R-MAN-02 · 危险权限声明

- 状态：无法判定 ｜ 通道：A ｜ 人工签署：pending
- 定位坐标：
- 说明：机械规则已执行、未命中。仅代表本规则集范围内未发现问题，不构成「安全」结论。

### 3. R-MAN-03 · 明文流量许可

- 状态：无法判定 ｜ 通道：A ｜ 人工签署：pending
- 定位坐标：
- 说明：机械规则已执行、未命中。仅代表本规则集范围内未发现问题，不构成「安全」结论。

### 4. R-MAN-04 · 调试与备份风险

- 状态：无法判定 ｜ 通道：A ｜ 人工签署：pending
- 定位坐标：
- 说明：机械规则已执行、未命中。仅代表本规则集范围内未发现问题，不构成「安全」结论。

### 5. R-MAN-05 · 敏感广播监听

- 状态：无法判定 ｜ 通道：A ｜ 人工签署：pending
- 定位坐标：
- 说明：机械规则已执行、未命中。仅代表本规则集范围内未发现问题，不构成「安全」结论。

### 6. R-PERM-01 · 定时/后台结构 × 敏感权限

- 状态：无法判定 ｜ 通道：A ｜ 人工签署：pending
- 定位坐标：
- 说明：机械规则已执行、未命中。仅代表本规则集范围内未发现问题，不构成「安全」结论。

### 7. R-PERM-02 · 非交互组件使用敏感 API

- 状态：无法判定 ｜ 通道：A ｜ 人工签署：pending
- 定位坐标：
- 说明：机械规则已执行、未命中。仅代表本规则集范围内未发现问题，不构成「安全」结论。

### 8. R-PERM-03 · 声明与使用不一致

- 状态：无法判定 ｜ 通道：A ｜ 人工签署：pending
- 定位坐标：
- 说明：机械规则已执行、未命中。仅代表本规则集范围内未发现问题，不构成「安全」结论。

### 9. R-STR-01 · 硬编码凭据

- 状态：无法判定 ｜ 通道：A ｜ 人工签署：pending
- 定位坐标：
- 说明：机械规则已执行、未命中。仅代表本规则集范围内未发现问题，不构成「安全」结论。

### 10. R-STR-02 · 内网/明文端点

- 状态：无法判定 ｜ 通道：A ｜ 人工签署：pending
- 定位坐标：
- 说明：机械规则已执行、未命中。仅代表本规则集范围内未发现问题，不构成「安全」结论。

### 11. R-CODE-01 · 动态代码加载

- 状态：无法判定 ｜ 通道：A ｜ 人工签署：pending
- 定位坐标：
- 说明：机械规则已执行、未命中。仅代表本规则集范围内未发现问题，不构成「安全」结论。

### 12. R-CODE-02 · WebView 危险组合

- 状态：无法判定 ｜ 通道：A ｜ 人工签署：pending
- 定位坐标：
- 说明：机械规则已执行、未命中。仅代表本规则集范围内未发现问题，不构成「安全」结论。

### 13. R-NET-01 · 证书校验绕过结构

- 状态：无法判定 ｜ 通道：A ｜ 人工签署：pending
- 定位坐标：
- 说明：机械规则已执行、未命中。仅代表本规则集范围内未发现问题，不构成「安全」结论。

### 14. R-NET-02 · WebView SSL 错误忽略

- 状态：无法判定 ｜ 通道：A ｜ 人工签署：pending
- 定位坐标：
- 说明：机械规则已执行、未命中。仅代表本规则集范围内未发现问题，不构成「安全」结论。

## B 通道观察（非结论 · 保留模型原声）

> 以下为 LLM 复核/扫描的补充观察，**未经机械核查、不作为结论、不计入三档统计**；仅用于人工参考。

- [B2] SyncReceiver 声明了自定义 action com.synth.good02.action.SYNC，虽 exported=False，但需确认其接收的广播是否为有序/可伪造的系统广播，以及发送方是否用 PendingIntent 可变标志导致广播被劫持。（位置：com.synth.good02.SyncReceiver (receiver; exported=False; actions=[com.synth.good02.action.SYNC])）
    - LLM 观察（低置信），未经机械核查，不作为结论
- [B2] MainActivity 未导出，攻击面较小，但需确认其是否通过隐式 Intent、deep link 或任务栈复用方式被外部拉起并携带敏感参数。（位置：com.synth.good02.MainActivity (activity; exported=False)）
    - LLM 观察（低置信），未经机械核查，不作为结论

---
*本报告由 apkaudit 生成（规则包 0.1.6）。复核方式：按定位坐标直达原文，比对 raw_snippet 与证据 JSONL；结论未经人工签署前不生效。*
