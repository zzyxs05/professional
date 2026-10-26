# release · 启动、重置、已知问题、恢复【release】

> 状态：v0.2。**签署前为待复核状态。**

## 1. 环境要求

| 项 | 要求 | 说明 |
|----|------|------|
| Python | 3.8+（仅标准库，**零第三方依赖**） | 任意发行版 |
| Java | 8+（推荐 JRE 8/11/17 任选其一） | 仅 apktool 解码用 |
| 工具链 | `.tools/apktool_3.0.3.jar`（随仓库入库） | 缺失时自动降级（M/S 类照跑） |
| 模型（可选） | `key.txt`（项目根，**不入库**）：一行 `模型名,base_url,api_key` | 缺失时通道 B 跳过并声明 |

工具链查找顺序：项目内 `.tools/` → `JAVA_HOME` → PATH。

## 2. 启动

```bash
# 主命令：完整审计（双通道 + 融合 + 报告）
python cli.py analyze lab/apks/bad01.apk

# 输出目录另存一份
python cli.py analyze <apk> --out <dir>

# 演练模式：跑完整链路（含通道 B）但**不写入 evidence/**——调准则/做实验时使用，
# 避免实验性运行污染运行正本（证据与报告落在临时区）
python cli.py analyze <apk> --no-evidence --out <dir>

# 登记新样本（打印待粘贴真值模板，不写 registry）
python cli.py register <apk>

# 运行评价器（默认确定性；--llm 启用判读，失败自动降级）
python cli.py evaluate --run RUN-20261015-145016 --llm

# B3：六样本汇总报告（模型生成，无模型/失败自动降级为模板渲染）
python cli.py summary [--no-llm] [--out review/summary.md]

# 清理可重建产物（解码缓存；不动 evidence 正本）
python cli.py reset
```

通道 B 模型配置：项目根 `key.txt`（一行 `模型名,base_url,api_key`，可多行按序取第一个可用；
**不入库**，已在 `.gitignore`）。缺失/端点不可用时自动降级——B 通道跳过并在覆盖声明中注明。

产物位置：`evidence/RUN-<时间戳>/`（`report.md` 人读 / `report.json` 机器读 / `meta.json` / `channel_a/hits.jsonl`）；
汇总件 `review/summary.md`（B3 六合一）+ `review/truth_result.json`（真值一致性成绩）。

契约脚本：

```bash
python scripts/truth_check.py            # 真值一致性（84 判点；写入 review/truth_result.json）
python scripts/truth_check.py --no-evidence   # 同上，但不把运行写进 evidence/
python scripts/e2e.py [--no-evidence]    # 端到端验收（A-01/A-09）
python scripts/b_stability.py --sample bad03 --runs 5   # B 通道稳定性实验（多轮，不落 evidence）
python -m unittest discover -s tests     # 单元测试（合成夹具，不依赖真实 APK）
```

**纪律**：`evidence/` 只收**运行正本**。任何"调准则过程中的实验性运行"必须走 `--no-evidence`
（或 b_stability 这类只产出统计的脚本），不得把试错数据写进正本库。

## 3. 重置（干净环境恢复）

1. `python cli.py reset`（清 `%TEMP%/apkaudit_decode`；可重建）；
2. 删除 `.tools/framework/`（apktool 缓存，可重建）；
3. `evidence/`、`lab/`、`docs/`、`handoff/` **不要删**——是运行正本与交付物；
4. 重跑同一 APK：同输入 + 同版本 → 同一份报告（e2e A-09 已验证）。

## 4. 已知问题与限制（如实声明）

| ID | 问题 | 影响 | 规避 |
|----|------|------|------|
| I-1 | 通道 B 依赖 `key.txt` 模型配置 | 无配置时自动降级：B 跳过 + 覆盖声明注明；A 通道结论不受影响 | 项目根放置 `key.txt` 后重跑 |
| I-2 | apktool 缺失时 P/C/N 类规则不运行 | 覆盖声明如实列出；M/S 类正常 | 确保 `.tools/` 完整 |
| I-3 | 加固样本不在范围（不脱壳） | 壳内代码不可见 | 样本纪律：不用加固样本 |
| I-4 | R-PERM-01 的调用链证据只覆盖**同一方法内可解析调度目标**（`const-class` / Intent 类参数 / `PendingIntent.get*` 上下文）；跨方法、动态注册的调度链不解析 | 跨方法场景回退到"样本级共存"档（待复核），不是漏判 | 报告只断言"存在定时/后台触发敏感组件的结构"，不写实际行为；跨方法链列为 Change 候选（OBS-3） |
| I-5 | 凭据模式宽匹配（示例值照报） | 可能产生"形式命中"噪声 | 报告注明模式名；人工判读 |
| I-6 | B1/B2 判定依赖模型质量；**B2 疑点产出存在运行间波动**（同一输入多次运行可能提出 0—N 条 B 侧疑点） | 报告中的 `R-B-*` 待复核条目数量逐次可能不同；标准规则结论（84 判点）不受影响 | B 侧波动属 LLM 生成特性，按总档 §3.6 声明；需要稳定复现时以 A 通道结论为准比对 |
| I-7 | 真实第三方应用仅限本地分析与教师批准 | — | 合规边界（总档 §10） |
| I-8 | 模型选型未做横向评测（只验证了 `mimo-v2.6-flash` 可跑通） | 不能声称"选了效果最好的模型"；端点波动会影响 B 通道可用性 | 表述限定为"当前可用"；待办 R-1（ADR-0010） |

## 5. 合规声明

只读不执行被测 APK（证据层级上限 STATIC）；子进程白名单仅 java；分析链路零网络调用
（B 通道仅在显式配置模型时经用户指定端点通信）；不向公共模型提交真实用户数据。
