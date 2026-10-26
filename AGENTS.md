# AGENTS.md · 给 AI 协作者的入口指针

> 本文件只做导航，不重复总纲。任何规则冲突，以 `总档.md` 为准。

## 先读什么

1. `总档.md` —— 唯一总纲：做什么、课程硬性要求、系统怎么运转、目录职责、当前进度。
2. `docs/requirements.md` —— 需求层（谁、什么场景、系统要保证什么）。
3. `docs/specification.md` —— 规格层（数据源、14 条规则契约、报告 schema、定位格式）。
4. `docs/decision-log.md` —— 关键决策索引（决策 → ADR → 证据 → 决策人）。
5. `docs/research/apk-audit-landscape.md` —— 领域调研与需求来源。
6. `docs/events.md` + `review/{e1_challenge_pack,e3_attack_surface}.md` —— 对抗事件的输入材料与记录模板。

## 硬性纪律（违反即返工）

- **证据不可伪装**：`evidence/` 存运行事实，`review/` 存解释与复核；已签署的 RUN 不改写。
- **没有证据的结论不出现**：先核证据再解释；拿不到证据写「无法判定」，不许写成「通过」。
- **静态疑点不得升级措辞**：只断言结构，不断言行为（例：不得写"该应用在半夜录音"）。
- **LLM 不得直接升级结论**：模型只提疑；升级必须经 `pin_evidence` 机械核对（ADR-0004）。
- **改规则 = 改版本**：bump `RULE_PACK_VERSION` + 记 `docs/changes.md` + 重跑靶场真值。
- **未覆盖就声明未覆盖**：`coverage.not_checked` 必须如实填写。
- **人签署、人负责**：`human_signoff: pending` 的结论不生效；AI 不代签。

## 常用命令

```bash
python cli.py analyze <apk>              # 完整审计
python cli.py evaluate --run <RUN>       # 评价器（默认确定性）
python scripts/truth_check.py            # 靶场真值一致性（84 判点）
python scripts/e2e.py                    # 端到端验收 A-01/A-09
python -m unittest discover -s tests     # 单元测试（38 用例）
```

## 不要做的事

- 不要为通过检查而放宽契约、改判罚口径、删减规则；
- 不要把对话里的口头决定当作已批准契约（契约以文档 + 签署为准）；
- 不要把真实样本、密钥、模型凭据写入仓库（`key.txt` 已在 `.gitignore`）；
- 不要在 `evidence/` 里写实验性运行（用 `--no-evidence`）。
