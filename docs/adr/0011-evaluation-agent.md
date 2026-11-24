# ADR-0011 · 评价 Agent 的实现形态：Python 受限多轮循环，不引入 DeepSeek Harness

> 性质：design ｜ 版本：v1.0 ｜ 状态：生效
> 职责：回答评价器为何重构成 Python 受限多轮循环、不引入 DeepSeek Harness；不规定评分数值与 Rubric 细节。
> 关联：依据 `总档.md` §2.6 / §8.3、`HARNESS.md` §1.5；实现 `evaluator/agent.py`、`evaluator/tools.py`；校准 `scripts/eval_calibrate.py`；变更 `docs/changes.md` S14—S22。
> 签署：状态统一见 `docs/signoff.md`，本文不设独立签署栏。

- 状态：已采纳（签署状态见 `docs/signoff.md`）
- 日期：2026-11-18
- 决策人：周宗正（起草）、余俊辉（复核）
- 关联：`总档.md` §2.6 / §8.3、`AGENTS.md`、`HARNESS.md` §1.5、`docs/changes.md` S14—S22

## 背景

课程要求每组交付独立的评价 Agent：先自评、再评对抗组项目；并说明可以使用
DeepSeek Harness（DSH，2026-08 开源的插件化 agent 运行时，Node.js/TypeScript，
Trajectory append-only 会话日志、沙箱、多种 preset）。

仓库原有的 `evaluator/` 是一次性确定性检查脚本 + 一句模型文本建议，四个受限工具
定义了但从未被任何代码调用，不构成 Agent。

## 决策

**以现有 `evaluator/` 为内核重构成 Python 标准库的多轮 Agent，不引入 DSH。**

1. 模型用项目默认 `key.txt` 配置的 OpenAI 兼容端点（`evaluator/llm.py:chat`），支持多轮消息；
2. 模型每轮输出一个结构化工具调用，由 `AgentLoop` 解析并分派到四个受限工具
   （`get_approved_contract` / `list_evidence` / `read_evidence` / `request_registered_test`）；
   工具白名单与路径白名单由程序强制，不提供任意 Shell / URL；
3. 原确定性预检 `precheck.py` 降级为注册测试 `verify_claims`，成为 Agent 可调用的机械核对工具；
4. 判定由机械结果给出：`status` 由程序依据预检结果与 rubric 判定条件给出，
   模型输出只进 `observations` / `suggested_checks`（ADR-0004、总档 §2.6）；
5. 每次工具调用写 append-only 轨迹 JSONL 到 `review/evaluation/`，预算
   ≤10 次模型交互 / ≤5 次注册补测 / 8—12 个审查项；
6. 目标参数化：`--target` + `--mode self|peer`；批准契约外置，互评不得套用本仓库规则；
7. 输出按课件 Schema：`criterion_id / status / evidence_level / evidence_ids / finding /
   scope / missing_evidence / suggested_check / score_suggestion: null / human_signoff: pending`。

## 理由

- **权限冲突**：总档 §2.6 要求「不提供任意 Shell / 任意 URL，**而不是用 Prompt 禁止**」。
  DSH Standard 默认带文件编辑、shell 与网络；裁剪到合规需要写 TypeScript 插件与自定义 preset。
- **契约冲突**：REQ-15「零第三方运行时依赖（仅标准库）」是冻结需求；DSH 需 Node 22+ 与 npm 依赖树，
  会连带改 ADR-0002 / ADR-0007 与需求层。
- **隔离更难**：自评与互评要按目标加载不同批准契约，塞进同一通用运行时更容易串味；
  本方案用 `contract.py` 在数据层隔离。
- **已有骨架**：确定性预检、四状态、注册补测白名单、K-1~K-6 校准判例都在，属于「补」不是「重做」。
- **可复现**：评价器随仓库入库、零外部依赖、轨迹与结果成对存盘，对抗组可独立复跑。

## 后果

- 正面：真 Agent（自主选工具、多轮、停止条件、轨迹）、模型可降级、判定不受模型措辞影响、
  自评与互评共用一套审查器但契约隔离。
- 负面：没有现成的 Trajectory UI，会话回放靠 JSONL；模型停止依赖预算与收尾提示，
  换模型需重新校准 K-1~K-6。
- 反面约束：模型不得直接给四状态、不得算分、不得改目标仓库；
  `rerun_analyze` 在受控 runner 未接入时如实返回未执行并维持 STATIC 层级。

## 替代方案（被否）

- **用 DSH Standard 重写评价器**：权限面与零依赖契约冲突，裁剪成本 > 收益；否。
- **保留一次性确定性脚本，仅加一次 LLM 调用**：无工具编排、无轨迹、无自主性，不算 Agent；否。
- **让模型直接输出四状态与分数**：违反 ADR-0004 与「最终成绩只在教师层」；否。
- **把 DSH 当观测壳**：可作为后续可选项（仅 Minimal preset + 自定义受限工具插件），
  但需单独评估 Node 环境与安装成本；本轮不引入。

## 校准与验证

`scripts/eval_calibrate.py` 跑 K-1~K-6 → 6/6；`tests/test_eval_agent.py` 7 例 +
全库 53 例全过；6 个 RUN 自评产物与轨迹成对落 `review/evaluation/`。
模型主样本自评暴露「历史正本 0.1.3 / 当前契约 0.1.4」版本错配，已按
「旧证据不判新版本」输出 `INSUFFICIENT_EVIDENCE` 与最小补查，不掩盖。
