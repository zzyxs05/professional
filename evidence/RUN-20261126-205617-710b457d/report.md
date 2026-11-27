# APK 静态审计报告 RUN-20261126-205617-710b457d

- 样本：`good02.apk`
- sha256：`710b457d51f2b960d63470001105522e5eea24d63c4d09d9696d549b3978b1f2`
- 规则包版本：`0.1.8`　｜　通道 B 模型：`mimo-v2.6-flash`
- 工具链：java=openjdk version "1.8.0_492", apktool=apktool_3.0.3.jar

> 证据层级说明：本项目只读、不执行被测 APK，全部证据层级上限为 STATIC。

## 覆盖声明

- 已检查（15 条）：R-MAN-01(manifest)；R-MAN-02(manifest)；R-MAN-03(manifest+res_decoded)；R-MAN-04(manifest)；R-MAN-05(manifest)；R-PERM-01(smali_src)；R-PERM-02(manifest/smali_src)；R-PERM-03(manifest/smali_src)；R-STR-01(dex_strings)；R-STR-02(dex_strings)；R-CODE-01(dex_strings/smali_src)；R-CODE-02(smali_src)；R-NET-01(smali_src)；R-NET-02(smali_src)；通道B(模型:mimo-v2.6-flash)
- 未覆盖（0 条）：—
- 解码状态：正常（复用缓存）

## 已确认（0 条）

（无）

## 待复核（2 条）

### 1. R-B-001 · ProtectedService 为 exported=True，其访问控制完全依赖自定义权限 com.synth.good02.permission.INTERNAL（protectionLevel=signature），未见其他鉴权描述；需人工确认该权限确实在 AndroidManifest 中声明、声明顺序早于使用方，且服务端（onStartCommand/onBind/调用入口）有实际的 

- 状态：待复核 ｜ 通道：B ｜ 人工签署：pending
- 证据：`EV-20261126-205617-710b457d-002`
- 定位坐标：
    - `com.synth.good02.ProtectedService (service; exported=True; permission=com.synth.good02.permission.INTERNAL)`
- 说明：B 侧疑点（LLM 提疑），未经确定性钉证据，不得升级措辞
- 缺口：钉证据未通过：断言未被机械事实证实（候选规则 R-MAN-01, R-MAN-02, R-PERM-02 均无机械命中；claim 提及实体（INTERNAL、PROTECTEDSERVICE、com.synth.good02.permission.INTERNAL）未被机械命中覆盖）

### 2. R-B-002 · 自定义权限 protectionLevel 标注为 signature，需核实清单原文是否为纯 signature 而非 signatureOrSystem/debuggable 等弱化取值，并确认未与系统或第三方同名权限冲突（权限抢占）

- 状态：待复核 ｜ 通道：B ｜ 人工签署：pending
- 证据：`EV-20261126-205617-710b457d-003`
- 定位坐标：
    - `自定义权限声明：com.synth.good02.permission.INTERNAL`
- 说明：B 侧疑点（LLM 提疑），未经确定性钉证据，不得升级措辞
- 缺口：钉证据未通过：断言未被机械事实证实（候选规则 R-MAN-02, R-MAN-04 均无机械命中）

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

- [B2] SyncReceiver 虽声明 exported=False，但监听自定义 action com.synth.good02.action.SYNC；需核查是否存在动态注册（registerReceiver）时未指定权限或使用了 exported=true 的情形，以及该 action 是否可被外部广播触发（位置：com.synth.good02.SyncReceiver (receiver; exported=False; actions=[com.synth.good02.action.SYNC])）
    - LLM 观察（低置信），未经机械核查，不作为结论
- [B2] 自有代码中出现网络出口 URL https://example.com/api/profile 与 https:///secure，样本摘要未包含网络安全配置（networkSecurityConfig）、证书校验或明文流量策略信息，需人工确认是否启用 cleartext、是否对 API 域名做证书/主机名校验（位置：https://example.com/api/profile; https://example.com/secure）
    - LLM 观察（低置信），未经机械核查，不作为结论
- [B2] 申请了 android.permission.INTERNET 权限且存在外部 URL 出口，但摘要中未见动态加载/反射/dex 加载点，需确认是否存在未被摘要覆盖的代码执行或下载后加载路径（位置：权限：android.permission.INTERNET）
    - LLM 观察（低置信），未经机械核查，不作为结论

---
*本报告由 apkaudit 生成（规则包 0.1.8）。复核方式：按定位坐标直达原文，比对 raw_snippet 与证据 JSONL；结论未经人工签署前不生效。*
