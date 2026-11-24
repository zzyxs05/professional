# 代码审查报告 · zhuan（APK 静态审计系统）· 第四次审查

> 性质：review ｜ 版本：v1.0 ｜ 状态：归档
> 职责：记录第四次独立全量复核的扫描结论、安全清单、既往修复复核与遗留待办；不沿用第三次报告文本。
> 关联：前次报告 `review/第三次审查/code_review_2026-11-24.md`；登记 `review/审查模型表.md`；修复明细 `docs/changes.md`。
> 签署：状态统一见 `docs/signoff.md`，本文不设独立签署栏。

## 审查概览

- 审查目标：`D:/专业能力提升/professional-main`（全仓库）
- 审查范围：全量（60 个 Python 文件；不含 `.git`、`.workbuddy`、`.tools`、`evidence/`）
- 技术栈：Python 3（标准库为主，无第三方运行时依赖）；自研 AXML 解析器 + 自研 DEX 解析器 + apktool 子进程 + OpenAI 兼容 HTTP 客户端
- 审查方式：AST 静态扫描 + 安全检查清单逐项核查 + 五维度人工深审 + 既往修复逐项复核 + 单测/真值回归
- 审查模型：MiMo-V2.6-Pro（code-review-analyzer v1.2.4）
- 总体结论：**0 Critical / 0 Major**，无新增需修复项
- 总体评分：**8 / 10**（无 Critical/Major；扣分项为遗留治理待办与真值回归的环境受限）
- 合并建议：**✅ 可签署**（遗留治理待办沿袭前轮记录，按流程单独排期，不构成签署阻碍）

## 脚本扫描结论（analyze.py · AST 版）

- 分析文件数 60，发现问题 108：**Minor 81、Nit 27，无 Critical/Major**。与第 3 次审查基线完全一致（第 3 次提交 `c164870` 之后工作区无代码变更，本轮为独立复核）。
- Minor 集中为超长函数 / 高圈复杂度 / 过深嵌套：`cli.cmd_analyze`（209 行 / 圈复杂度 36）、`core/axml.py`（parse_axml / _build_tree / extract_manifest_facts）、`core/adapters.py`、`fusion.build_conclusions`、`evaluator/agent._mechanical_verdict` 等——均为二进制格式解析与融合逻辑的固有复杂度，与第 1/2/3 次审查结论一致；按 AGENTS.md 纪律「改规则就是改版本」，重构需 bump `RULE_PACK_VERSION` + 记 `docs/changes.md` + 重跑 84 判点，不在审查轮进行。
- Nit 为魔法数字（DEX 结构体字段宽度、截断上限等）与 2 处设计内 TODO（`cli.py:261` 登记模板占位符、`scripts/truth_check.py:38` truth 缺省兜底，前轮已核实为设计内）。
- 无硬编码密钥、无 SQL 注入、无命令注入、无不安全反序列化；未使用导入清零。

## 安全检查清单（逐项核查，全部通过）

| 类别 | 核查结果 |
|------|----------|
| 注入类 | 无 SQL（无数据库）；apktool / java 子进程均为参数列表式调用（`core/adapters.py:128`、`core/runner.py:80`），全仓 `shell=True` / `os.system` / `eval(` 命中数为 0 |
| 敏感信息 | `key.txt` 在 `.gitignore` 且 `git ls-files` 确认未被追踪；key 解析 `split(',', 2)` + `UnicodeDecodeError` 捕获（`channel_b.py:45-48`、`evaluator/llm.py:25-28`）；密钥不进日志 |
| 反序列化 | 无 pickle / yaml.load；模型响应经 `_tolerant_json` + `json.JSONDecoder().raw_decode` 严格解析 |
| 文件与路径 | 证据落盘使用 `run_id`（`RUN-` + 时间戳 + sha[:8]，字符集安全）+ 固定文件名，无用户可控路径拼接 |
| 资源与可用性 | safezip 按中央目录声明体积预检 + `MAX_XML_DEPTH` 深度上限（`core/axml.py:244,293`）；敏感区扫描 80 文件/前 15 条截断（`channel_b.py:379,389`）；LLM 预算熔断 `BUDGET_MAX_LLM_CALLS_PER_RUN = 30`（`core/registry.py:351`） |

## 既往修复复核（逐项验证在位，全部 ✅）

