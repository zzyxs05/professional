# APK 静态审计报告 RUN-20261127-191550-3464015c

- 样本：`v2_crossmethod.apk`
- sha256：`3464015c37b913c544ffc4c210c8f39d22be5d97666e03b1d851e8add7290e93`
- 规则包版本：`0.1.8`　｜　通道 B 模型：`deepseek-flash`
- 工具链：java=openjdk version "11.0.0.2" 2024-07-02, apktool=apktool_3.0.3.jar

> 证据层级说明：本项目只读、不执行被测 APK，全部证据层级上限为 STATIC。

## 覆盖声明

- 已检查（15 条）：R-MAN-01(manifest)；R-MAN-02(manifest)；R-MAN-03(manifest+res_decoded)；R-MAN-04(manifest)；R-MAN-05(manifest)；R-PERM-01(smali_src)；R-PERM-02(manifest/smali_src)；R-PERM-03(manifest/smali_src)；R-STR-01(dex_strings)；R-STR-02(dex_strings)；R-CODE-01(dex_strings/smali_src)；R-CODE-02(smali_src)；R-NET-01(smali_src)；R-NET-02(smali_src)；通道B(模型:deepseek-flash)
- 未覆盖（0 条）：—
- 解码状态：正常（复用缓存）

## 已确认（7 条）

### 1. R-MAN-02 · 危险权限声明

- 状态：已确认 ｜ 通道：fusion ｜ 人工签署：pending
- 证据：`EV-20261127-191550-3464015c-001`, `EV-20261127-191550-3464015c-002`
- 定位坐标：
    - `AndroidManifest.xml:5 [uses-permission]`
    - `AndroidManifest.xml:6 [uses-permission]`
- 说明：声明敏感权限：android.permission.RECORD_AUDIO（录音）
- 说明：声明敏感权限：android.permission.ACCESS_FINE_LOCATION（精确定位）

### 2. R-PERM-01 · 定时/后台结构 × 敏感权限

- 状态：已确认 ｜ 通道：fusion ｜ 人工签署：pending
- 证据：`EV-20261127-191550-3464015c-003`, `EV-20261127-191550-3464015c-004`, `EV-20261127-191550-3464015c-005`
- 定位坐标：
    - `smali/com/synth/bad03/MainActivity.smali:227（原始行 56）`
    - `smali/com/synth/bad03/RecordingService.smali:46（原始行 44）`
    - `smali/com/synth/bad03/MainActivity.smali:145（原始行 77）`
- 说明：定时/后台调度点：Landroid/os/Handler;->postDelayed
- 说明：跨方法链目标组件：Lcom/synth/bad03/RecordingService;（存在敏感 API：录音）
- 说明：跨方法链：Lcom/synth/bad03/MainActivity$1; → startRecordingService → Lcom/synth/bad03/RecordingService;

### 3. R-PERM-02 · 非交互组件使用敏感 API

- 状态：已确认 ｜ 通道：fusion ｜ 人工签署：pending
- 证据：`EV-20261127-191550-3464015c-006`, `EV-20261127-191550-3464015c-007`, `EV-20261127-191550-3464015c-008`, `EV-20261127-191550-3464015c-009`, `EV-20261127-191550-3464015c-010`, `EV-20261127-191550-3464015c-011`, `EV-20261127-191550-3464015c-012`, `EV-20261127-191550-3464015c-013`, `EV-20261127-191550-3464015c-014`, `EV-20261127-191550-3464015c-015`, `EV-20261127-191550-3464015c-016`
- 定位坐标：
    - `smali/com/synth/bad03/RecordingService.smali:46（原始行 44）`
    - `smali/com/synth/bad03/RecordingService.smali:48（原始行 44）`
    - `smali/com/synth/bad03/RecordingService.smali:55（原始行 45）`
    - `smali/com/synth/bad03/RecordingService.smali:60（原始行 46）`
    - `smali/com/synth/bad03/RecordingService.smali:65（原始行 47）`
    - `smali/com/synth/bad03/RecordingService.smali:74（原始行 48）`
    - `smali/com/synth/bad03/RecordingService.smali:79（原始行 49）`
    - `smali/com/synth/bad03/RecordingService.smali:84（原始行 50）`
    - `smali/com/synth/bad03/RecordingService.smali:137（原始行 78）`
    - `smali/com/synth/bad03/RecordingService.smali:181（原始行 93）`
    - `smali/com/synth/bad03/RecordingService.smali:201（原始行 97）`
