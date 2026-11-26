# changes · 规则/结构变更记录（版本锚点）【review】

> 性质：review ｜ 版本：v1.0 ｜ 状态：生效
> 职责：按时间记录规则包与结构的每次变更、触发来源与回归结果；不重述规约正文，也不保存运行事实。
> 关联：变更纪律 `HARNESS.md` §1.3；规则契约 `docs/specification.md`；回归 `scripts/truth_check.py`；实验数据 `docs/experiments.md`。
> 签署：状态统一见 `docs/signoff.md`，本文不设独立签署栏。

规则变更 = bump RULE_PACK_VERSION + 本文件记录 + 重跑靶场真值。历史报告保留原有解释，不被新规则悄悄改写。

## B 通道建设期修正（2026-10-14/15，真实模型连测驱动；B 通道有独立 prompt 版本号）

> 背景：key.txt 配置后对 6 样本做真实连测，暴露出通道 B 的首批设计缺陷，逐项修复后
> 达成 **B 开启口径 84/84**（详见 `experiments.md` 实验 4）。以下均为"对齐契约语义"的修复，
> 非检测结果驱动的调参；每项均有独立暴露渠道与回归记录。

| # | 日期 | 变更 | 暴露渠道 | 回归 |
|---|------|------|----------|------|
| B1 | 10-14 | 预算 10→30 次/run（运行参数，经项目负责人指示） | 用户指示 | 不影响结论 |
| B2 | 10-14 | LLM_MAX_TOKENS 1024→2048、超时 60→90s（推理模型 reasoning tokens 计入配额，实测） | 端点连测 | 不影响结论 |
| B3 | 10-14 | **B1 提示词 v0.1→v0.2**：复核标准改为"该规则的误报口径"（`RULE_META.fp_notes` 注入），明确禁止真伪/危害判断——修复"模型把示例凭据判为上下文无害"的越权降级 | bad02 实跑 | bad02 恢复已确认 |
| B4 | 10-14 | **B2 提示词 v0.1→v0.3**：只许提可机械核查的断言型疑点；复述事实不算疑点 | bad01/good02 实跑 | 疑点收敛 |
| B5 | 10-14 | **钉证据 v2 严格化**（fusion.py）：语义疑点→规则映射（registry.PIN_RULE_MAP）→机械规则复核 + 实体级核对（claim 提及的样本内实体必须被命中覆盖）。修复 v1"实体存在即钉成功"导致的假证据式「已确认」（bad02 R-B-001） | bad02 实跑 | 假升级清零；新增 4 项单测 |
| B6 | 10-14 | R-MAN-01 映射关键词缺"未设置/未附带"等变体 → 改三组 AND 结构（导出×权限词×否定词） | bad01 实跑（3 条残留疑点） | bad01 R-B 清零 |
| B7 | 10-14 | B1 证据片段不完整（receiver 只截起始行，B1 看不到 intent-filter）→ r_man_01/05 改为元素完整行区间（500 字截断） | bad01 实跑（R-MAN-05 被误降级） | R-MAN-05 恢复已确认 |
| B8 | 10-14 | B2 敏感区摘要补全（组件带 exported/permission 属性；自定义权限带 protectionLevel 符号名；URL/动态加载点）——修复"模型在残缺信息上产出事实性错误疑点" | good02 实跑 | good02 疑点清零 |
| B9 | 10-15 | 新增 **B3 任务与 `cli.py summary`**：六合一汇总报告（模型生成，降级模板渲染）；统计数字由程序提供、模型只许引用（修复模型自行加总算错） | 生成实测 | 数字全对 |

**R-MAN-01 三组结构说明**（B6）：`[导出|exported|暴露] ∧ [permission|权限|保护] ∧ [未|无|缺少|…]`——
覆盖"未设置/未附带/缺少 permission"等全部否定表述变体，避免继续打补丁式补词。

## 实验纪律与工具（2026-10-15，项目负责人指出）

> 问题：调准则过程中反复运行 → 每次都在 `evidence/` 产生一个 RUN 目录，
> **把试错数据写进了运行正本库**（evidence 已积累 100+ 个 RUN，多数为实验性运行）。
> 且此前的改进方式是"跑一次→看→改→再跑"，无协议、无重复、无统计，无法区分真实改进与单次运气。

| # | 变更 | 作用 |
|---|------|------|
| E1 | `cli.py analyze --no-evidence`（演练模式）：跑完整链路（含通道 B），证据与报告写**临时区**，不进 `evidence/` | 实验不污染运行正本（已验证：evidence RUN 数零增长） |
| E2 | `truth_check.py` / `e2e.py` 同步支持 `--no-evidence` 透传 | 质量门脚本批量重跑也不污染 |
| E3 | 新增 `scripts/b_stability.py`：B 通道稳定性实验（固定样本 × N 轮 × 固定 prompt 版本 → verdict 分布 / 观察出现率 / 一致性），只产出统计 JSON 到 `review/`，**不产生 RUN** | 把"反复无记录"变成有协议、可复算的实验 |
| E4 | `_chat` 增加可恢复错误重试：429 限流 / 5xx / `IncompleteRead`（响应截断）退避重试 1 次（`LLM_RETRY_BACKOFF_SECONDS=20`） | 实测遇到过 429 与 IncompleteRead；重试后恢复，避免整轮 B 通道被跳过 |
| E5 | 实验统计口径：调用失败记为 `error` 并**从一致性判定中剔除**，全失败时明确输出"无有效数据"（不误报为稳定） | 修掉"全 error 却显示 ✅ 稳定"的误导 |

**初测数据（bad03，b1-v0.3，2 轮）**：R-NET-01 一致率 1.00，观察字段出现率 1.00。
样本量过小，**结论待服务稳定后以 `--runs 5` 重测**（外部模型端点曾出现 429 / IncompleteRead）。

## 换样本泛化性加固（规则包 0.1.2 → **0.1.3**，2026-10-15）

> 触发：项目负责人提出"换样本后这些路径还能稳定产出报告吗"。逐层评估后，
> 报告**产出**本身稳定（多层降级已验证），真正的风险是**清单老化**与**自有代码范围判定**，
> 故在本轮一次性加固，并顺带完成 R-PERM-03 的升档（路径 2）。

| # | 变更 | 作用 |
|---|------|------|
| G1 | 敏感权限清单补 Android 12/13+ 新权限 13 项（READ_MEDIA_IMAGES/VIDEO/AUDIO、NEARBY_WIFI_DEVICES、BLUETOOTH_SCAN/CONNECT/ADVERTISE、BODY_SENSORS(_BACKGROUND)、ACTIVITY_RECOGNITION、MANAGE_EXTERNAL_STORAGE、USE_BIOMETRIC、ACCESS_MEDIA_LOCATION） | 抗**清单老化**（新平台权限漏检） |
| G2 | `SmaliFacts.app_files` 兜底：包名前缀**零匹配**时退化为"排除已知库前缀"法，并记入 `rule_notes` | 抗多进程/插件化/包名与代码路径不一致导致的漏扫 |
| G3 | **R-PERM-03 静态排除力分档**（路径 2）：新增 `HIDDEN_CHANNEL_PATTERNS`（反射/JNI/动态加载）检测；无隐藏通道 → **已确认**（措辞带范围限定），有通道 → 待复核并列明 | 与 R-PERM-01 同构：按证据强度分档，升级有机械依据 |
| G4 | R-PERM-03 新增**声明即生效权限排除集** `DECLARATION_ONLY_PERMISSIONS`（QUERY_ALL_PACKAGES、SYSTEM_ALERT_WINDOW、REQUEST_INSTALL_PACKAGES 等 7 项） | 消除对"无需 API 调用即生效"的权限误判"未使用" |
| G5 | `Hit.context` 字段：规则可附带"机械层已完成的检索说明"，注入 B1 输入 | 信息不全会让 B1 判"无法判断"；补齐后 bad01 R-PERM-03 由 B1 判"确认可疑"并正确升档 |

**G4 的来源**：它来自 **B 通道的观察**（B1 在 observation 中指出 QUERY_ALL_PACKAGES 等
"属清单声明即生效的能力型权限，通常无对应 API 调用"）→ 经人/规则采纳为机械改进。
这是「B 提疑 → 规则改进」闭环的第一次实证。

**实测**：bad01 R-PERM-03 由「待复核」升为「已确认」（6 已确认 / 0 待复核）；全量 **84/84**。

**仍未覆盖（诚实声明）**：真泛化性需要**全新的、未经本系统参与设计的样本**验证
（现有 6 样本既是设计参照也是评分集）。此项留给 E3 对抗组——见 `docs/experiments.md` 后续实验。

## 机械能力升级：R-PERM-01 调用链级判定（规则包 0.1.1 → **0.1.2**，2026-10-15）

> 背景：此前 R-PERM-01 只能给"调度结构 × 敏感 API 在样本内共存"的**疑点组合**（待复核）。
> 项目负责人要求继续机械能力升级，让有完整证据的待复核项能定案。

