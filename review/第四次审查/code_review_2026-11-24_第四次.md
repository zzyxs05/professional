# 代码审查报告 · 第四次审查

> 审查模型：MiMo-V2.6-Pro + code-review-analyzer v1.2.4（AST 扫描 + 安全清单 + 五维深审）
> 审查时间：2026-11-24 12:05—12:35
> 审查基线：`b83f986`（审查前 fetch origin/main 无新提交，朋友侧无代码更新；代码自 `e2f6716`/`c164870` 零变更，本次为全量独立复核，未沿用既往结论文本）

## 审查概览

- 审查目标：`professional-main` 全仓库（60 个 Python 文件）
- 审查范围：全量（非 diff）
- 技术栈：Python 3（apk 静态审计流水线，规则引擎 + 双通道 + 融合报告 + 评价 Agent）
- 总体评分：**8 / 10**
- 合并建议：✅ 可签署（签署动作由人执行，AI 不代签）

## 风险摘要

本轮新增发现 1 项 Major（U1：评价器 run_id 未校验即参与路径拼接，存在路径穿越写入/读取风险），已当场修复并补回归测试。其余与既有基线一致：AST 扫描 108 条（Minor 81 / Nit 27）无新增，安全清单全过，真值复跑 84/84，单测 72/72（含新增 2 项回归）。无 Critical。

## 关键问题（Critical / Major）

### [U1] 评价器 run_id 未校验即拼接路径，可路径穿越 — 🟠 Major（已修复）

- 位置：`core/evidence.py:52`（EvidenceStore）、`evaluator/tools.py:52`（RestrictedTools.run_dir）、`evaluator/agent.py:64`（evaluate_run）
- 问题：三处均以 `os.path.join(root, run_id)` 直接拼接用户可控的 `run_id`（`cli.py evaluate --run` 参数、API 调用方传入），未做格式校验。传入 `../..`、绝对路径或含分隔符的 run_id 时，RUN 目录会落到 `evidence/` 之外：`EvidenceStore` 可在任意位置创建目录并写入 hits.jsonl/raw 证据；`RestrictedTools.read_evidence(evidence_id=...)` 绕过 `_safe_path` 白名单，读取穿越后目录下的 JSONL。评价 Agent 的「路径白名单由程序强制」边界被这条路径绕过。
- 修复建议：已在三处入口统一调用 `core.evidence.check_run_id()`（白名单正则 `^RUN-[A-Za-z0-9][A-Za-z0-9_-]*$`，拒绝 `..`、路径分隔符、绝对路径），不合法抛 `BadRunId`（`ValueError` 子类）；`cli.py cmd_evaluate` 捕获后友好报错退出 2。回归测试 2 项（`tests/test_evidence_store.py::test_path_traversal_run_id_rejected`、`tests/test_eval_agent.py::test_run_id_traversal_rejected_in_tools`）钉住该行为。

## 一般问题（Minor）

与既有基线一致（81 条，无新增），集中于：`cli.cmd_analyze`（209 行 / 圈复杂度 36）、`core/axml.py`、`core/adapters.py`、`fusion.build_conclusions` 等格式解析固有复杂度。沿袭遗留治理待办（见审查模型表），按治理流程单独排期，本轮不修。

## 优化建议（Nit）

27 条魔法数字/待办标记类 Nit，与既有基线一致，无新增。

## 五维深审要点（本轮独立复读代码核实）

1. **正确性**：`fusion.py:195-211` 未发现档两态区分正确（`executed = rule_id in hits_by_rule`）；B1「上下文无害」降级 `min_status` 方向正确（fusion.py:224-231）；`_tolerant_json`（channel_b.py:276-284）孤立键正则仅匹配 `}` 不碰 `]`；B2 verdict 白名单校验兜底「无法判断」（channel_b.py:288-295）。`_chat` 三类可恢复错误（429/5xx、HTTPException、OSError）退避重试齐备（channel_b.py:68-92）。未发现新增逻辑缺陷（U1 属边界校验缺口，已修）。
2. **安全性**：全仓 `shell=True` / `eval(` / `pickle` / `yaml.load` / `os.system` 命中 0（subprocess 全部列表参数、无 shell）；`key.txt` 未入 git；key 解析 `split(',', 2)` + `OSError/UnicodeDecodeError` 双模块一致（channel_b.py:40-50、llm.py:20-31）；B1/B2/B3 数据边界 + `_INJECTION_RE` 降级抑制 + `injection_flag` 落盘齐备（channel_b.py:100-144,188-238、summary.py:64）；safezip 声明体积预检（safezip.py）+ MAX_XML_DEPTH（axml.py）；评价器路径白名单 `_safe_path` 强制（tools.py:58-77）+ **本轮补上 run_id 入口校验（U1）**。未发现其他安全问题。
3. **性能**：预算熔断、`probe_calls` 记账、截断上限齐备；无 N+1 或无谓 IO。
4. **可维护性**：72/72 单测全过（0.2s，含 U1 回归 2 项）；超长函数为格式解析固有复杂度，沿袭治理待办。
5. **架构**：分层清晰（规则注册表 / 通道 A / 通道 B / 融合 / 报告 / 评价器），依赖单向（evaluator → core，core 不依赖 evaluator），无循环依赖。

