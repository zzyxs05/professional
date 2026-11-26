# APK 静态审计报告 RUN-20261125-205955-21cf5a06

- 样本：`bad03.apk`
- sha256：`21cf5a06cc615b6e8ce71b66dbcda9386a136f63d861fcc258a195b98c4728aa`
- 规则包版本：`0.1.7`　｜　通道 B 模型：`mimo-v2.6-flash`
- 工具链：java=openjdk version "1.8.0_492", apktool=apktool_3.0.3.jar

> 证据层级说明：本项目只读、不执行被测 APK，全部证据层级上限为 STATIC。

## 覆盖声明

- 已检查（15 条）：R-MAN-01(manifest)；R-MAN-02(manifest)；R-MAN-03(manifest+res_decoded)；R-MAN-04(manifest)；R-MAN-05(manifest)；R-PERM-01(smali_src)；R-PERM-02(manifest/smali_src)；R-PERM-03(manifest/smali_src)；R-STR-01(dex_strings)；R-STR-02(dex_strings)；R-CODE-01(dex_strings/smali_src)；R-CODE-02(smali_src)；R-NET-01(smali_src)；R-NET-02(smali_src)；通道B(模型:mimo-v2.6-flash)
- 未覆盖（0 条）：—
- 解码状态：正常（复用缓存）

## 已确认（7 条）

### 1. R-MAN-02 · 危险权限声明

- 状态：已确认 ｜ 通道：fusion ｜ 人工签署：pending
- 证据：`EV-20261125-205955-21cf5a06-001`, `EV-20261125-205955-21cf5a06-002`
- 定位坐标：
    - `AndroidManifest.xml:5 [uses-permission]`
    - `AndroidManifest.xml:6 [uses-permission]`
- 说明：声明敏感权限：android.permission.RECORD_AUDIO（录音）
- 说明：声明敏感权限：android.permission.ACCESS_FINE_LOCATION（精确定位）

### 2. R-PERM-01 · 定时/后台结构 × 敏感权限

- 状态：已确认 ｜ 通道：fusion ｜ 人工签署：pending
- 证据：`EV-20261125-205955-21cf5a06-003`, `EV-20261125-205955-21cf5a06-004`, `EV-20261125-205955-21cf5a06-005`
- 定位坐标：
    - `smali/com/synth/bad03/MainActivity.smali:188（原始行 87）`
    - `smali/com/synth/bad03/MainActivity.smali:161（原始行 83）`
    - `smali/com/synth/bad03/RecordingService.smali:46（原始行 44）`
- 说明：定时/后台调度点：Landroid/app/AlarmManager;->set
- 说明：调度目标组件：Lcom/synth/bad03/RecordingService;（该组件内存在敏感 API：录音）
- 说明：敏感 API：录音（位于被调度的组件 Lcom/synth/bad03/RecordingService; 内）

### 3. R-PERM-02 · 非交互组件使用敏感 API

- 状态：已确认 ｜ 通道：fusion ｜ 人工签署：pending
- 证据：`EV-20261125-205955-21cf5a06-006`, `EV-20261125-205955-21cf5a06-007`, `EV-20261125-205955-21cf5a06-008`, `EV-20261125-205955-21cf5a06-009`, `EV-20261125-205955-21cf5a06-010`, `EV-20261125-205955-21cf5a06-011`, `EV-20261125-205955-21cf5a06-012`, `EV-20261125-205955-21cf5a06-013`, `EV-20261125-205955-21cf5a06-014`, `EV-20261125-205955-21cf5a06-015`, `EV-20261125-205955-21cf5a06-016`
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
- 证据：`EV-20261125-205955-21cf5a06-017`, `EV-20261125-205955-21cf5a06-018`, `EV-20261125-205955-21cf5a06-019`
- 定位坐标：
    - `smali/com/synth/bad03/MainActivity.smali:82（原始行 69）`
    - `smali/com/synth/bad03/MainActivity.smali:101（原始行 73）`
    - `smali/com/synth/bad03/MainActivity.smali:106（原始行 74）`
- 说明：动态代码加载调用：Ldalvik/system/DexClassLoader;
- 说明：动态代码加载调用：Ldalvik/system/DexClassLoader;
- 说明：动态代码加载调用：Ldalvik/system/DexClassLoader;