| # | 变更 | 说明 |
|---|------|------|
| C1 | **R-PERM-01 升级为调用链判定** | 同一方法内：调度原语 + 可解析的调度目标（`const-class` / Intent 类参数 / `PendingIntent.get*` 上下文），且目标组件内含敏感 API → **调用链证据成立**（已确认）。无可解析目标时回退"样本级共存"（仍待复核）。**按证据强度分档**，不是一律升级 |
| C2 | 档位契约细化 | `RULE_META[R-PERM-01].max_status`：REVIEW → **CONFIRMED**（仅链证据走高；共存 hit 仍显式标 REVIEW，弱证据不会被一起拉高） |
| C3 | 措辞边界 | 两档均不得表述"真实执行时间/实际滥用"；链证据只断言"存在定时/后台触发敏感组件的结构" |
| C4 | 响应解析鲁棒性 | 模型输出出现尾部畸形（`, ""}`、`,]`）时，旧 `json.loads` 整段失败→兜底"无法判断"→**误降级结论**（实测 bad03 R-NET-02）。改为宽容解析（去尾逗号/孤立键 + raw_decode 取首个完整对象），并加 5 项回归测试 |
| C5 | B1 输入上下文增强 | 命中片段过窄导致模型常判"无法判断"（它自己在 observation 里说"片段未展示完整方法体"）。改为附带命中点 ±3 行 smali 上下文——**只补输入信息，不改判定标准**；实测后 bad03 七条标准结论全部定案 |

**实测**：bad03 的 R-PERM-01 由「待复核」升为「已确认」，证据链三处定位：
`MainActivity.smali:188`（setRepeating）→ `:161`（const-class RecordingService）→ `RecordingService.smali:46`（MediaRecorder）。

**未升级项（性质决定，非能力问题）**：`R-PERM-03` 仍为待复核——它是**排除性结论**
（"未发现使用"），反射/JNI/动态下发永远无法静态排除，档位由契约锁定，不因覆盖更全而改变。
若需变更档位口径，须先改真值表与 `docs/specification.md` §2 的规则契约（属契约变更，非实现变更）。

## B 通道提示词"去禁令"改造（2026-10-15，项目负责人指出后整改）

> **问题**：此前 B1/B2/B3 提示词里堆积了"不要/不许/禁止/宁缺毋滥/违反即失败"等否定式指令——
> 这些是我"改提示词→跑→看输出→再改"多轮调教沉淀下来的话术，等于在**输出端**裁掉了模型的
> 独立判断（上一轮讨论由项目负责人指出）。总档对 B 的限制只有"结论天花板=待复核"与"升级靠钉证据"，
> 未授权限制 B 的审查输出范围。

**整改（数据契约式，替代禁令式）**：

| 项 | 改动 |
|----|------|
| B1 提示词 | b1-v0.2 → **v0.3**：删掉全部否定指令；输入改为"检测点 + 误报口径 + 命中片段"（误报口径作为**数据**给）；输出 schema 加 `observation` 字段承载判定之外的补充观察 |
| B2 提示词 | b2-v0.3 → **v0.4**：删掉"禁止推测/复述不算/宁缺毋滥"；输出 schema 加 `confidence`（high/medium/low）用于**结构性分流** |
| B3 提示词 | b3-v0.1 → **v0.2**：删掉"硬性纪律（违反即失败）"；改为正向输出要求 |
| 报告 schema | 新增 `observations` 区（B 通道观察：低置信疑点 + B1 补充观察），**非结论、不计入三档**（规则包 0.1.0 → **0.1.1**） |
| 机械修复 | 钉证据 `_claim_entities` 的 URL 提取误吞中文右括号 `）`，导致实体比对失败、疑点无法正确归属（机械 bug，非引导问题） |

**实测结论**：去禁令后 B1 **并未**回到"判真伪/降档"——它按误报口径判"确认可疑"，
同时用 `observation` 说出"疑似示例/占位值"的观察。**说明之前的禁令本就不必要：模型能区分
"判定"与"观察"，是我没给 observation 出口才误以为需要堵嘴。** B2 也恢复了推理型观察
（如"攻击面来自网络入口而非组件"），以 `confidence: low` 进观察区。

**纪律（写入 specification.md）**：约束长在数据结构（字段/枚举/程序统计），不写在散文禁令里。

## RULE_PACK v0.1.0（2026-10-14，建设中，尚未对外发布）

建设期修正（内部迭代，未越出 0.1.0 边界；下不为例——发布后任何变更必须 bump）：

| # | 日期 | 变更 | 影响面 | 回归 |
|---|------|------|--------|------|
| 1 | 2026-10-14 | `SmaliFacts.app_files` 路径切分修复（`split('/',2)`→`smaliN/` 前缀正则） | P/C/N 类全部规则（自有代码判空） | bad03 从 3/7 → 7/7 命中；全量 84/84 |
| 2 | 2026-10-14 | `axml.py` UTF-8 StringPool 双长度字节解析修复 | manifest 数据源（UTF-8 池样本） | 合成夹具 6/6；全样本回归一致 |
| 3 | 2026-10-14 | `SENSITIVE_APIS` 类级模式去 `->`（配合 invoke/new-instance 行过滤） | R-PERM-01/02 | 单测修正后 26/26；全量 84/84 |

**版本规则**：规则包 0.1.0 在 E1 基线冻结后对外可见；此后：
- 规则/阈值/正则变更 → bump → `docs/changes.md` 记录 → 重跑靶场 → 更新真值（若真值表本身变更）。
- 历史 RUN 不被改写；新版本产生新 RUN。

## 观察项（记录的已知限制，待未来 Change 候选）

| ID | 内容 | 触发升级条件 |
|----|------|--------------|
| OBS-1 | R-CODE-02 不解析布尔实参（setJavaScriptEnabled(false) 亦计要素） | 出现"显式 false 被误报"的真实反例 |
| OBS-2 | R-MAN-01 隐式导出判定未按 targetSdk 分档（一律计入） | 出现 targetSdk≥31 且无 intent-filter 的误报例 |
| OBS-3 | R-PERM-01 组合判定为样本级共存（未做调用链可达性） | E2 Change 候选方向 |
| OBS-4 | 凭据模式宁宽勿漏（示例值照报），未设白名单 | 对抗组提出噪声挑战 |
| OBS-5 | `R-CODE-01` 弱模式用精确集合成员匹配带 MUTF-8 长度前缀的 dex 类型描述符，降级分支在现有样本上从未触发（EXP-6 实测：bad03 `substring_present=1` / `exact_membership=0`） | Change 候选批准，或出现「apktool 不可用 + 样本含动态加载」的真实降级场景 |

> **OBS-5 已闭环**：2026-11-11 随规则包 **0.1.4** 修复，详见下方「规则变更：0.1.3 → 0.1.4」；
> 保留本行作为发现记录，不删除。

## 结构变更：补齐项目级治理文档（2026-11-11）

> 性质：**文档结构变更，非规则变更**。不改 `RULE_PACK_VERSION`（仍 0.1.3）、不改判罚口径、
> 不动 `evidence/` 运行正本、不重跑样本；84 判点与 38 用例不受影响。
> 背景：项目此前只有分散的工程实践，治理约定、目标/计划/任务缺少可核查的单一入口。

| # | 变更 | 交付类 | 说明 |
|---|------|--------|------|
| S1 | 新增 `HARNESS.md` | design | 收拢开发规范 / AI 操作约定 / 代码规范 / 文档规范 / 日志规范 / 观测性约定；**收拢既有实践，不新造契约** |
| S2 | 新增 `GLOBAL.md` | brief | 项目级目标、三条核心承诺、成功标准、范围外清单、硬约束 |
| S3 | 新增 `PLAN.md` | brief / review | M0—M5 阶段归档、进度状态、下一步、计划变更规则；注明为归档式整理，非开工前预填快照 |
| S4 | 新增 `TASKS.md` | review | 任务分解规范（ID / 字段 / 状态值域 / 禁止事项）+ 当前未闭环任务台账，状态如实 |
| S5 | `AGENTS.md` 导航补 4 个入口 | — | 质量门命令补 `--no-evidence` / `--no-run`，避免实验性运行写进 `evidence/` |
| S6 | `总档.md` v0.5 → v0.6 | — | §7 目录树与六类交付物映射表同步；进度状态未变 |

**未闭环项不因本次变更而消失**：12 条决策复核签字、6 份报告签署、E1/E2/E3 交互、验证轮换仍为
`待签署 / 待排期 / 待执行`（见 `HARNESS.md` §8、`TASKS.md` §2）。新增文档不宣称任何材料已获批准。

## 结构变更：EXP-6 对照实验与文档规范化（2026-11-11）

> 性质：新增实验与文档，**不改规则包版本**（仍 0.1.3）、不动 `evidence/`、不影响 84 判点与 38 用例。

