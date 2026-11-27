# APK 静态审计报告 RUN-20261127-191624-867c78d2

- 样本：`v2bis_isolated.apk`
- sha256：`867c78d29fd463c6d303503582e405e3d1fa0bbb5fb9e4463bb4b92870a0a5a7`
- 规则包版本：`0.1.8`　｜　通道 B 模型：`deepseek-flash`
- 工具链：java=openjdk version "11.0.0.2" 2024-07-02, apktool=apktool_3.0.3.jar

> 证据层级说明：本项目只读、不执行被测 APK，全部证据层级上限为 STATIC。

## 覆盖声明

- 已检查（15 条）：R-MAN-01(manifest)；R-MAN-02(manifest)；R-MAN-03(manifest+res_decoded)；R-MAN-04(manifest)；R-MAN-05(manifest)；R-PERM-01(smali_src)；R-PERM-02(manifest/smali_src)；R-PERM-03(manifest/smali_src)；R-STR-01(dex_strings)；R-STR-02(dex_strings)；R-CODE-01(dex_strings/smali_src)；R-CODE-02(smali_src)；R-NET-01(smali_src)；R-NET-02(smali_src)；通道B(模型:deepseek-flash)
- 未覆盖（0 条）：—
- 解码状态：正常（复用缓存）

## 已确认（5 条）

### 1. R-MAN-02 · 危险权限声明

- 状态：已确认 ｜ 通道：fusion ｜ 人工签署：pending
- 证据：`EV-20261127-191624-867c78d2-001`, `EV-20261127-191624-867c78d2-002`
- 定位坐标：
    - `AndroidManifest.xml:5 [uses-permission]`
    - `AndroidManifest.xml:6 [uses-permission]`
- 说明：声明敏感权限：android.permission.RECORD_AUDIO（录音）
- 说明：声明敏感权限：android.permission.ACCESS_FINE_LOCATION（精确定位）

### 2. R-CODE-01 · 动态代码加载

- 状态：已确认 ｜ 通道：fusion ｜ 人工签署：pending
- 证据：`EV-20261127-191624-867c78d2-005`, `EV-20261127-191624-867c78d2-006`, `EV-20261127-191624-867c78d2-007`
- 定位坐标：
    - `smali/com/synth/bad03/MainActivity.smali:82（原始行 69）`
    - `smali/com/synth/bad03/MainActivity.smali:101（原始行 73）`
    - `smali/com/synth/bad03/MainActivity.smali:106（原始行 74）`
- 说明：动态代码加载调用：Ldalvik/system/DexClassLoader;
- 说明：动态代码加载调用：Ldalvik/system/DexClassLoader;
- 说明：动态代码加载调用：Ldalvik/system/DexClassLoader;

### 3. R-CODE-02 · WebView 危险组合

- 状态：已确认 ｜ 通道：fusion ｜ 人工签署：pending
- 证据：`EV-20261127-191624-867c78d2-008`, `EV-20261127-191624-867c78d2-009`, `EV-20261127-191624-867c78d2-010`
- 定位坐标：
    - `smali/com/synth/bad03/MainActivity.smali:197（原始行 46）`
    - `smali/com/synth/bad03/MainActivity.smali:183（原始行 44）`
    - `smali/com/synth/bad03/MainActivity.smali:186（原始行 45）`
- 说明：WebView 危险组合要素：addJavascriptInterface
- 说明：WebView 危险组合要素：setJavaScriptEnabled
- 说明：WebView 危险组合要素：setAllowFileAccess

### 4. R-NET-01 · 证书校验绕过结构

- 状态：已确认 ｜ 通道：fusion ｜ 人工签署：pending
- 证据：`EV-20261127-191624-867c78d2-011`, `EV-20261127-191624-867c78d2-012`, `EV-20261127-191624-867c78d2-013`, `EV-20261127-191624-867c78d2-014`
- 定位坐标：
    - `smali/com/synth/bad03/InsecureTls$1.smali:35（原始行 32）`
    - `smali/com/synth/bad03/InsecureTls$1.smali:41（原始行 32）`
    - `smali/com/synth/bad03/InsecureTls$1.smali:47（原始行 32）`
    - `smali/com/synth/bad03/InsecureTls$2.smali:35（原始行 53）`
- 说明：X509TrustManager.checkClientTrusted 空实现（证书校验被跳过）；检测到安装点 smali/com/synth/bad03/InsecureTls.smali:53（原始行 51）
- 说明：X509TrustManager.checkServerTrusted 空实现（证书校验被跳过）
- 说明：X509TrustManager.getAcceptedIssuers 返回空数组
- 说明：HostnameVerifier.verify 返回恒真（域名校验被跳过）

### 5. R-NET-02 · WebView SSL 错误忽略

- 状态：已确认 ｜ 通道：fusion ｜ 人工签署：pending
- 证据：`EV-20261127-191624-867c78d2-015`
- 定位坐标：
    - `smali/com/synth/bad03/InsecureWebViewClient.smali:45（原始行 20）`
- 说明：onReceivedSslError 忽略 SSL 错误（proceed）

## 待复核（1 条）

### 1. R-PERM-01 · 定时/后台结构 × 敏感权限

- 状态：待复核 ｜ 通道：fusion ｜ 人工签署：pending
- 证据：`EV-20261127-191624-867c78d2-003`, `EV-20261127-191624-867c78d2-004`
- 定位坐标：
    - `smali/com/synth/bad03/MainActivity.smali:227（原始行 56）`
    - `smali/com/synth/bad03/Worker.smali:20（原始行 ?）`
