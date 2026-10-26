# APK 静态审计报告 RUN-20261015-145536

- 样本：`bad03.apk`
- sha256：`21cf5a06cc615b6e8ce71b66dbcda9386a136f63d861fcc258a195b98c4728aa`
- 规则包版本：`0.1.3`　｜　通道 B 模型：`mimo-v2.6-flash`
- 工具链：java=openjdk version "1.8.0_492", apktool=apktool_3.0.3.jar

> 证据层级说明：本项目只读、不执行被测 APK，全部证据层级上限为 STATIC。

## 覆盖声明

- 已检查（15 条）：R-MAN-01(manifest)；R-MAN-02(manifest)；R-MAN-03(manifest+res_decoded)；R-MAN-04(manifest)；R-MAN-05(manifest)；R-PERM-01(smali_src)；R-PERM-02(manifest/smali_src)；R-PERM-03(manifest/smali_src)；R-STR-01(dex_strings)；R-STR-02(dex_strings)；R-CODE-01(dex_strings/smali_src)；R-CODE-02(smali_src)；R-NET-01(smali_src)；R-NET-02(smali_src)；通道B(模型:mimo-v2.6-flash)
- 未覆盖（0 条）：—
- 解码状态：正常（复用缓存）

## 已确认（7 条）

### 1. R-MAN-02 · 危险权限声明

- 状态：已确认 ｜ 通道：fusion ｜ 人工签署：pending
- 证据：`EV-20261015-145536-001`, `EV-20261015-145536-002`
- 定位坐标：
    - `AndroidManifest.xml:5 [uses-permission]`
    - `AndroidManifest.xml:6 [uses-permission]`
- 说明：声明敏感权限：android.permission.RECORD_AUDIO（录音）
- 说明：声明敏感权限：android.permission.ACCESS_FINE_LOCATION（精确定位）

### 2. R-PERM-01 · 定时/后台结构 × 敏感权限

- 状态：已确认 ｜ 通道：fusion ｜ 人工签署：pending
- 证据：`EV-20261015-145536-003`, `EV-20261015-145536-004`, `EV-20261015-145536-005`
- 定位坐标：
    - `smali/com/synth/bad03/MainActivity.smali:188（原始行 87）`
    - `smali/com/synth/bad03/MainActivity.smali:161（原始行 83）`
    - `smali/com/synth/bad03/RecordingService.smali:46（原始行 44）`
- 说明：定时/后台调度点：Landroid/app/AlarmManager;->set
- 说明：调度目标组件：Lcom/synth/bad03/RecordingService;（该组件内存在敏感 API：录音）
- 说明：敏感 API：录音（位于被调度的组件 Lcom/synth/bad03/RecordingService; 内）

### 3. R-PERM-02 · 非交互组件使用敏感 API

- 状态：已确认 ｜ 通道：fusion ｜ 人工签署：pending
- 证据：`EV-20261015-145536-006`, `EV-20261015-145536-007`, `EV-20261015-145536-008`, `EV-20261015-145536-009`, `EV-20261015-145536-010`, `EV-20261015-145536-011`, `EV-20261015-145536-012`, `EV-20261015-145536-013`, `EV-20261015-145536-014`, `EV-20261015-145536-015`, `EV-20261015-145536-016`
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
- 证据：`EV-20261015-145536-017`, `EV-20261015-145536-018`, `EV-20261015-145536-019`
- 定位坐标：
    - `smali/com/synth/bad03/MainActivity.smali:82（原始行 69）`
    - `smali/com/synth/bad03/MainActivity.smali:101（原始行 73）`
    - `smali/com/synth/bad03/MainActivity.smali:106（原始行 74）`
- 说明：动态代码加载调用：Ldalvik/system/DexClassLoader;
- 说明：动态代码加载调用：Ldalvik/system/DexClassLoader;
- 说明：动态代码加载调用：Ldalvik/system/DexClassLoader;

### 5. R-CODE-02 · WebView 危险组合

