# impact-map · Change 影响分析【review / E2 必交物】

> 性质：review ｜ 版本：v1.0 ｜ 状态：生效
> 职责：任何规则/结构变更前填此表，记录触发、冻结基线、改动边界、影响面与回归计划；不保存变更历史。
> 关联：配套 `docs/changes.md`；候选来源 `docs/events.md` CHG-004；证据位置 `evidence/`、`review/`。
> 签署：状态统一见 `docs/signoff.md`，本文不设独立签署栏。

模板 + 已发生变更的完整示例（建设期修正 #1 为实例）。

## 模板

```
### CHG-<编号>：<一句话>
- 触发：来源（对抗组 Finding / 教师指令 / 自检发现）
- 冻结基线：<版本或 RUN id>（变更前的对照）
- 改动边界：仅动的文件/常量/规则（不扩成整站重做）
- 影响面（逐项勾）：
 [ ] 规则集（哪几条）  [ ] 输出 schema  [ ] 档位规则  [ ] 证据格式
 [ ] 真值表（是否需重标）[ ] 报告渲染   [ ] 历史 RUN 的可解释性
- 回归计划：跑哪些样本、期望哪些点变化、哪些点必须不变
- 前后差异与回归证据：<链接 evidence/ 与 review/>
```

## CHG-001（示例，已于建设期执行）：自有代码路径判定修复

- **触发**：自检——bad03 首跑命中数异常少（3 条规则 vs 真值 7 条）
- **冻结基线**：RULE_PACK 0.1.0 建设期批次（正本未随仓库保留，见文末「证据保留说明」）
- **改动边界**：仅 `core/adapters.py::SmaliFacts.app_files` 一处
- **影响面**：规则集（P/C/N 类 7 条规则的扫描范围）；其余 schema/规则/真值表均不动
- **回归计划**：bad03 期望 7 命中点恢复；good01/good02 期望仍全安静（防"放开范围引入误报"）
- **前后差异与回归证据**：
 - 前：`R-MAN-02(2) R-PERM-02(10) R-PERM-03(1)`，7 个期望命中缺失
 - 后：命中 7 条规则（30 处），good 样本保持 0 命中；全量真值 84/84
 - 证据：修复后的效果由最终批次承接——`evidence/RUN-20261015-145536`（bad03 命中 7 条规则、30 处）；
  建设期逐轮 RUN 未随仓库保留，此处只保留结论与最终可核对证据

## CHG-002（示例）：敏感 API 模式类级化

- **触发**：单元测试暴露（构造引用行 `new-instance ... MediaRecorder;` 不含 `->` 漏配）
- **改动边界**：`core/registry.py::SENSITIVE_APIS` 5 个类级模式
- **影响面**：R-PERM-01/02 的敏感侧要素；档位/真值/格式不变
- **回归**：单测 26/26（含新增构造引用用例）；靶场 84/84 保持
- **证据**：`review/truth_result.json`（最新轮）

## CHG-003（实例）：B 通道提示词与钉证据严格化

- **触发**：真实模型连测（实验 4）暴露——B1 越权判真伪降级、钉证据"实体存在即升级"产生假证据、
 B2 产出推测型/复述型疑点
- **冻结基线**：建设期首次 B 连测前批次（正本未保留）；对照规则：A 通道基线 84/84
- **改动边界**：`channel_b.py`（B1 提示词 v0.2 / B2 提示词 v0.3 / 敏感区摘要补全）、
 `fusion.py`（钉证据 v2：规则映射 + 机械复核 + 实体级核对）、`registry.py`（`fp_notes` / `PIN_RULE_MAP`）；
 **规则集（14 条检测逻辑）未动**
- **影响面**：
 [x] 通道 B 的判定语义  [x] 钉证据升级路径  [ ] 规则集  [ ] 输出 schema
 [ ] 档位规则（不变）  [ ] 真值表（不需重标） [x] 报告中的 B 侧条目
- **回归计划**：全量 6 样本 B 开启重跑；期望：标准规则结论与基线一致（84/84）、
 假证据升级清零、good 样本 B 侧疑点收敛
- **前后差异与回归证据**：
 - 前：bad02 出现假证据式「已确认 R-B-001」＋ R-STR 被误降级（1/2 档位）；good02 3 条错误疑点
 - 后：bad02 恢复「已确认 2」；假升级清零；六样本 B 侧疑点清零（某一轮快照）；
  全量 **84/84（B 开启规则）**
 - 证据：`evidence/RUN-20261015-145503`（bad02 恢复「已确认 2」，B 侧疑点收敛）；
  最终批次其余样本见 `evidence/RUN-20261015-*`；单测 +4 项（`tests/test_pin_fusion.py`）
- **遗留声明**：B2 疑点产出存在运行间波动（`handoff/README.md` 的 I-6），A-09 复现规则按标准规则结论判定

## CHG-004（已确认候选，范围已修正）：R-PERM-01 不可直接解析调度目标的链路识别

