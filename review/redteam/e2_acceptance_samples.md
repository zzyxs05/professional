# E2 验收样本集（CHG-004 / 规则包 0.1.7）

> 视角：毛舒逸组（对抗组）｜**本测试基于 commit `6276391` / 规则包 0.1.6（基线）**
> 基线生成时间：2026-11-25（GMT+8）｜RUN 正本位置：`D:\redteam\e1_run_20261125\evidence\`（对抗组自有目录，不写对面 `evidence/`）
> 样本正本：`review/redteam/samples/`（sha256 固定）
> **状态：全部为「待验收」。CHG-004 的修复尚未实施，本文件不含"已通过"结论。**

---

## 1. 验收矩阵（对面修复后逐行跑）

| # | 样本 | sha256 | 基线 RUN（0.1.6） | 基线 R-PERM-01 | 修复后预期 | 判定 |
|---|---|---|---|---|---|---|
| V-1 | `samples/v2_crossmethod.apk` | `3464015c37b913c544ffc4c210c8f39d22be5d97666e03b1d851e8add7290e93` | `RUN-20261125-194928-3464015c` | **待复核**（missing 空、无链说明） | **已确认** | 升档成功 |
| V-2 | `samples/v4_isolated.apk` | `63823c87e1e1e0bdbf4a4ff31c0706bcd7e86f149a49c1860884c9bd4c90a553` | `RUN-20261125-194958-63823c87` | **待复核** | **仍待复核**（不许升档） | 防串链硬门 |
| V-3 | `lab/apks/bad01.apk` | `3356097a33fb044d848ee1930523924b2d08ba7bbfdf47f43c7dbad10aae1414` | `RUN-20261124-141033-3356097a`（0.1.6 批） | 既有结论 | **逐点不变** | 基线回归 |
| V-3 | `lab/apks/bad02.apk` | `232666b8c0bf411dd454f5ec0922a5795a5c594e0eff56cbecce9f376a4f0d4c` | `RUN-20261124-141327-232666b8` | 既有结论 | **逐点不变** | 基线回归 |
| V-3 | `lab/apks/bad03.apk` | `21cf5a06cc615b6e8ce71b66dbcda9386a136f63d861fcc258a195b98c4728aa` | `RUN-20261124-140458-21cf5a06` | 既有结论 | **逐点不变** | 基线回归 |
| V-3 | `lab/apks/bad04.apk` | `e11522640317bad12bafb2aecd880d348343b66234a42b1b28e206e7c846dab7` | `RUN-20261124-141435-e1152264` | 既有结论 | **逐点不变** | 基线回归 |
| V-3 | `lab/apks/good01.apk` | `4cbacbdd6f878f7128ee4938f311ebac9a65e54e53f809a1b9b61634c17355dc` | `RUN-20261124-141502-4cbacbdd` | 既有结论 | **逐点不变** | 基线回归 |
| V-3 | `lab/apks/good02.apk` | `710b457d51f2b960d63470001105522e5eea24d63c4d09d9696d549b3978b1f2` | `RUN-20261124-141518-710b457d` | 既有结论 | **逐点不变** | 基线回归 |

外加全局底线：`python scripts/truth_check.py --no-run` 保持 **84/84，硬错 0，噪声 0**；`python -m unittest discover -s tests` 保持全过。

---

## 2. 每个样本的复跑命令（修复后由对抗组执行）

```bash
# 基线环境：D:\redteam\e1_run_20261125（干净克隆）；修复后先 git pull 对面 0.1.7 并记录新 commit

# V-1 跨方法链（期望：待复核 → 已确认）
python cli.py analyze review/redteam/samples/v2_crossmethod.apk
# V-2 孤立类反例（期望：仍待复核，硬门）
python cli.py analyze review/redteam/samples/v4_isolated.apk
# V-3 既有 6 样本（期望：逐点不变）
python cli.py analyze lab/apks/bad01.apk
python cli.py analyze lab/apks/bad02.apk
python cli.py analyze lab/apks/bad03.apk
python cli.py analyze lab/apks/bad04.apk
python cli.py analyze lab/apks/good01.apk
python cli.py analyze lab/apks/good02.apk
# 全局底线
python scripts/truth_check.py --no-run
python -m unittest discover -s tests
```

## 3. 逐项判定条件（V-1 / V-2 详列）

### V-1（功能门）：`v2_crossmethod.apk`

链路：`MainActivity.onCreate` 的 `Handler.postDelayed(Runnable)` → `MainActivity$1.run()` → `startRecordingService()` → `RecordingService` 内 `MediaRecorder`（3 方法、2 类，`Runnable` 接口间接引用，无 `const-class`）。

| 检查 | 基线（0.1.6） | 修复后必须 |
|---|---|---|
| R-PERM-01 状态 | 待复核 | **已确认** |
| notes 链路说明 | 无（只写"调度原语/敏感 API"共存） | 给出解析到的链（或至少在 `missing_evidence` 声明"已识别跨方法链"） |
| `missing_evidence` | `[]` | 非空或状态已升档 |

### V-2（硬门）：`v4_isolated.apk`

在 V-1 基础上加同包孤立类 `Worker`（含 `MediaRecorder`，全项目零引用）。

| 检查 | 基线（0.1.6） | 修复后必须 |
|---|---|---|
| R-PERM-01 状态 | 待复核 | **仍待复核**（不许因孤立类升档） |
| 串链 | 未串（干净） | 仍不串 |

**这条是硬门**：CHG-004 若把"同包共存"误判成链，本样本即拦下。当前实现此样本干净，改动后不许变脏。

---

## 4. 验收结论模板（修复后填，现在留空）

| 样本 | 修复后 RUN id | 修复后 commit | R-PERM-01 | 对基线 | 判定 | 时间 |
|---|---|---|---|---|---|---|
| V-1 | | | | 待复核→ | | |
| V-2 | | | | 待复核→ | | |
| V-3 ×6 | | | | 逐点 | | |
| 84 判点 | | | | 84/84→ | | |

> 未跑不填，跑完才填。每行必须带 commit + 规则包版本 + 运行时间。