| # | 变更 | 说明 |
|---|------|------|
| S7 | 新增 `scripts/exp_datasource_ab.py` | ADR-0002 数据源实现 A/B 对照采集器；只读、不联网、不产生 RUN |
| S8 | 新增 `docs/experiment-protocol.md` | 变量控制、对比指标、计时起止、复算与协议变更规则 |
| S9 | `docs/experiments.md` 增实验 6 | 6 样本 × 2 方法 × 5 轮真实运行数据 + 负结果与成本口径；结果落 `review/exp_datasource_ab.json` |
| S10 | `HARNESS.md` 增 §1.5 自动化脚本配置、§4 文档元数据规范 | 脚本清单/参数/产物/退出码；新写文档须带项目名与版本 |
| S11 | `docs/decision-log.md` 补状态口径说明 | ADR「已采纳」= 方案已采用；决策表「待签署」= 复核签字未完成，二者不冲突 |
| S12 | `TASKS.md` 增 T-M4-07 | OBS-5 作为 Change 候选纳入台账 |
| S13 | `总档.md` v0.6 → v0.7、`AGENTS.md` 导航与命令同步 | §7 目录树、交付物映射表、修订记录 |

**实验结论摘要**：A 组在唯一正例 bad03 检出 3 条、B 组 0 条；5 个安静点两组一致；
耗时中位 A 78.787 ms / B 25.944 ms。漏检归因于匹配口径缺陷（OBS-5），**不是**设计取舍；
本轮未修改规则；**后续修复见下方「规则变更：0.1.3 → 0.1.4」**。

## 规则变更：0.1.3 → **0.1.4**（2026-11-11，OBS-5 修复）

> 触发：EXP-6 对照实验暴露 `R-CODE-01` 弱模式恒不命中。按「改规则 = 改版本」纪律执行：
> bump `RULE_PACK_VERSION` → 本文件记录 → 重跑靶场真值 → 补回归用例与前后差异。
> **历史报告与 0.1.3 成绩单不改写**；新成绩单另存 `review/truth_result_0_1_4.json`。

| # | 项 | 内容 |
|---|----|------|
| C1 | 根因 | `core/dexscan.py::_read_string_at` 从 `string_data_item` 起始位置直接解码，把 ULEB128 长度前缀当成字符串首字节，导致 `strings` / `type_descriptors` / `method_refs` 全带控制字符前缀（例 `'\x1eLdalvik/system/DexClassLoader;'`） |
| C2 | 修复 | 先跳过 ULEB128 长度字节再按 NUL 终止读取；**不改**任何规则的检测点、误报口径或档位上限 |
| C3 | 为何此前未暴露 | `R-STR-01/02` 用正则子串匹配，前缀不影响；`R-CODE-01` 弱模式用 `pat in set` 精确判断，恒 False；84 判点走强模式（apktool 可用），降级分支从未执行 |
| C4 | 版本 | `RULE_PACK_VERSION` 0.1.3 → **0.1.4**（`core/registry.py`） |
| C5 | 回归用例 | 新增 `tests/test_dex_weak_mode.py` 8 例（单/多字节 ULEB128、MUTF-8 内嵌 NUL、截断保护、合成 dex 解析、弱模式命中与档位、安静点、`find_type_refs`），合计 **46 例全过** |
| C6 | 真值回归 | 影子副本（不含 `key.txt`，B 通道自动降级）跑 `scripts/truth_check.py --no-evidence`：**84/84，硬错 0、噪声 0**；成绩单与 0.1.3 逐字节一致 |
| C7 | 前后差异 | EXP-6（0.1.3）→ EXP-7（0.1.4）：B 组检出 0/6 → **1/6**，样本级一致 5/6 → **6/6**，bad03 `exact_membership` False → True；A 组与其余 5 样本结论不变 |
| C8 | 影响面 | 正常路径结论不变；降级路径 `R-CODE-01` 现可给「待复核」弱证据；`DexFacts.find_type_refs` / `method_refs` 恢复可用（当前无规则依赖 `method_refs`） |
| C9 | 状态 | **OBS-5 已闭环**；`TASKS.md` T-M4-07 标「已实施，待具名人复核」， |

**未做的事**：不改 `evidence/RUN-*` 正本；不改 0.1.3 成绩单、汇总报告、真值表与签署台账；
不重跑通道 B 在线模型（本轮无需）；不改 E2 候选 CHG-004 的提案内容——其「冻结基线 0.1.3」为提案时点取值，
实施前须按当前规则包重新冻结基线。
**版本锚点同步**：`GLOBAL.md`、`handoff/README.md`、`docs/specification.md` 头部与 schema 示例、
`总档.md` v0.8、`docs/experiment-protocol.md` 改为以运行时版本为准。

## 结构变更：评价器重构为评价 Agent（2026-11-18）

> 性质：评价器架构重构，**不改 `RULE_PACK_VERSION`**（仍 0.1.4）、不动 `evidence/` 运行正本。
> 课件材料已按约定从项目目录移除，只保留提取后的判据，不入库 PPT 原文。

| # | 变更 | 说明 |
|---|------|------|
| S14 | 新增 `evaluator/skills/evidence-review/rubric.json` | 从 7 份课程 PPT（472 页）提取：项目评分构成 45/15/15/25 及细分、章节 9 维 Rubric、8 条最低质量红线、4 条评分校准、10 项可审查条目、四状态输出 Schema、证据来源/层级、预算、五道边界、K-1~K-6 与四类评价情境 |
| S15 | 新增 `evaluator/skills/evidence-review/SKILL.md` | 模型加载的工作流：角色、四工具协议、判定契约、预算/停止、输出 Schema、降级与校准 |
| S16 | 新增 `evaluator/contract.py` | 批准契约外置：互评必须显式契约；自评用本仓库规格层生成「未批准内部快照」 |
| S17 | `evaluator/tools.py` 重写 | 四个受限工具真正接入主循环；目标参数化；路径白名单由程序强制；`precheck` 降级为注册测试 `verify_claims` |
| S18 | `evaluator/agent.py` 重写 | 多轮 AgentLoop（自主选工具、预算、停止、append-only 轨迹）；四状态由机械核对收口，模型输出只进 `observations` |
| S19 | `evaluator/llm.py` 改多轮 | `chat()` 支持多轮消息；模型固定读本仓库 `key.txt`；失败自动降级确定性路径 |
| S20 | `cli.py evaluate` 参数化 | `--target / --mode self\|peer / --contract / --no-llm / --max-model-calls`；输出从 `evidence/<run>/evaluation.json` 搬到 `review/evaluation/`（历史评价件保留不改写） |
| S21 | 新增 `scripts/eval_calibrate.py`、`tests/test_eval_agent.py` | K-1~K-6 校准记录落盘；7 个离线回归用例，合计 **53 例全过** |
| S22 | 自评 6 个 RUN | 主样本走模型路径（`mimo-v2.6-flash`，7 次交互，输出 final + 8 条观察 + 6 条最小补查）；其余 5 个走确定性降级；轨迹与结果成对落 `review/evaluation/` |

**模型在自评中发现并已如实记录的两个问题**（不掩盖、不自动修复）：

1. **版本错配**：现有 6 个 RUN 正本是规则包 0.1.3 生成，当前契约为 0.1.4。按「旧证据不判新版本」，
  评价结果整体为 `INSUFFICIENT_EVIDENCE`，补查建议是「按 0.1.4 生成新 RUN 正本，或提供版本豁免记录」，
  历史正本不改写。
2. **存在性 ≠ 内容合格**：原机械层只查锚点存在就给 PASS 过于宽松。已收紧：只有 `verify_claims`
  机械核对通过的条目可给 PASS，其余标 `INSUFFICIENT_EVIDENCE` 并列出未做字段级内容核对的条目。

**未做的事**：不使用 DeepSeek Harness（见 ADR-0011）；不装任何依赖；不评对抗组项目
（材料与批准契约尚未交换，`--mode peer` 在无契约时返回 `INSUFFICIENT_EVIDENCE`）。

---

## 状态变更：本组签署与评价 Agent 重跑（2026-11-18）

> 性质：签署与重跑，**不改规则、不改判罚口径、不 bump `RULE_PACK_VERSION`**（仍 0.1.4）、不动 `evidence/` 运行正本。

| # | 变更 | 说明 |
|---|------|------|
| R1 | 6 份报告本组签署完成 | 余俊辉抽验（提交 `9cfdc03`）+ 周宗正复核（2026-11-18）；对抗组、教师两栏仍空 |
| R2 | 新增 `review/evaluation/SIGNOFF.md` | 6 份评价输出逐份签署；签的是「输出如实反映当前证据状态」，不是「报告已通过」 |
| R3 | 评价 Agent 重跑 | 同一输入重跑 6 份，结论与首跑一致（10 项全 `INSUFFICIENT_EVIDENCE`）：版本错配 + 未做字段级核对 |
| R4 | 治理文档状态同步 | `HARNESS.md` §8、`TASKS.md`（T-M4-06 / T-M5-06 / T-M5-09 / 新增 T-M5-13）、`docs/decision-log.md` §4、`总档.md` v0.10 |

**仍未闭环（不因本次签署而消失）**：12 条决策复核签字（复核人余俊辉）、T-M5-10 版本错配、
T-M5-12 字段级内容核对、E1/E2/E3 交互、R-1 模型横向评测。

---

## 状态变更：决策复核签字完成与全模型重跑（2026-11-18 17:13，提交 `25f22da`）

> 提交人：余俊辉。性质：签署 + 重跑，**不改规则、不改判罚口径、不动 `evidence/` 正本**。

