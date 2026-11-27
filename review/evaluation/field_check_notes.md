# 字段级核对与四状态变化说明（T-M5-12 步骤 5）【review】

> 性质：review ｜ 版本：v1.0 ｜ 状态：复核中
> 职责：解释"从只查文件存在到读字段内容"之后，评价四状态为什么这样变、为什么没变成全 PASS。
> 关联：字段表 `review/evaluation/field_check.json`；字段定义 `evaluator/skills/evidence-review/fields.json`；该批评价输出已于 2026-11-26 清理，属测试产物，不纳入签署台账。
> 本文是测试记录，不含签名，也不纳入签署台账。

## 1. 改了什么

- 新增字段定义 `evaluator/skills/evidence-review/fields.json`：10 项审查项，每项 ≥2 个字段，字段全部来自本仓库真实文件（文档锚点、JSON 取值、目录条目、文件存在），不发明字段。
- 新增 `evaluator/fieldcheck.py`：三态核对 `match`（符合）/ `mismatch`（字段在但期望不满足）/ `missing`（文件或键读不到）；只读、走 `RestrictedTools` 白名单、不把读到的文本当指令执行。
- 评价器 `evaluator/agent.py` 接入字段核对，**只加严不放宽**：字段全符合是 PASS 的必要条件；任一字段 `mismatch`/`missing` 都不得仅凭"文件在"判 PASS。轨迹新增 `field_check` 事件，逐项记录字段路径与三态。

## 2. 状态变化（如实列，不美化）

| 对比维度 | 旧批次（2026-11-18，0.1.3/0.1.4 正本） | 新批次（2026-11-24，0.1.6 正本 + 字段核对） |
|---|---|---|
| 顶层四状态 | 6/6 `INSUFFICIENT_EVIDENCE` | 6/6 `INSUFFICIENT_EVIDENCE`（**顶层未变**） |
| 版本错配 | `mismatch=true`（0.1.3 正本 vs 0.1.4 契约） | `mismatch=false`（0.1.6 正本 vs 0.1.6 契约）——**T-M5-10 通过重跑解决** |
| 10 项审查明细 | 10/10 项 `INSUFFICIENT_EVIDENCE` | **7 项 PASS + 3 项 `INSUFFICIENT_EVIDENCE`** |
| 核对深度 | 只确认锚点文件存在 | 读字段内容，逐项三态 |

## 3. 为什么明细从"全不足"变成"7 PASS"，而顶层仍是"证据不足"

1. **7 项升为 PASS**（E-03/04/05/06/08/09/10）：版本错配消除后，这 7 项的锚点齐全，且全部字段 `match`——例如 E-05 的 `report.versions.rule_pack == meta.rule_pack`、`target.apk_sha256` 一致、`conclusions`/`coverage.checked` 非空；E-06 的 `changes.md` 含 0.1.6 版本锚点与回归成绩、`registry.py` 版本号绑定。这是机械核对的真实结果，不是放宽标准换来的。
2. **3 项仍为 INSUFFICIENT**（E-01/E-02/E-07）：各自有 1 个字段 `missing`——rubric 的 `expected_evidence` 列了文档合并前的历史文件名 `docs/brief.md`、`docs/acceptance-matrix.md`、`docs/release.md`，这些文件在 2026-11-18 文档重组中已并入 `requirements.md` / `specification.md` / `handoff/README.md`。字段核对**如实记 missing，不伪造这些文件**，也不擅自改教师固定的 rubric 清单。
3. **顶层未变**：只要有 1 项 `INSUFFICIENT_EVIDENCE`，顶层就是 `INSUFFICIENT_EVIDENCE`（`_decide` 与收口逻辑未改）。这符合证据纪律——不能因为多数项通过就把整体写成通过。

## 4. 状态变化可解释性核对

- 7 项 PASS 的范围仅限"机械 + 字段层"，结论语义正确性仍待人工复核，`score_suggestion=null`、`human_signoff=pending` 未被改写。
- 6 份新输出形态完全一致：PASS 7 / INSUFFICIENT 3、`mismatch=false`、字段核对已接入、轨迹含 `field_check` 事件。
- **未做的事**（不因文档补齐而消失）：E-01/E-02/E-07 的 3 个历史文件名缺口需决定——是把内容拆回独立文件，还是请教师确认 rubric 映射已由合并文档覆盖。本说明不擅自选。
- **回归证据**：94 个单测全过（含 7 项字段核对测试）；K-1~K-6 校准 6/6；84 判点 84/84 一致、硬错 0。

## 5. 待人工抽验（步骤 4，签名留空）

`field_check.json` 中 `human_spot_check.items` 预留 5 条：每条填 `run_id` / `criterion_id` / `field_id` / 程序三态，由抽验人打开原文核对后填 `human_result` / `checker` / `date`。
