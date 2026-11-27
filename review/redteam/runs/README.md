# 验收 RUN 报告副本索引

> 视角：毛舒逸组（对抗组）｜**本测试基于 commit `3c7a371` / 规则包 0.1.8**
> 运行时间：2026-11-27 19:15—19:17（GMT+8）｜命令统一为 `python cli.py analyze <样本> --no-evidence --out review/redteam/runs/<tag>`
> 说明：`--no-evidence` 不写对面 `evidence/`；本目录存报告副本（`report.md`/`report.json`）供复核。完整 RUN 元数据见各 report.json 的 `versions`/`target` 字段。

| 目录 | RUN id | 样本 | sha256 | R-PERM-01 | 摘要 |
|---|---|---|---|---|---|
| `v1/` | `RUN-20261127-191550-3464015c` | `samples/v2_crossmethod.apk` | `3464015c…` | **已确认** | 7 已确认 / 0 待复核 / 7 无法判定 |
| `v2bis/` | `RUN-20261127-191624-867c78d2` | `samples/v2bis_isolated.apk` | `867c78d2…` | **待复核** | 5 已确认 / 1 待复核 / 8 无法判定 |
| `v2_old/` | `RUN-20261127-191646-63823c87` | `samples/v4_isolated.apk` | `63823c87…` | **已确认** | 7 已确认 / 1 待复核 / 7 无法判定（本次开 B 未被压档，印证压档不稳定） |

对应验收结论见 `../e2_acceptance_samples.md` §4；F-01/02/03/05 回归结果见 `../fix_verification_result_regression.json`。
