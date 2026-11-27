# APK 静态审计报告 RUN-20261126-205405-21cf5a06

- 样本：`bad03.apk`
- sha256：`21cf5a06cc615b6e8ce71b66dbcda9386a136f63d861fcc258a195b98c4728aa`
- 规则包版本：`0.1.8`　｜　通道 B 模型：`mimo-v2.6-flash`
- 工具链：java=openjdk version "1.8.0_492", apktool=apktool_3.0.3.jar

> 证据层级说明：本项目只读、不执行被测 APK，全部证据层级上限为 STATIC。

## 覆盖声明

- 已检查（15 条）：R-MAN-01(manifest)；R-MAN-02(manifest)；R-MAN-03(manifest+res_decoded)；R-MAN-04(manifest)；R-MAN-05(manifest)；R-PERM-01(smali_src)；R-PERM-02(manifest/smali_src)；R-PERM-03(manifest/smali_src)；R-STR-01(dex_strings)；R-STR-02(dex_strings)；R-CODE-01(dex_strings/smali_src)；R-CODE-02(smali_src)；R-NET-01(smali_src)；R-NET-02(smali_src)；通道B(模型:mimo-v2.6-flash)
- 未覆盖（0 条）：—
- 解码状态：正常（复用缓存）

## 已确认（7 条）

### 1. R-MAN-02 · 危险权限声明

- 状态：已确认 ｜ 通道：fusion ｜ 人工签署：pending
- 证据：`EV-20261126-205405-21cf5a06-001`, `EV-20261126-205405-21cf5a06-002`
- 定位坐标：
    - `AndroidManifest.xml:5 [uses-permission]`
    - `AndroidManifest.xml:6 [uses-permission]`
- 说明：声明敏感权限：android.permission.RECORD_AUDIO（录音）
- 说明：声明敏感权限：android.permission.ACCESS_FINE_LOCATION（精确定位）

### 2. R-PERM-01 · 定时/后台结构 × 敏感权限

- 状态：已确认 ｜ 通道：fusion ｜ 人工签署：pending
- 证据：`EV-20261126-205405-21cf5a06-003`, `EV-20261126-205405-21cf5a06-004`, `EV-20261126-205405-21cf5a06-005`, `EV-20261126-205405-21cf5a06-006`, `EV-20261126-205405-21cf5a06-007`, `EV-20261126-205405-21cf5a06-008`
- 定位坐标：
    - `smali/com/synth/bad03/MainActivity.smali:188（原始行 87）`
    - `smali/com/synth/bad03/MainActivity.smali:161（原始行 83）`
    - `smali/com/synth/bad03/RecordingService.smali:46（原始行 44）`
    - `smali/com/synth/bad03/MainActivity.smali:278（原始行 56）`
    - `smali/com/synth/bad03/RecordingService.smali:46（原始行 44）`
    - `smali/com/synth/bad03/MainActivity.smali:194（原始行 87）`
- 说明：定时/后台调度点：Landroid/app/AlarmManager;->set
- 说明：调度目标组件：Lcom/synth/bad03/RecordingService;（该组件内存在敏感 API：录音）
- 说明：敏感 API：录音（位于被调度的组件 Lcom/synth/bad03/RecordingService; 内）
- 说明：定时/后台调度点：Landroid/os/Handler;->postDelayed
- 说明：跨方法链目标组件：Lcom/synth/bad03/RecordingService;（存在敏感 API：录音）
- 说明：跨方法链：Lcom/synth/bad03/MainActivity$1; → startRecordingService → Lcom/synth/bad03/RecordingService;

### 3. R-PERM-02 · 非交互组件使用敏感 API

- 状态：已确认 ｜ 通道：fusion ｜ 人工签署：pending
- 证据：`EV-20261126-205405-21cf5a06-009`, `EV-20261126-205405-21cf5a06-010`, `EV-20261126-205405-21cf5a06-011`, `EV-20261126-205405-21cf5a06-012`, `EV-20261126-205405-21cf5a06-013`, `EV-20261126-205405-21cf5a06-014`, `EV-20261126-205405-21cf5a06-015`, `EV-20261126-205405-21cf5a06-016`, `EV-20261126-205405-21cf5a06-017`, `EV-20261126-205405-21cf5a06-018`, `EV-20261126-205405-21cf5a06-019`
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
- 证据：`EV-20261126-205405-21cf5a06-020`, `EV-20261126-205405-21cf5a06-021`, `EV-20261126-205405-21cf5a06-022`
- 定位坐标：
    - `smali/com/synth/bad03/MainActivity.smali:82（原始行 69）`
    - `smali/com/synth/bad03/MainActivity.smali:101（原始行 73）`
    - `smali/com/synth/bad03/MainActivity.smali:106（原始行 74）`
