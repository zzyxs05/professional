# 代码审查报告 · zhuan（APK 静态审计系统）· 第二次审查

## 审查概览

- 审查目标：`C:/Users/shixz/Desktop/study/zhuan`（全仓库）
- 审查范围：全量（59 个 Python 文件；AST 扫描 120 条原始发现，剔除 Skill 自身 10 条后按维度归并）
- 技术栈：Python 3.13（仅标准库）；自研 AXML/DEX 解析器 + apktool 子进程 + OpenAI 兼容 HTTP 客户端
- 审查方式：AST 静态扫描 + 五维度人工深审 + 17 组可复现行为实验 + 61 单测 + 84 判点真值重跑
- 独立性声明：**本次为全新审查，不沿用第一次审查的任何结论**；下文每条发现均由本次阅读代码与实验重新得出
- 总体评分：**7 / 10**
- 合并建议：**⚠️ 修改后可合并/签署**（无 Critical；1 项 Major 影响汇总报告正确性，非审计主链路）
- 审查基线：`python -m unittest discover -s tests` 61/61 通过；`python scripts/truth_check.py --no-evidence` 84/84 一致、硬错 0

## 风险摘要

审计主链路（解码 → 双通道 → 融合钉证据 → 报告 → 评价）在本次审查中表现稳健：结论全量化、证据钉合、敌对样本防御（zip bomb / XML 深嵌套 / prompt 注入）经 5 组实验验证均真实生效，已签署正本.protect 机制（run_id 指纹 + 目录独占创建）到位。**唯一需要优先处理的是一处跨模块语义回归**：上一轮"判点全量化"改造让每条规则都产出 `UNDECIDED` 占位结论，但 B3 汇总模块仍用"没有标准结论 = 干净样本"的旧假设判定，导致干净样本被统计成"有 14 条结论、无检出样本 0 个"，汇总报告自相矛盾——这会直接误导评审人对样本洁净度的判断。其余为可维护性（高复杂度热点）与覆盖完整性（12 项新权限无使用模式定义）问题，不阻断主链路。

## 关键问题（Critical / Major）

### [M-1] 全量化改造引入汇总回归：干净样本被误判为"有结论、无检出 0 个" — 🟠 Major

- 位置：`core/summary.py:113-127`（`build_summary_input` 的 `n_quiet`/`std` 判定）、`core/summary.py:177-183`（`_template_render` 的 `if not std` 分支）、`core/fusion.py:191-212`（占位结论产生源）

- 问题：

  `build_conclusions` 现在对**每一条规则**都产出结论：无命中但已执行的规则会得到一条 `status=UNDECIDED`、`missing_evidence=[]` 的占位结论（这是正确的，避免判点消失）。但 `summary.py` 仍沿用旧假设——用"标准结论列表 `std` 为空"来识别"规则侧无检出的干净样本"：

  ```python
  # core/summary.py:113-118
  std = [c for c in concl if not c['criterion_id'].startswith('R-B-')]
  if not std:                      # ← 全量化后恒为 False（每条规则都有占位结论）
      n_quiet += 1
      quiet_names.append(b['sample'])
  for c in std:
      if c['status'] == CONFIRMED: n_conf += 1
      elif c['status'] == REVIEW: n_rev += 1
  # UNDECIDED 占位结论既不计数，也没触发 n_quiet
  ```

  后果（本次实验 17 可复现）：把一个"14 条规则全部已执行、全部未命中"的干净样本喂进 `build_summary_input`，输出为：

  ```
  【汇总统计】样本 1 个：规则侧无检出的样本 0 个（无）；其余样本共 0 条规则结论（已确认 0、待复核 0）
  - 本样本规则结论 14 条（已确认 0、待复核 0），B 侧疑点 0 条
  ```

  同一份报告里，汇总统计说"无检出样本 0 个"（错，应为 1），逐样本明细却说"规则结论 14 条"——两者矛盾。`_template_render:194-200` 同理：干净样本永远走 `if std` 分支，把 14 条 UNDECIDED 占位当成"已检出"逐条列出，而非输出"未发现可检出违规"。B3 汇总报告是给评审人/对抗组的交付材料，样本洁净度被系统性低估，属于"结论与事实不符"。

- 修复建议：把"是否干净"的判据从"有没有标准结论"改为"标准结论里有没有非 UNDECIDED 的实结论"，并同步两处渲染。

  ```python
  # core/summary.py —— build_summary_input
  std = [c for c in concl if not c['criterion_id'].startswith('R-B-')]
  substantive = [c for c in std if c['status'] in (registry.STATUS_CONFIRMED,
                                                   registry.STATUS_REVIEW)]
  if not substantive:                       # 干净样本：执行了但无实结论
      n_quiet += 1
      quiet_names.append(b['sample'])
  for c in substantive:                     # 只统计实结论
      ...
  ```

  `_template_render` 的 `if std` 同样改为 `if substantive`。判定口径建议抽成 `core/summary.py` 内的单一辅助函数 `substantive_conclusions(concl)`，两处共用，避免再次分叉。补一条单测：干净样本（全 UNDECIDED + 无 missing_evidence）经 `build_summary_input` 后统计行必须为"无检出样本 1 个"。

