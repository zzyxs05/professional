# 第四次审查 · mimo-v2.6-flash 输出

> 模型：`mimo-v2.6-flash`（OpenAI 兼容端点，密钥读项目根 key.txt，不入库）
> 审查时间：2026-11-23　审查范围：core/channel_a.py、core/channel_b.py、evaluator/llm.py、cli.py（完整内容送审）
> 审查方式：项目自配模型直评（第四次），与第三次（GLM-5.3-Flash + code-review-analyzer 技能）交叉印证

# apkaudit 核心代码审查

## 正确性

- **[Major] 预算耗尽被静默漏报**：`channel_b.py` 中 B1 循环 `if not hits or not available: continue`、B2 `if available and runner.budget.consume_llm()`，一旦中断即跳过，但 `res.ran=True`；`cli.py` 据此写入 `coverage['checked'].append('通道B(...)')`，与"不可静默"原则相悖。修复：`BResult` 增加 `skipped` 清单，coverage 分别记录"部分复核/预算耗尽"。
- **[Major] 规则导入未纳入保护**：`channel_a.py` 中 `importlib.import_module(modpath)` 在 `try` 之外，单个规则模块路径错误会击穿 `cli.cmd_analyze`，证据半途而废、状态机停在 RULE_A。修复：移入 `try`，按"规则执行异常"记入 `coverage_not_checked`。
- **[Major] key 解析截断**：`channel_b.load_key_config` 与 `evaluator/llm._load_cfg` 均用 `line.split(',')` 取前 3 段，api_key 含逗号时被截断导致鉴权失败。修复：`split(',', 2)`。
- **[Minor] 粒度过粗的失败归类**：`build_context` 中 `SmaliFacts/ResFacts` 构造无保护，解码目录异常会升格为"样本失败"（manifest 明明可用）。修复：try/except 后记入 `ctx.rule_notes`。
- **[Minor] 连通性 ping 未计预算**：`run_channel_b` 探测调用绕过 `budget.consume_llm()`。修复：计入。

## 安全

- **[Minor] 无 URL 协议校验**：`base_url` 直接拼接请求，可为 `http://`，API key 明文外发。修复：强制 `https://` 或显式告警。
- 说明：`describe_model` 只回传模型/端点不回传密钥，凭据隔离处理得当；两处异常兜底未泄漏 Authorization 头。

## 性能

- **[Nit]** `_hits_with_context` 对每个命中调 `ctx.smali.read_lines(rel)`，同文件可能重复读盘（取决于 SmaliFacts 是否缓存）。建议按 `rel` 缓存行。
- 其余（zip 直读、单次 dex 扫描、定长退避重试）无明显问题。

## 可维护性

- **[Minor] 硬编码特例**：`run_channel_a` 中 `if rule_id == 'R-MAN-03'` 的 res_decoded 旁路破坏声明式设计。修复：规则元组中声明可选附加源。
- **[Minor] 证据截断与承诺不符**：`raw[:400]`/`raw[:2000]`/`reason[:200]` 与模块注释"原始响应落盘"矛盾。修复：全量落盘，摘要字段另存。
- **[Nit]** `cli.py` 写 `channel_a/hits.jsonl` 实为全量 `store.records`，命名误导；key 解析逻辑在两模块重复，建议抽公共函数。
