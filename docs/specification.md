# specification · 需求与检查项规格【design】

> 交付类：design　｜　上游：总档.md §3/§5/§6　｜　版本：v0.1（2026-10-14 契约冻结稿）
> 实现唯一来源：`core/registry.py`（规则、阈值、正则全部登记于此）。本文档与 registry 不符时，以本文档为准并修 registry。

## 1. 数据源四层与降级口径

| 数据源 | 生产者 | 可用条件 | 不可用时行为 |
|--------|--------|----------|--------------|
| `manifest` | 自研 AXML 直读（`core/axml.py`） | APK 内含可解析 AndroidManifest.xml | 属解码级失败 → 样本级"无法判定" |
| `dex_strings` | 自研 dex 扫描（`core/dexscan.py`） | APK 内含可解析 classes*.dex | 属解码级失败 → 样本级"无法判定" |
| `smali_src` | apktool 反汇编 | 工具链可用（`.tools/`→环境变量→PATH） | 语义类规则（P/C/N 类）输出"数据源未覆盖：缺少 apktool"，进覆盖声明 |
| `res_decoded` | apktool 资源解码 | 同上 | S 类资源侧字符串跳过，进覆盖声明 |

- 逐规则声明依赖；**不可用即显式跳过，不静默**。
- apktool 调用固定 `-p .tools/framework`（项目可控路径）；解码产物放**工作区外临时区**（`%TEMP%/apkaudit_decode/<sha256[:16]>/`，可重建不入库）。
- 子进程白名单：仅 `java`（apktool 调用）。名单外一律拒绝。

## 2. 规则契约（14 条）

约定：**档位上限（max_status）** = 该规则在无 B 通道复核时允许输出的最高档位；融合层不得越过。

