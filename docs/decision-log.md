# decision-log · 关键决策索引

> 交付类：design（决策可追溯性）｜版本：v1.0
> 用途：老师/对抗组核查时**按这张表走**，每条决策都能落到"为什么这么定 + 证据在哪 + 谁定的"。
> 纪律：决策人栏为"起草/复核"分工；**复核未签字前，状态一律为「待签署」**，不得写成已批准。

---

## 1. 老师点名的四类决策（先看这四行）

| ID | 决策 | 结论 | ADR | 支撑证据 | 决策人 | 状态 |
|----|------|------|-----|----------|--------|------|
| D-01 | **软件形态 / 交付形态** | 本地 CLI + 文件产物；单机离线；无服务端、无 GUI | [ADR-0007](adr/0007-software-form.md) | `cli.py` 五子命令；`handoff/README.md` 克隆即跑；`release.md` §1 依赖表；`scripts/e2e.py` | 周宗正 / 余俊辉 | 待签署 |
| D-02 | **目标用户** | 主用户=复核者（对抗组/教师/验证者）；次用户=分析者；不服务批量扫描与非技术用户 | [ADR-0008](adr/0008-target-users.md) | `evidence/RUN-20261015-145536/report.md` 三档+坐标结构；`specification.md` §4 定位契约；`signoff.md` 抽验流程 | 周宗正 / 余俊辉 | 待签署 |
| D-03 | **工作方式** | 人工触发；一样本一 RUN 正本；不覆盖；签署后才生效；不接 CI 裁决 | [ADR-0009](adr/0009-working-mode.md) | `evidence/` 6 个独立 RUN；`--no-evidence` 隔离；`changes.md` 变更留痕 | 周宗正 / 余俊辉 | 待签署 |
| D-04 | **选用模型** | `mimo-v2.6-flash`（OpenAI 兼容）；可用性优先，**未做横向评测** | [ADR-0010](adr/0010-model-selection.md) | `experiments.md` 实验 4/5；`review/summary_gen_record.json`；`report.json.versions.channel_b_model` | 周宗正 / 余俊辉 | 待签署（附待办 R-1） |

---

## 2. 架构与工程决策

| ID | 决策 | 结论 | ADR | 支撑证据 | 决策人 | 状态 |
|----|------|------|-----|----------|--------|------|
| D-05 | 检测架构 | 双通道 A（确定性）+ B（LLM 提疑），融合层确定性合并 | [ADR-0001](adr/0001-dual-channel.md) | `core/channel_a.py`、`channel_b.py`、`fusion.py`；`experiments.md` 实验 1/4 | 周宗正 / 余俊辉 | 待签署 |
| D-06 | 工具链与数据源 | 四层数据源，各自独立降级；语义规则用 smali 不用 jadx | [ADR-0002](adr/0002-toolchain-layered-sources.md) | `core/axml.py`、`dexscan.py`、`adapters.py`；`tests/test_axml.py`；`experiments.md` 实验 2 | 周宗正 | 待签署 |
| D-07 | 结论分档 | 三档 + 逐规则档位上限；融合不得越限 | [ADR-0003](adr/0003-three-tier-status.md) | `specification.md` §2 `max_status` 列；`fusion.py` | 周宗正 / 余俊辉 | 待签署 |
| D-08 | 疑点升级机制 | LLM 提疑、规则钉证据；钉失败保留待复核 | [ADR-0004](adr/0004-pin-evidence.md) | `core/fusion.py` `pin_evidence`；`tests/test_pin_fusion.py` 6 用例 | 周宗正 | 待签署 |
| D-09 | 解码与工具链存放 | 解码产物工作区外；apktool jar 随仓库入库 | [ADR-0005](adr/0005-decode-outside-workspace.md) | `.tools/apktool_3.0.3.jar`；`adapters.py`；`release.md` §3 重置 | 周宗正 | 待签署 |
| D-10 | 真值评分口径 | 硬错=FP+漏检+档位错；EXPECTED_SILENT 上的待复核单列噪声 | [ADR-0006](adr/0006-truth-scoring.md) | `scripts/truth_check.py`；`review/truth_result.json`（84/84） | 周宗正 / 余俊辉 | 待签署 |
| D-11 | 需求与范围 | 6 条用户需求 + 18 条系统需求；范围外明确 6 项 | [requirements.md](requirements.md)、[brief.md](brief.md) §4 | 追溯矩阵 `requirements.md` §5 | 周宗正 / 余俊辉 | 待签署 |
| D-12 | 样本边界 | 不含加固；不执行样本；不发布真实应用结论 | `brief.md` §4、`release.md` I-3/I-7 | 调研 §2.4（APKiD 说明加固使静态失效）；`total` §10 | 周宗正 | 待签署 |

---

## 3. 这张表怎么被核查

1. **抽查任意一行** → 打开 ADR 看背景/替代方案/后果 → 打开"支撑证据"里的文件确认存在且内容对得上；
2. **看决策人** → 起草人与复核人是否分工（不是一个人既写又批）；
3. **看状态** → 未签字的写"待签署"，不允许写"已批准"；签署后在此表补日期与签名；
4. **看反例** → 每个 ADR 都有"替代方案（被否）"，被否理由必须具体，不能写"不合适"。

---

## 4. 尚未闭环的决策（如实列出）

| 项 | 缺什么 | 影响 | 计划 |
|----|--------|------|------|
| D-04 的横向评测 | 未对比其他模型 | 选型结论只到"可用"，不到"最优" | 待办 R-1（见 ADR-0010） |
| 全部决策的复核签字 | 余俊辉复核栏为空 | 决策处于"待签署"，不能作为已批准依据 | 下周五前完成 |
| E1/E2/E3 | 与对抗组的交互未发生 | O5 变化与对抗证据缺失 | 按 `events.md` 推进 |

> 这三项不隐藏。按课程纪律，"确认的阻断问题必须报告，展示数量上限不是隐瞒理由"。
