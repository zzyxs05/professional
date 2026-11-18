# handoff · 交接包

> 给对抗组和教师：在一台干净机器上复现本组的结论、跑评价器、提出挑战。
> 规则包 0.1.4 ｜ 历史正本是 0.1.3，不改写，各 RUN 的 `meta.json` 里能看到生成时的版本。

## 1. 环境

| 项 | 要求 | 没有会怎样 |
|---|---|---|
| Python | 3.8 以上，只用标准库，不用装任何包 | 跑不了 |
| Java | 8 以上（JRE 8/11/17 都行） | 少了它，语义类规则（P/C/N）不运行，写进覆盖声明 |
| apktool | `.tools/apktool_3.0.3.jar`，随仓库带着 | 同上 |
| 模型（可选） | 项目根 `key.txt`，一行 `模型名,base_url,api_key`，不入库 | 通道 B 跳过并声明，A 通道结论不受影响 |

工具链查找顺序：项目内 `.tools/` → `JAVA_HOME` → PATH。

## 2. 启动

```bash
python cli.py analyze lab/apks/bad03.apk            # 完整审计，产物在 evidence/RUN-<时间>/
python cli.py analyze <apk> --out <dir>             # 报告另存一份
python cli.py analyze <apk> --no-evidence           # 演练：跑完整链路但不写 evidence/
python cli.py register <apk>                        # 登记新样本，打印真值模板，不写 registry
python cli.py evaluate --run <RUN>                  # 评价 Agent，默认用 key.txt 的模型
python cli.py evaluate --run <RUN> --no-llm         # 只走确定性路径
python cli.py summary [--no-llm]                    # 六样本汇总，无模型时用模板
python cli.py reset                                 # 清解码缓存，不动 evidence
```

`--no-evidence` 是给调规则用的：产物写临时区，不进 `evidence/`。运行正本只收正式运行。

## 3. 复现与验证

| 想确认什么 | 命令 | 期望结果 |
|---|---|---|
| 结论和真值是否一致 | `python scripts/truth_check.py` | 84 个判点全一致，硬错 0，噪声 0 |
| 端到端能不能跑通 | `python scripts/e2e.py` | A-01 全样本受理；A-09 两次运行一致 |
| 评价器是否正常 | `python cli.py evaluate --run <RUN>` | 四状态之一 + 引用校验 |
| 单元测试 | `python -m unittest discover -s tests` | 53 个全过 |

## 4. 重置

1. `python cli.py reset`：清 `%TEMP%/apkaudit_decode`，可以重建；
2. 删 `.tools/framework/`：apktool 的缓存，可以重建；
3. `evidence/`、`lab/`、`docs/`、`handoff/` **不要删**，这些是正本和交付物；
4. 重跑同一个 APK：同输入 + 同版本 → 同一份报告（A-09 验证过）。

## 5. 注册补测接口

- 评价器的受限工具：`request_registered_test(target_id, test_id)`，只认 `rerun_analyze` 和 `truth_check`，最多 5 次；
- 只接受注册过的目标和测试，**不接受任意脚本和网址**；
- 所有交互记进 `review/`。

## 6. 已知问题（复现前先看）

| ID | 问题 | 影响 | 怎么办 |
|---|---|---|---|
| I-1 | 通道 B 依赖 `key.txt` | 没配置就降级：B 跳过并在覆盖声明里写；A 的结论不受影响 | 放好 `key.txt` 再跑 |
| I-2 | 没有 apktool 时 P/C/N 类规则不运行 | 覆盖声明会列出来，M/S 类照常 | 确认 `.tools/` 完整 |
| I-3 | 不含加固样本，不脱壳 | 壳里的代码看不到 | 样本纪律：不用加固样本 |
| I-4 | R-PERM-01 的调用链证据只看同一方法内能解析的调度目标（`const-class`、Intent 类参数、`PendingIntent.get*`），跨方法和动态注册不解析 | 跨方法场景退回"样本级共存"，是待复核，不是漏判 | 报告只写"存在定时或后台触发敏感组件的结构"，不写实际行为；跨方法链列为 OBS-3 |
| I-5 | 凭据按形式宽匹配，示例值也照报 | 会有"形式命中"的噪声 | 报告里注明模式名，人来判读 |
| I-6 | B2 的疑点数量每次运行会波动（同一输入可能 0—N 条） | `R-B-*` 待复核条数每次都不同；14 条规则的结论不受影响 | 这是 LLM 生成的特点，已在报告里声明；要比对稳定性就看 A 通道 |
| I-7 | 真实第三方应用只在本地分析，需教师批准 | — | 合规边界 |
| I-8 | 模型没做横向评测，只验证了 `mimo-v2.6-flash` 能跑 | 不能说"选了最好的模型" | 表述限定为"当前可用"，待办 R-1（ADR-0010） |

另外几条要提前知道：

- 最终批次有 **9 条没钉住的 B 侧疑点**（bad01×2、bad02×1、good01×2、good02×4），全部停在"待复核"。这是 B 通道的正常输出，不是失败，也不是"清零"；
- **B 与规则冲突的场景还没覆盖**，B 的召回增量要用新样本检验（T-M4-04）；
- bad04 是诱导对抗样本，good02 是边界陷阱样本，复现时核对它们分别"检出 2 条 / 全安静"；
- 保留测试和实现答案不提前交换；对方给的文件不等于独立复现。

## 7. 合规

被测 APK 只读，不执行；子进程只允许 java；分析过程不联网（B 通道只在显式配置模型时，走你指定的端点）；不把真实用户数据发给公共模型。

## 8. 目录导航

```
总档.md             总纲（指针）
docs/               需求、规约、决策、调研、实验、变更、事件、签署
core/               审计流水线
evaluator/          评价 Agent
evidence/RUN-*/     运行正本，不改写
review/             复核与互评材料
lab/                靶场：样本 + 真值表 + sha256
scripts/ tests/     契约脚本与单元测试
```