### 5. R-CODE-02 · WebView 危险组合

- 状态：已确认 ｜ 通道：fusion ｜ 人工签署：pending
- 证据：`EV-20261125-205955-21cf5a06-020`, `EV-20261125-205955-21cf5a06-021`, `EV-20261125-205955-21cf5a06-022`
- 定位坐标：
    - `smali/com/synth/bad03/MainActivity.smali:246（原始行 46）`
    - `smali/com/synth/bad03/MainActivity.smali:232（原始行 44）`
    - `smali/com/synth/bad03/MainActivity.smali:235（原始行 45）`
- 说明：WebView 危险组合要素：addJavascriptInterface
- 说明：WebView 危险组合要素：setJavaScriptEnabled
- 说明：WebView 危险组合要素：setAllowFileAccess

### 6. R-NET-01 · 证书校验绕过结构

- 状态：已确认 ｜ 通道：fusion ｜ 人工签署：pending
- 证据：`EV-20261125-205955-21cf5a06-023`, `EV-20261125-205955-21cf5a06-024`, `EV-20261125-205955-21cf5a06-025`, `EV-20261125-205955-21cf5a06-026`
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
- 证据：`EV-20261125-205955-21cf5a06-027`
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

- [B2] 自有代码中唯一网络入口为 https://example.com/app，为占位示例域名，需确认实际通信域名是否通过动态加载点或运行时配置下发以规避静态检测（位置：URL 列表 https://example.com/app）
    - LLM 观察（低置信），未经机械核查，不作为结论
- [B2] 两个组件均设置 exported=False，导出面较小，但需确认是否通过隐式 Intent、PendingIntent 或 deeplink 间接暴露入口（位置：com.synth.bad03.MainActivity, com.synth.bad03.RecordingService）
    - LLM 观察（低置信），未经机械核查，不作为结论
- [B1·R-MAN-02] 两条声明位于 AndroidManifest.xml 第 5、6 行，为标准 uses-permission 格式，未附带权限组或自定义前缀。
    - B1 复核的补充观察（不构成判定），未经机械核查
- [B1·R-PERM-01] 三条命中分属同一包内两个类，MainActivity 中构造指向 RecordingService 的 Intent 与 setRepeating 调用位置相邻，链路在样本内可关联；本判定仅确认结构存在，不涉及真实执行时间或实际滥用。
    - B1 复核的补充观察（不构成判定），未经机械核查
- [B1·R-PERM-02] 命中片段跨 5 处，均围绕同一 MediaRecorder 实例的创建与配置流程，属于对敏感 API 的真实调用链。
    - B1 复核的补充观察（不构成判定），未经机械核查
- [B1·R-CODE-01] 三处命中位于同一方法内且寄存器 v4 贯穿实例化、构造与 loadClass 调用，证据链完整；加载的目标类为 "com.synth.bad03.plugin.EntryPoint"，构成典型插件式动态加载
    - B1 复核的补充观察（不构成判定），未经机械核查
- [B1·R-CODE-02] 三处命中同属 MainActivity 同一方法内，v1 寄存器在 229 行被置为 1 后连续用于开启 JS 与文件访问；随后还创建了 JsBridge 对象与 InsecureWebViewClient，进一步印证接口注入路径
    - B1 复核的补充观察（不构成判定），未经机械核查
- [B1·R-NET-01] InsecureTls$1 为自定义 X509TrustManager，InsecureTls$2 为自定义 HostnameVerifier；getAcceptedIssuers 返回空数组本身常见于宽松 TrustManager，与空校验方法一致
    - B1 复核的补充观察（不构成判定），未经机械核查
- [B1·R-NET-02] 命中位于方法末尾（45 行 proceed 后 47 行即 return-void），上下文未展示方法签名与前面的 SSL 错误判断逻辑，但 proceed 的存在本身已满足该规则的检测结构。
    - B1 复核的补充观察（不构成判定），未经机械核查

---
*本报告由 apkaudit 生成（规则包 0.1.7）。复核方式：按定位坐标直达原文，比对 raw_snippet 与证据 JSONL；结论未经人工签署前不生效。*