## 一般问题（Minor）

### [m-1] R-PERM-03 对 12 项 Android 12/13+ 敏感权限的检测空转 — 🟡 Minor

- 位置：`core/registry.py:63-119`（`SENSITIVE_PERMISSIONS`）、`core/registry.py:213-243`（`PERMISSION_USAGE_PATTERNS`）、`core/rules/perm/r_perm_03.py:43-53`

- 问题：

  敏感权限清单有 43 项，扣除"声明即生效"（7 项）和广播型（1 项）后，35 项理论上需要"使用模式"才能在 R-PERM-03（声明与使用不一致）里比对；但 `PERMISSION_USAGE_PATTERNS` 只定义了 23 项。实验 8 复现出 **12 项无使用模式定义**：

  ```
  READ_MEDIA_IMAGES / READ_MEDIA_VIDEO / READ_MEDIA_AUDIO / ACCESS_MEDIA_LOCATION
  NEARBY_WIFI_DEVICES / BLUETOOTH_SCAN / BLUETOOTH_CONNECT / BLUETOOTH_ADVERTISE
  BODY_SENSORS / BODY_SENSORS_BACKGROUND / ACTIVITY_RECOGNITION / USE_BIOMETRIC
  ```

  这 12 项进入 `r_perm_03.py:44-45` 的 `unchecked` 分支，`continue` 后不参与"是否使用"比对——即这些权限声明了却完全不调用时，**永远不会**被判为"过度声明"。代码在 `:50-53` 如实写入 `ctx.rule_notes`（附注），没有掩盖，符合项目"没证据写无法判定"纪律，故定为 Minor 而非 Major；但清单宣称覆盖 Android 13+ 权限，检测能力与实际口径不一致，建议补齐。

- 修复建议：为这 12 项补充 `PERMISSION_USAGE_PATTERNS`（如 `READ_MEDIA_IMAGES → ['Landroid/provider/MediaStore$Images;', 'Landroid/content/ContentResolver;->openInputStream']`、`BLUETOOTH_SCAN → ['Landroid/bluetooth/le/BluetoothLeScanner;->']`、`USE_BIOMETRIC → ['Landroidx/biometric/BiometricPrompt;', 'Landroid/hardware/biometrics/']`）。补齐后 `R-PERM-03` 的 `unchecked` 应为 0；在单测中断言"除豁免集外，每个敏感权限都有使用模式"。若某权限确实无法静态判定使用，则加入 `DECLARATION_ONLY_PERMISSIONS` 并在文档说明，不要留在灰色地带。

### [m-2] `run_channel_b` 的连通性探测不计入 LLM 预算与调用计数 — 🟡 Minor

- 位置：`core/channel_b.py:154-159`（ping 探测）、`core/channel_b.py:165/206`（`consume_llm`）、`core/channel_b.py:193/221`（`res.calls += 1`）

- 问题：

  实验 16 核实：`run_channel_b` 先发一次 `_chat(cfg, [{'role':'user','content':'ping'}], max_tokens=4)` 做连通性探测，这次**真实 HTTP 调用**既不调用 `runner.budget.consume_llm()`，也不 `res.calls += 1`。因此：

  ```
  实际 HTTP 调用 = 1(ping) + N(B1 复核) + 1(B2 扫描)
  预算/报告记录  = N + 1
  ```

  `meta.json` 的 `budget.llm_calls_used` 与 `report.md` 打印的"调用 N 次"会比真实调用少 1。这不越预算上限（30 次，多 1 次无实质影响），但违反了本项目"成本/调用可追溯"的口径一致性——评价器核对预算时拿到的是偏小的数字。

- 修复建议：在 ping 成功后补一次计数。二选一：(1) 把 ping 计入预算——在 `try` 前 `if not runner.budget.consume_llm(): res.reason='预算不足，无法探测'; return res`，成功后续写 `res.calls += 1`；(2) 若刻意不把探测计入审计预算，则在 `res` 与 `meta` 里显式记一个 `probe_calls=1` 字段，让实际调用数可从报告还原。推荐 (2)，语义更清楚（探测不是审计判定调用，但成本真实发生）。

### [m-3] 高复杂度热点集中在融合/编排/报告层，可测试性偏弱 — 🟡 Minor

- 位置（AST 扫描客观结果，函数行数 / 圈复杂度）：
  - `core/fusion.py:166 build_conclusions()` 158 行 / 复杂度 35（本次 m-1 的回归正出在此类巨函数）
  - `cli.py:34 cmd_analyze()` 206 行 / 复杂度 34
  - `evaluator/agent.py:289 _mechanical_verdict()` 90 行 / 复杂度 36
  - `evaluator/precheck.py:34 precheck()` 92 行 / 复杂度 30
  - `core/summary.py:99 build_summary_input()` 65 行 / 复杂度 28
  - `core/channel_b.py:332 _collect_sensitive_area()` 复杂度 27
  - `core/report.py:29 render_md()` 96 行 / 复杂度 29
  - 另有 deploy 层 `core/adapters.py`、`core/axml.py` 多处圈复杂度 14—18、嵌套深度 5