| # | 变更 | 说明 |
|---|------|------|
| R5 | 13 条决策复核具名 | `docs/decision-log.md` 逐条填「余俊辉 已复核 2026.11.18」；D-04 标注 R-1 未闭环；T-M5-07 闭环 |
| R6 | 评价 Agent 全模型重跑 | 6 份均为 `llm`（模型 `mimo-v2.6-flash`，8—9 次交互、均输出 final），结论仍为 10 项全 `INSUFFICIENT_EVIDENCE`；产物为 08:58—09:07 批次 |
| R7 | 评价输出批次待归一 | 现存 12 份 EVAL：05:26 批次 6 份（已登记 `SIGNOFF.md`）+ 08:58 批次 6 份（未登记）；归一见 T-M5-14 |
| 更正 | 决策条数口径 | 全表为 D-01—D-13 共 **13 条**；此前多处写「12 条」，漏计 D-13，已改 `docs/ai-disclosure.md` 核对清单与 `总档.md` 进度 |

**评审备注**：`docs/decision-log.md` 的表格被整体重排为对齐格式（含行尾双空格），
内容与状态列未变，仅为格式差异，导致该文件 diff 较大；后续编辑建议关闭自动格式化，避免历史行噪声。

---

## 文档重组：一份文档只回答一个问题（2026-11-18）

> 起因：教师点评"AI 味太重、说的不是中文""任务划分笼统""文档之间重复率高、单份结构乱"。
> 性质：只改结构和写法，**不改规则、不动 `evidence/` 正本、不 bump `RULE_PACK_VERSION`**（仍 0.1.4）。

| # | 变更 | 说明 |
|---|------|------|
| S23 | 新增根目录 `README.md` | 人看的入口：项目一句话、三条命令、文档归属表（哪份文档管什么、不管什么） |
| S24 | `总档.md` v0.11 → v0.12 | 611 行压到 348 行。规则明细交给 `specification.md`、接口格式交给 `specification.md` 第 3/4 节、目录细节交给 `HARNESS.md` 第 1 节、进度交给 `PLAN.md`、任务交给 `TASKS.md`；73 行修订历史移出，只留一句指向本文件 |
| S25 | `TASKS.md` 重写 | 每条任务拆到步骤，每步写清产出和"怎么算做完"；补上 T-M5-10 / T-M5-12 / T-M5-14 的具体步骤；已完成的任务单独成表 |
| S26 | `PLAN.md` 重写 | 成为阶段与进度的唯一来源，删掉"以总档 §9 为准"却又自存一份的矛盾；更新过期事实（提交数、M5 签署状态） |
| S27 | `GLOBAL.md` 重写 | 改成白话；修正"38 个单元测试"为 53；签署状态改为与 `signoff.md` 一致 |
| S28 | `AGENTS.md` 压缩 | 从 49 行压到指针 + 六条禁令 + 命令表，删掉与 `HARNESS.md` 重复的规范条文 |
| S29 | `HARNESS.md` 补映射表 | 六类交付物映射表原来在总档 §7，移到文档规范一节；修掉指向已删除小节的引用 |
| S30 | 引用修正 | ADR-0006、`changes.md` 旧条目里指向"总档 §5.3/§5.1"的引用改指 `specification.md` §6/§2；`GLOBAL.md`、`HARNESS.md` 里指向"总档 §9"的进度引用改指 `PLAN.md` |

**没做的（下一批）**：`docs/` 层的合并还没动——`brief.md` 与 `requirements.md` 有重叠、`state-model.md` / `acceptance-matrix.md` 与 `specification.md` 有重叠、`experiment-protocol.md` 可并进 `experiments.md`、`release.md` 与 `handoff/README.md` 重复。
这些涉及删文件或改交付物归属，等确认后再做。

---

## 文档合并（第二批）：把四组重复文档收成两处（2026-11-18）

> 性质：合并与改写，**不改规则、不动 `evidence/` 正本、不 bump `RULE_PACK_VERSION`**（仍 0.1.4）。

| # | 变更 | 说明 |
|---|------|------|
| S31 | `docs/brief.md` 并入 `docs/requirements.md` | 问题陈述、调研结论、做与不做直接写进需求文档开头；责任分工并到 `docs/team-roster.md`；`brief.md` 删除。课程要求的 brief 类内容由 `GLOBAL.md`（目标）+ `requirements.md`（问题与范围）承载 |
| S32 | `docs/state-model.md`、`docs/acceptance-matrix.md` 并入 `docs/specification.md` | 作为第 7 节（状态机与预算）、第 8 节（A-01—A-10 验收）、第 9 节（K-1—K-6 校准判例）；两个文件删除。规约现在一份文档说清"规则、格式、状态、验收" |
| S33 | `docs/release.md` 并入 `handoff/README.md` | 环境、启动、复现、重置、已知问题 I-1—I-8、合规、目录导航合并成一份交接包；`release.md` 删除。已知问题的编号 I-1—I-8 原样保留，避免其他文档的引用失效 |
| S34 | `docs/experiment-protocol.md` 保留 | 复核后判定它和 `experiments.md` 是"方法 / 数据"分工，硬合并会变成 260 行的混合体。改为在 `experiments.md` 开头声明"变量与计时只看协议"，两边不重复 |
| S35 | 全库术语替换 | `口径`→`规则`/`判定`、`落盘`→`存盘`、`收口`→`判定`、`锚点`→`位置`/`对应`、`事实本体`→`同一份结果`、`可核查`→`能核对`、`未闭环`→`未完成`；改完逐条抽查，修掉替换产生的病句（如"规则规则"） |
| S36 | 引用同步 | 删除四份文件后，`GLOBAL.md`、`HARNESS.md`、`PLAN.md`、`README.md`、`docs/decision-log.md`、10 份 ADR、`docs/ai-disclosure.md`、`docs/impact-map.md`、`docs/research/` 中的引用一并改指新位置 |

**结果**：md 文件从 43 份降到 39 份，`docs/` 从 17 份降到 13 份；需求、规约、交接三处各自只有一份正文。

---

## 代码审查修复：结论全量化 + 敌对样本防御（2026-11-23）

> 性质：**结构变更**（报告形态 + 预处理防御 + B 通道 prompt），`RULE_PACK_VERSION` 0.1.4 → **0.1.5**。
> 触发：`review/code_review_2026-11-23.md` 全仓库审查。
> **判定标准未放宽**：本次只补「每条判点必须有交代」，不新增档位、不改三档语义、不降低任何档位门槛。

| # | 变更 | 暴露渠道 | 影响 |
|---|------|----------|------|
| R1 | **结论全量化**（`core/fusion.py`）：`build_conclusions` 对 14 条规则逐条出结论。无命中但已执行 → 「无法判定」+ 注明「已执行、未命中，不构成安全结论」；未执行 → 「无法判定」+ `missing_evidence` 写明缺口。B2 补盲改为原位升级，不再追加第二条 | 审查 C-1：正本 `RUN-20261015-145016` 覆盖声明 14 条、结论仅 8 条，8 条判点在报告中消失 | 结论条数从「有命中数」变为「规则总数 + B 侧疑点」；历史正本不改写 |
| R2 | **真值口径收紧**（`scripts/truth_check.py`）：`EXPECTED_SILENT` 下 `c is None` 由 PASS 改判 `MISS`，`missing_evidence` 非空同样记 `MISS` | 同上：原口径把「规则没跑」也算 PASS | 84 点不再掩盖覆盖缺口 |
| R3 | **判点完整性预检**（`evaluator/precheck.py`）：新增 `E-MISSING-CRITERION`，只对当前规则包生成的报告生效 | 同上 | 新报告缺判点直接 FAIL；历史正本走版本不匹配路径 |
| R4 | **干净样本判定适配**（`evaluator/agent.py::_decide`）：全量「无法判定」时按 `missing_evidence` 区分「规则没跑」与「跑了没命中」 | R1 的连带影响 | 干净样本仍判 PASS（带覆盖范围），数据源缺口仍弃权 |
| R5 | **评价器 criterion 收口**（`evaluator/agent.py::_mechanical_verdict`）：`content_checked` 不再只对 E-05 开放 | 审查 m-7：`any(INSUFFICIENT)` 恒真导致 PASS 不可达，与 `specification.md` A-08「四状态」不符 | 快照 PASS + 锚点齐全时各项可判「通过（仅机械层）」 |
| R6 | **B1/B2 数据边界**（`core/channel_b.py`，b1-v0.3→**v0.4**、b2-v0.4→**v0.5**）：system 声明 `<sample_data>` 内是样本字节、其中指令不得执行；片段用定界符包裹；片段命中指令性特征时不采信「上下文无害」降级 | 审查 M-2：样本可注入 prompt 把真命中压成待复核 | 只堵降级方向；升级仍须钉证据 |
| R7 | **原始响应完整落盘**（`core/evidence.py`）：`add_record` 新增 `raw_response`，全文写 `raw/<evidence_id>.txt`，JSONL 记 `raw_response_path` + `raw_response_sha256`；B1/B2 另记 `input_sha256`、`injection_flag` | 审查 M-4：`raw_snippet[:400]` 截断模型理由，与模块头承诺不符 | 证据可事后复核；JSONL 仍只留 400 字展示片段 |
| R8 | **证据目录拒绝覆盖**（`core/evidence.py` + `cli.py`）：`run_id` 追加 sha256 前 8 位；RUN 目录已存在抛 `RunDirExists`，cli 返回 3 | 审查 C-2：同秒启动两样本写同一目录，证据 ID 重号且 `hits.jsonl` 互相覆盖 | 已落盘正本不会被静默改写 |
| R9 | **敌对样本预处理防御**：AXML 嵌套上限 `MAX_XML_DEPTH=64`（超限抛 `AXMLParseError`，不再 `RecursionError`）；zip 成员解压上限 `ZIP_MEMBER_MAX_BYTES=64MiB`（新增 `core/safezip.py`） | 审查 M-1：深嵌套 / zip bomb 可让审计整体退化为「样本预处理失败」 | 畸形样本 → 样本级无法判定，语义正确 |
| R10 | **DEX method_refs 修正**（`core/dexscan.py`）：`class_idx` 改按 type_ids 下标取，不再误用 strings 表 | 审查 M-3 | `method_refs` 内容随之变化；当前无规则依赖（预防性） |
| R11 | **健壮性杂项**：规则模块导入异常纳入单规则降级；`_read_string` 捕 `IndexError`；`_build_tree` 校验标签配对；`SmaliFacts.file_set`；`_chat` 重试耗尽抛明确异常；`cmd_reset` 清理演练临时目录；B 通道记录另存 `channel_b/records.jsonl`；报告遇未知档位 fail-fast；AXML 空值属性输出 `name=""` | 审查 m-1/m-2/m-3/m-4/m-5/m-6/m-8 及 Nit | 不改变正常样本结论 |
| R12 | **单测**：53 → 61（新增 C-1 / C-2 / M-1 / M-4 回归 8 项） | — | — |
| R13 | **e2e 归一化修正**（`scripts/e2e.py`）：`observations`（B 通道模型原声、非结论）不再参与 A-09 逐字段比较，只比条数 | 判点全量化后 B1 调用面变大，观察区波动每次都会触发假失败；A-09 契约本就只要求「14 条规则结论一致」 | A-09 只对标准结论报差异 |

