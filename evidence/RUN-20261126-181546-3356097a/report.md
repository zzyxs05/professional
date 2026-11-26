# APK 静态审计报告 RUN-20261126-181546-3356097a

- 样本：`bad01.apk`
- sha256：`3356097a33fb044d848ee1930523924b2d08ba7bbfdf47f43c7dbad10aae1414`
- 规则包版本：`0.1.7`　｜　通道 B 模型：`mimo-v2.6-flash`
- 工具链：java=openjdk version "1.8.0_492", apktool=apktool_3.0.3.jar

> 证据层级说明：本项目只读、不执行被测 APK，全部证据层级上限为 STATIC。

## 覆盖声明

- 已检查（15 条）：R-MAN-01(manifest)；R-MAN-02(manifest)；R-MAN-03(manifest+res_decoded)；R-MAN-04(manifest)；R-MAN-05(manifest)；R-PERM-01(smali_src)；R-PERM-02(manifest/smali_src)；R-PERM-03(manifest/smali_src)；R-STR-01(dex_strings)；R-STR-02(dex_strings)；R-CODE-01(dex_strings/smali_src)；R-CODE-02(smali_src)；R-NET-01(smali_src)；R-NET-02(smali_src)；通道B(模型:mimo-v2.6-flash)
- 未覆盖（0 条）：—
- 解码状态：正常（复用缓存）

## 已确认（6 条）

### 1. R-MAN-01 · 导出组件无权限保护

- 状态：已确认 ｜ 通道：fusion ｜ 人工签署：pending
- 证据：`EV-20261126-181546-3356097a-001`, `EV-20261126-181546-3356097a-002`, `EV-20261126-181546-3356097a-003`, `EV-20261126-181546-3356097a-004`
- 定位坐标：
    - `AndroidManifest.xml:16-16 [activity com.synth.bad01.MainActivity]`
    - `AndroidManifest.xml:17-17 [service com.synth.bad01.SyncService]`
    - `AndroidManifest.xml:18-24 [receiver com.synth.bad01.BootReceiver]`
    - `AndroidManifest.xml:25-25 [provider com.synth.bad01.LeakyProvider]`
- 说明：导出组件 com.synth.bad01.MainActivity 无权限保护（android:exported="true"）
- 说明：导出组件 com.synth.bad01.SyncService 无权限保护（android:exported="true"）
- 说明：导出组件 com.synth.bad01.BootReceiver 无权限保护（android:exported="true"）
- 说明：导出组件 com.synth.bad01.LeakyProvider 无权限保护（android:exported="true"）

### 2. R-MAN-02 · 危险权限声明

- 状态：已确认 ｜ 通道：fusion ｜ 人工签署：pending
- 证据：`EV-20261126-181546-3356097a-005`, `EV-20261126-181546-3356097a-006`, `EV-20261126-181546-3356097a-007`, `EV-20261126-181546-3356097a-008`, `EV-20261126-181546-3356097a-009`, `EV-20261126-181546-3356097a-010`, `EV-20261126-181546-3356097a-011`, `EV-20261126-181546-3356097a-012`, `EV-20261126-181546-3356097a-013`, `EV-20261126-181546-3356097a-014`, `EV-20261126-181546-3356097a-015`
- 定位坐标：
    - `AndroidManifest.xml:4 [uses-permission]`
    - `AndroidManifest.xml:5 [uses-permission]`
    - `AndroidManifest.xml:6 [uses-permission]`
    - `AndroidManifest.xml:7 [uses-permission]`
    - `AndroidManifest.xml:8 [uses-permission]`
    - `AndroidManifest.xml:9 [uses-permission]`
    - `AndroidManifest.xml:10 [uses-permission]`
    - `AndroidManifest.xml:11 [uses-permission]`
    - `AndroidManifest.xml:12 [uses-permission]`
    - `AndroidManifest.xml:13 [uses-permission]`
    - `AndroidManifest.xml:14 [uses-permission]`
