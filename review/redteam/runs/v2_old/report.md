# APK 静态审计报告 RUN-20261127-191646-63823c87

- 样本：`v4_isolated.apk`
- sha256：`63823c87e1e1e0bdbf4a4ff31c0706bcd7e86f149a49c1860884c9bd4c90a553`
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
- 证据：`EV-20261127-191646-63823c87-001`, `EV-20261127-191646-63823c87-002`
- 定位坐标：
    - `AndroidManifest.xml:5 [uses-permission]`
    - `AndroidManifest.xml:6 [uses-permission]`
- 说明：声明敏感权限：android.permission.RECORD_AUDIO（录音）
- 说明：声明敏感权限：android.permission.ACCESS_FINE_LOCATION（精确定位）

### 2. R-PERM-01 · 定时/后台结构 × 敏感权限

- 状态：已确认 ｜ 通道：fusion ｜ 人工签署：pending
- 证据：`EV-20261127-191646-63823c87-003`, `EV-20261127-191646-63823c87-004`, `EV-20261127-191646-63823c87-005`
- 定位坐标：
    - `smali/com/synth/bad03/MainActivity.smali:227（原始行 56）`
    - `smali/com/synth/bad03/RecordingService.smali:46（原始行 44）`
    - `smali/com/synth/bad03/MainActivity.smali:145（原始行 77）`
- 说明：定时/后台调度点：Landroid/os/Handler;->postDelayed
- 说明：跨方法链目标组件：Lcom/synth/bad03/RecordingService;（存在敏感 API：录音）
- 说明：跨方法链：Lcom/synth/bad03/MainActivity$1; → startRecordingService → Lcom/synth/bad03/RecordingService;

### 3. R-PERM-02 · 非交互组件使用敏感 API

- 状态：已确认 ｜ 通道：fusion ｜ 人工签署：pending
- 证据：`EV-20261127-191646-63823c87-006`, `EV-20261127-191646-63823c87-007`, `EV-20261127-191646-63823c87-008`, `EV-20261127-191646-63823c87-009`, `EV-20261127-191646-63823c87-010`, `EV-20261127-191646-63823c87-011`, `EV-20261127-191646-63823c87-012`, `EV-20261127-191646-63823c87-013`, `EV-20261127-191646-63823c87-014`, `EV-20261127-191646-63823c87-015`, `EV-20261127-191646-63823c87-016`
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
- 证据：`EV-20261127-191646-63823c87-017`, `EV-20261127-191646-63823c87-018`, `EV-20261127-191646-63823c87-019`
- 定位坐标：
    - `smali/com/synth/bad03/MainActivity.smali:82（原始行 69）`
    - `smali/com/synth/bad03/MainActivity.smali:101（原始行 73）`
    - `smali/com/synth/bad03/MainActivity.smali:106（原始行 74）`
- 说明：动态代码加载调用：Ldalvik/system/DexClassLoader;
- 说明：动态代码加载调用：Ldalvik/system/DexClassLoader;
- 说明：动态代码加载调用：Ldalvik/system/DexClassLoader;

### 5. R-CODE-02 · WebView 危险组合

- 状态：已确认 ｜ 通道：fusion ｜ 人工签署：pending
- 证据：`EV-20261127-191646-63823c87-020`, `EV-20261127-191646-63823c87-021`, `EV-20261127-191646-63823c87-022`
- 定位坐标：
    - `smali/com/synth/bad03/MainActivity.smali:197（原始行 46）`
    - `smali/com/synth/bad03/MainActivity.smali:183（原始行 44）`
    - `smali/com/synth/bad03/MainActivity.smali:186（原始行 45）`
- 说明：WebView 危险组合要素：addJavascriptInterface
- 说明：WebView 危险组合要素：setJavaScriptEnabled
- 说明：WebView 危险组合要素：setAllowFileAccess

### 6. R-NET-01 · 证书校验绕过结构