- **触发**：自检 + E3 攻击面 A-05；对抗组 `review/redteam/e3_findings.md` §6 实测后修正范围
- **冻结基线**（2026-11-25 对抗组确认，见 `review/redteam/e2_change_relay.md` §2）：
   规则包 **0.1.6** / commit **`6276391`** / 12 个 RUN（6×0.1.3 历史 + 6×0.1.6 新批）/
   靶场 6×14=84 判点一致 / 单测 79 全过。历史 RUN 正本不改写。
   > 原提案写的 0.1.3 是提出时点取值，已过时；以本节为准。
- **范围修正（必须写进 Change，不得按原提案实施）**：

   | 场景 | 实测（0.1.6） | 原提案假设 | 本次是否改 |
   |---|---|---|---|
   | 同类内 `const-class` 链（bad03） | 已确认 | 已确认 | 否 |
   | 跨类 `const-class` 链（a05 样本） | **已确认** | 待复核 | **否——提案误判，实测已支持** |
   | **`Runnable` 接口跨方法链**（v2 样本） | **待复核**，`missing_evidence` 空 | 未区分 | **是——真正目标** |
   | 同包孤立类（v4 样本） | 待复核，无串链 | 风险项 | 否——验收反例，必须保持 |

- **改动边界**：`core/rules/perm/r_perm_01.py`（不可直接解析调度目标的链路识别 +
   `missing_evidence` 能力边界声明）；不动其余 13 条规则、不动 schema、不动档位规则。
   **描述从"跨方法可达性"改为"不可直接解析的调度目标（Runnable/回调/动态类名）的链路识别"**。
- **影响面**：
   [x] 规则集（仅 R-PERM-01） [ ] 输出 schema [ ] 档位规则 [x] 证据格式（`missing_evidence`）
   [x] 真值表（新增 v2/v4 样本，不改既有 6 样本） [ ] 报告渲染 [x] 历史 RUN（旧结论保留原解释）
- **回归计划**（验收样本见 `review/redteam/e2_acceptance_samples.md`）：
   1. 既有 6 样本 84 判点逐点不变；
   2. v2（Runnable 跨方法链，sha256 `3464015c…`）从「待复核」升「已确认」，
   或至少在 `missing_evidence` 写明"存在跨方法链，未解析"；
   3. v4（同包孤立类，sha256 `63823c87…`）仍待复核，不许升档；
   4. a05（跨类 `const-class`）保持已确认，不因本次改动回退。
- **验收标准**：上述 4 条全过；报告措辞仍只断言"存在定时/后台触发敏感组件的结构"，不升级为行为断言。
- **风险**：接口链识别可能把孤立类误判为链（v4 反例专门压这个）；压不住就只补 `missing_evidence` 声明、不升档。
- **先行条件**：对抗组已确认候选并附范围修正，`e2_change_relay.md` 注明批边界按用户指令视为已过；
   冻结基线已落。
- **状态（2026-11-25）**：**部分实施**——0.1.7 已补 `missing_evidence` 能力边界声明
   （`e2_v2v4_local.json` 实测 v2/v4 均写明链未解析），满足 fix_verify 的 F-05 验收条件；
   V-1「升为已确认」的功能门当时**未做**（该段为 2026-11-25 状态）；已于 0.1.8 由 CHG-006 实施，见本文末节。

## 证据保留说明（补充）

- 建设期（2026-10-14）的逐轮 RUN 目录**未随当前仓库保留**；`evidence/` 只保留 2026-10-15 的 6 个最终批次。
- 因此本文件中 CHG-001—CHG-003 的"冻结基线"无法给出可打开的 RUN，已改为指向**最终可核对证据**，并在此声明缺口。
- 影响：变更的**效果**仍可由 `review/truth_result.json`（84/84）与 6 个 RUN 核对；但"变更前后逐轮对比"这一层证据缺失。
   **不补造、不补写 RUN 编号**——补造比缺失更严重。
- 后续纪律：任何新 Change 必须同时保留前后两个 RUN；不允许再出现"只有结论、没有批次"。

## CHG-005（已实施，0.1.7）：权限标签补全 `uses-permission-sdk-23`

- **来源**：E3 Finding **F-02**（确认·漏报），我按 CHG-004 同一批在 0.1.7 实施。
- **触发**：敏感权限用 `<uses-permission-sdk-23>` 声明时 R-MAN-02 不识别，R-PERM-03 声明与使用比对同步漏。
- **冻结基线**：0.1.6 / commit `6276391` / 12 RUN；实际与 CHG-004 同批在 0.1.7 实施，
   实施前基线见本节上文与 `review/redteam/e2_change_relay.md` §2。
- **改动边界**：manifest 权限标签收集 + R-MAN-02 判据中涉及标签来源的部分；
   未动 `SENSITIVE_PERMISSIONS`、未动其余 13 条规则、未动 schema、未动档位规则。
- **改动位置**：`core/adapters.py` 只负责 apktool 解码，不含权限标签收集；
   权限解析实际在 `core/axml.py` 的 `extract_manifest_facts()`，改在那里，
   规则侧改 `core/rules/man/r_man_02.py`。
- **影响面**：[x] 规则集（R-MAN-02 / R-PERM-03 的权限来源） [ ] schema [ ] 档位
   [ ] 证据格式（但 `PermissionDecl` 增加 `tag` 字段用于校正证据片段）
   [ ] 真值表 [ ] 报告渲染 [x] 历史 RUN（旧结论保留）。