## 既往修复验证（9 项逐项复核，全部在位）

| 修复项 | 验证位置 | 结论 |
|--------|----------|------|
| C-1 未发现档两态（已执行未命中 vs 未执行） | `core/fusion.py:195-211` | ✅ 在位 |
| C-2 run_id 同秒防撞（样本指纹 sha[:8]） | `cli.py:40-43` | ✅ 在位 |
| AXML 深度上限 | `core/axml.py`（MAX_XML_DEPTH → AXMLParseError） | ✅ 在位 |
| zip bomb 声明体积预检 | `core/safezip.py` + `channel_a.py` / `dexscan.py` 走 `read_member` | ✅ 在位 |
| T1 decode_failed 语义 | `cli.py`（`not decode.ok`） | ✅ 在位 |
| B 通道注入防御（数据边界 + 正则 + 落盘） | `core/channel_b.py:100-144,188-238` | ✅ 在位 |
| B3 数据边界（M-5 / T4） | `core/summary.py:64` | ✅ 在位 |
| key 解析容错（两模块一致） | `core/channel_b.py:45-48` / `evaluator/llm.py:25-28` | ✅ 在位 |
| B 探测记账 probe_calls | `core/channel_b.py:30,163-166` | ✅ 在位 |

## 真值复跑

- **审查中复跑**：`python scripts/truth_check.py --no-evidence --out <临时路径>`：**84 点 · 一致 84 · 硬错 0（FP 0 / 漏检 0 / 档位错 0）· 噪声 0 · 未标定 0**。
- **U1 修复后回归复跑**：同样 `--out` 显式临时路径，结果见「修复记录」小节；`review/truth_result.json` 正本未被触碰。
- **纪律**：沿袭遗留待办第 6 条教训，`--out` 始终显式指向临时路径；`--no-evidence` 演练模式 evidence/ 零写入。

## 遗留治理待办（沿袭前轮 6 条，本轮复核确认仍在，按治理流程单独排期）

1. B1 循环体 `RULE_META[rule_id]` / `_hits_with_context` 位于降级 try 之外（实际崩溃路径极窄）——加固建议；
2. `advance('DONE')`（cli.py:227）在 `build_report_json`（cli.py:180）之后，状态与产物顺序不一致（仅 meta 状态字段观感）；
3. R-MAN-03 特例声明化、`sources_note` 按组汇总口径、key 解析两模块抽公共 `_client`（需 bump 版本 + 同步总档）；
4. `networkSecurityConfig` 正则只匹配双引号写法（低危）；safezip 无跨成员累计上限；
5. `cli.cmd_analyze` 拆分（209 行 / 圈复杂度 36）——非缺陷，重构风险高于收益，单独排期；
6. `truth_check.py` 默认 `--out` 指向正本路径的流程风险（本轮已按规避方式执行，建议改为默认临时路径）。

## 修复记录（本轮 U1）

详见 `docs/changes.md`「第四次审查修复」小节。变更性质：评价器边界加固，`RULE_PACK_VERSION` 不变（0.1.6）——不动规则、判罚口径与三档语义。

| # | 变更 | 暴露渠道 | 影响 |
|---|------|----------|------|
| U1 | **run_id 入口校验**（`core/evidence.py` 新增 `check_run_id`/`BadRunId`；`EvidenceStore.__init__`、`RestrictedTools.__init__`、`evaluate_run` 三处调用；`cli.py cmd_evaluate` 友好报错） | 第四次审查（MiMo-V2.6-Pro）：三处 `os.path.join(root, run_id)` 无校验，run_id 可路径穿越出 evidence/ 根 | 白名单正则 `^RUN-[A-Za-z0-9][A-Za-z0-9_-]*$`；合法 run_id（含历史 RUN-20261015-145536、RUN-20261124-121104-3356097a 等）行为不变 |
| U2 | **单测**：70 → 72（新增穿越拒绝回归 2 项） | — | — |