- 说明：动态代码加载调用：Ldalvik/system/DexClassLoader;
- 说明：动态代码加载调用：Ldalvik/system/DexClassLoader;
- 说明：动态代码加载调用：Ldalvik/system/DexClassLoader;

### 5. R-CODE-02 · WebView 危险组合

- 状态：已确认 ｜ 通道：fusion ｜ 人工签署：pending
- 证据：`EV-20261126-205405-21cf5a06-023`, `EV-20261126-205405-21cf5a06-024`, `EV-20261126-205405-21cf5a06-025`
- 定位坐标：
    - `smali/com/synth/bad03/MainActivity.smali:246（原始行 46）`
    - `smali/com/synth/bad03/MainActivity.smali:232（原始行 44）`
    - `smali/com/synth/bad03/MainActivity.smali:235（原始行 45）`
- 说明：WebView 危险组合要素：addJavascriptInterface
- 说明：WebView 危险组合要素：setJavaScriptEnabled
- 说明：WebView 危险组合要素：setAllowFileAccess

### 6. R-NET-01 · 证书校验绕过结构

- 状态：已确认 ｜ 通道：fusion ｜ 人工签署：pending
- 证据：`EV-20261126-205405-21cf5a06-026`, `EV-20261126-205405-21cf5a06-027`, `EV-20261126-205405-21cf5a06-028`, `EV-20261126-205405-21cf5a06-029`
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
- 证据：`EV-20261126-205405-21cf5a06-030`
- 定位坐标：
    - `smali/com/synth/bad03/InsecureWebViewClient.smali:45（原始行 20）`
- 说明：onReceivedSslError 忽略 SSL 错误（proceed）

## 待复核（1 条）

### 1. R-B-001 · 自有代码中出现 https://example.com/app 网络入口，需核查其用途及是否与录音/定位数据外传相关

- 状态：待复核 ｜ 通道：B ｜ 人工签署：pending
- 证据：`EV-20261126-205405-21cf5a06-044`
- 定位坐标：
    - `代码内 URL 字符串`
- 说明：B 侧疑点（LLM 提疑），未经确定性钉证据，不得升级措辞
- 缺口：钉证据未通过：未识别到可核查断言（claim 无法映射到任何规则）

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

- [B2] 组件均为 exported=False，导出面较小，需确认动态加载点是否用于加载外部/解密载荷以规避静态检测（位置：com.synth.bad03.MainActivity / RecordingService）
    - LLM 观察（低置信），未经机械核查，不作为结论
- [B1·R-MAN-02] 两条命中均为 Android 系统标准危险权限，且位于 AndroidManifest.xml 的 uses-permission 声明位置，符合规则检测的危险权限声明结构。
    - B1 复核的补充观察（不构成判定），未经机械核查
- [B1·R-PERM-01] 片段中未直接展示 PendingIntent 的创建调用（Intent→PendingIntent→setRepeating 的中间一环为相邻行推断）；RecordingService 的 MediaRecorder 命中在输入中重复列出一次；按规则口径，此结论仅为结构事实，不涉及真实执行时间或实际滥用的表述。
    - B1 复核的补充观察（不构成判定），未经机械核查
- [B1·R-PERM-02] MediaRecorder 用于音频录制，属敏感 API；调用发生在 Service 的非交互上下文中
    - B1 复核的补充观察（不构成判定），未经机械核查
- [B1·R-CODE-01] loadClass 的目标类名由 const-string 提供且随后 move-result-object，构成典型的动态加载并反射调用插件入口点的模式
    - B1 复核的补充观察（不构成判定），未经机械核查
- [B1·R-CODE-02] 命中片段位于同一 onCreate/初始化流程中（行 232-246），紧邻创建 JsBridge 与 InsecureWebViewClient，属典型危险组合
    - B1 复核的补充观察（不构成判定），未经机械核查
- [B1·R-NET-01] getAcceptedIssuers 返回空数组，与上述空 TrustManager 一致，进一步表明该校验器不进行任何实际校验
    - B1 复核的补充观察（不构成判定），未经机械核查
- [B1·R-NET-02] 该方法在 proceed() 后直接 return-void，且此前仅有 Log.w 调用，没有对错误进行任何拒绝处理。
    - B1 复核的补充观察（不构成判定），未经机械核查

---
*本报告由 apkaudit 生成（规则包 0.1.8）。复核方式：按定位坐标直达原文，比对 raw_snippet 与证据 JSONL；结论未经人工签署前不生效。*