| 修复项 | 验证位置 | 结论 |
|--------|----------|------|
| C-1 结论区丢失「已检查未命中」判点 | `core/fusion.py:190-210`（未发现档区分「已执行未命中」与「规则未执行」，`missing_evidence` 如实标注） | ✅ 在位 |
| C-2 run_id 同秒冲突、证据覆盖 | `cli.py:43` run_id 带样本指纹 sha[:8] | ✅ 在位 |
| AXML 深度上限（防 RecursionError 击穿） | `core/axml.py:244,293`（`MAX_XML_DEPTH` → `AXMLParseError`） | ✅ 在位 |
| zip bomb 防御 | `core/safezip.py:22` `read_member` 声明体积上限；`channel_a.py`、`dexscan.py` 全部经其读取 | ✅ 在位 |
| T1 覆盖声明语义失真 | `cli.py:107` `decode_failed = not decode.ok` | ✅ 在位 |
| T2 超时/连接失败纳入退避重试 | `core/channel_b.py:68-94`（HTTPError 429/5xx / HTTPException / OSError 三面重试，耗尽 `raise RuntimeError`） | ✅ 在位 |
| T3 key.txt 解析加固 | `channel_b.py:45-48` 与 `evaluator/llm.py:25-28` 同步 | ✅ 在位 |
| T4 B3 数据边界 | `core/summary.py:64,256`（`_DATA_BOUNDARY` + `<sample_data>` 包裹） | ✅ 在位 |
| T5 safezip 测试固化 | `tests/test_safezip.py` | ✅ 在位 |
| B 通道注入防御 | `channel_b.py:135` `_INJECTION_RE` + 降级方向设防（命中指令性文本不采信「上下文无害」，`channel_b.py:191-197`）+ `injection_flag` 落盘 | ✅ 在位 |
| `_tolerant_json` 孤立键正则 | `channel_b.py:284` 仅匹配对象闭合 `}`，不碰 `]`（字符串数组尾元素保真） | ✅ 在位 |
| 单规则异常隔离（含导入期） | `core/channel_a.py:126-131` `importlib.import_module` 纳入降级 try，异常记为未判定不阻断其余规则 | ✅ 在位 |

## 五维深审要点

1. **正确性**：fusion 未发现档两态区分（「已执行未命中」≠「规则未执行」）语义正确；`substantive_conclusions`（`core/summary.py:41`）为干净样本判定唯一判据，输入组装与模板渲染共用；通道 A/B 失败路径均如实降级并归因。逻辑闭环正确，未发现新增逻辑缺陷。
2. **安全性**：见上表，未发现安全问题。
3. **性能**：预算熔断与截断上限齐备；`SmaliFacts.read_lines` 有内存缓存；无 N+1 查询或无谓 IO。
4. **可维护性**：单测 70/70 全过；`cli.py reset` 可统一清理演练临时目录。超长函数/深嵌套为固有复杂度，沿袭前轮结论不在本轮重构。
5. **架构**：分层清晰（规则注册表 / 通道 A / 通道 B / 融合 / 报告 / 评价器），依赖方向单向，无循环依赖；evidence 层 `raw_response` 旁车文件落盘完整响应，`channel_b/records.jsonl` 按通道分文件落盘供 precheck 读取。

## 回归验证

- **单测**：70/70 全过（`python -m unittest discover -s tests`）。
- **真值重跑**：本审查环境无 java（`java: command not found`，`.tools/JRE`、`JAVA_HOME`、`PATH` 均无）→ apktool 解码不可用 → 依赖 smali/res 数据源的规则无法执行 → 无法复现 84/84。该结果为**环境性缺源，非代码回归**：历史 84/84 由具备 java 的环境产出（第 1/2 次审查记录），70/70 单测（不依赖 java）全过。**签署前需在含 java 的环境复跑 `python scripts/truth_check.py --no-evidence` 确认 84/84**。
- **过程纪律（如实记录）**：本轮曾执行 `truth_check.py --no-run` 尝试复算，其读取的最近 evidence RUN 报告为 2026-10-15 历史存量（早于当前规则包口径），结果不具验证效力；且脚本默认 `--out review/truth_result.json` 再次覆盖正本，已从 git 恢复——与第 3 次同一踩坑点，佐证遗留待办中「truth_check 默认写出路径」的流程风险确实存在。

## 遗留治理待办（沿袭前轮，不因本轮消失，需按治理流程处理）

1. B1 循环体 `RULE_META[rule_id]` / `_hits_with_context` 位于降级 try 之外（`channel_b.py:178-179`，实际崩溃路径极窄：rule_id 均来自 RULES_PIPELINE，`read_lines` 已捕获 IO 异常）——加固建议；
2. `advance('DONE')` 在 `build_report_json` 之后（`cli.py:227` vs `cli.py:180`），状态与产物顺序不一致（仅 meta 状态字段观感）；
3. R-MAN-03 特例声明化、`sources_note` 按组汇总口径、key 解析两模块抽公共 `_client`（需 bump 版本 + 同步总档）；
4. `networkSecurityConfig` 正则只匹配双引号写法（apktool 输出恒为双引号，低危）；safezip 无跨成员累计上限；
5. `cli.cmd_analyze` 拆分（209 行 / 圈复杂度 36）——非缺陷，重构风险高于收益，单独排期。
6. `truth_check.py` 默认 `--out` 直接覆盖 `review/truth_result.json` 正本（第 3、4 次审查均因此踩坑后从 git 恢复）——建议默认写临时路径或要求显式 `--out`，属流程加固项。

## 备注

- 修复明细：`docs/changes.md`（R1—R13、T1—T5）。
- 审查模型表：`review/审查模型表.md`（本报告已登记为第 4 次）。
- 本轮为独立全量复核：AST 扫描重跑、单测重跑、安全清单逐项重查、既往修复逐项重验，未沿用第 3 次结论文本。

---

*本报告由代码审查与架构分析助手（code-review-analyzer v1.2.4，模型 MiMo-V2.6-Pro）生成。所有结论均基于代码阅读、AST 扫描与可复现验证；不改变任何审计结论。*