- 状态：已确认 ｜ 通道：fusion ｜ 人工签署：pending
- 证据：`EV-20261015-145536-020`, `EV-20261015-145536-021`, `EV-20261015-145536-022`
- 定位坐标：
    - `smali/com/synth/bad03/MainActivity.smali:246（原始行 46）`
    - `smali/com/synth/bad03/MainActivity.smali:232（原始行 44）`
    - `smali/com/synth/bad03/MainActivity.smali:235（原始行 45）`
- 说明：WebView 危险组合要素：addJavascriptInterface
- 说明：WebView 危险组合要素：setJavaScriptEnabled
- 说明：WebView 危险组合要素：setAllowFileAccess

### 6. R-NET-01 · 证书校验绕过结构

- 状态：已确认 ｜ 通道：fusion ｜ 人工签署：pending
- 证据：`EV-20261015-145536-023`, `EV-20261015-145536-024`, `EV-20261015-145536-025`, `EV-20261015-145536-026`
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
- 证据：`EV-20261015-145536-027`
- 定位坐标：
    - `smali/com/synth/bad03/InsecureWebViewClient.smali:45（原始行 20）`
- 说明：onReceivedSslError 忽略 SSL 错误（proceed）

## 待复核（0 条）

（无）

## 无法判定（0 条）

（无）

## B 通道观察（非结论 · 保留模型原声）

> 以下为 LLM 复核/扫描的补充观察，**未经机械核查、不作为结论、不计入三档统计**；仅用于人工参考。

- [B2] 自有代码仅出现一个硬编码 URL（https://example.com/app），且域名与包名合成性质不匹配，可能是占位/配置端点，需核实是否存在其它拼接、加密或从 assets/SP 中读取的 C2 地址（位置：网络 URL 列表（唯一项 https://example.com/app））
    - LLM 观察（低置信），未经机械核查，不作为结论
- [B2] 无 exported=true 组件且未声明自定义权限，外部直接调用面较小，但需人工确认是否通过隐式 Intent、PendingIntent 或 ContentProvider URI 权限授予对外暴露能力（位置：com.synth.bad03.MainActivity / RecordingService 导出状态）
    - LLM 观察（低置信），未经机械核查，不作为结论
- [B1·R-MAN-02] 两个权限分别对应麦克风录音与精确地理位置，通常意味着应用具备监听/定位用户的能力；若应用功能与之无关，则风险进一步升高。
    - B1 复核的补充观察（不构成判定），未经机械核查
- [B1·R-PERM-01] 方法内 164-187 行的 PendingIntent 构造细节未在片段中给出，但调度调用与目标组件 Intent 同处一个方法（161→188），链路归属明确；周期参数常量值未展示，故不对实际触发间隔或执行时间作任何推断，仅认定为结构层面的定时+录音组合。
    - B1 复核的补充观察（不构成判定），未经机械核查
- [B1·R-PERM-02] 命中点位于 onCreate/onStartCommand 类初始化路径，字段 recorder 被赋值并反复 iget 使用，调用链完整。
    - B1 复核的补充观察（不构成判定），未经机械核查
- [B1·R-CODE-01] loadClass 的目标类名 "com.synth.bad03.plugin.EntryPoint" 为硬编码常量，且 DexClassLoader 位于应用自身包路径下，建议结合 dex 路径来源进一步复核。
    - B1 复核的补充观察（不构成判定），未经机械核查
- [B1·R-CODE-02] 命中片段中 v1 为 0x1，即两个布尔开关均设为 true；JsBridge 与 InsecureWebViewClient 随后实例化，进一步支持该组合为有意配置
    - B1 复核的补充观察（不构成判定），未经机械核查
- [B1·R-NET-01] 类名 com/synth/bad03/InsecureTls 也印证这是故意构造的不安全 TLS 实现，三个方法共同构成完整的证书/主机名校验绕过
    - B1 复核的补充观察（不构成判定），未经机械核查
- [B1·R-NET-02] 所在方法上下文中仅有一处 Log.w 记录，无任何 cancel 分支，proceed 为无条件执行。
    - B1 复核的补充观察（不构成判定），未经机械核查

---
*本报告由 apkaudit 生成（规则包 0.1.3）。复核方式：按定位坐标直达原文，比对 raw_snippet 与证据 JSONL；结论未经人工签署前不生效。*
