# handoff · 交接包（对抗组 / 教师通道）

> 用途：他人在干净环境复现本组结论、运行评价器、提出挑战。
> 版本：规则包 **0.1.3** ｜ 报告版本锚点：见各 RUN 的 `meta.json`

## 1. 启动（克隆即跑）

```bash
# 环境要求：Python 3.8+（零第三方依赖）、Java 8+
python cli.py analyze lab/apks/bad03.apk
```

- 工具链 `apktool_3.0.3.jar` 随仓库携带（`.tools/`），Java 缺失时自动降级、覆盖声明如实；
- 通道 B 需 `key.txt`（项目根，一行 `模型名,base_url,api_key`，不入库）；无配置时自动跳过并声明——
  这是**预期降级路径**，不是故障。

## 2. 复现与验证入口

| 目的 | 命令 | 期望 |
|------|------|------|
| 真值一致性 | `python scripts/truth_check.py` | 84 判点全一致（硬错 0、噪声 0） |
| 端到端验收 | `python scripts/e2e.py` | A-01 全样本受理；A-09 两次运行一致 |
| 评价器 | `python cli.py evaluate --run <RUN>` | 四状态输出 + 引用校验 |
| 六合一汇总 | `python cli.py summary` | `review/summary.md`（模型生成；`--no-llm` 走模板降级） |
| 单元测试 | `python -m unittest discover -s tests` | 38 用例全过 |

## 3. 重置

见 `docs/release.md` §3。一句话：删 `%TEMP%/apkaudit_decode` 与 `.tools/framework/` 即可；
`evidence/` 为运行正本，不得改动。

## 4. 注册补测接口（对抗组用）

- 评价器受限工具：`request_registered_test(target_id, test_id)`，白名单仅
  `rerun_analyze` / `truth_check`，预算 ≤5 次；
- 协议：只接受注册过的目标与测试，**不接受任意脚本/URL**；
- 所有交互留痕进 `review/`。

## 5. 已知限制（复现前必读）

- 通道 B 已配置模型（mimo-v2.6-flash）实测通过：B 开启口径 84/84 保持；最终批次仍有 **9 条未钉 B 侧疑点**
  （bad01×2、bad02×1、good01×2、good02×4，全部为「待复核」）——这是 B 通道的正常输出，不是失败，也不是"清零"；
  但 **B 与规则冲突场景尚未覆盖**——B 的召回增量需新样本检验（下一步验证重点）；
- **模型选型未做横向评测**（ADR-0010）：只验证了"可跑通、成本可接受"，不能据此认为它是效果最优的模型；
- R-PERM-01/03 档位封顶「待复核」为刻意设计（ADR-0003），不是漏判；
- bad04 为诱导对抗样本、good02 为边界陷阱样本——复现时请核对它们仍分别"检出 2 条 / 全安静"；
- 保留测试与实现答案不提前互换（课程纪律）；对抗组文件不自动等于独立复现。

## 6. 目录导航

```
总档.md            设计唯一权威
docs/              契约（brief/specification/acceptance-matrix/adr/...）
core/              产品本体（registry/axml/dexscan/adapters/channel_a/rules/channel_b/fusion/summary）
evaluator/         评价器（四状态、受限工具、校准判例）
evidence/RUN-*/    运行正本（不可改写）
review/            互评材料：truth_result.json（一致性成绩）、summary.md（六合一）、
                   e1_challenge_pack.md（E1 输入）、e3_attack_surface.md（E3 输入）、
                   truth_review_worksheet.md（真值复核底稿）、signoff_prep.md（签署准备）
lab/               靶场（apks + truth + sha256）
scripts/ tests/    契约脚本与单元测试
```