- 状态：已确认 ｜ 通道：fusion ｜ 人工签署：pending
- 证据：`EV-20261127-191646-63823c87-023`, `EV-20261127-191646-63823c87-024`, `EV-20261127-191646-63823c87-025`, `EV-20261127-191646-63823c87-026`
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
- 证据：`EV-20261127-191646-63823c87-027`
- 定位坐标：
    - `smali/com/synth/bad03/InsecureWebViewClient.smali:45（原始行 20）`
- 说明：onReceivedSslError 忽略 SSL 错误（proceed）

## 待复核（1 条）

### 1. R-B-001 · 应用同时申请 RECORD_AUDIO、INTERNET、ACCESS_FINE_LOCATION，存在录音/定位数据经网络外传的隐私风险，需核查实际调用链与数据传输行为。

- 状态：待复核 ｜ 通道：B ｜ 人工签署：pending
- 证据：`EV-20261127-191646-63823c87-036`
- 定位坐标：
    - `AndroidManifest 权限声明：android.permission.INTERNET, android.permission.RECORD_AUDIO, android.permission.ACCESS_FINE_LOCATION`
- 说明：B 侧疑点（LLM 提疑），未经确定性钉证据，不得升级措辞
- 说明：结构事实：ANDROID.PERMISSION.ACCESS_FINE_LOCATION、ANDROID.PERMISSION.RECORD_AUDIO
- 缺口：结构已核对、意图未证实：结构事实已核对：claim 提及的实体（ANDROID.PERMISSION.ACCESS_FINE_LOCATION、ANDROID.PERMISSION.RECORD_AUDIO）均在样本声明中；组合/意图类断言无对应规则，未证实

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

- [B2] 存在 RecordingService 录音相关服务，虽 exported=False 降低外部直接调用风险，但仍需核查其启动方式、录音触发条件及录音数据存储/上传路径。（位置：com.synth.bad03.RecordingService (service; exported=False)）
    - LLM 观察（低置信），未经机械核查，不作为结论
- [B2] 自有代码中仅出现 HTTPS URL https://example.com/app，表面风险较低，但需核查该地址是否用于上报录音、位置或其他敏感数据，以及是否存在运行时拼接/隐藏端点。（位置：自有代码 URL：https://example.com/app）
    - LLM 观察（低置信），未经机械核查，不作为结论
- [B1·R-MAN-02] 两处权限分别位于 AndroidManifest.xml 第 5、6 行，均为系统危险权限；是否实际使用需结合代码进一步确认。
    - B1 复核的补充观察（不构成判定），未经机械核查
- [B1·R-PERM-01] 延迟常量为 0x2710（10000ms）；startRecordingService 片段仅见 Intent 构造，未展示 startService 或 Runnable.run 的实现内容。
    - B1 复核的补充观察（不构成判定），未经机械核查
- [B1·R-PERM-02] 命中片段还包含 MediaRecorder 构造调用与字段赋值，均发生在 RecordingService.smali 内；不属于仅声明无调用或 Activity 场景。
    - B1 复核的补充观察（不构成判定），未经机械核查
- [B1·R-CODE-01] 加载的类名位于插件包 com.synth.bad03.plugin，dex 路径由 File.getAbsolutePath() 派生，样本目录名 bad03 提示为合成测试样本；未见校验 dex 来源完整性或签名的逻辑。
    - B1 复核的补充观察（不构成判定），未经机械核查
- [B1·R-CODE-02] 命中上下文还显示后续创建 InsecureWebViewClient，可进一步关注其 URL 加载与证书处理逻辑。
    - B1 复核的补充观察（不构成判定），未经机械核查
- [B1·R-NET-01] 四个命中片段位于同一 InsecureTls 相关类中，共同构成信任所有证书并跳过主机名校验的实现。
    - B1 复核的补充观察（不构成判定），未经机械核查
- [B1·R-NET-02] 片段未展示方法签名（无法直接确认位于 onReceivedSslError 内），也未出现对 SslError 的主机名/证书校验或条件分支，proceed 为无条件执行后即 return-void。
    - B1 复核的补充观察（不构成判定），未经机械核查

---
*本报告由 apkaudit 生成（规则包 0.1.8）。复核方式：按定位坐标直达原文，比对 raw_snippet 与证据 JSONL；结论未经人工签署前不生效。*
