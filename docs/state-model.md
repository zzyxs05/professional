# state-model · 状态机与构成【design】

> 关联：`core/runner.py`、`specification.md` §3

## 1. 运行状态机（一次 analyze）

```
PENDING → DECODING → RULE_A → CHANNEL_B → FUSION → REPORT → DONE
                                              ↘ FAILED（任意步骤未捕获异常）
```

- 状态序列写入 `evidence/RUN-*/meta.json` 的 `state.history`（含每步附注）；
- 解码失败**不是**运行失败：`DECODING` 步骤照常推进，降级信息进覆盖声明；
- 样本级失败（manifest 直读失败）：全部规则输出「无法判定」+ `coverage.decode_failed=true`。

## 2. 结论状态与证据层级

| 概念 | 取值 | 约束 |
|------|------|------|
| 结论档位 | 已确认 / 待复核 / 无法判定 | 受规则档位上限约束（ADR-0003）；融合层不得越权 |
| 结论通道 | A / B / fusion | B 单独结论天花板=待复核；fusion=经钉证据或复核 |
| 证据层级 | STATIC（本项目上限） | 只读不执行；报告不得暗示动态验证 |
| 证据来源 | target_claim / static_inspection / b_channel / b_channel_pin | 来源与层级分开记录 |
| 签署状态 | pending → signed / rejected | 未签署报告不生效 |

## 3. 预算与熔断

- LLM 交互：≤30 次/run（2026-10-14 调整，见 `changes.md` B1；B1 复核按命中规则数消耗、B2 一次）；
  耗尽列未完成项，不填充无证据文字；
- 注册补测：≤5 次（评价器工具 `request_registered_test`）；
- 解码超时 300s；子进程仅白名单 java。

## 4. 权限边界（评价器）

- 只有四个受限工具：`get_approved_contract` / `list_evidence` / `read_evidence` /
  `request_registered_test`；
- **不提供任意 Shell / 任意 URL —— 是权限边界，不是 Prompt 禁令**；
- 评价进程与目标仓库隔离（只读 evidence 与契约，不继承产品执行能力）；
- 文本防护不替代权限防护；教师保留测试不交给学生 Agent；Hash 证明完整性不证明真实性。