- **实施内容**：
   1. `core/axml.py`：`uses-permission` 与 `uses-permission-sdk-23` 都收入 `facts.permissions`；
   2. `PermissionDecl` 增加 `tag`，证据片段写真实标签，不再硬编码 `<uses-permission>`；
   3. `r_man_02.py`：按权限名去重，两种标签混用时只出一条 Hit，
   首次出现的标签与行号作为证据。
- **回归**：
   1. `a02.apk`（sha256 `cc1a7084…`）R-MAN-02 notes 重现 `RECORD_AUDIO`；
   `fix_verify.py --phase regression` F-02 **PASS**（去重后重验仍 PASS）；
   2. 既有 6 样本 84/84 逐点不变；单测 **91/91**（新增 2 例：混用去重、仅 sdk-23 标签）；
   3. K-1~K-6 校准 6/6。
- **回滚**：解析处恢复仅匹配 `uses-permission`、去掉 `PermissionDecl.tag` 与 r_man_02 去重；
   `a02.apk` 的 R-MAN-02 回到只报 LOCATION。
- **状态：已实施并验收。**

---

## CHG-006（已实施，0.1.8）：R-PERM-01 跨方法 Runnable 链解析（V-1）

- **来源**：对抗组 E2 变更请求 V-1（`review/redteam/e2_change_relay.md` §3）；
  CHG-004 当时只补了能力边界声明，未做升档，本次补齐。
- **提出人**：余俊辉（轮换周期 2：验证 → 实现）
- **复核人**：周宗正（独立复核实现与回归），2026.11.26
- **触发样本**：`review/redteam/samples/v2_crossmethod.apk`（sha256 `3464015c…`）。
- **现状（0.1.7）**：`MainActivity.onCreate` 的 `postDelayed(new MainActivity$1)` 与
  `const-class RecordingService` 分处不同方法；规则只在单方法块内找目标，链断 →
  R-PERM-01 待复核，`missing_evidence` 声明"跨方法链未解析"（0.1.7 的 F-05 边界声明）。
- **改动边界**：仅 `core/rules/perm/r_perm_01.py`——建全 app 方法索引 + 类索引；
  从调度点往上找实际传入的匿名 Runnable 类 → 该类 `run()` → 静态 invoke 目标方法
  （剥 `-$$Nest$m` bridge 前缀）→ 目标方法里的 `const-class` → 目标类含敏感 API。
- **防误报约束**：只追 `invoke-static/direct/virtual`，遇 `invoke-interface` 立即停；
  最多 2 跳；找不到静态目标就退回原待复核路径，不猜链。
- **验收结果（按证据链判定，不按书面预期判定）**：
  - V-1：R-PERM-01 **待复核 → 已确认**，notes 写明跨方法链与敏感 API 位置；
  - V-2（`v4_isolated.apk`）：书面期望保持待复核，但实测样本与 V-1 的链**逐字相同**
    （同样 `MainActivity$1 → startRecordingService → RecordingService`），
    多出的孤立类 Worker 未被本实现引用；因此 R-PERM-01 也升为已确认。
    **结论**：按"证据支持什么就判什么"的纪律处理，不为迎合书面预期扭曲判定逻辑；
    样本与期望的偏差如实记录，交对抗组确认。
  - 既有 6 样本 84/84 判点逐点不变；94 单测全过；双模式校准各 6/6。
- **回归**：`python scripts/truth_check.py --no-run` 一致 84、硬错 0；
  `python -m unittest discover -s tests` 94 全过；
  `python scripts/eval_calibrate.py` 与 `--llm` 均 6/6。
- **回滚**：移除 `_method_index` / `_resolve_cross_method` 与 `if not linked` 分支里的
  跨方法尝试，恢复单方法块内判定；版本回退需同步降回 0.1.7 并记 changes.md。
- **偏差闭环（2026-11-27）**：对抗组回执 `review/redteam/reply_v2_deviation.md` 确认分析属实、
  偏差责任在旧 V-2 样本构造（从 V-1 复制时未拆干净 RecordingService 链），
  明确同意不加"有孤立敏感类就降档"的规则。
  - 旧 V-2（`v4_isolated.apk`）书面期望作废，改判"已确认（正确）"，保留作对照、不再作硬门；
  - 防串链硬门移交新反例 `review/redteam/samples/v2bis_isolated.apk`
    （sha256 `867c78d2…`）：断开 Runnable 链、RecordingService 清空壳、保留孤立 Worker；
    对抗组独立复验 R-PERM-01 **保持待复核** + `missing_evidence` 声明未解析链，**通过**；
  - V-1 功能门对抗组复验通过（待复核 → 已确认）；F-01/02/03/05 回归 4/4；84/84、94/94。
  - 补充观察：旧 V-2 开 B 通道时 B1 会把档位压回待复核，纯 A 通道为已确认；
    两者均真实，复跑时注意 B 是否启用。
- **状态：已实施并闭环（对抗组 2026-11-27 回执确认）。**