**影响面**：

- 新 RUN 的 `report.md` 会列出全部 14 条判点（多数为「无法判定 · 已执行未命中」），比历史报告长；
- 历史正本（0.1.3 / 0.1.4）保持原样，评价时走 `version_mismatch` → `INSUFFICIENT_EVIDENCE`；
- 契约 `rule_pack_version` 需同步到 0.1.5，才能对新报告判 PASS。

**回归**：单测 61/61；K-1—K-6 校准 6/6；靶场真值 `--no-evidence` 重跑 **84 点 · 一致 84 · 硬错 0（FP 0 / 漏检 0 / 档位错 0）· 噪声 0**（结果见 `review/truth_result.json`）。
六个样本的新报告均为 14 条标准判点全量出结论、覆盖缺口 0。

---

## 第二次审查修复：汇总回归 + 权限模式补齐（2026-11-23）

> 性质：**结构变更**（汇总判定 + 规则表），`RULE_PACK_VERSION` 0.1.5 → **0.1.6**。
> 触发：`review/第二次审查/code_review_2026-11-23_第二次.md` 全仓库独立审查（M-1 / m-1 / m-2）。
> **判定标准未放宽**：只补齐"全量化改造的连带适配"与"权限使用模式覆盖"，不改三档语义、不降低任何档位门槛。

| # | 变更 | 暴露渠道 | 影响 |
|---|------|----------|------|
| S1 | **B3 汇总干净样本判定修正**（`core/summary.py`）：新增 `substantive_conclusions()` 作为唯一判据（标准结论中非 UNDECIDED 的实结论），输入组装与模板渲染三处共用；把"无检出样本"判据从"没有标准结论"改为"没有实结论" | 第二次审查 M-1：全量化后每条规则都有 UNDECIDED 占位，干净样本被统计成"无检出 0 个 / 14 条结论"，汇总报告自相矛盾 | B3 prompt 版本 b3-v0.2 → v0.3；干净样本正确计入 n_quiet；不改变审计结论 |
| S2 | **补齐 12 项 Android 12/13+ 敏感权限使用模式**（`core/registry.py` `PERMISSION_USAGE_PATTERNS`）：READ_MEDIA_*、ACCESS_MEDIA_LOCATION、NEARBY_WIFI_DEVICES、BLUETOOTH_SCAN/CONNECT/ADVERTISE、BODY_SENSORS(_BACKGROUND)、ACTIVITY_RECOGNITION、USE_BIOMETRIC | 第二次审查 m-1：43 项敏感权限中 35 项需模式，原仅 23 项，12 项声明后永不判"未发现使用" | R-PERM-03 对这 12 项从"检测空转"变为可比对；靶场未声明这些权限，既有 84 判点不受影响 |
| S3 | **B 通道探测调用记账**（`core/channel_b.py` + `cli.py`）：`BResult.probe_calls` 记录连通性探测；`meta.json` 增 `channel_b_probe_calls`，实际 HTTP 调用数可从报告还原 | 第二次审查 m-2：ping 探测不计预算、不计调用，报告"调用 N 次"比实际少 1 | 预算口径不变（探测不占判定预算），成本可追溯 |
| S4 | **清理未使用导入**（`core/adapters.py`、`core/channel_a.py`、`core/rules/net/r_net_01.py`、`tests/test_evidence_store.py`） | 第二次审查 Nit | 无行为影响 |
| S5 | **单测**：61 → 66（新增 `tests/test_summary.py` 4 项 M-1 回归 + `test_rules.py` 权限模式覆盖断言 1 项） | — | — |
| S6 | **e2e 归一化补齐**（`scripts/e2e.py`）：A-09 比较前剔除 `observations_count` / `_b_side_count` 两个 LLM 波动计数（保留取值用于 WARN），避免 B 通道开启时模型原声条数波动触发假失败 | 修复后 e2e 验收发现：标准结论完全一致，但两个波动计数字段参与 `r1==r2` 致 A-09 误报 FAIL（R13 只归一化 observations 内容，漏了 count） | A-09 只对 14 条标准规则结论判确定性；B 侧波动继续按 I-6 单列 WARN |

**影响面**：

- 新 RUN 的 `report.json` 版本为 0.1.6；历史正本（0.1.3/0.1.4/0.1.5）评价时走 `version_mismatch`；
- B3 汇总报告对干净样本的统计口径修正，不影响任何已签署审计报告；
- 12 项新权限的使用模式为静态模式扩充，靶场未使用，真值判点不变。

**回归**：单测 66/66；靶场真值 `--no-evidence` 重跑 84 点全量核对（结果见 `review/truth_result.json`）。

---

## 第三次审查（GLM-5.3-Flash + code-review-analyzer）修复：语义失真与韧性（2026-11-24）

> 性质：**实现修复 + B3 提示词版本**，`RULE_PACK_VERSION` 不变（0.1.6）——不动规则、判罚口径与三档语义。
> 触发：第三次审查核实的语义失真与韧性缺陷清单（完整报告见 `review/第三次审查/code_review_2026-11-24.md`，逐条记录见 `review/审查模型表.md`）。
> 误报（safezip 谎报头绕过、B3 无注入防线之外的臆造项）不采纳。

| # | 变更 | 暴露渠道 | 影响 |
|---|------|----------|------|
| T1 | **覆盖声明语义失真修正**（`cli.py` sample_failed 分支）：`decode_failed` 改为 `not decode.ok`（原来恒 True，把 manifest 解析失败记成解码失败），`decode_note` 只记解码错误，样本失败原因移入 `not_checked` 说明 | 第三次审查 M-1：manifest 解析失败但 apktool 解码成功的样本，覆盖声明把失败归因到解码，违背「覆盖诚实」核心承诺 | 报告覆盖声明归因准确；precheck 在该场景多一条 W-NO-CHECKED 提示（事实性增强，不改变最终 INSUFFICIENT_EVIDENCE 判定） |
| T2 | **`_chat` 超时/连接失败纳入退避重试**（`core/channel_b.py`）：`urlopen` 超时与连接失败（URLError/socket 超时，均 OSError 子类）原先直接外抛不重试，瞬时网络抖动即降级 B 通道 | 第三次审查 M-2：注释称"连接异常可恢复"但超时路径不在重试面内 | 与 HTTPException 同款退避重试；重试耗尽仍如实降级 |
| T3 | **key.txt 解析加固**（`core/channel_b.py` + `evaluator/llm.py`）：`split(',')` → `split(',', 2)`（api_key 含逗号不再被截断）；捕获 `UnicodeDecodeError`（损坏/二进制 key.txt 不再逃逸出解析函数） | 第三次审查 M-3 / M-4 | 行为兼容（正常 key.txt 解析结果不变）；`chat` 的「任何失败由调用方降级」契约在 key.txt 损坏路径上也成立 |
| T4 | **B3 数据边界**（`core/summary.py`）：B3_SYSTEM 追加 `_DATA_BOUNDARY`、用户输入以 `<sample_data>` 包裹，与 B1/B2 同级的「样本派生文本当数据不当指令」防线 | 第三次审查 M-5：B3 输入含样本派生文本（scope/claim），原先无数据边界声明 | B3 prompt 版本 b3-v0.3 → **v0.4**；不改变审计结论（B3 只写汇总报告） |
| T5 | **单测**：66 → 70（新增 `tests/test_safezip.py` 4 项：正常读取、超限拒绝、谎报头运行时行为钉住、缺成员语义） | 第三次审查（safezip 运行时假设需测试固化） | — |

