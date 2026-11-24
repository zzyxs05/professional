# AGENTS.md · 给 AI 的入口

> 性质：design ｜ 版本：v1.0 ｜ 状态：生效
> 职责：只做导航，不写规则；指清开工前读什么、哪六条不能违反、常用命令在哪。
> 关联：依据 `HARNESS.md`、`总档.md`；与之冲突时分别以 `HARNESS.md`、`总档.md` 为准。下游 `TASKS.md`、`docs/specification.md`。
> 签署：状态统一见 `docs/signoff.md`，本文不设独立签署栏。

## 开工前读三份

1. `总档.md`：项目是什么、系统怎么转、课程有哪些硬要求；
2. `HARNESS.md`：目录怎么放、代码怎么写、产物和日志存哪；
3. `TASKS.md`：现在在做什么，做到什么算完。

要改需求、规则或报告格式，先看 `docs/specification.md` 和 `docs/decision-log.md`，别自己发明。

## 六条不能违反的

1. **证据不能编**：`evidence/` 放跑出来的事实，`review/` 放解释；签过字的正本不改。
2. **没证据就写"无法判定"**，不许写"通过"。
3. **静态疑点不许升级措辞**：只能说结构上存在什么，不能说这个应用实际在干什么。
4. **模型只提疑，规则拿证据**：要升"已确认"，必须过 `pin_evidence`。
5. **改规则就是改版本**：`RULE_PACK_VERSION` 加号 + 记 `docs/changes.md` + 重跑 84 判点。
6. **人签署、人负责**：AI 不代签，不改别人的状态。

## 常用命令

```bash
python cli.py analyze <apk>                  # 完整审计
python cli.py analyze <apk> --no-evidence    # 演练，产物不进 evidence/
python cli.py evaluate --run <RUN>           # 评价 Agent 自评（默认用 key.txt 的模型）
python cli.py evaluate --run <RUN> --no-llm  # 只走确定性路径
python scripts/truth_check.py --no-run       # 复算 84 个判点
python scripts/eval_calibrate.py             # K-1~K-6 校准
python scripts/e2e.py --no-evidence          # 端到端验收 A-01/A-09
python -m unittest discover -s tests         # 61 个单测
```

## 不要做

- 不要为了通过检查放宽契约、改判定标准、删规则；
- 不要把聊天里的口头决定当成已批准的契约；
- 不要把真实样本、密钥、模型凭据写进仓库（`key.txt` 在 `.gitignore` 里）；
- 不要在 `evidence/` 里写实验数据（用 `--no-evidence`）。
