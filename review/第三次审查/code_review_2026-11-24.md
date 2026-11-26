# 代码审查报告 · 第三次审查

> 审查模型：GLM-5.3-Flash + code-review-analyzer v1.2.4（AST 扫描 + 安全清单 + 五维深审）
> 审查时间：2026-11-24 11:40—11:50
> 审查基线：`e2f6716`（pull 自 origin/main，含朋友文档重构提交 `c7dfdc2`/`e2f6716`；经 `git diff c164870..HEAD -- core evaluator scripts cli.py tests` 确认**代码零变更**，本次为全量独立复核，未沿用既往结论文本）

## 审查概览

- 审查目标：`professional-main` 全仓库（60 个 Python 文件）
- 审查范围：全量（非 diff）
- 技术栈：Python 3（apk 静态审计流水线，规则引擎 + 双通道 + 融合报告）
- 总体评分：**8 / 10**
- 合并建议：✅ 可签署（签署动作由人执行，AI ）

## 风险摘要

本轮无 Critical/Major 新增。AST 扫描 108 条（Minor 81 / Nit 27）与既有基线完全一致，均为二进制格式解析与融合逻辑的固有复杂度治理项（需按治理流程升版本重构，不在审查轮进行）。本轮重点成果：**配置 `.tools/JRE-17` 便携 JRE 后，真值复跑首次在本机完整执行，84/84 全一致（硬错 0），消除了前两轮「环境性缺源」的验证缺口**。

## 关键问题（Critical / Major）

未发现。

## 一般问题（Minor）

与既有基线一致（81 条，无新增），集中于：`cli.cmd_analyze`（209 行 / 圈复杂度 36）、`core/axml.py`、`core/adapters.py`、`fusion.build_conclusions` 等格式解析固有复杂度。沿袭遗留治理待办（见审查模型表），按治理流程单独排期，本轮不修。

## 优化建议（Nit）

27 条魔法数字/待办标记类 Nit，与既有基线一致，无新增。

## 五维深审要点（本轮独立复读代码核实）

1. **正确性**：`fusion.py:188-208` 未发现档两态区分正确（`executed = rule_id in hits_by_rule`，notes 分别为「已执行未命中」与「规则未执行，不得视为通过」）；B1「上下文无害」降级 `min_status` 方向正确（fusion.py:205-207）；`_tolerant_json`（channel_b.py:276-284）孤立键正则仅匹配 `}` 不碰 `]`，字符串数组保真；B2 verdict 白名单校验兜底为「无法判断」。未发现新增逻辑缺陷。
2. **安全性**：全仓 `shell=True` / `eval(` / `pickle` / `yaml.load` / `os.system` 命中为 0；`key.txt` 未被 git 追踪，key 解析 `split(',', 2)` + 捕获 `OSError/UnicodeDecodeError`（channel_b.py:45-48、llm.py:25-28 两处一致）；B1/B2/B3 均 `<sample_data>` 数据边界 + `_INJECTION_RE` 检测 + `injection_flag` 落盘（channel_b.py:103-144、summary.py:64）；safezip 按中央目录声明体积预检（safezip.py:22-33），channel_a.py:82 / dexscan.py:151 全部走 `read_member`；AXML 深度上限 MAX_XML_DEPTH → AXMLParseError（axml.py:293-294）。未发现安全问题。
3. **性能**：预算熔断与截断上限齐备；B 通道连通性探测单独记账 `probe_calls`（channel_b.py:168-174）；无 N+1 或无谓 IO。未发现问题。
4. **可维护性**：70/70 单测全过（0.9s）；`mkdtemp` 演练目录由 `cli.py reset` 统一清理。超长函数/深嵌套为固有复杂度，沿袭治理待办。
5. **架构**：分层清晰（规则注册表 / 通道 A / 通道 B / 融合 / 报告 / 评价器），依赖方向单向，无循环依赖；evidence 旁车落盘完整响应。

## 既往修复验证（本轮逐项复核，全部在位）

| 修复项 | 验证位置 | 结论 |
|--------|----------|------|
| C-1 未发现档两态（已执行未命中 vs 未执行） | `core/fusion.py:195-208` | ✅ 在位 |
| C-2 run_id 同秒防撞（样本指纹 sha[:8]） | `cli.py:41-43` | ✅ 在位 |
| AXML 深度上限 | `core/axml.py:244,293-294` | ✅ 在位 |
| zip bomb 声明体积预检 | `core/safezip.py:22-33` + `channel_a.py:82` / `dexscan.py:151` | ✅ 在位 |
| T1 decode_failed 语义 | `cli.py:107,114` | ✅ 在位 |
| B 通道注入防御（数据边界 + 正则 + 落盘） | `core/channel_b.py:103-144,184,213,223,238` | ✅ 在位 |
| B3 数据边界（第三次审查 M-5） | `core/summary.py:60-64` | ✅ 在位 |
| key 解析容错（两模块一致） | `core/channel_b.py:45-48` / `evaluator/llm.py:25-28` | ✅ 在位 |
| B 探测记账 probe_calls | `core/channel_b.py:168-174` | ✅ 在位 |

## 真值复跑（本轮首次完整执行 ✅）

- **环境变更**：本轮在项目 `.tools/JRE-17/` 配置 Temurin JRE 17.0.21.1（`_probe_java` 优先查找 `.tools/JRE*/bin/java.exe`，`.gitignore` 已加 `.tools/JRE*/` 忽略规则，JRE 不入库）。`probe_toolchain` 识别 java + apktool_3.0.3.jar 成功。
- **结果**：`python scripts/truth_check.py --no-evidence --out <临时路径>` 复跑 6 样本 × 14 判点：**84 点 · 一致 84 · 硬错 0（FP 0 / 漏检 0 / 档位错 0）· 噪声 0 · 未标定 0**。
- **纪律**：本轮按遗留待办第 6 条的教训，`--out` 显式指向临时路径，`review/truth_result.json` 正本未被触碰；`--no-evidence` 演练模式，evidence/ 零写入。

## 遗留治理待办（沿袭前轮，本轮复核确认仍在，按治理流程单独排期）

1. B1 循环体 `RULE_META[rule_id]` / `_hits_with_context` 位于降级 try 之外（实际崩溃路径极窄）——加固建议；
2. `advance('DONE')`（cli.py:227）在 `build_report_json`（cli.py:180）之后，状态与产物顺序不一致（仅 meta 状态字段观感）；
3. R-MAN-03 特例声明化、`sources_note` 按组汇总口径、key 解析两模块抽公共 `_client`（需 bump 版本 + 同步总档）；
4. `networkSecurityConfig` 正则只匹配双引号写法（低危）；safezip 无跨成员累计上限；
5. `cli.cmd_analyze` 拆分（209 行 / 圈复杂度 36）——非缺陷，重构风险高于收益，单独排期；
6. `truth_check.py` 默认 `--out` 指向正本路径的流程风险（本轮已按规避方式执行，建议改为默认临时路径）。

## 本轮非代码改进（环境项，非审查发现）

- `.gitignore` 新增 `.tools/JRE*/`、`.tools/_jre_tmp/` 忽略规则（便携 JRE 属本机工具，与 `.tools/framework/` 同理不入库）。