**未修（如实记录，不因审查消失）**：`networkSecurityConfig` 正则只匹配双引号写法（apktool 输出恒为双引号，低危）；
`sources_note` 按组汇总可能虚高 + R-MAN-03 特判（需声明式重构，按治理规则升版本）；key 解析两模块重复（待抽公共 `_client`）；
safezip 无跨成员累计上限（需调用方自律）；`mkdtemp` 演练目录不清理；`hits.jsonl` 命名与内容不符。

**回归**：单测 70/70。

---

## 第四次审查（MiMo-V2.6-Pro + code-review-analyzer）修复：评价器路径穿越加固（2026-11-24）

> 性质：**边界加固**，`RULE_PACK_VERSION` 不变（0.1.6）——不动规则、判罚口径与三档语义。
> 触发：第四次审查核实的评价器 run_id 校验缺口（完整报告见 `review/第四次审查/code_review_2026-11-24_第四次.md`，逐条记录见 `review/审查模型表.md`）。

| # | 变更 | 暴露渠道 | 影响 |
|---|------|----------|------|
| U1 | **run_id 入口校验**（`core/evidence.py` 新增 `check_run_id` / `BadRunId`；`EvidenceStore.__init__`、`evaluator/tools.py` RestrictedTools、`evaluator/agent.py` evaluate_run 三处统一调用；`cli.py cmd_evaluate` 捕获后友好报错退出 2）：白名单正则 `^RUN-[A-Za-z0-9][A-Za-z0-9_-]*$`，拒绝 `..`、路径分隔符、绝对路径 | 第四次审查 U1：三处 `os.path.join(root, run_id)` 未校验，`cli.py evaluate --run` 可传入穿越 run_id，在 evidence/ 根外创建 RUN 目录 / 读取 JSONL，绕过 `_safe_path` 白名单 | 合法 run_id（RUN-20261015-145536、RUN-20261124-121104-3356097a 等历史格式）行为不变；非法 run_id 明确报错 |
| U2 | **单测**：70 → 72（新增穿越拒绝回归 2 项：`tests/test_evidence_store.py::test_path_traversal_run_id_rejected`、`tests/test_eval_agent.py::test_run_id_traversal_rejected_in_tools`） | — | — |

**未修（沿袭治理待办，如实记录）**：B1 循环体 RULE_META/_hits_with_context 在降级 try 之外；`advance('DONE')` 与 `build_report_json` 顺序；R-MAN-03 特例声明化 / `sources_note` 汇总口径 / key 解析抽公共 `_client`（需升版本）；`networkSecurityConfig` 正则只匹配双引号；safezip 无跨成员累计上限；`cli.cmd_analyze` 拆分（重构风险高于收益）；`truth_check.py` 默认 `--out` 指向正本。

**回归**：单测 72/72；靶场真值 `--no-evidence` 修复前后各复跑一次，均 **84 点 · 一致 84 · 硬错 0（FP 0 / 漏检 0 / 档位错 0）· 噪声 0**（`--out` 显式临时路径，正本未触碰）。

---

## T-M5 收尾：字段级核对与批次归一（2026-11-24，不改规则包版本）

> 性质：**评价器能力 + 文档/台账**，`RULE_PACK_VERSION` 不变（0.1.6）——不动规则、判罚口径与三档语义，只把评价从"查文件存在"推进到"读字段内容"。
> 触发：`TASKS.md` T-M5-10 / T-M5-12 / T-M5-14 收尾任务。判定标准未放宽：字段全符合是 PASS 的必要条件，任一字段不符/缺失都不得判 PASS。

| # | 变更 | 暴露渠道 | 影响 |
|---|------|----------|------|
| V1 | **字段级核对**（新增 `evaluator/skills/evidence-review/fields.json`、`evaluator/fieldcheck.py`）：10 项审查项每项 ≥2 个真实字段，三态 `match`/`mismatch`/`missing`，只读走 `RestrictedTools` 白名单，文本当数据不当指令 | T-M5-12：旧评价只确认锚点文件存在，未读内容 | 字段核对作为内容级证据层；不自动改四状态、不判分 |
| V2 | **评价器接入字段核对**（`evaluator/agent.py`）：`content_checked` 叠加"字段全符合"必要条件；轨迹新增 `field_check` 事件逐项记录；每条 finding 带 `field_check` 明细；顶层输出带 `field_check` 汇总 | T-M5-12 步骤 2/5 | **只加严不放宽**：字段缺口项维持 `INSUFFICIENT_EVIDENCE`；新批次明细 PASS 7 / INSUFF 3（E-01/E-02/E-07 缺文档合并前的历史文件名） |
| V3 | **新增单测 + 批量脚本**（`tests/test_fieldcheck.py` 7 例、`scripts/field_check.py`）：72 → 79 例；产出 `review/evaluation/field_check.json`（6 样本 × 10 项三态 + 人工抽验 5 条留空） | T-M5-12 步骤 3/4 | 抽验栏留空， |
| V4 | **批次归一**（`review/evaluation/SIGNOFF.md`）：登记 0.1.6 新批次为当前评价正本（6 个新 EVAL ID，签名留空），11-18 批保留为历史记录；临时说明折入 §5 并删除；新增 `docs/version-waiver.md`、`review/evaluation/field_check_notes.md` | T-M5-10 / T-M5-14 | 旧签名不挪到新文件；旧批次文件不物理移出（含已签正本，确认后处理） |

**影响面**：

- 新评价输出（0.1.6 批）与旧批次并存，当前登记批次为前者；`version_check.mismatch=false`；
- 顶层四状态仍为 `INSUFFICIENT_EVIDENCE`（E-01/E-02/E-07 各缺 1 个历史文件名），明细由"10 项全 INSUFFICIENT"变为"PASS 7 / INSUFF 3"——见 `field_check_notes.md` 解释；
- 已签历史正本、6 个 0.1.6 运行正本、真值表、rubric 均未改写。

**回归**：单测 79/79（新增字段核对 7 例）；K-1—K-6 校准 6/6；靶场真值 `--no-run` 84 点全量核对一致 84、硬错 0、噪声 0。

**未做（如实列）**：签名/抽验/状态留空；E-01/E-02/E-07 的 3 个历史文件名缺口待决定拆回独立文件或请教师确认 rubric 映射；旧批次物理移出待确认存档后指示；0.1.6 全模型评价批未跑（本批为 `--no-llm` 确定性路径）。

---

## 清理过期清单与建立"不建第二台账"约定（2026-11-24）

> 性质：**文档治理变更**（不涉规则包，`RULE_PACK_VERSION` 保持 0.1.6）。
> 触发：审查发现"待办清单"类文件反复生成且不回填完成状态，`T-M5_待签署清单.md` 9 项中多项已在同批提交完成，清单仍写"待办"，会误导签署人。

| # | 变更 | 影响 |
|---|------|------|
| C1 | 删除 `review/T-M5_待签署清单.md`、`review/signoff_prep_0.1.6.md`：两份均为阶段性快照，所列事项已写入权威台账（`SIGNOFF.md` §2、`field_check.json`、`docs/signoff.md`、`team-roster.md`），逐项核实未丢信息 | 签署状态回到两处权威台账，不再有第三份过期转述 |
| C2 | `review/signoff_prep.md` 状态由「生效」改「归档」：对应 0.1.3 历史批次，保留作追溯，当前状态看 `docs/signoff.md` | 历史件不冒充当前待办 |
| C3 | `HARNESS.md` §4 新增「不建第二台账」约定，文件版本 v1.1 → v1.2：待办清单写入台账后即删除；需留的是决策解释，不是"谁还没签"的清单 | 防止后续审查再生成同类过期清单 |

**边界**：不改任何规则、阈值、schema、判定标准；`RULE_PACK_VERSION` 不变；已签署台账与运行正本未动。

---

## 评价器通用化与评分框架修正（2026-11-25）

> 性质：评价器能力变更，`RULE_PACK_VERSION` 不变。

| # | 变更 | 影响 |
|---|------|------|
| S30 | `rubric.json` 1.2→1.3：新增 `evaluation_scoring`，按课程 S1—S4 完整 100 分框架定义 15 个子项，每项引用支撑的 E 项 | 评测分有课程依据，不再是 E 项 82 分的孤立数字 |
| S31 | E 项 `score_suggestion` 保持 null；评测分独立到顶层 `evaluation_scores[]`，带子项 ID/分数/满分/理由/证据引用/层级 | 审查与评分分离 |
| S32 | HTML 评测分区按 S1—S4 子项展示得分、满分、扣分理由、证据引用与层级；未评项显示「未评」，不猜分 | 报告逐项给分与证据链 |
| S33 | `SKILL.md` / `agent.py` 提示词注入评分子项清单；越界丢弃、未定义子项丢弃 | 模型给的分数受框架约束 |
| S34 | HTML 删除逐项签署栏、顶部签署状态与 `.sign` 样式 | 导出报告只保留判定、扣分原因、证据链、补查与分项评测分 |
| S35 | JSON 删除 `signoff_chain`、`human_signoff`（顶层与 findings）；快路径控制台删除签署栏 | 评价产物不含签署字段 |
| S36 | `SKILL.md` / `rubric.json` 输出 schema 删除签署字段；`calibration.py` 夹具删除 `human_signoff` | 文档与产物一致 |

