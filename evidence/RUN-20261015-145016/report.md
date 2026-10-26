# APK 静态审计报告 RUN-20261015-145016

- 样本：`bad01.apk`
- sha256：`3356097a33fb044d848ee1930523924b2d08ba7bbfdf47f43c7dbad10aae1414`
- 规则包版本：`0.1.3`　｜　通道 B 模型：`mimo-v2.6-flash`
- 工具链：java=openjdk version "1.8.0_492", apktool=apktool_3.0.3.jar

> 证据层级说明：本项目只读、不执行被测 APK，全部证据层级上限为 STATIC。

## 覆盖声明

- 已检查（15 条）：R-MAN-01(manifest)；R-MAN-02(manifest)；R-MAN-03(manifest+res_decoded)；R-MAN-04(manifest)；R-MAN-05(manifest)；R-PERM-01(smali_src)；R-PERM-02(manifest/smali_src)；R-PERM-03(manifest/smali_src)；R-STR-01(dex_strings)；R-STR-02(dex_strings)；R-CODE-01(dex_strings/smali_src)；R-CODE-02(smali_src)；R-NET-01(smali_src)；R-NET-02(smali_src)；通道B(模型:mimo-v2.6-flash)
- 未覆盖（0 条）：—
- 解码状态：正常（复用缓存）

## 已确认（6 条）

### 1. R-MAN-01 · 导出组件无权限保护

- 状态：已确认 ｜ 通道：fusion ｜ 人工签署：pending
- 证据：`EV-20261015-145016-001`, `EV-20261015-145016-002`, `EV-20261015-145016-003`, `EV-20261015-145016-004`
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
- 证据：`EV-20261015-145016-005`, `EV-20261015-145016-006`, `EV-20261015-145016-007`, `EV-20261015-145016-008`, `EV-20261015-145016-009`, `EV-20261015-145016-010`, `EV-20261015-145016-011`, `EV-20261015-145016-012`, `EV-20261015-145016-013`, `EV-20261015-145016-014`, `EV-20261015-145016-015`
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
- 证据：`EV-20261015-145016-016`, `EV-20261015-145016-017`
- 定位坐标：
    - `AndroidManifest.xml [application]`
    - `res/xml/network_security_config.xml:3 [base-config]`
- 说明：显式开启明文流量许可
- 说明：networkSecurityConfig 允许明文流量

### 4. R-MAN-04 · 调试与备份风险

- 状态：已确认 ｜ 通道：fusion ｜ 人工签署：pending
- 证据：`EV-20261015-145016-018`, `EV-20261015-145016-019`
- 定位坐标：
    - `AndroidManifest.xml [application]`
    - `AndroidManifest.xml [application]`
- 说明：应用显式开启调试标记
- 说明：允许备份（未设置限制）

### 5. R-MAN-05 · 敏感广播监听

- 状态：已确认 ｜ 通道：fusion ｜ 人工签署：pending
- 证据：`EV-20261015-145016-020`
- 定位坐标：
    - `AndroidManifest.xml:18-24 [receiver com.synth.bad01.BootReceiver]`
- 说明：静态注册监听敏感事件：android.intent.action.BOOT_COMPLETED（开机完成）、android.provider.Telephony.SMS_RECEIVED（短信接收）、android.intent.action.PHONE_STATE（电话状态）

### 6. R-PERM-03 · 声明与使用不一致

- 状态：已确认 ｜ 通道：fusion ｜ 人工签署：pending
- 证据：`EV-20261015-145016-021`
- 定位坐标：
    - `AndroidManifest.xml:4-10 [uses-permission × 7]`
- 说明：敏感权限声明后未发现使用：在当前 APK 自有代码范围内检索无对应调用，且样本未使用反射/JNI/动态加载等可隐藏调用的机制（不排除运行时动态下发的代码调用）

## 待复核（2 条）

### 1. R-B-001 · REQUEST_INSTALL_PACKAGES 与 CALL_PHONE 同时存在，暗示可能静默拉起 APK 安装流程或发起付费通话，属于高风险可执行操作。

- 状态：待复核 ｜ 通道：B ｜ 人工签署：pending
- 证据：`EV-20261015-145016-039`
- 定位坐标：
    - `uses-permission: REQUEST_INSTALL_PACKAGES / CALL_PHONE`
- 说明：B 侧疑点（LLM 提疑），未经确定性钉证据，不得升级措辞
- 缺口：钉证据未通过：未识别到可核查断言（claim 无法映射到任何规则）

### 2. R-B-002 · SYSTEM_ALERT_WINDOW + QUERY_ALL_PACKAGES 组合可用于覆盖层钓鱼界面与全量应用枚举，具备持久化与横向探测能力。

- 状态：待复核 ｜ 通道：B ｜ 人工签署：pending
- 证据：`EV-20261015-145016-040`
- 定位坐标：
    - `uses-permission: SYSTEM_ALERT_WINDOW / QUERY_ALL_PACKAGES`
- 说明：B 侧疑点（LLM 提疑），未经确定性钉证据，不得升级措辞
- 缺口：钉证据未通过：未识别到可核查断言（claim 无法映射到任何规则）

## 无法判定（0 条）

（无）

## B 通道观察（非结论 · 保留模型原声）

> 以下为 LLM 复核/扫描的补充观察，**未经机械核查、不作为结论、不计入三档统计**；仅用于人工参考。

- [B1·R-MAN-01] MainActivity 与 SyncService 为无过滤器的裸导出；BootReceiver 同时注册 BOOT_COMPLETED、SMS_RECEIVED、PHONE_STATE 等系统广播；LeakyProvider 作为 provider 导出且未见 readPermission/writePermission，provider 风险面更高。
    - B1 复核的补充观察（不构成判定），未经机械核查
- [B1·R-MAN-02] 命中集中在 AndroidManifest.xml 连续 5 行，同时请求麦克风、摄像头、精确定位、联系人、短信五类敏感能力，权限组合面较广，若应用功能与之不匹配，可进一步评估其数据采集范围是否超出合理必要。
    - B1 复核的补充观察（不构成判定），未经机械核查
- [B1·R-MAN-03] 两处配置方向一致，base-config 未限定具体域名，意味着对所有未单独配置的域名默认放行明文 HTTP；即使 manifest 属性在 API 24+ 会被 network security config 覆盖，二者结论仍相同，不构成误报。
    - B1 复核的补充观察（不构成判定），未经机械核查
- [B1·R-MAN-04] 两者均显式设置为 true 且位于同一 <application> 标签，风险叠加：允许调试且允许应用数据被 adb 备份，建议改为 debuggable=false 并显式设置 allowBackup=false。
    - B1 复核的补充观察（不构成判定），未经机械核查
- [B1·R-MAN-05] 该 receiver 未附带任何 permission 属性，任意应用可向其发送伪造广播，加剧了敏感广播监听的风险面。
    - B1 复核的补充观察（不构成判定），未经机械核查
- [B1·R-PERM-03] ① 检索范围仅限自有代码 7 个文件，未见对内嵌第三方 SDK（jar/aar 合并代码）的同等扫描，RECORD_AUDIO/CAMERA/ACCESS_FINE_LOCATION 等常被 SDK 声明并调用，若 SDK 代码未纳入检索需在报告中显式声明该范围限制；② 建议补充核对字符串型权限检查（checkSelfPermission("android.permission.XXX")）与权限
    - B1 复核的补充观察（不构成判定），未经机械核查

---
*本报告由 apkaudit 生成（规则包 0.1.3）。复核方式：按定位坐标直达原文，比对 raw_snippet 与证据 JSONL；结论未经人工签署前不生效。*
