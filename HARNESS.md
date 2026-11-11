# HARNESS.md · 项目级开发 Harness（工程约定收拢）

> 交付类：design（工程治理）｜版本：v1.0｜状态：已提交，复核栏见 §8
> 定位：把项目里**已经存在、但分散**在 `总档.md`、`AGENTS.md`、`docs/` 与各模块实现中的开发约定，收拢成一份可核查的规范索引。
> **本文件不新增契约、不改判罚口径、不放宽任何规则、不产生新结论**；与既有文档冲突时以 `总档.md` 为准，并回改本文件。
> 依据：`总档.md` §0/§2.8/§7/§10、`AGENTS.md`、`docs/ai-disclosure.md`、`docs/changes.md`、`docs/state-model.md`、`core/registry.py`、`core/runner.py`。

---

## 0. 这份文件回答什么

项目治理要求的六类工程约定，此前分散在总纲、入口指针与各模块实现中，缺少一份统一的可核查入口。本文件按「开发规范 / AI 操作约定 / 代码规范 / 文档规范 / 日志规范 / 观测性约定」逐节给出**约定 + 落地位置 + 核查方式**。

一句话边界：**收拢不等于新造，提交不等于签署。** 涉及契约与决策的条目，仍以 `docs/decision-log.md`、`docs/signoff.md` 的签署状态为准；本规范自提交起用于约束后续工作。

---

## 1. 项目开发规范

### 1.1 环境与入口

| 项 | 约定 | 落地位置 |
|----|------|----------|
| 运行时 | Python 3.8+，**零第三方依赖**（标准库实现 HTTP 调用） | `docs/requirements.md` REQ-15、`docs/release.md` §1 |
| 可选工具链 | Java 8+；`.tools/apktool_3.0.3.jar` 随仓库入库，查找顺序：`.tools/` → 环境变量 → PATH | `总档.md` §10、`core/adapters.py` |
| 唯一入口 | `cli.py`：`analyze` / `register` / `evaluate` / `summary` / `reset` | `cli.py`、`总档.md` §6.1 |
| 子进程 | 白名单仅 `java`（apktool），名单外一律拒绝 | `core/runner.py`、`registry.SUBPROCESS_ALLOWED_BINARIES` |
| 数据边界 | 对被测 APK 只读、不执行、不联网；模型调用是唯一外部网络出口，缺失即降级 | `总档.md` §10、§6.6 |

### 1.2 目录职责（不许混用）

| 目录 | 存什么 | 不许做什么 |
|------|--------|------------|
| `evidence/RUN-*/` | **运行事实正本**：meta / hits / 报告 / 评价器输出 | 不改写已签署 RUN；不写实验性运行 |
| `review/` | 对事实的解释、复核底稿、成绩单、挑战包 | 不把解释写成运行事实 |
| `docs/` | 需求、规格、ADR、决策索引、实验卡、变更记录 | 不复制总纲正文 |
| `lab/` | 自建样本、真值表、sha256 | 不放真实第三方应用与凭据 |
| `handoff/` | 干净环境复现说明 | 不代对抗组跑结论 |

### 1.3 变更流程（硬）

1. 改规则/阈值/schema → bump `RULE_PACK_VERSION` → 记 `docs/changes.md` → 重跑 `scripts/truth_check.py`（84 判点）；
2. 改结构/接口/目录 → 同步 `总档.md` 并升其版本号 → 记 `docs/changes.md`；
3. 改 UN/REQ → 同步 `docs/specification.md`、`docs/acceptance-matrix.md`，评估已有证据是否仍成立；
4. 历史报告保留原有解释，**不被新规则悄悄改写**；旧证据不判新版本。

### 1.4 禁止事项

为通过检查而放宽契约、改判罚口径、删减规则；把对话里的口头决定当已批准契约；把真实样本/密钥/模型凭据写入仓库（`key.txt` 已在 `.gitignore`）；在 `evidence/` 写试错数据（用 `--no-evidence`）。

### 1.5 自动化脚本配置

| 脚本 | 作用 | 主要参数 | 产物 | 退出码 |
|------|------|----------|------|--------|
| `cli.py` | 唯一入口：`analyze` / `register` / `evaluate` / `summary` / `reset` | `analyze --out / --no-evidence / --force-decode`；`summary --no-llm`；`evaluate --llm` | `evidence/RUN-*/` 或临时区 | 0 / 1 / 2 |
| `scripts/truth_check.py` | 靶场 84 判点一致性 | `--no-run`、`--no-evidence`、`--only`、`--out` | `review/truth_result.json` | 0 / 1 |
| `scripts/e2e.py` | A-01 / A-09 端到端验收 | `--no-evidence` | 控制台 + 临时区 | 0 / 1 |
| `scripts/b_stability.py` | B 通道稳定性（固定样本 × N 轮） | `--sample`、`--runs`、`--rules`、`--no-b2` | `review/b_stability_*.json` | 0 / 2 |
| `scripts/exp_datasource_ab.py` | 数据源实现 A/B 对照（EXP-6） | `--runs`、`--samples`、`--out` | `review/exp_datasource_ab.json` | 0 |