- 说明：非交互组件 com.synth.bad03.RecordingService（service）中调用敏感 API：录音
- 说明：非交互组件 com.synth.bad03.RecordingService（service）中调用敏感 API：录音
- 说明：非交互组件 com.synth.bad03.RecordingService（service）中调用敏感 API：录音
- 说明：非交互组件 com.synth.bad03.RecordingService（service）中调用敏感 API：录音
- 说明：非交互组件 com.synth.bad03.RecordingService（service）中调用敏感 API：录音
- 说明：非交互组件 com.synth.bad03.RecordingService（service）中调用敏感 API：录音
- 说明：非交互组件 com.synth.bad03.RecordingService（service）中调用敏感 API：录音
- 说明：非交互组件 com.synth.bad03.RecordingService（service）中调用敏感 API：录音
- 说明：非交互组件 com.synth.bad03.RecordingService（service）中调用敏感 API：定位
- 说明：非交互组件 com.synth.bad03.RecordingService（service）中调用敏感 API：录音
- 说明：非交互组件 com.synth.bad03.RecordingService（service）中调用敏感 API：录音

### 4. R-CODE-01 · 动态代码加载

- 状态：已确认 ｜ 通道：fusion ｜ 人工签署：pending
- 证据：`EV-20261127-191550-3464015c-017`, `EV-20261127-191550-3464015c-018`, `EV-20261127-191550-3464015c-019`
- 定位坐标：
    - `smali/com/synth/bad03/MainActivity.smali:82（原始行 69）`
    - `smali/com/synth/bad03/MainActivity.smali:101（原始行 73）`
    - `smali/com/synth/bad03/MainActivity.smali:106（原始行 74）`
- 说明：动态代码加载调用：Ldalvik/system/DexClassLoader;
- 说明：动态代码加载调用：Ldalvik/system/DexClassLoader;
- 说明：动态代码加载调用：Ldalvik/system/DexClassLoader;

### 5. R-CODE-02 · WebView 危险组合

- 状态：已确认 ｜ 通道：fusion ｜ 人工签署：pending
- 证据：`EV-20261127-191550-3464015c-020`, `EV-20261127-191550-3464015c-021`, `EV-20261127-191550-3464015c-022`
- 定位坐标：
    - `smali/com/synth/bad03/MainActivity.smali:197（原始行 46）`
    - `smali/com/synth/bad03/MainActivity.smali:183（原始行 44）`
    - `smali/com/synth/bad03/MainActivity.smali:186（原始行 45）`
- 说明：WebView 危险组合要素：addJavascriptInterface
- 说明：WebView 危险组合要素：setJavaScriptEnabled
- 说明：WebView 危险组合要素：setAllowFileAccess

### 6. R-NET-01 · 证书校验绕过结构

- 状态：已确认 ｜ 通道：fusion ｜ 人工签署：pending
- 证据：`EV-20261127-191550-3464015c-023`, `EV-20261127-191550-3464015c-024`, `EV-20261127-191550-3464015c-025`, `EV-20261127-191550-3464015c-026`
- 定位坐标：
    - `smali/com/synth/bad03/InsecureTls$1.smali:35（原始行 32）`
    - `smali/com/synth/bad03/InsecureTls$1.smali:41（原始行 32）`
    - `smali/com/synth/bad03/InsecureTls$1.smali:47（原始行 32）`
    - `smali/com/synth/bad03/InsecureTls$2.smali:35（原始行 53）`
