# 回执：V-2 样本偏差确认与新反例交付

> 视角：毛舒逸组（对抗组）→ 余俊辉 / 周宗正
> 对应：`handoff/to-redteam-v2-deviation.md`（2026-11-27）
> **本测试基于 commit `3c7a371` / 规则包 0.1.8**，运行时间 2026-11-27 19:06—19:12（GMT+8）

---

## 1. 确认：你们的分析属实，偏差在我方样本

逐条核对 smali 原文，`to-redteam-v2-deviation.md` 的三点全部成立：

1. V-2（`v4_isolated.apk`）的 `MainActivity$1.run()` 确实 `invoke-static` 到 `-$$Nest$mstartRecordingService`，`startRecordingService()` 内 `const-class RecordingService` + `startService()`——**真实链完整**；
2. `Worker.smali` 全项目零引用（`grep -rl Worker smali/` 无其他命中）；
3. 升档依据是 RecordingService 链，不是 Worker。

**责任在我方**：V-2 的构造意图是"只有孤立类、无真实链"，实际从 V-1 工作目录复制时忘了把 `RecordingService` 链拆干净。书面期望与样本产物不符，是样本缺陷，不是你们的判定问题。

**你们的处理是对的**：没有为了让样本符合书面期望去加"样本内有孤立敏感类就降档"的规则——那确实是按样本数量猜、不是按证据链判。同意不加。

## 2. 你们提的两件事，我方逐条答复

**Q1（是否重做 V-2）→ 是，已重做。**

新反例样本 `review/redteam/samples/v2bis_isolated.apk`（sha256 `867c78d29fd463c6d303503582e405e3d1fa0bbb5fb9e4463bb4b92870a0a5a7`）：

- `MainActivity$1.run()` 内对 `startRecordingService` 的调用已注释（Runnable 链断开，run() 只剩 Log）；
- `RecordingService` 清为空壳（无任何 MediaRecorder）；
- 保留孤立 `Worker.smali`（含 `MediaRecorder`，零引用）；
- 保留 `Handler.postDelayed` 调度原语。

意图：调度原语在场、敏感 API 在场（Worker）、**两者无任何链连接**。期望 R-PERM-01 **不得升「已确认」**。

**我方复验（0.1.8 / `3c7a371`）**：

| 样本 | R-PERM-01 | 关键内容 | 判定 |
|---|---|---|---|
| V-2bis（新） | **待复核** | `missing_evidence` 写明"存在不可直接解析的调度目标…Runnable/接口回调…跨方法链未解析" | **防串链通过** ✅ |

顺带说明：0.1.8 的 `missing_evidence` 声明也生效了（F-05 的"声明缺失"子项一并修复），比我方预期更好。

**Q2（V-2 期望怎么写）→ 旧 V-2 期望作废，按你们实测改判为「已确认（正确）」，防串链硬门移交 V-2bis。**

同时补一条我方独立复验的**补充观察**（不改你们的结论）：

| 模式 | V-2 现状（v4_isolated.apk）R-PERM-01 | 说明 |
|---|---|---|
| 纯 A 通道（无 `key.txt`） | **已确认** | 与你们实测一致 |
| 开 B 通道（deepseek-flash） | **待复核**（notes 仍写明跨方法链，但档位被 B1 复核压回） | B 通道的保守复核会压档，非 A 通道判定问题 |

两个结果都是真实的，取决于 B 是否启用。建议在 Change 说明里注明"B 通道可能压档"，避免后续复跑对不上。

## 3. 我方验收结论（对抗组独立复验，非引用贵方文件）

| 门 | 样本 | 结果 |
|---|---|---|
| V-1 功能门 | `v2_crossmethod.apk` | **通过**：待复核 → **已确认**，notes 写明 `MainActivity$1 → startRecordingService → RecordingService` 链 |
| 防串链硬门 | `v2bis_isolated.apk`（新） | **通过**：保持待复核，且 `missing_evidence` 声明未解析链 |
| 防串链（旧样本，供对照） | `v4_isolated.apk` | 见 §2 补充观察（A 已确认 / 开 B 待复核） |
| F-01/02/03/05 回归 | `fix_verify.py --phase regression` | **4/4 PASS**（F-01/02/03 在 0.1.8 也已修复，不只 CHG-006） |
| 84 判点 | `truth_check.py --no-run` | **84/84，硬错 0，噪声 0** |
| 单测 | `unittest discover` | **94/94** |

## 4. 文档更新

- `review/redteam/e2_acceptance_samples.md`：V-2 期望改判 + V-2bis 登记 + 偏差记录；
- `review/redteam/e2_change_relay.md`：同步偏差说明；
- 旧 V-2（`v4_isolated.apk`）保留在库中作对照，**不再作防串链硬门**。

毛舒逸组
2026-11-27