约定：

1. 脚本默认参数即实验/质量门的固定条件，改动默认值等于改口径，须记 `docs/changes.md` 并复算；
2. 实验性运行一律 `--no-evidence`，脚本只写 `review/` 或工作区外临时区，**不写 `evidence/`**；
3. 统计类输出 JSON 必须带生成时间、规则包版本、输入指纹与逐轮明细，供第三方复算；
4. 新增脚本同步更新本表、`AGENTS.md` 常用命令与 `docs/experiment-protocol.md`（若属对照实验）；
5. 退出码非 0 时保留原始输出，不将失败轮次改写成「通过」。

---

## 2. AI 操作约定

| 环节 | 允许 | 禁止 |
|------|------|------|
| 分析链路 | 仅通道 B（B1 复核 / B2 提疑）与评价器判读 | 不得直接产出「已确认」；升级必须经 `pin_evidence` 机械核对（ADR-0004） |
| 执行能力 | 分析进程不执行样本；评价器只用四个受限工具 | 不提供任意 Shell / 任意 URL（权限防护，不是提示词禁令） |
| 文档与代码 | 起草、检索、整理、复算 | 不得代签、不得改写 `evidence/`、不得把口头决定写成契约 |
| 调研 | AI 铺开候选；人逐条打开原始页面核对 | 数字、排名、「最优/最流行」类断言无原始来源一律删 |

- **人机责任四分**：决定 / 生成 / 检查 / 停止逐环节具名，见 `docs/ai-disclosure.md` §1；被拒绝的 AI 建议逐条记录（同文件 §3、§4）。
- **新会话工作流**：读 `AGENTS.md` → 读 `总档.md` → 核对 §7 目录与代码实际差异 → 从 §9 找当前阶段 → 动手前先核证据。
- **结论措辞**：静态疑点只断言结构，不断言行为；没拿到证据写「无法判定」，不写「通过」；未覆盖就声明未覆盖。
- **待复核态**：所有产物在签署前为 `human_signoff: pending`；模型不替代人的判断。

---

## 3. 代码规范（现状约定，从已入库实现归纳）

> 以下不是新增强制 lint 规则，而是对 `core/` 与 `evaluator/` 现有风格的描述；新增代码保持一致即可。

| 项 | 约定 |
|----|------|
| 文件头 | `# -*- coding: utf-8 -*-` + 模块 docstring（说明职责与依据文档） |
| 格式 | 4 空格缩进；函数/变量 `snake_case`；异常类 `PascalCase`；不强制类型标注（保持 Python 3.8 兼容） |
| 常量 | 规则表、阈值、白名单、预算、版本**集中**在 `core/registry.py`，模块内不散落魔法值；`UPPER_CASE` 命名 |
| 规则实现 | 一条规则一文件：`core/rules/<类>/r_<类>_<序号>.py`；统一输出命中三元组 `{rule_id, location, raw_snippet}` |
| 依赖 | 仅标准库；模型调用用标准库 HTTP，不引 SDK |
| 子进程 | 一律经 `Runner.run_subprocess` 走白名单，不直接 `subprocess.run` |
| 测试 | `unittest`，合成夹具放 `tests/fixtures/`，不依赖真实 APK；当前 46 用例（含 8 个 OBS-5 回归），`python -m unittest discover -s tests` |
| 质量门 | `scripts/truth_check.py`（84 判点）、`scripts/e2e.py`（A-01/A-09）；改规则后必须复跑 |

---

## 4. 文档规范

- **唯一总纲**：`总档.md`。其余文档只给锚点与链接，不复制正文；每类 1—2 页说明 + 3—5 个关键链接。
- **六类交付物**：brief / design / eval / evidence / release / review，映射见 `总档.md` §7 表；新增文件必须能挂到某一类。
- **ADR**：一决策一文件，含背景、被否替代方案（理由必须具体）、后果；索引进 `docs/decision-log.md`（决策 → ADR → 证据 → 决策人）。
- **状态标注**：复核未签字写「待签署」，不得写「已批准」；抽验动作 ≠ 签署动作；未发生的事件写「材料就绪」，不预填结果。
- **版本区分**：`总档` 文档版本 ≠ `RULE_PACK_VERSION` 规则包版本 ≠ B 通道 prompt 版本；报告绑定生成时的规则包与模型版本。
- **变更留痕**：`docs/changes.md` 记录规则/结构变更；实验数据进 `docs/experiments.md`，允许并保留负结果。
- **文档元数据**：新写文档头部标注项目名（APK 通用静态审计 / apkaudit）、文档版本与规则包版本；存量文档在下次实质修订时补齐，不批量倒填日期。
- **实验记录**：对照实验沿用 `docs/experiment-protocol.md` 的变量控制与计时口径，实验卡进 `docs/experiments.md`，真实运行数据落 `review/`；历史结果 JSON 不改写，口径变更须升协议版本并重跑。

---

## 5. 日志规范