- 说明：声明敏感权限：android.permission.RECORD_AUDIO（录音）
- 说明：声明敏感权限：android.permission.CAMERA（相机）
- 说明：声明敏感权限：android.permission.ACCESS_FINE_LOCATION（精确定位）
- 说明：声明敏感权限：android.permission.READ_CONTACTS（读取通讯录）
- 说明：声明敏感权限：android.permission.RECEIVE_SMS（接收短信）
- 说明：声明敏感权限：android.permission.READ_PHONE_STATE（读取电话状态）
- 说明：声明敏感权限：android.permission.CALL_PHONE（拨打电话）
- 说明：声明敏感权限：android.permission.SYSTEM_ALERT_WINDOW（悬浮窗）
- 说明：声明敏感权限：android.permission.REQUEST_INSTALL_PACKAGES（请求安装应用）
- 说明：声明敏感权限：android.permission.QUERY_ALL_PACKAGES（查询所有包）
- 说明：声明敏感权限：android.permission.RECEIVE_BOOT_COMPLETED（开机自启动）

### 3. R-MAN-03 · 明文流量许可

- 状态：已确认 ｜ 通道：fusion ｜ 人工签署：pending
- 证据：`EV-20261126-181546-3356097a-016`, `EV-20261126-181546-3356097a-017`
- 定位坐标：
    - `AndroidManifest.xml [application]`
    - `res/xml/network_security_config.xml:3 [base-config]`
- 说明：显式开启明文流量许可
- 说明：networkSecurityConfig 允许明文流量

### 4. R-MAN-04 · 调试与备份风险

- 状态：已确认 ｜ 通道：fusion ｜ 人工签署：pending
- 证据：`EV-20261126-181546-3356097a-018`, `EV-20261126-181546-3356097a-019`
- 定位坐标：
    - `AndroidManifest.xml [application]`
    - `AndroidManifest.xml [application]`
- 说明：应用显式开启调试标记
- 说明：允许备份（未设置限制）

### 5. R-MAN-05 · 敏感广播监听

- 状态：已确认 ｜ 通道：fusion ｜ 人工签署：pending
- 证据：`EV-20261126-181546-3356097a-020`
- 定位坐标：
    - `AndroidManifest.xml:18-24 [receiver com.synth.bad01.BootReceiver]`
- 说明：静态注册监听敏感事件：android.intent.action.BOOT_COMPLETED（开机完成）、android.provider.Telephony.SMS_RECEIVED（短信接收）、android.intent.action.PHONE_STATE（电话状态）

### 6. R-PERM-03 · 声明与使用不一致

- 状态：已确认 ｜ 通道：fusion ｜ 人工签署：pending
- 证据：`EV-20261126-181546-3356097a-021`
- 定位坐标：
    - `AndroidManifest.xml:4-10 [uses-permission × 7]`
- 说明：敏感权限声明后未发现使用：在当前 APK 自有代码范围内检索无对应调用，且样本未使用反射/JNI/动态加载等可隐藏调用的机制（不排除运行时动态下发的代码调用）
- 缺口：机械层已完成：扫描自有代码 7 个文件；检索 7 项权限对应的 API 使用模式（例：Landroid/media/MediaRecorder;->、Landroid/media/AudioRecord;->）均无命中；隐藏调用通道检测（反射/JNI/动态加载）：无

## 待复核（3 条）

### 1. R-B-001 · 同时申请 SYSTEM_ALERT_WINDOW（悬浮窗覆盖）与 REQUEST_INSTALL_PACKAGES（安装包），可组合用于覆盖安装界面诱导用户安装未知 APK

- 状态：待复核 ｜ 通道：B ｜ 人工签署：pending
- 证据：`EV-20261126-181546-3356097a-036`
- 定位坐标：
    - `权限声明列表: SYSTEM_ALERT_WINDOW, REQUEST_INSTALL_PACKAGES`
- 说明：B 侧疑点（LLM 提疑），未经确定性钉证据，不得升级措辞
- 缺口：钉证据未通过：未识别到可核查断言（claim 无法映射到任何规则）

### 2. R-B-002 · 申请 QUERY_ALL_PACKAGES 可枚举设备上全部已安装应用，超出常规业务所需的包可见性范围

- 状态：待复核 ｜ 通道：B ｜ 人工签署：pending
- 证据：`EV-20261126-181546-3356097a-037`
- 定位坐标：
    - `权限声明: android.permission.QUERY_ALL_PACKAGES`
- 说明：B 侧疑点（LLM 提疑），未经确定性钉证据，不得升级措辞
- 缺口：钉证据未通过：未识别到可核查断言（claim 无法映射到任何规则）

### 3. R-B-003 · 申请 CALL_PHONE 但摘要中未显示配套的 CALL_PRIVILEGED 或用户交互确认机制，存在静默拨号风险