| ID | 检测点（可验收定义） | 数据源 | 档位上限 | 误报口径（什么不算） |
|----|---------------------|--------|:--------:|---------------------|
| R-MAN-01 | 组件 exported 判定：①显式 `android:exported="true"`；②含 `<intent-filter>` 且未显式声明 exported；**且**无组件级 `permission`/`readPermission`/`writePermission` 保护 | manifest | 已确认 | 带 signature 级自定义权限的导出组件不算（good02 口径） |
| R-MAN-02 | `<uses-permission>` ∩ 敏感权限清单（录音/相机/定位/短信/通话/通讯录/无障碍/悬浮窗/安装包/查询包/自启动等，清单见 registry `SENSITIVE_PERMISSIONS`） | manifest | 已确认 | 仅 INTERNET、自定义 `com.*.permission.*` 不算（good 口径） |
| R-MAN-03 | ①`usesCleartextTraffic="true"`；②`networkSecurityConfig` 指向的配置含 `cleartextTrafficPermitted="true"`（依赖 res_decoded） | manifest(+res) | 已确认 | 未设置、或配置明确禁明文不算 |
| R-MAN-04 | `debuggable="true"` 或 `allowBackup="true"`（未显式声明 allowBackup 视为系统默认 true，标注"默认值"） | manifest | 已确认 | `allowBackup="false"` 不算 |
| R-MAN-05 | 静态注册 Receiver（manifest 内）的 intent-filter action ∩ 敏感广播清单（BOOT_COMPLETED / SMS_RECEIVED / PHONE_STATE / USER_PRESENT / CONNECTIVITY_CHANGE 等，registry `SENSITIVE_ACTIONS`） | manifest | 已确认 | 自定义 action、非敏感系统事件不算（good02 口径） |
| R-PERM-01 | **自有代码**内「调度原语 × 敏感 API」（AlarmManager/WorkManager/JobScheduler/Timer/Handler.postDelayed/ScheduledExecutor × 录音/定位/相机/短信等 API） | smali_src | **按证据强度分档**：①有调用链证据→**已确认**；②仅样本级共存→**待复核** | 仅一侧存在不算（good01 口径：只有 postDelayed）。**调用链证据**＝同一方法内调度原语 + 可解析调度目标（`const-class`/Intent 类参数/`PendingIntent.get*` 上下文）且目标组件内含敏感 API；无链时回退共存档。**两档均禁止表述"在半夜录音"**（只断言结构，不断言行为） |
| R-PERM-02 | manifest 声明的 Service/Receiver/Provider 类文件中**直接**出现敏感 API 调用（方法体级） | manifest + smali_src | 已确认 | Activity 不算；仅 import/字段声明不算 |
| R-PERM-03 | 敏感权限"声明与使用不一致"：manifest 声明的敏感权限在**自有代码**中找不到对应 API 使用（排除性结论） | manifest + smali_src | **按静态排除力分档**：①无隐藏调用通道→**已确认**；②有通道→**待复核** | 排除**声明即生效**权限（QUERY_ALL_PACKAGES/SYSTEM_ALERT_WINDOW/REQUEST_INSTALL_PACKAGES 等）与广播类权限；措辞必须限定"在当前 APK 自有代码范围内未发现使用"，不得写"未使用" |
| R-STR-01 | 凭据形式匹配：PEM 私钥 / JWT / AWS(AKIA…) / GitHub(ghp_…) / Slack / Stripe(sk_…) / Google(AIza…) / 阿里(LTAI…) / 腾讯(AKID…) 等，registry `CREDENTIAL_PATTERNS` | dex_strings + res_decoded | 已确认 | 示例值/形式值**照报**（bad02/bad04 口径：形式匹配即事实） |
| R-STR-02 | `http://` + 内网/明文端点：10./192.168./172.16-31. /localhost /127.0.0.1/`.local`/`.internal` | dex_strings + res_decoded | 已确认 | 公网 https 不算（good 口径 example.com）；公网 http 亦不在本条范围 |
| R-CODE-01 | 动态代码加载：DexClassLoader / PathClassLoader / InMemoryDexClassLoader / System.load。smali 有调用上下文→已确认；仅 dex 弱模式（类型引用）→待复核 | smali_src（强）/ dex_strings（弱） | 已确认 | 字符串里出现类名不算 |
| R-CODE-02 | WebView 危险组合：`addJavascriptInterface` × `setJavaScriptEnabled` × `setAllowFileAccess` 三要素齐备 | smali_src | 已确认 | 仅启用 JS、无接口注入不算（good02 口径）；要素为调用出现，暂不解析布尔实参（记 changes.md 观察项） |
| R-NET-01 | 证书校验绕过结构：①`X509TrustManager` 实现的 checkClientTrusted/checkServerTrusted 为**空方法体**（无 invoke 指令）或 getAcceptedIssuers 返回空数组；②`HostnameVerifier` 实现 verify 恒 true（方法体无 invoke 且返回常量真）；③自定义 SSLSocketFactory 子类 | smali_src | 已确认 | 委托系统默认实现的正确校验不算（good02 口径：方法体含委托 invoke） |
| R-NET-02 | `onReceivedSslError` 方法体内调用 `SslErrorHandler;->proceed()` | smali_src | 已确认 | 调 `cancel()` 的正确实现不算（good02 口径） |

**语义规则扫描范围纪律**：P/C/N 类规则只扫描**自有代码**（manifest package 前缀匹配的类），
避免 kotlin/androidx 等库代码干扰（实证：`kotlin/concurrent/TimersKt` 含 Timer 引用，全量扫描必误报）。
S 类字符串规则扫描全量 dex 字符串 + 资源字符串（库字符串可能命中凭据模式 → 属事实，如实报位置）。

## 3. 结论与报告 schema

### 3.1 结论条目（report.json `conclusions[]`）

```json
{
  "criterion_id": "R-MAN-01",
  "status": "已确认 | 待复核 | 无法判定",
  "channel": "A | B | fusion",
  "location": "多定位用 ' | ' 分隔，格式见 §4",
  "evidence_ids": ["EV-..."],
  "scope": "该结论的适用范围（≤一句话）",
  "missing_evidence": [],
  "human_signoff": "pending"
}
```

### 3.2 报告顶层

```json
{
  "run_id": "RUN-<yyyymmdd-HHMMSS>",
  "target": {"apk_name": "...", "apk_sha256": "..."},
  "versions": {"rule_pack": "0.1.2", "channel_b_model": "none|模型名"},
  "conclusions": [],
  "observations": [],   ← B 通道观察区（低置信/补充观察），**非结论、不计入三档**
  "coverage": {
    "checked": ["R-MAN-01(manifest)", "..."],
    "not_checked": ["R-CODE-01(smali_src: 缺少 apktool)", "..."],
    "decode_failed": false,
    "decode_note": ""
  }
}
```