> 事实口径：本项目**不引入 logging 框架，也不产生独立文本日志文件**（零第三方依赖 + 保持可复算）。运行可追溯性由结构化产物承担，不应事后补造日志。
> 路径口径：下表 `channel_a/`、`fusion/`、`report.md`、`report.json`、`evaluation.json`、`meta.json` 等均相对 `evidence/RUN-<id>/`；`review/`、`docs/` 相对仓库根。

| 层 | 落点 | 内容 |
|----|------|------|
| 运行事实 | `evidence/RUN-<id>/meta.json` | run_id、apk_sha256、rule_pack、channel_b_model、toolchain、decode、created、budget、state |
| 通道 A | `channel_a/hits.jsonl` | 逐命中：规则 ID、坐标、原文片段 |
| 通道 B | `channel_b/` | prompt 模板版本、模型标识、原始响应、输入片段哈希 |
| 融合 | `fusion/` | 分歧记录与钉证据过程 |
| 结论 | `report.md` / `report.json` | 同一事实本体的两种渲染 |
| 评价器 | `evaluation.json` | 四状态输出、范围、引用校验、缺口 |
| 解释与复核 | `review/` | 成绩单、复核底稿、挑战包、签署准备 |

- 控制台只输出进度与汇总（例：`[bad03] 14/14 一致`、`=== 汇总：84 点 · 一致 84 ===`），不承载结论正本；
- **实验性运行必须写临时区**：`cli.py analyze --no-evidence`，脚本透传 `--no-evidence`；试错数据不得进 `evidence/`（依据 `docs/changes.md` E1/E2）；
- 失败、超时、降级、预算耗尽一律可见：进 `coverage.not_checked` / `exhausted_notes` / 「无法判定」档，不静默跳过。

---

## 6. 观测性约定

> 字段口径：本节 `meta.json` / `report.json` / `evaluation.json` 均为 `evidence/RUN-*/` 下的产物（路径见 §5）；
> `review/truth_result.json` 相对仓库根。

| 可观测对象 | 字段 / 位置 | 判定口径 |
|------------|-------------|----------|
| 身份冻结 | `meta.json`: apk_sha256 + rule_pack + channel_b_model + toolchain | 五环：目标版本 ↔ Fixture ↔ 契约 ↔ 评价器 ↔ 证据来源 |
| 覆盖 | `report.json.coverage.checked / not_checked / decode_failed` | 「未发现」必须带覆盖声明 |
| 结论强度 | `conclusions[].status`（已确认 / 待复核 / 无法判定）、`channel`、`evidence_ids`、`location`、`human_signoff` | 三档不越规则 `max_status`；来源与层级分开标 |
| 定位 | `location`（smali 行 + 原始行 / manifest 行区间 / dex#str 索引）+ `raw_snippet` | 复核方按坐标直达原文，不需要重跑 |
| 预算与熔断 | `meta.json.budget`（LLM ≤30 次/run、注册补测 ≤5 次）、`exhausted_notes` | 耗尽列未完成项，不填充无证据文字 |
| 状态机 | `meta.json.state.history`（PENDING→…→DONE / FAILED） | 失败原因留痕 |
| 评价器 | `evaluation.json` 四状态 + 引用校验 | PASS 只代表引用/版本/结构通过，**不代表结论内容正确** |
| 质量门 | `review/truth_result.json`（84 判点，硬错 0 / 噪声 0） | 自评一致性，不是能力证明 |

**边界**：哈希证明完整性，不证明真实性；静态证据层级上限为 STATIC，报告不得暗示已完成动态验证；模型输出进入 `observations` 观察区，非结论、不计入三档。

---

## 7. 核查入口（给复核者）

1. 看 §1.1 环境 → 按 `handoff/README.md` 克隆即跑；
2. 抽查任一 RUN 的 `meta.json` ↔ `report.json` ↔ `channel_a/hits.jsonl`（均在 `evidence/RUN-<id>/` 下，见 §5）三处是否对得上；
3. 抽查 `docs/decision-log.md` 任一行 → ADR → 支撑证据文件是否真实存在；
4. 跑 `python scripts/truth_check.py --no-run` 与 `python -m unittest discover -s tests` 复算（本仓库实测：84/84、46 用例全过）。

---

## 8. 未闭环（如实列出，不因本文件而消失）

| 项 | 状态 | 位置 |
|----|------|------|
| 12 条关键决策复核签字 | 待签署 | `docs/decision-log.md` |
| 6 份报告本组签署 / 对抗组复核 / 教师复评 | pending | `docs/signoff.md` |
| E1 / E2 / E3 结对交互 | 材料就绪，交互未发生 | `docs/events.md` |
| 验证任务与角色轮换 | 待执行 | `docs/team-roster.md` |
| 模型横向评测（R-1） | 未做 | `docs/adr/0010-model-selection.md`、`docs/release.md` I-8 |
| 本文件与新增三件套的复核 | 待具名人登记；登记前不作为「已批准契约」 | `TASKS.md` T-M4-06 |

> 本文件为工程约定索引，不改变任何已有结论的签署状态；`human_signoff: pending` 的结论仍不生效。
