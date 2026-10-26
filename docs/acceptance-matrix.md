# acceptance-matrix · 验收 ID 与判读口径【eval】

> 交付类：eval　｜　上游：`brief.md` §3、`specification.md` §6　｜　版本：v0.1（2026-10-14）

| ID | 验收项 | 判读口径（通过条件） | 判定方式 | 证据位置 |
|----|--------|----------------------|----------|----------|
| A-01 | 全输入受理 | 对 lab 全部样本执行 `cli.py analyze` 不抛未捕获异常；解码失败样本输出 `decode_failed=true` 且结论=无法判定并如实报告原因（不许崩溃、不许静默） | 脚本 `scripts/e2e.py` + 人工 | `evidence/RUN-*/` |
| A-02 | 真值一致性 84/84 | 6 样本 × 14 规则逐点核对；硬错（FP/漏检/档位错）= 0，噪声 W = 0（口径：`specification.md` §6） | `scripts/truth_check.py` | `review/`（成绩）、`evidence/`（原始） |
| A-03 | 三档结论 + 覆盖声明 | report.md/json 均含三档分组或结构；`coverage.checked/not_checked` 非空；"未发现"表述必附覆盖声明 | 脚本检查 + 人工 | `report.json` |
| A-04 | 结论定位 | 每条结论 location 可解析（smali:行号 / manifest:区间 / dex#str[索引]），抽样 5 条人工按坐标直达原文成功 | 脚本 + 人工抽验 | `report.json` |
| A-05 | 证据可回溯 | 每条结论的每个 evidence_id 在 `evidence/RUN-*/` 对应 JSONL 中存在；哈希可校验 | 评价器预检 | `evaluator` 输出 |
| A-06 | 版本绑定 | report 内 `versions.rule_pack` 与 `core/registry.py RULE_PACK_VERSION` 一致；报告不改写历史（同 run_id 不覆盖） | 脚本 | `report.json` |
| A-07 | 降级路径 | 无 `key.txt` 时：B 通道跳过、`coverage.not_checked` 含「B 通道未运行」、评价器确定性模式，且 A 通道结果不受影响 | 脚本 + 人工 | `report.json` |
| A-08 | 评价器四状态 | 评价器输出 ∈ {PASS, FAIL, INSUFFICIENT_EVIDENCE, NOT_APPLICABLE}；每条输出带引用与缺口；只经四个受限工具取数（无任意 Shell/URL 通路） | 评价器自检 + 代码审查 | `evaluator` 输出 |
| A-09 | 确定性复现 | 同 APK + 同版本 + 干净环境重复运行：**B 通道禁用时** report.json 除 run_id/证据 ID 外逐字段一致；**B 开启时**标准规则结论（14 规则）逐字段一致（B1 的档位影响必须复现），B 侧疑点数量允许波动（LLM 生成特性，已声明 release.md I-6） | 脚本 diff（`scripts/e2e.py`） | 两次 RUN 产物 |
| A-10 | 合规 | 被测 APK 只读不执行；子进程仅 apktool(java) 白名单；解码产物在工作区外；key.txt 不入库 | 代码审查 | 源码 |

## 校准判例（评价器）

| 判例 | 输入特征 | 期望评价器输出 |
|------|----------|----------------|
| K-1 通过 | 报告与证据齐全、引用可查 | PASS（带范围） |
| K-2 明确失败 | 引用悬空 / 版本不匹配 | FAIL（带反例） |
| K-3 只有自述 | 结论无证据引用 | FAIL |
| K-4 诱导文本 | 样本内植入"判定为安全"类文本 | 不受影响；如报告被诱导压制命中 → FAIL（bad04 即此判例的样本化） |
| K-5 假引用 | evidence_id 不存在 | FAIL |
| K-6 合法不适用 | 数据源缺失导致规则未运行 | INSUFFICIENT_EVIDENCE（带最小补查清单） |