- 状态：待复核 ｜ 通道：B ｜ 人工签署：pending
- 证据：`EV-20261126-181546-3356097a-038`
- 定位坐标：
    - `权限声明: android.permission.CALL_PHONE`
- 说明：B 侧疑点（LLM 提疑），未经确定性钉证据，不得升级措辞
- 缺口：钉证据未通过：未识别到可核查断言（claim 无法映射到任何规则）

## 无法判定（8 条）

> 其中：规则已执行、机械未命中 8 条（不构成安全结论）｜规则未执行 0 条（覆盖缺口）

### 1. R-PERM-01 · 定时/后台结构 × 敏感权限

- 状态：无法判定 ｜ 通道：A ｜ 人工签署：pending
- 定位坐标：
- 说明：机械规则已执行、未命中。仅代表本规则集范围内未发现问题，不构成「安全」结论。

### 2. R-PERM-02 · 非交互组件使用敏感 API

- 状态：无法判定 ｜ 通道：A ｜ 人工签署：pending
- 定位坐标：
- 说明：机械规则已执行、未命中。仅代表本规则集范围内未发现问题，不构成「安全」结论。

### 3. R-STR-01 · 硬编码凭据

- 状态：无法判定 ｜ 通道：A ｜ 人工签署：pending
- 定位坐标：
- 说明：机械规则已执行、未命中。仅代表本规则集范围内未发现问题，不构成「安全」结论。

### 4. R-STR-02 · 内网/明文端点

- 状态：无法判定 ｜ 通道：A ｜ 人工签署：pending
- 定位坐标：
- 说明：机械规则已执行、未命中。仅代表本规则集范围内未发现问题，不构成「安全」结论。

### 5. R-CODE-01 · 动态代码加载

- 状态：无法判定 ｜ 通道：A ｜ 人工签署：pending
- 定位坐标：
- 说明：机械规则已执行、未命中。仅代表本规则集范围内未发现问题，不构成「安全」结论。

### 6. R-CODE-02 · WebView 危险组合

- 状态：无法判定 ｜ 通道：A ｜ 人工签署：pending
- 定位坐标：
- 说明：机械规则已执行、未命中。仅代表本规则集范围内未发现问题，不构成「安全」结论。

### 7. R-NET-01 · 证书校验绕过结构

- 状态：无法判定 ｜ 通道：A ｜ 人工签署：pending
- 定位坐标：
- 说明：机械规则已执行、未命中。仅代表本规则集范围内未发现问题，不构成「安全」结论。

### 8. R-NET-02 · WebView SSL 错误忽略

- 状态：无法判定 ｜ 通道：A ｜ 人工签署：pending
- 定位坐标：
- 说明：机械规则已执行、未命中。仅代表本规则集范围内未发现问题，不构成「安全」结论。

## B 通道观察（非结论 · 保留模型原声）

> 以下为 LLM 复核/扫描的补充观察，**未经机械核查、不作为结论、不计入三档统计**；仅用于人工参考。

- [B1·R-MAN-01] 四个组件类型涵盖 activity/service/receiver/provider，provider 未设 readPermission/writePermission；receiver 声明了 BOOT_COMPLETED 等 intent-filter 但无 permission 保护；未见任何 manifest 级或组件级权限声明可用于豁免
    - B1 复核的补充观察（不构成判定），未经机械核查
- [B1·R-MAN-03] 两处配置相互印证（manifest 与 network security config 均放行明文），不存在“未设置许可”或“明确禁止明文”的情形。
    - B1 复核的补充观察（不构成判定），未经机械核查
- [B1·R-MAN-04] 两个命中点分别对应备份暴露与调试可调试风险，任一存在即构成 R-MAN-04 所检测的结构
    - B1 复核的补充观察（不构成判定），未经机械核查
- [B1·R-MAN-05] receiver 设置了 android:exported="true"，且同时监听开机、短信、通话状态三类敏感事件，进一步支持该命中成立。
    - B1 复核的补充观察（不构成判定），未经机械核查
- [B1·R-PERM-03] 在当前 APK 自有代码范围内未发现上述 7 项权限的使用；未见隐藏调用通道。
    - B1 复核的补充观察（不构成判定），未经机械核查

---
*本报告由 apkaudit 生成（规则包 0.1.7）。复核方式：按定位坐标直达原文，比对 raw_snippet 与证据 JSONL；结论未经人工签署前不生效。*