---

## 评价器默认改为纯 harness 评分（2026-11-25）

| # | 变更 | 影响 |
|---|------|------|
| S37 | 新增 `evaluator/scoring.py` + `scoring-fields.json`：15 个子项挂真实字段 | 不调 API 也能覆盖全部子项 |
| S38 | `agent.py` / `cli.py` 默认 `use_llm=False`；`--llm` 改为显式开启 | 默认路径无 API 调用、不需要 key |
| S39 | 评分字段锚点校正；HTML 评测分区标注；去掉「未判定」兜底 | 分数不再被误读为质量满分 |

---

## 评分改为 harness 主观判断（2026-11-25）

> 触发：纯机械按字段符合比例算分得到 100/100——评分必须根据证据满足程度主观判断。

| # | 变更 | 影响 |
|---|------|------|
| S41 | `scoring.py` 从机械算分改为**证据包生成器**：逐子项返回字段核对 + 原文片段，不产出分数 | 机械层只摆证据，不猜分 |
| S42 | `agent.py` 默认 `scoring_status=pending_harness`；新增 `apply_scores()` 回填分数 | 分数由执行评价的 agent 看过证据后主观给出 |
| S43 | `cli.py` 新增 `--apply-scores <EVAL.json> --scores-file <scores.json>` | 先跑证据包，再回填分数 |
| S44 | HTML 开头新增醒目评分区：总分大字 + S1—S4 四张分项卡片 + 进度条 | 分数在报告开头第一屏 |

**评分口径**：主观分按「证据对该评分项的满足程度」判断——章节齐全不代表写得好，
个人自述空白、结对交互未发生、疑点未钉都要扣分。扣分理由必须指到具体缺口。

---

## 清理复评表述与评分流程自描述（2026-11-25）

| # | 变更 | 影响 |
|---|------|------|
| S45 | 全局删除相应流程表述：evaluator 代码与配置、SKILL.md、AGENTS.md、handoff、ADR、decision-log、signoff 流程节 | 已发生的具名复核签名事实保留，只改流程描述措辞 |
| S46 | `evaluate` 输出新增 `next_action` 与 `scores.template.json` | 评价器自己声明下一步（模板路径 + 回填命令），调用方读输出即可发现流程 |
| S47 | SKILL.md / AGENTS.md 的流程说明由「两步硬编码」改为「读 next_action」 | 流程从文档私令变成输出契约 |

---

## 0.1.7 · 修 E3 四条确认缺陷（2026-11-25）

> 冻结基线：0.1.6 / commit `6276391` / 12 RUN / 84 判点。

| # | 变更 | 影响 |
|---|------|------|
| C7-1 | `core/rules/common.py` `is_empty_method_body` 扩宽为「无实质校验」：允许日志类 invoke，仍拒绝 throw/条件跳转/证书对象调用（F-01） | 假 TrustManager 加一行日志不再绕过 R-NET-01 |
| C7-2 | `core/axml.py` 权限声明收 `uses-permission-sdk-23`（F-02，CHG-005） | 标准 API23+ 标签不再漏报 |
| C7-3 | `core/rules/man/r_man_05.py` 检查 `android:enabled="false"`，命中降待复核并写明禁用（F-03） | 禁用 Receiver 不再误报 |
| C7-4 | `core/rules/perm/r_perm_01.py` 无链回退时声明接口/回调链未解析；`core/fusion.py` 聚合到 `missing_evidence`（F-05） | 复核者能区分「查过未解析」与「根本没查」 |
| C7-5 | `rule_pack_version` 0.1.6 → 0.1.7；CHG-004 落冻结基线 + 范围修正 | 规则变更留版本锚点，旧正本不改写 |
| C7-6 | `scripts/truth_check.py` 产物补 `rule_pack` / `commit` 字段 | 84/84 能回答对应哪个版本与 commit |

**回归**：单测 91/91；靶场 84 判点一致 84、硬错 0；K-1~K-6 6/6；
对抗组自动验收 `fix_verification_result_regression.json` **4/4 PASS**（baseline 本机复跑 4/4 复现）。

**未做**：CHG-004 只补 `missing_evidence` 边界声明，V-1 Runnable 跨方法链未升为已确认；
E1 三条质询的回应栏留空；个人自述两栏留空。

### CHG-005 补充实施

- `PermissionDecl` 增 `tag` 字段；`r_man_02` 按权限名去重，两种标签混用时只出一条 Hit，
 证据片段写真实标签；
- 单测 89 → 91（新增 `test_sdk23_permission_tag_dedup`、`test_sdk23_only_permission_reported`）；
- F-02 验收重测仍 PASS；CHG-005 已落 `docs/impact-map.md`。

### 0.1.7 验收结果

- 对抗组自动验收 **4/4 PASS**；E2 样本集 V-1/V-2 本机跑通（`e2_v2v4_local.json`）：
 V-1 待复核 + `missing_evidence` 写明 Runnable 链未解析；V-2 仍待复核（防串链硬门通过）。
- 新 RUN 正本 `RUN-20261125-*` 生成；旧 0.1.6 证据在新版本下被评价器正确判为版本错配，
 历史正本未改写。

---

## 文档口吻统一

> 性质：文档表述变更，不涉规则包。

- 清理文档里所有人机对举的流程表述，统一用项目自己的口吻；
- 已发生的具名复核签名、`evidence/` 运行正本一律不动。

---

## 评价分数提升：86 → 93（2026-11-25）

> 性质：文档与字段映射变更，不涉规则包，`RULE_PACK_VERSION` 保持 0.1.7。

| # | 变更 | 影响 |
|---|------|------|
| S48 | `fields.json` 三个历史文件名锚点改到合并后文档：brief→requirements §0、acceptance-matrix→specification §8、release→handoff；从 `file_exists` 改为 `text_all`，比原来更严 | E-01/E-02/E-07 字段全 match |
| S49 | `rubric.json` 的 `expected_evidence` 同步去掉已删除的 brief/acceptance-matrix/state-model/release | 审查项从 PASS 7 / INSUFF 3 升到 **PASS 10** |
| S50 | `docs/events.md` 回 E1 三条质询：语义强度匹配未实现认下来、旧批次无 commit 锚点认下来、84/84 收缩为自建靶场回归门；事件状态更新为已发生 | E1 交叉审查闭环 |
| S51 | `docs/team-roster.md` 补两人个人自述草稿，按 ADR/decision-log/SIGNOFF/对抗组产物的实际事实写，未完成的如实列 | S4 四项待本人审后计分 |

**回归**：单测 91/91、84 判点一致 84、K-1~K-6 6/6；判定指纹 `84575d4a…`；
评价总分 **86 → 93**，审查项全 PASS。

**仍扣 7 分**：V-1 Runnable 链只声明边界未升档（1）、模型未横向评测（2）、
主观评分无跨人对照（1）、个人自述待审（3）。自述草稿需本人核对改成自己的话。

---

## PLAN/TASKS 未完成项收口（2026-11-25）

> 性质：状态同步与签署对齐，不涉规则包，`RULE_PACK_VERSION` 保持 0.1.7。

| # | 变更 | 影响 |
|---|------|------|
| S52 | 6 份 0.1.6 评价输出的 `human_signoff` 从 pending 同步为台账已有事实（余俊辉 2026.11.24），`signoff_chain` 去掉旧流程字样 | 产物与 `SIGNOFF.md` 台账对齐；不改写四状态、不改写判定 |
| S53 | `PLAN.md` / `TASKS.md` 状态同步：M4 已完成、M5 技术侧完成；E1/E2/E3、字段缺口、抽验 5 条、T-M4-07、T-M5-09 均标已完成 | 台账反映已发生的事实；旧批次物理移出仍标未执行 |
| S54 | `docs/adr/0010` 写死 R-1 横向评测协议（同批样本/同提示词/同预算/四项指标/版本锚点） | 协议已定，评测仍标未执行——只有一个模型 key，同模型多开子代理不构成横向评测 |
| S55 | T-M4-04「B 提疑但规则能证伪」样本：对抗组 a16（诱导文本）+ v2/v4（接口链与反例）+ 固定 sha256 已覆盖该场景，自动验收 4/4 PASS | 以对抗组固定样本为验收载体，不另造样本、不冒充独立复现 |

**未执行**：旧批次物理移出仓库（含已签正本，保留在仓库内）；
R-1 多模型横向评测（缺 key，协议已定）；独立复核单独登记（对抗组已交付 E1/E2/E3 与验收脚本）。

**回归**：91 单测、84 判点一致 84、K-1~K-6 6/6；`evidence/` 历史正本未改写。