- 说明：调度原语：Landroid/os/Handler;->postDelayed
- 说明：敏感 API：录音
- 缺口：存在不可直接解析的调度目标（smali/com/synth/bad03/MainActivity.smali:227（原始行 56） 等），Runnable/接口回调/动态类名的跨方法链未解析

## 无法判定（8 条）

> 其中：规则已执行、机械未命中 8 条（不构成安全结论）｜规则未执行 0 条（覆盖缺口）

### 1. R-MAN-01 · 导出组件无权限保护

- 状态：无法判定 ｜ 通道：A ｜ 人工签署：pending
- 定位坐标：
- 说明：机械规则已执行、未命中。仅代表本规则集范围内未发现问题，不构成「安全」结论。

### 2. R-MAN-03 · 明文流量许可

- 状态：无法判定 ｜ 通道：A ｜ 人工签署：pending
- 定位坐标：
- 说明：机械规则已执行、未命中。仅代表本规则集范围内未发现问题，不构成「安全」结论。

### 3. R-MAN-04 · 调试与备份风险

- 状态：无法判定 ｜ 通道：A ｜ 人工签署：pending
- 定位坐标：
- 说明：机械规则已执行、未命中。仅代表本规则集范围内未发现问题，不构成「安全」结论。

### 4. R-MAN-05 · 敏感广播监听

- 状态：无法判定 ｜ 通道：A ｜ 人工签署：pending
- 定位坐标：
- 说明：机械规则已执行、未命中。仅代表本规则集范围内未发现问题，不构成「安全」结论。

### 5. R-PERM-02 · 非交互组件使用敏感 API

- 状态：无法判定 ｜ 通道：A ｜ 人工签署：pending
- 定位坐标：
- 说明：机械规则已执行、未命中。仅代表本规则集范围内未发现问题，不构成「安全」结论。

### 6. R-PERM-03 · 声明与使用不一致

- 状态：无法判定 ｜ 通道：A ｜ 人工签署：pending
- 定位坐标：
- 说明：机械规则已执行、未命中。仅代表本规则集范围内未发现问题，不构成「安全」结论。

### 7. R-STR-01 · 硬编码凭据

- 状态：无法判定 ｜ 通道：A ｜ 人工签署：pending
- 定位坐标：
- 说明：机械规则已执行、未命中。仅代表本规则集范围内未发现问题，不构成「安全」结论。

### 8. R-STR-02 · 内网/明文端点

- 状态：无法判定 ｜ 通道：A ｜ 人工签署：pending
- 定位坐标：
- 说明：机械规则已执行、未命中。仅代表本规则集范围内未发现问题，不构成「安全」结论。

## B 通道观察（非结论 · 保留模型原声）

> 以下为 LLM 复核/扫描的补充观察，**未经机械核查、不作为结论、不计入三档统计**；仅用于人工参考。

- [B2] 声明了非导出的 RecordingService 且应用持有 RECORD_AUDIO 权限，需核查该服务是否可能在无用户明确交互时录音，以及录音数据存储/传输路径。（位置：com.synth.bad03.RecordingService (service; exported=False)）
    - LLM 观察（低置信），未经机械核查，不作为结论
- [B2] 自有代码中仅见 URL https://example.com/app，使用保留示例域名，需确认是否为占位/测试端点，以及发布版本是否会向该地址发送敏感数据。（位置：自有代码 URL：https://example.com/app）
    - LLM 观察（低置信），未经机械核查，不作为结论
- [B1·R-MAN-02] 两条声明分别位于 AndroidManifest.xml 第 5、6 行，均为 uses-permission 标签，未附带 maxSdkVersion 等限定属性。
    - B1 复核的补充观察（不构成判定），未经机械核查
- [B1·R-PERM-01] postDelayed 的 Runnable 具体类型及其与 Worker.run 的调用关系未解析；MediaRecorder 出现在独立方法中，未见到权限声明或运行时权限检查片段。
    - B1 复核的补充观察（不构成判定），未经机械核查
- [B1·R-CODE-01] 构造参数含文件路径绝对路径与动态类名 com.synth.bad03.plugin.EntryPoint，随后 loadClass 结果被 move-result-object 保存，后续未见反射实例化/调用片段，可进一步追踪是否执行插件代码。
    - B1 复核的补充观察（不构成判定），未经机械核查
- [B1·R-CODE-02] 注入的 Java 对象为 MainActivity$JsBridge，且 WebViewClient 为 InsecureWebViewClient，可能进一步扩大攻击面。
    - B1 复核的补充观察（不构成判定），未经机械核查
- [B1·R-NET-01] 前三个命中位于同一个 X509TrustManager 匿名类 InsecureTls$1 中，第四个命中是同文件中 HostnameVerifier 的恒真实现，两者组合形成完整的 TLS 校验绕过；如果单独看 getAcceptedIssuers 返回空数组，本身并不敏感，需要结合空实现才能定性。
    - B1 复核的补充观察（不构成判定），未经机械核查
- [B1·R-NET-02] 调用前有 Log.w 输出但未做任何校验或分支，proceed 为无条件执行；方法体在 proceed 后直接 return-void。
    - B1 复核的补充观察（不构成判定），未经机械核查

---
*本报告由 apkaudit 生成（规则包 0.1.8）。复核方式：按定位坐标直达原文，比对 raw_snippet 与证据 JSONL；结论未经人工签署前不生效。*