- `report.md` 由同一事实本体渲染（三档分组 + 覆盖声明 + 证据引用 + 来源/层级标注）；
- 证据层级本项目上限 = STATIC（只读，不执行被测 APK）。

## 4. 结论定位格式【硬性】

| 来源 | 坐标格式 |
|------|----------|
| smali 语义 | `smali/<相对路径>.smali:<行号>（原始行 <N>）` + 类/方法全名（`.line` 指令可得时给原始行，缺失给"原始行 ?"） |
| manifest | `AndroidManifest.xml:<重建行起>-<止>` + 组件/权限全名 |
| dex 字符串 | `classes<N>.dex#str[<索引>]` + 值原文（截断 200 字符） |
| 资源字符串 | `res/values/strings.xml:<行号>` + 资源名 |

每条结论同时携带 `evidence_id`（JSONL 证据指针）与 `raw_snippet`（截断原文）。

## 5. LLM 接入（通道 B / 评价器共用）

- 配置 `key.txt`（项目根，**不入库**）：一行一条、逗号分隔 `模型名,base_url,api_key`，多个按序取第一个可用；
- OpenAI 兼容端点，标准库 HTTP 实现，参数统一在 registry 常量区；
- **缺失/加载失败 → 自动降级**：B 通道整体跳过并声明「B 通道未运行」；评价器退化确定性判读（硬要求）。

**B 通道任务集**（各自独立 prompt 版本，变更 = bump 版本号）：

| 任务 | 版本 | 内容与纪律 |
|------|------|-----------|
| B1 上下文复核 | b1-v0.3 | 输入=规则检测点+误报口径+命中片段；输出 schema `{verdict(枚举), reason, observation}`；判定标准来自**误报口径数据**（registry `fp_notes`）；`observation` 承载判定之外的补充观察 |
| B2 敏感区扫描 | b2-v0.4 | 输入=敏感区摘要（组件及属性/权限/自定义权限/URL/动态加载点）；输出 schema `[{claim, location, rule_guess, confidence(枚举 high/medium/low)}]`；`confidence=low` 进观察区，其余走钉证据 |
| B3 跨样本汇总 | b3-v0.2 | 输入=六样本结构化结果+【汇总统计】行（程序统计）；输出=Markdown 报告（≤900 字）；无模型降级模板渲染 |

**B 通道提示词纪律（2026-10-15 确立）**：约束长在**数据结构**上（字段、枚举、必填、程序统计），
不写在散文禁令里——不出现"不要/不许/禁止/宁缺毋滥"等否定式指令。模型的判断由它自己给，
程序只负责：给全事实输入、限定输出 schema、按置信度分流、机械验证后才升级结论。
B1 的 `observation` 与 B2 的 `low` 置信观察进入报告 `observations` 区（**非结论、不计入三档**），
用于保留模型的原始声音供人工参考。

## 6. 真值一致性评分口径（A-02 判读细节）

对每个标定样本（`lab/truth/*.json`）跑 `cli.py analyze`，以 `report.json` 逐点核对：

| 真值 | 判 PASS | 记误报 FP | 记噪声 W | 记漏检 M | 记档位错 T |
|------|---------|-----------|----------|-----------|------------|
| `EXPECTED_HIT:CONFIRMED` | 结论存在且状态=已确认 | — | — | 无结论 | 状态=待复核/无法判定 |
| `EXPECTED_HIT:REVIEW` | 结论存在且状态∈{已确认,待复核} | — | — | 无结论或无法判定 | — |
| `EXPECTED_SILENT` | 无结论 | 状态=已确认 | **状态=待复核**（低置信输出，单独统计） | — | — |

- 硬错 = FP + M + T（目标 0）；噪声 W 单独列示（目标 0，但按"不把合理不确定性判错"精神不并入硬错）；
- 输出：`passed/HARD-errors breakdown (FP/M/T) / W / 84`，作为交付材料进 `review/`；
- **注意区分**：审计报告（对目标的事实与结论）与一致性成绩（自评质量门）不混用。
