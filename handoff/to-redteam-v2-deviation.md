主题：CHG-006 / V-1 升档已实施，V-2 样本与书面期望存在偏差，请确认

毛舒逸组，你们好。

E2 变更请求 V-1（`e2_change_relay.md` §3）已在 0.1.8 实施（CHG-006，见 `docs/impact-map.md`）：
R-PERM-01 现在支持跨方法 Runnable 链解析，调度点 → 匿名 `Runnable.run()` → 目标方法 →
`const-class` 组件 → 敏感 API，静态可解析链升「已确认」。

验收实测结果：

- V-1 `v2_crossmethod.apk`（`3464015c…`）：R-PERM-01 **待复核 → 已确认**，
  notes 写明 `MainActivity$1 → startRecordingService → RecordingService`，与你们的功能门期望一致。
- V-2 `v4_isolated.apk`（`63823c87…`）：你们的书面期望是**保持待复核**（防串链误报），
  但实测也升为「已确认」。

我们核对了 smali 原文，发现一个样本与期望的偏差，想请你们确认：

1. V-2 的 `MainActivity.smali` 里，`startRecordingService()` 方法体与 V-1 **逐字相同**——
   同样 `const-class RecordingService` + `startService()`；
2. `MainActivity$1.run()` 同样 `invoke-static` 到 `-$$Nest$mstartRecordingService`；
3. V-2 多出的孤立类 `Worker.smali`（含 MediaRecorder）在我们的实现里**没有被引用**——
   升档依据的是真实存在的 RecordingService 链，不是 Worker。

所以按「证据支持什么就判什么」的纪律，我们没有为了让 V-2 符合书面期望而加一条
「样本内有孤立敏感类就降档」的规则——那是按样本数量猜，不是按证据链判，会引入新的误判。

想请你们确认两件事：

- 如果 V-2 的本意是「没有真实链、只有孤立 Worker」，那当前样本产物与意图不符，
  是否需要重做 V-2 样本（移除 RecordingService 链，只留 Worker）？我们乐于按新样本复验。
- 如果 V-2 保持现状，那 R-PERM-01 升为已确认是正确结果，请更新 `e2_change_relay.md`
  与 `e2_acceptance_samples.md` 里的期望，把 V-2 从「保持待复核」改成「已确认」，
  并注明偏差原因。

在你们确认前，我们把这条偏差如实记在 `docs/impact-map.md` CHG-006 里，不掩盖、不单方面改期望。

余俊辉 / 周宗正
2026-11-27