- 说明：X509TrustManager.checkClientTrusted 空实现（证书校验被跳过）；检测到安装点 smali/com/synth/bad03/InsecureTls.smali:53（原始行 51）
- 说明：X509TrustManager.checkServerTrusted 空实现（证书校验被跳过）
- 说明：X509TrustManager.getAcceptedIssuers 返回空数组
- 说明：HostnameVerifier.verify 返回恒真（域名校验被跳过）

### 7. R-NET-02 · WebView SSL 错误忽略

- 状态：已确认 ｜ 通道：fusion ｜ 人工签署：pending
- 证据：`EV-20261127-191550-3464015c-027`
- 定位坐标：
    - `smali/com/synth/bad03/InsecureWebViewClient.smali:45（原始行 20）`
- 说明：onReceivedSslError 忽略 SSL 错误（proceed）

## 待复核（0 条）

（无）

## 无法判定（7 条）

> 其中：规则已执行、机械未命中 7 条（不构成安全结论）｜规则未执行 0 条（覆盖缺口）

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

### 5. R-PERM-03 · 声明与使用不一致

- 状态：无法判定 ｜ 通道：A ｜ 人工签署：pending
- 定位坐标：
- 说明：机械规则已执行、未命中。仅代表本规则集范围内未发现问题，不构成「安全」结论。

### 6. R-STR-01 · 硬编码凭据

- 状态：无法判定 ｜ 通道：A ｜ 人工签署：pending
- 定位坐标：
- 说明：机械规则已执行、未命中。仅代表本规则集范围内未发现问题，不构成「安全」结论。

### 7. R-STR-02 · 内网/明文端点

- 状态：无法判定 ｜ 通道：A ｜ 人工签署：pending
- 定位坐标：
- 说明：机械规则已执行、未命中。仅代表本规则集范围内未发现问题，不构成「安全」结论。

## B 通道观察（非结论 · 保留模型原声）

> 以下为 LLM 复核/扫描的补充观察，**未经机械核查、不作为结论、不计入三档统计**；仅用于人工参考。

- [B1·R-MAN-02] 两条声明均来自 AndroidManifest.xml 第 5、6 行；是否与录音或定位等敏感功能的实际代码路径对应，需要结合实现部分另行核实。
    - B1 复核的补充观察（不构成判定），未经机械核查
- [B1·R-PERM-01] postDelayed 使用常量 0x2710；startRecordingService 仅见 Intent 创建，未展示该 Runnable 与 startRecordingService 或 RecordingService 的关联。
    - B1 复核的补充观察（不构成判定），未经机械核查
- [B1·R-PERM-02] 调用链使用常量 0x1 作为音频源与编码器参数，建议结合清单中该 Service 的 exported/权限配置进一步确认暴露面。
    - B1 复核的补充观察（不构成判定），未经机械核查
- [B1·R-CODE-01] 构造参数来自 File.getAbsolutePath() 与另一路径变量，且加载类名为硬编码的 "com.synth.bad03.plugin.EntryPoint"，路径来源与插件 dex 是否来自外部存储需进一步追踪确认。
    - B1 复核的补充观察（不构成判定），未经机械核查
- [B1·R-CODE-02] 注入的接口名为 "nativeBridge"，对应对象为 Lcom/synth/bad03/MainActivity$JsBridge；相邻还 new 出 InsecureWebViewClient，提示可能同时存在 WebViewClient 校验缺失，但该点不属于本条规则的判定依据。
    - B1 复核的补充观察（不构成判定），未经机械核查
- [B1·R-NET-01] 该组方法均位于 InsecureTls 相关内部类中，建议进一步确认其是否被实际用于 SSLContext 或 HttpsURLConnection。
    - B1 复核的补充观察（不构成判定），未经机械核查
- [B1·R-NET-02] 该调用位于 onReceivedSslError 相关方法中，proceed 后直接 return-void，未见任何取消或错误处理逻辑。
    - B1 复核的补充观察（不构成判定），未经机械核查

---
*本报告由 apkaudit 生成（规则包 0.1.8）。复核方式：按定位坐标直达原文，比对 raw_snippet 与证据 JSONL；结论未经人工签署前不生效。*
