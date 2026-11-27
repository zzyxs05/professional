# APK 静态审计报告 RUN-20261126-205219-3356097a

- 样本：`bad01.apk`
- sha256：`3356097a33fb044d848ee1930523924b2d08ba7bbfdf47f43c7dbad10aae1414`
- 规则包版本：`0.1.8`　｜　通道 B 模型：`mimo-v2.6-flash`
- 工具链：java=openjdk version "1.8.0_492", apktool=apktool_3.0.3.jar

> 证据层级说明：本项目只读、不执行被测 APK，全部证据层级上限为 STATIC。

## 覆盖声明

- 已检查（15 条）：R-MAN-01(manifest)；R-MAN-02(manifest)；R-MAN-03(manifest+res_decoded)；R-MAN-04(manifest)；R-MAN-05(manifest)；R-PERM-01(smali_src)；R-PERM-02(manifest/smali_src)；R-PERM-03(manifest/smali_src)；R-STR-01(dex_strings)；R-STR-02(dex_strings)；R-CODE-01(dex_strings/smali_src)；R-CODE-02(smali_src)；R-NET-01(smali_src)；R-NET-02(smali_src)；通道B(模型:mimo-v2.6-flash)
- 未覆盖（0 条）：—
- 解码状态：正常（复用缓存）

## 已确认（6 条）

### 1. R-MAN-01 · 导出组件无权限保护

- 状态：已确认 ｜ 通道：fusion ｜ 人工签署：pending
- 证据：`EV-20261126-205219-3356097a-001`, `EV-20261126-205219-3356097a-002`, `EV-20261126-205219-3356097a-003`, `EV-20261126-205219-3356097a-004`
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
- 证据：`EV-20261126-205219-3356097a-005`, `EV-20261126-205219-3356097a-006`, `EV-20261126-205219-3356097a-007`, `EV-20261126-205219-3356097a-008`, `EV-20261126-205219-3356097a-009`, `EV-20261126-205219-3356097a-010`, `EV-20261126-205219-3356097a-011`, `EV-20261126-205219-3356097a-012`, `EV-20261126-205219-3356097a-013`, `EV-20261126-205219-3356097a-014`, `EV-20261126-205219-3356097a-015`
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
- 证据：`EV-20261126-205219-3356097a-016`, `EV-20261126-205219-3356097a-017`
- 定位坐标：
    - `AndroidManifest.xml [application]`
    - `res/xml/network_security_config.xml:3 [base-config]`
- 说明：显式开启明文流量许可
- 说明：networkSecurityConfig 允许明文流量

### 4. R-MAN-04 · 调试与备份风险

- 状态：已确认 ｜ 通道：fusion ｜ 人工签署：pending
- 证据：`EV-20261126-205219-3356097a-018`, `EV-20261126-205219-3356097a-019`
- 定位坐标：
    - `AndroidManifest.xml [application]`
    - `AndroidManifest.xml [application]`
- 说明：应用显式开启调试标记
- 说明：允许备份（未设置限制）

### 5. R-MAN-05 · 敏感广播监听

- 状态：已确认 ｜ 通道：fusion ｜ 人工签署：pending
- 证据：`EV-20261126-205219-3356097a-020`
- 定位坐标：
    - `AndroidManifest.xml:18-24 [receiver com.synth.bad01.BootReceiver]`
- 说明：静态注册监听敏感事件：android.intent.action.BOOT_COMPLETED（开机完成）、android.provider.Telephony.SMS_RECEIVED（短信接收）、android.intent.action.PHONE_STATE（电话状态）

### 6. R-PERM-03 · 声明与使用不一致

- 状态：已确认 ｜ 通道：fusion ｜ 人工签署：pending
- 证据：`EV-20261126-205219-3356097a-021`
- 定位坐标：
    - `AndroidManifest.xml:4-10 [uses-permission × 7]`
- 说明：敏感权限声明后未发现使用：在当前 APK 自有代码范围内检索无对应调用，且样本未使用反射/JNI/动态加载等可隐藏调用的机制（不排除运行时动态下发的代码调用）
- 缺口：机械层已完成：扫描自有代码 7 个文件；检索 7 项权限对应的 API 使用模式（例：Landroid/media/MediaRecorder;->、Landroid/media/AudioRecord;->）均无命中；隐藏调用通道检测（反射/JNI/动态加载）：无

## 待复核（4 条）

### 1. R-B-001 · 申请 RECORD_AUDIO、CAMERA、ACCESS_FINE_LOCATION、READ_CONTACTS 组合，属于典型的音视频/位置/通讯录多维采集面

- 状态：待复核 ｜ 通道：B ｜ 人工签署：pending
- 证据：`EV-20261126-205219-3356097a-032`
- 定位坐标：
    - `权限列表: RECORD_AUDIO, CAMERA, ACCESS_FINE_LOCATION, READ_CONTACTS`
