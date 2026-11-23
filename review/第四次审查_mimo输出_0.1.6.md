# 第四次审查（mimo 直评）· mimo-v2.6-flash 输出

> 模型：`mimo-v2.6-flash`（OpenAI 兼容端点，密钥读项目根 key.txt，不入库）
> 审查时间：2026-11-23 23:40　审查范围：core/channel_a.py、core/channel_b.py、core/safezip.py、core/summary.py、evaluator/llm.py、cli.py（完整内容送审）
> 审查方式：项目自配模型直评，与上一轮（GLM-5.3-Flash + code-review-analyzer 技能）交叉印证

# apkaudit 核心代码审查

## 正确性

- **Major · cli.py `cmd_analyze`（sample_failed 分支）**：`coverage['decode_failed'] = True`、`decode_note = fail_reason`，但失败原因是 manifest 解析，apktool 解码可能成功；与正常分支中该字段"指解码结果"的语义冲突，覆盖声明失真。建议改为 `decode_failed = not decode.ok`，另设 `preprocess_failed`。
- **Major · channel_b.py `_chat`**：重试仅覆盖 `HTTPError(4xx/5xx)` 与 `http.client.HTTPException`；`urlopen(timeout=…)` 超时抛 `TimeoutError`/`socket.timeout`，不在两个 except 内，超时不重试直接外抛，与注释"连接异常可恢复"不符，易致 B 通道整体降级。建议显式捕获超时异常并纳入退避重试。
- **Minor · channel_b.py `load_key_config`**：`line.split(',')` 未限次数，api_key 含逗号会被截断。建议 `split(',', 2)`。
- **Minor · channel_a.py `build_context`**：`re.search(r'networkSecurityConfig="@xml/…')` 仅匹配双引号写法，单引号/带命名空间前缀时 `nsc_ref` 静默为 None。建议改用 `ctx.manifest_doc` 结构化取值。
- **Minor · channel_a.py `run_channel_a`**：`sources_note` 汇总所有组的可用源，而非实际满足的那一组，覆盖记录可能虚高；`rule_id == 'R-MAN-03'` 特判硬编码在通用引擎中。

## 安全

- B1/B2 已有 `_DATA_BOUNDARY` + `_INJECTION_RE` 只堵降级方向，思路正确；key.txt 不回显、`describe_model` 不泄漏密钥，合规。
- **Minor · summary.py B3**：输入含样本派生文本（scope/claim），无与 B1/B2 同级的注入防线；虽"不改结论"，仍建议加数据边界声明。
- **Nit · safezip.py**：单成员上限完备，但无跨成员累计上限约束，多成员累积内存需调用方自律。

## 性能

- 除上述超时未重试导致的降级放大外，未见明显问题：B1 有预算闸、snippet 截断（`hits[:5]`）、逐规则异常隔离均合理。

## 可维护性

- **Major · channel_b.py 与 evaluator/llm.py**：key.txt 解析与 LLM 调用两份实现且行为分叉（evaluator 无重试）；两处均只 `except OSError`，二进制/损坏 key.txt 的 `UnicodeDecodeError` 会逃逸，违反 `chat`"任何失败由调用方降级"契约。建议下沉为共享 `_client` 模块并统一异常面。
- **Nit · cli.py**：演练模式 `mkdtemp` 不清理；`channel_a/hits.jsonl` 混入 B 记录（命名与内容不符）；evaluator 每次调用重读 key.txt。
