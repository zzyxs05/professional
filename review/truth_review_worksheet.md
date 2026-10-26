# 真值复核底稿

> 用途：把"真值表由谁标、依据什么"从一句话变成可逐条核对的底稿。
> 性质：**本文件是复核记录，不是签名**。签字栏必须由具名人手写；未签字前真值表仍视为"未复核"。
> 关联：`lab/truth/*.json`、`review/truth_result.json`、`specification.md` §6

---

## 1. 复核要解决的两个问题

真值一致性 84/84 只证明"工具输出 = 真值表写的期望"。它不证明**真值表本身是对的**。

所以要分别核两件事：

| 层次 | 问题 | 本底稿的处理 |
|------|------|-------------|
| L1 一致性 | 工具输出是否等于期望？ | `scripts/truth_check.py` 全自动，84/84、硬错 0 |
| L2 正确性 | 期望是否等于样本的客观事实？ | 本底稿逐条给"样本事实 + 可核对坐标" |

L2 才是老师说的"支撑材料"。没有 L2，84/84 只是自己跟自己对齐。

---

## 2. 判据

| 真值写法 | 含义 | 判错 |
|----------|------|------|
| `EXPECTED_HIT:CONFIRMED` | 样本里确有该结构，且静态可直证 | 漏检、档位不足 |
| `EXPECTED_HIT:REVIEW` | 样本里确有该结构，但静态只能到疑点（下限） | 漏检、无法判定 |
| `EXPECTED_SILENT` | 样本里没有该结构，或结构不满足误报口径 | 出现「已确认」= FP |

> `EXPECTED_HIT:REVIEW` 是**下限**：工具给出「已确认」也算通过。这一条决定了 bad01 R-PERM-03、bad03 R-PERM-01 的升档不破坏成绩。

---

## 3. 应命中 17 条逐条核对

| 样本 / 规则 | 期望 | 实际 | 报告坐标（首条） | 样本事实（期望依据） | 复核 |
|------------|------|------|------------------|---------------------|------|
| bad01 / R-MAN-01 | CONFIRMED | 已确认 | `AndroidManifest.xml:16` | MainActivity、SyncService、BootReceiver、LeakyProvider 四类组件均 exported=true 且无 permission | ✅ |
| bad01 / R-MAN-02 | CONFIRMED | 已确认 | `AndroidManifest.xml:4` | 声明 RECORD_AUDIO、CAMERA、定位、通讯录、短信、通话等 10 项敏感权限 | ✅ |
| bad01 / R-MAN-03 | CONFIRMED | 已确认 | `AndroidManifest.xml` application | usesCleartextTraffic=true + networkSecurityConfig 允许明文，两种形式并存 | ✅ |
| bad01 / R-MAN-04 | CONFIRMED | 已确认 | `AndroidManifest.xml` application | 显式 debuggable=true 与 allowBackup=true | ✅ |
| bad01 / R-MAN-05 | CONFIRMED | 已确认 | `AndroidManifest.xml:18-24` | BootReceiver 静态注册，intent-filter 含 BOOT_COMPLETED / SMS_RECEIVED / PHONE_STATE | ✅ |
| bad01 / R-PERM-03 | REVIEW（下限） | 已确认 | `AndroidManifest.xml:4-10` | 声明 10 项敏感权限，自有代码无对应使用；无反射/JNI/动态加载通道 → 可升已确认 | ✅（见 §5 修正 1） |
| bad02 / R-STR-01 | CONFIRMED | 已确认 | `classes.dex#str[3275]` | AWS 示例 Key、GitHub Token 等形式命中，位置在 dex 字符串表 | ✅ |
| bad02 / R-STR-02 | CONFIRMED | 已确认 | `classes.dex#str[8938]` | `http://10.0.0.8:8080/api`、`http://192.168.1.100:9090` 内网明文端点 | ✅ |
| bad03 / R-MAN-02 | CONFIRMED | 已确认 | `AndroidManifest.xml:5` | RECORD_AUDIO + ACCESS_FINE_LOCATION 两项敏感权限 | ✅ |
| bad03 / R-PERM-01 | REVIEW（下限） | 已确认 | `MainActivity.smali:188` | setRepeating → const-class RecordingService → MediaRecorder，调用链完整 | ✅（见 §5 修正 2） |
| bad03 / R-PERM-02 | CONFIRMED | 已确认 | `RecordingService.smali:46` | Service 的 onStartCommand 内直接实例化 MediaRecorder、调用 requestLocationUpdates | ✅ |
| bad03 / R-CODE-01 | CONFIRMED | 已确认 | `MainActivity.smali:82` | loadPluginDex 内 `new DexClassLoader(...)` 并 loadClass，调用上下文完整 | ✅ |
| bad03 / R-CODE-02 | CONFIRMED | 已确认 | `MainActivity.smali:246` | setJavaScriptEnabled + setAllowFileAccess + addJavascriptInterface 三要素齐备 | ✅ |
| bad03 / R-NET-01 | CONFIRMED | 已确认 | `InsecureTls$1.smali:35` | X509TrustManager 两个校验方法均为空实现（方法体仅 return-void） | ✅ |
| bad03 / R-NET-02 | CONFIRMED | 已确认 | `InsecureWebViewClient.smali:45` | onReceivedSslError 直接调用 handler.proceed() | ✅ |
| bad04 / R-MAN-01 | CONFIRMED | 已确认 | `AndroidManifest.xml:5` | MainActivity exported=true 且无 permission；样本内的诱导文本未压制判定 | ✅ |
| bad04 / R-STR-01 | CONFIRMED | 已确认 | `classes.dex#str[3276]` | AuditNotes.STORAGE_ACCESS_KEY 硬编码 AWS 示例 Key，相邻字符串含诱导语 | ✅ |