- 说明：B 侧疑点（LLM 提疑），未经确定性钉证据，不得升级措辞
- 说明：结构事实：ANDROID.PERMISSION.ACCESS_FINE_LOCATION、ANDROID.PERMISSION.CAMERA、ANDROID.PERMISSION.READ_CONTACTS、ANDROID.PERMISSION.RECORD_AUDIO
- 缺口：结构已核对、意图未证实：结构事实已核对：claim 提及的实体（ANDROID.PERMISSION.ACCESS_FINE_LOCATION、ANDROID.PERMISSION.CAMERA、ANDROID.PERMISSION.READ_CONTACTS、ANDROID.PERMISSION.RECORD_AUDIO）均在样本声明中；组合/意图类断言无对应规则，未证实

### 2. R-B-002 · 申请 REQUEST_INSTALL_PACKAGES，具备拉起应用安装流程的能力，需核查是否配合网络下载来源使用

- 状态：待复核 ｜ 通道：B ｜ 人工签署：pending
- 证据：`EV-20261126-205219-3356097a-033`
- 定位坐标：
    - `权限列表: android.permission.REQUEST_INSTALL_PACKAGES`
- 说明：B 侧疑点（LLM 提疑），未经确定性钉证据，不得升级措辞
- 说明：结构事实：ANDROID.PERMISSION.REQUEST_INSTALL_PACKAGES
- 缺口：结构已核对、意图未证实：结构事实已核对：claim 提及的实体（ANDROID.PERMISSION.REQUEST_INSTALL_PACKAGES）均在样本声明中；组合/意图类断言无对应规则，未证实

### 3. R-B-003 · 申请 QUERY_ALL_PACKAGES，可枚举设备上全部已安装应用，常用于画像或环境探测

- 状态：待复核 ｜ 通道：B ｜ 人工签署：pending
- 证据：`EV-20261126-205219-3356097a-034`
- 定位坐标：
    - `权限列表: android.permission.QUERY_ALL_PACKAGES`
- 说明：B 侧疑点（LLM 提疑），未经确定性钉证据，不得升级措辞
- 说明：结构事实：ANDROID.PERMISSION.QUERY_ALL_PACKAGES
- 缺口：结构已核对、意图未证实：结构事实已核对：claim 提及的实体（ANDROID.PERMISSION.QUERY_ALL_PACKAGES）均在样本声明中；组合/意图类断言无对应规则，未证实

### 4. R-B-004 · 申请 RECEIVE_SMS 与 CALL_PHONE 组合，可监听短信并直接发起呼叫

- 状态：待复核 ｜ 通道：B ｜ 人工签署：pending
- 证据：`EV-20261126-205219-3356097a-036`
- 定位坐标：
    - `权限列表: RECEIVE_SMS, CALL_PHONE`
- 说明：B 侧疑点（LLM 提疑），未经确定性钉证据，不得升级措辞
- 说明：结构事实：ANDROID.PERMISSION.CALL_PHONE、ANDROID.PERMISSION.RECEIVE_SMS
- 缺口：结构已核对、意图未证实：结构事实已核对：claim 提及的实体（ANDROID.PERMISSION.CALL_PHONE、ANDROID.PERMISSION.RECEIVE_SMS）均在样本声明中；组合/意图类断言无对应规则，未证实

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

- [B2] MainActivity 被声明为 exported=True，若未设置权限保护或 intent-filter 限制，可被外部应用直接拉起（位置：com.synth.bad01.MainActivity (activity; exported=True)）
    - LLM 观察（低置信），未经机械核查，不作为结论
- [B1·R-MAN-01] BootReceiver 声明了 BOOT_COMPLETED/SMS_RECEIVED/PHONE_STATE 三个系统广播，其中 SMS_RECEIVED 属敏感广播，缺少权限保护时暴露面更大；LeakyProvider 仅设置 authorities 未设 readPermission/writePermission，provider 类组件默认可读性风险较高
    - B1 复核的补充观察（不构成判定），未经机械核查
- [B1·R-MAN-02] 五个权限均需运行时用户授权，其中 RECEIVE_SMS 属于高危短信类权限
    - B1 复核的补充观察（不构成判定），未经机械核查
- [B1·R-MAN-03] manifest 与 network_security_config 双重确认，许可效果一致且相互叠加，配置层面无法通过默认策略回退为禁止明文。
    - B1 复核的补充观察（不构成判定），未经机械核查
- [B1·R-MAN-04] 两个属性均在 [application] 节点显式声明为 true，属于规则直接覆盖的高风险配置
    - B1 复核的补充观察（不构成判定），未经机械核查
- [B1·R-MAN-05] 该 receiver 还被显式设为 exported=true，进一步扩大了外部触发面
    - B1 复核的补充观察（不构成判定），未经机械核查
- [B1·R-PERM-03] 结论措辞须限定为'在当前 APK 自有代码范围内未发现使用'；RECEIVE_SMS、READ_CONTACTS 等权限理论上亦可能由广播接收器或系统组件间接触发，静态检索仅覆盖自有 7 个文件的直接 API 调用模式
    - B1 复核的补充观察（不构成判定），未经机械核查

---
*本报告由 apkaudit 生成（规则包 0.1.8）。复核方式：按定位坐标直达原文，比对 raw_snippet 与证据 JSONL；结论未经人工签署前不生效。*
