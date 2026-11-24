# T-M5 待本人签署/确认清单【review】

> 性质：review ｜ 生成：2026-11-24 ｜ 状态：待本人处理
> 职责：把 T-M5-10/12/14 技术产物落地后**仍需具名人做**的事集中列出；AI 不代签、不改他人状态，本清单不代替签署台账。
> 关联：`docs/signoff.md`、`review/evaluation/SIGNOFF.md`、`docs/version-waiver.md`、`review/evaluation/field_check.json`。

## 已完成的技术产物（AI 落地，未代签）

| 任务 | 产物 | 验证 |
|---|---|---|
| T-M5-10 | `docs/version-waiver.md`；6 个 0.1.6 新正本已在仓库；新评价 `mismatch=false` | SIGNOFF §2 六份输出 `version_check.mismatch=false` |
| T-M5-12 | `fields.json`（10 项×≥2 字段）、`fieldcheck.py`、`agent.py` 接入、`field_check.json`、`field_check_notes.md`、`scripts/field_check.py`、7 个单测 | 79 单测全过；K-1~K-6 6/6；新批 PASS 7/INSUFF 3 |
| T-M5-14 | `SIGNOFF.md` §2 登记 0.1.6 批（签名留空）、§5 批次沿革、临时说明已折入并删除 | 旧签名未挪用；6 份新输出形态一致 |

## 需要本人处理（按优先级）

| # | 事项 | 位置 | 谁 | 动作 |
|---|------|------|----|------|
| 1 | **6 份新评价输出复核签署** | `review/evaluation/SIGNOFF.md` §2 签名栏 | 周宗正（或指定复核人） | 逐份读四状态、缺口、轨迹后填姓名与日期；当前"待本人复核" |
| 2 | **字段核对人工抽验 5 条** | `review/evaluation/field_check.json` → `human_spot_check.items` | 本人 | 填 `run_id`/`criterion_id`/`field_id`/程序三态，打开原文核对后填 `human_result`/`checker`/`date` |
| 3 | **版本豁免说明复核** | `docs/version-waiver.md` | 余俊辉（按 T-M5-10 步骤 5） | 复核版本演进描述后签署；TASKS.md 该任务状态由本人改 |
| 4 | **E-01/E-02/E-07 缺口决策** | `field_check_notes.md` §3 | 本组 / 教师 | 决定：把 brief/acceptance-matrix/release 内容拆回独立文件，或请教师确认 rubric 映射已由合并文档覆盖。**AI 未擅自改教师固定的 rubric，也未伪造这些文件** |
| 5 | **旧批次物理移出** | `review/evaluation/` 11-18 批文件 | 周宗正 | T-M5-14 步骤 3。旧批含已签正本，AI 未物理移出以免签署记录失去对应文件；本人确认另行存档后指示 |
| 6 | **0.1.6 全模型评价批（可选）** | — | 本组 | 当前登记批为 `--no-llm` 确定性路径；如要求模型判读批，需另跑并另登记 |
| 7 | **T-M5-01~05 组内验证** | `docs/team-roster.md` 验证清单 | 余俊辉 | 7 项状态由本人执行后改；含干净环境跑 6 样本、真值复算、抽验坐标、三档/钉证据解释、跑评价器、签报告 |
| 8 | **T-M5-08 角色轮换** | `docs/team-roster.md` 轮换记录 | 余俊辉 / 周宗正 | 周期 1 余俊辉独立验证、周宗正复核；周期 2 交换；状态由本人改 |
| 9 | **对抗组复核 / 教师复评** | `docs/signoff.md` | 毛舒逸组 / 教师 | 未发生，不预填；E1/E2/E3 交互当场记 `docs/events.md` |

## 纪律声明

- 本清单只列"待办"，不声称任何签署已完成；签名栏、状态栏一律由具名人本人填写。
- 技术产物可复核但不等同于"已签署"；`score_suggestion` 恒 `null`、`human_signoff` 恒 `pending` 未被模型改写。
- 字段核对只加严不放宽：7 项 PASS 仅限机械/字段层，结论语义正确性仍待人工与对抗组复核。