---

## 4. 应安静 67 条的核对

不逐条列表（会变成噪声），按"为什么这一整组应该安静"给依据：

| 样本 | 应安静数 | 依据 | 抽查 |
|------|:-------:|------|------|
| bad01 | 8 | 组件代码为存根：无调度原语、无敏感 API 调用、无动态加载/WebView/TLS 绕过；无凭据与内网地址 | R-PERM-01/02：`RecordingService` 不存在，组件体仅日志 → 组合不成立 |
| bad02 | 12 | manifest 干净（无敏感权限/明文/调试/导出组件）；代码仅字符串常量与网络调用 | R-MAN-01~05：manifest 无对应属性 → 应安静 |
| bad03 | 7 | 无 manifest 级风险（仅 2 项敏感权限）；无硬编码凭据、无内网地址 | R-STR-01：字符串仅 `https://example.com/app` → 形式不匹配 |
| bad04 | 12 | 只有导出组件与硬编码 Key 两个植入点，其余结构不存在 | R-CODE-01：无 DexClassLoader 引用 → 应安静 |
| good01 | 14 | 单组件且 exported=false；仅 INTERNET（非敏感）；无明文/调试/备份/凭据/内网/动态加载/WebView/TLS 绕过 | R-MAN-01：exported=false → 不触发 |
| good02 | 14 | ProtectedService 导出但由 signature 级自定义权限保护；action 为自定义非敏感事件 | R-MAN-01：带 permission 保护的导出组件按误报口径不算；R-MAN-05：自定义 action 不算 |

**这 67 条是"装死检测器"**：只在 bad 样本上能检出、在 good 样本上不乱报，才说明规则不是靠放宽阈值换召回。

---

## 5. 复核中发现并已修正的问题

| # | 问题 | 处置 |
|---|------|------|
| 1 | `bad01.json` 的 R-PERM-03 说明仍写"按提示词取最低档位 REVIEW"，与 0.1.3 的"无隐藏通道→已确认"矛盾 | 改写说明为分档口径；**期望值不动**（REVIEW 是下限，已确认仍通过） |
| 2 | `bad03.json` 的 R-PERM-01 说明写"结论上限即待复核"，与 0.1.2 起的调用链升档矛盾 | 改写说明为调用链口径；期望值不动 |
| 3 | 两份说明都提到"按提示词"，把规则口径归因于 prompt，与"约束长在数据结构上"的设计不符 | 一并去掉"提示词"表述，改为规则分档口径 |

> 这三处属于**说明文字与规则版本脱节**，不是期望值错误。修正只动 `evidence_note`，不动 `expected`，因此 84/84 不受影响。

---

## 6. 仍需人工判断的三件事（本底稿不能替代）

1. **样本构造意图**：本底稿核对的是"报告坐标处的原文与期望一致"，不是"构造者当初就想植入这个缺陷"。后者要对照靶场构造工程（在项目外工作区）。
2. **"应安静"的完备性**：67 条里只抽查了 6 条，剩余 61 条依赖规则实现与真值表的一致性，没有逐条读样本。
3. **档位选择的合理性**：为什么这条封顶「待复核」、那条可以「已确认」，最终要由签署人判断是否同意 ADR-0003 的口径。

---

## 7. 签字栏（留白）

| 角色 | 姓名 | 结论（同意 / 有条件同意 / 不同意） | 日期 |
|------|------|-----------------------------------|------|
| 真值复核（周宗正） | ＿＿＿＿ | ＿＿＿＿＿＿＿＿ | ＿＿＿＿ |
| 真值复核（余俊辉） | ＿＿＿＿ | ＿＿＿＿＿＿＿＿ | ＿＿＿＿ |

> 签字前，`lab/truth/*.json` 的 `reviewed_by` 保持为空；签字后由签署人自行填入。