- 问题：这些函数是"判点生成/收口/渲染"的核心，逻辑分支多。本次 m-1 表明，跨模块语义假设分叉（fusion 改了、summary 没跟上）正是巨函数 + 隐式契约容易滋生的回归类型。全部 85 条 Minor 中绝大多数是此类复杂度/嵌套告警，归并为一条。

- 修复建议：不强求全改。优先拆 `build_conclusions`（本次已经因它出回归）：按"无命中占位 / 有命中融合 / B2 钉证据补盲"三段提三个私有函数，让 `build_conclusions` 只做编排。`cmd_analyze` 可按"解码 / 通道A / 通道B / 落盘"四段拆分。其余保持，但对每个被拆出的判点生成函数补一条针对性单测。

## 优化建议（Nit，可选）

- **未使用导入**（AST 客观发现）：`core/adapters.py:13 struct`、`:15 sys`，`core/channel_a.py:13 registry`（该模块实际未引用 registry 属性），`core/rules/net/r_net_01.py:12 registry`，`tests/test_evidence_store.py:8 os` —— 直接删除。
- **魔法数字**：`core/dexscan.py` 的 DEX 头偏移 `0x38/0x40/0x58`（`:89-91`）与条目宽度 `4/8`（`:97/115/127`）建议提为具名常量（`DEX_HEADER_STRING_IDS_OFF` 等），它们实际是 DEX 规范字段，命名后可读性显著提升。`core/axml.py:160/163` 的 `8/3`、`core/summary.py:33` 的 `120`（批次跨度阈值分钟）同理。
- **待办标记**：`cli.py:258` 的 `'TODO（EXPECTED_HIT:...）'` 是 register 模板的占位文本，非真待办；`scripts/truth_check.py:38` 的 `'TODO'` 是未标定样本的默认 expected——建议改为显式哨兵 `'UNLABELED'` 并在 compare_sample 里单独计 SKIP，避免与真待办混淆。
- `core/evidence.py:55` 已用 `run_id[4:]` 正确替换了 `replace('RUN-','')`（第一次审查的 Nit 已修），无遗留。
- `docs/changes.md` 与 `registry.RULE_PACK_VERSION` 的联动仍只在注释约定，建议加一条单测断言 `changes.md` 含当前版本号字符串。

## 架构评估

- **模块边界**：`core/`（领域）、`evaluator/`（自评）、`scripts/`（实验与验收）三层职责清晰，`cli.py` 单一入口。规则按 `core/rules/{man,perm,str,code,net}/` 分域，统一 `run(ctx)` 契约，扩展成本低。

- **依赖方向**：`core/rules/* → registry + rules/common`，`core/fusion → registry + channel_a`（`fusion.py:22` 直接从 `channel_a` 取 `RULES_PIPELINE` 建 `_MODULE_BY_RULE`，是唯一逆向耦合：融合层依赖执行层）。建议把 `RULES_PIPELINE` 上提到 `registry`，让 fusion 只依赖 registry。未发现循环依赖。

- **数据流一致性（本次风险主线）**：`fusion.build_conclusions`（产生结论）与 `summary.build_summary_input`（消费结论）之间存在**隐式语义契约**——前者在 0.1.5 改成"全规则出结论"，后者仍按"无结论=干净"解读，导致 m-1。建议在 `registry` 定义统一的判定辅助（如 `substantive_statuses()` 与"是否干净样本"函数），fusion 与 summary 共用，杜绝同类分叉。

- **对抗性设计**：本次用 5 组实验验证了敌对样本防御的真实性——`safezip.read_member` 按声明体积拒绝超大成员、`_build_tree` 深度上限 + 标签配对、`_render` 递归深度上限、`_INJECTION_RE` 对中英文注入指令的识别、`B1_SYSTEM/B2_SYSTEM` 的 `<sample_data>` 数据边界声明——均生效。防御重心放在"B 只能降不能升"的降级方向，设计取舍正确。

- **证据链与签署纪律**：`EvidenceStore` 独占创建 + run_id 带样本指纹、raw 响应全文单独落盘 + 哈希、`precheck` 的 E-DANGLING/E-CLAIM-ONLY/E-MISSING-CRITERION 三道门，在本次阅读与实验中均自洽。84 判点真值重跑 84/84 一致，61 单测全绿，是本项目质量的正面证据。

- **测试策略缺口**：`tests/test_pin_fusion.py` 用人工桩验证融合，未覆盖 cli 真实回填路径；但本次 m-1 的根因不在融合本身，而在"fusion 产出 → summary 消费"的跨模块边界，该边界目前无单测。建议补一条端到端断言：干净样本 analyze → summary 统计行必须报"无检出样本 1 个"。

---

*本报告由代码审查与架构分析助手（code-review-analyzer）第二次全量审查生成。所有结论基于独立代码阅读、AST 扫描与 17 组可复现实验；未参考第一次审查结论。审查过程不改任何审计结论、不触碰已签署正本；仅运行 `--no-evidence` 真值重跑恢复了 `review/truth_result.json` 基线（84/84）。*