---

## R-1 横向评测支持（2026-11-25）

> 性质：B 通道可选模型参数 + 评测 runner，不涉审计规则包，`RULE_PACK_VERSION` 保持 0.1.7。
> `key.txt` 现有四个模型：`mimo-v2.6-flash`、`deepseek-flash`、`qwen3.8-max`、`glm-5.3`。

| # | 变更 | 影响 |
|---|------|------|
| S56 | `core/channel_b.py` `run_channel_b` 新增可选 `model_name`：按 key.txt 里的模型名选配置；不传仍取第一行，默认行为不变；名字不存在直接报未配置，不静默回退 | 避免横向评测跑错模型 |
| S57 | `cli.py analyze` 新增 `--model`，透传到通道 B | 可指定模型跑审计 |
| S58 | 新增 `review/model_eval/run.py`：按 ADR-0010 协议跑 4 模型 × 13 样本（6 靶场 + 7 对抗固定样本），全部 `--no-evidence`，产物写 `review/model_eval/<model>/`，不进 `evidence/` | 评测产物与主仓库正本隔离 |

**结果**：52/52 成功、0 失败；分析见 `review/model_eval/analysis.md`。
**连通性**：四个端点 HTTP 200 均可调用（`_chat` 的 ping 返回空串曾被误判为失败，实际正常）。
**协议**：见 `docs/adr/0010-model-selection.md` 的 R-1 节——同批样本、同提示词版本、同预算、
四项指标（B 疑点条数/命中、升级正确率、运行间波动）、每份带 rule_pack 与 commit。
**用同一模型开多个子代理不算横向评测**，已写进协议否掉。

---

## 自述定稿与最终评价（2026-11-26）

| # | 变更 | 影响 |
|---|------|------|
| S60 | `docs/team-roster.md` 两人个人自述定稿：对齐 R-1 横向评测已完成、E1 质询回应已落台账的事实；未做完项如实列（真值表逐点复核、语义强度匹配、轮换第二周期、跨人对照） | S4 四项计满分 |
| S61 | `TASKS.md` 补同步 T-M4-04（对抗组固定样本覆盖）、T-M4-05（R-1 已跑完）状态 | 两个漏标"待执行"的任务改为已完成 |

**最终评价**：PASS 10/10、**98/100**。剩余 2 分：V-1 Runnable 链升档（1，验收脚本已认可边界声明，不冒险改规则代码）与主观评分跨人对照（1，需第二人独立打分）。

**回归**：93 单测、84 判点一致 84、K-1~K-6 6/6；`evidence/` 历史正本未改写。

---

## 去除评价技能的特异化（2026-11-26）

> 触发：审查发现 `SKILL.md` 第 4 节写死本仓库命令（`python cli.py evaluate`、`python -m evaluator.checker`），
> 换 harness 不适用——这是把特定项目实现塞进通用技能文档。

| # | 变更 | 影响 |
|---|------|------|
| S62 | `SKILL.md` 第 4 节从"两种运行方式 + 具体命令"改为"运行由评价器自描述，技能不规定命令" | 技能只写方法论、契约、输出结构；启动方式与产物路径由评价器输出声明 |
| S63 | `next_action.submit_command`（写死的回填命令）改为 `next_action.submit`（语义接口：target/source/operation/contract） | 换 harness 也能实现回填，不依赖本仓库 CLI |
| S64 | `checker.py` 头部、`scoring.py` 头部、`agent.py` 兼容接口注释、`SKILL.md` 输出节去除具体命令与 `review/evaluation/` 路径 | 内核与文档不再绑定特定 CLI 或目录 |

**边界**：`fields.json` / `rubric.json` / `scoring-fields.json` 里的路径是**目标项目提供的字段规范**，
按 SKILL.md 第 0 节本就该由目标项目声明，不算评价器内置特异化，保留。
`cli.py evaluate --apply-scores` 是本仓库的一种实现方式，仍在，但不是技能文档规定的。

**回归**：93 单测、84 判点一致 84、K-1~K-6 6/6；去特异化后重新评价 PASS 10/10、98 分。

---

## 评价报告清理与文档口径统一（2026-11-26）

| # | 变更 | 影响 |
|---|------|------|
| S65 | 删除 `review/evaluation/` 下全部 111 个 `EVAL-*` 文件（20 HTML + 52 JSON + 39 trace） | 评价报告目录只留 SIGNOFF、校准记录、字段表等非报告文件 |
| S66 | 统一"当前态"描述：单测数改为 93（AGENTS/PLAN/TASKS/adr0012/field_check_notes/README/HARNESS）；当前规则包改为 0.1.7（GLOBAL/handoff/总档/specification/version-waiver/signoff） | 面向读者的现状描述与代码真值一致 |
| S67 | E3 五条 Finding 状态同步：F-01/02/03 已修复（0.1.7，4/4 PASS），F-04 不成立关闭，F-05 边界声明已补 | `docs/events.md` 不再写"待修复" |
| S68 | `truth_result.json` 状态改对：当前是 0.1.7 产物、带 rule_pack/commit 锚点，不再是"0.1.3 历史件" | HARNESS 质量门表与事实一致 |

**保留未改**：`evidence/` 历史正本里的旧版本号（生成时的真实记录）、`changes.md` 各节的历史回归数字、
`experiments.md` 的实验版本、对抗组提交时的快照、SIGNOFF 的批次登记状态——这些都是当时事实，改了即篡改历史。

**回归**：93 单测、84 判点一致 84、K-1~K-6 6/6。

---

## 评价输出退出签署台账（2026-11-26）

> 触发：评价输出本就是测试产物，报告文件已按要求清理；继续留在签署台账里只是指向空气的记录。

| # | 变更 | 影响 |
|---|------|------|
| S69 | 删除 `review/evaluation/SIGNOFF.md`——整份台账都是围绕测试评价建的，评价删了、也不该签，文件随之删除 | 签署状态只在 `docs/signoff.md` 一处维护，回归"不建第二台账"约定 |
| S70 | `scoring-fields.json` 的 SC-S3R-F1 改指向 `docs/signoff.md`（本组签署台账） | 字段核对仍有真实锚点 |
| S71 | `fields.json` 的 E-07-F2 锚点从"待签署"改为"未发生/不预填" | 对齐 docs/signoff 现状，不再要求过时的"待签署"字样 |
| S72 | HARNESS / README / docs/signoff / version-waiver / field_check_notes / PLAN / TASKS 的当前态引用清理：评价输出明确为测试产物、不纳入签署 | 消除"文档说有、实际已删"的矛盾；历史任务描述保留不改 |
| S73 | rubric K-3 期望改 FAIL（`evaluation_agent.calibration_cases`，上次改错字段）；docs/signoff 0.1.6 批"待签署"改为已抽验 | 校准与判定契约一致 |

**保留未改**：changes.md 各节的历史记录、TASKS.md 里 T-M5-13/T-M5-14 当时的任务描述——那是历史事实，删了即篡改。
**评价产物**：每次评价生成的 EVAL 文件按约定清理，不留在仓库。

**回归**：93 单测、84 判点一致 84、K-1~K-6 6/6；评价 PASS 10/10。

---

## 实验代差消除与 llm 校准补齐（2026-11-26）

> 触发：评价指出主实验停在 0.1.4、校准只有快路径。核查后发现 llm 模式一个真 bug 与一个夹具口径问题。

| # | 变更 | 影响 |
|---|------|------|
| S74 | `exp_datasource_ab.py --out review/exp_datasource_ab_v017.json` 在 0.1.7 重跑：6 样本检出全一致，A 中位 69.489ms / B 25.100ms，记录见 experiments 实验 8 | 主实验数据与当前版本对齐；0.1.3/0.1.4 数据保留 |
| S75 | 修 `AgentLoop.run` 里 `evidence_pack` 只在非 llm 分支初始化的 bug——llm 模式走到 `pending_harness` 分支时属性不存在直接崩 | **不是 token 截断**：`--llm` 现在能跑通，PASS 10/10、指纹与确定性路径一致 |
| S76 | `RestrictedTools` / `AgentLoop` / `run_agent` 加可选 `run_dir`，外部 harness 可直传合成 RUN 目录；`_safe_path` 把 `evidence/<run_id>/` 重定向到该目录 | 校准判例能走完整 llm 流程，默认路径不变 |
| S77 | `scripts/eval_calibrate.py` 加 `--llm`，产物 `calibration_k1_k6_llm.json`，与快路径产物互不覆盖 | 两套校准都有记录 |
| S78 | 校准夹具 `_write_run` 跟随当前规则包版本，并补齐 14 条判点占位（其余给"无法判定"） | 消除"0.1.0 夹具跳过判点完整性检查"的假阴性；两套校准口径一致 |
| S79 | `fields.json` E-06-F1/F2 的版本锚点 0.1.6 → 0.1.7 | 补上之前统一文档口径时漏掉的字段规范 |

**回归**：快路径校准 6/6、llm 校准 **6/6**；93 单测、84 判点一致 84；默认 evaluate PASS 10/10。
**结论**：llm 模式此前不可用的根因是代码 bug，不是 max_tokens 设置——改大 token 无效，已修代码本身。
