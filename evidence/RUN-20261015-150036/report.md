# APK 静态审计报告 RUN-20261015-150036

- 样本：`good01.apk`
- sha256：`4cbacbdd6f878f7128ee4938f311ebac9a65e54e53f809a1b9b61634c17355dc`
- 规则包版本：`0.1.3`　｜　通道 B 模型：`mimo-v2.6-flash`
- 工具链：java=openjdk version "1.8.0_492", apktool=apktool_3.0.3.jar

> 证据层级说明：本项目只读、不执行被测 APK，全部证据层级上限为 STATIC。

## 覆盖声明

- 已检查（15 条）：R-MAN-01(manifest)；R-MAN-02(manifest)；R-MAN-03(manifest+res_decoded)；R-MAN-04(manifest)；R-MAN-05(manifest)；R-PERM-01(smali_src)；R-PERM-02(manifest/smali_src)；R-PERM-03(manifest/smali_src)；R-STR-01(dex_strings)；R-STR-02(dex_strings)；R-CODE-01(dex_strings/smali_src)；R-CODE-02(smali_src)；R-NET-01(smali_src)；R-NET-02(smali_src)；通道B(模型:mimo-v2.6-flash)
- 未覆盖（0 条）：—
- 解码状态：正常（复用缓存）

## 已确认（0 条）

（无）

## 待复核（2 条）

### 1. R-B-001 · 样本声明了 android.permission.INTERNET，但摘要中未列出任何 URL、网络入口或已知的网络客户端组件，网络行为可能位于未被静态识别的代码路径中

- 状态：待复核 ｜ 通道：B ｜ 人工签署：pending
- 证据：`EV-20261015-150036-002`
- 定位坐标：
    - `权限声明: android.permission.INTERNET`
- 说明：B 侧疑点（LLM 提疑），未经确定性钉证据，不得升级措辞
- 缺口：钉证据未通过：断言未被机械事实证实（候选规则 R-MAN-02 均无机械命中；claim 提及实体（ANDROID.PERMISSION.INTERNET、INTERNET、android.permission.INTERNET）未被机械命中覆盖）

### 2. R-B-002 · com.synth.good01.MainActivity 是当前唯一被列出的组件且 exported=False，其内是否包含 AsyncTask/Thread/WebView 等发起网络请求或动态加载的逻辑需人工确认

- 状态：待复核 ｜ 通道：B ｜ 人工签署：pending
- 证据：`EV-20261015-150036-003`
- 定位坐标：
    - `com.synth.good1.MainActivity (activity)`
- 说明：B 侧疑点（LLM 提疑），未经确定性钉证据，不得升级措辞
- 缺口：钉证据未通过：断言未被机械事实证实（候选规则 R-CODE-01, R-CODE-02 均无机械命中；claim 提及实体（MAINACTIVITY、MainActivity、com.synth.good01.MainActivity）未被机械命中覆盖）

## 无法判定（0 条）

（无）

## B 通道观察（非结论 · 保留模型原声）

> 以下为 LLM 复核/扫描的补充观察，**未经机械核查、不作为结论、不计入三档统计**；仅用于人工参考。

- [B2] 敏感区域摘要中未出现自定义权限声明、动态加载点与调度结构，样本可能通过其他入口（如 Provider/Service/Receiver）或被混淆的类实现敏感行为（位置：全局摘要）
    - LLM 观察（低置信），未经机械核查，不作为结论

---
*本报告由 apkaudit 生成（规则包 0.1.3）。复核方式：按定位坐标直达原文，比对 raw_snippet 与证据 JSONL；结论未经人工签署前不生效。*
