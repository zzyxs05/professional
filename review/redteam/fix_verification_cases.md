# F-01 / F-02 / F-03 / F-05 修复验收用例

> 视角：毛舒逸组（对抗组）｜**本测试基于 commit `6276391` / 规则包 0.1.6**
> 生成时间：2026-11-25（GMT+8）｜运行环境：`D:\redteam\e1_run_20261125`（干净克隆，Java 11 / Python 3.13 / apktool 3.0.3）
> 配套脚本：`review/redteam/fix_verify.py`｜固定样本：`review/redteam/samples/*.apk`
> **状态：全部为「待验收」。对面规则包 0.1.7 的修复尚未发生，本文件不含任何"已通过"结论。**

---

## 0. 使用方法

```bash
# 修复前：确认 4 条 Finding 仍可复现（期望 4/4 REPRODUCED）
python review/redteam/fix_verify.py --tool-root <apkaudit仓库> --phase baseline

# 修复后：回归验收（期望 4/4 PASS；修复前跑它必然是 FAIL，这是诚实状态）
python review/redteam/fix_verify.py --tool-root <apkaudit仓库> --phase regression
```

- 脚本自动校验样本 sha256，不符即拒跑（SHA256_MISMATCH）；
- 全部运行带 `--no-evidence`，**不写对面 `evidence/`**；
- 输出 `review/redteam/fix_verification_result_baseline.json` / `_regression.json`；
- 本次 baseline 实测：**4/4 REPRODUCED**（`fix_verification_result_baseline.json`）。

**注意**：apktool 回编译产物含时间戳，重建 APK 的 sha256 不可复现（实测三次互不相同）。因此**样本二进制以仓库内 `review/redteam/samples/` 为唯一正本**，sha256 固定；构造步骤仅作复核理解用，重建产物请以新 sha256 重新登记。

---

## 1. F-01 · 非空但无效的 TrustManager（漏报）

| 项 | 内容 |
|---|---|
| 样本 | `review/redteam/samples/a13.apk` |
| sha256 | `6d431e92d124466c299aa1fb17b9b498de47690b0c3fa6a17398d6850d359091` |
| 规则 | R-NET-01 |

**构造步骤**（基准 `lab/apks/bad03.apk`）：

1. `apktool d bad03.apk`；
2. 改 `smali/com/synth/bad03/InsecureTls$1.smali` 的 `checkServerTrusted` 方法（原 38—42 行）：方法体从 `.locals 0 / return-void`（空实现）改为 `.locals 3` + `const-string v0,"InsecureTls"` + `const-string v1,"trust-all"` + `invoke-static {v0,v1}, Landroid/util/Log;->d(...)I` + `return-void`。**只改这一个方法**，`checkClientTrusted`/`getAcceptedIssuers` 保持原样；
3. `apktool b` + `jarsigner` 自签。

**判定条件**：

| 相位 | 命令 | 判定 |
|---|---|---|
| 修复前复现 | `python review/redteam/fix_verify.py --tool-root <repo> --phase baseline` | 期望 `REPRODUCED`：R-NET-01 的 notes 中**不含** `checkServerTrusted` 条目（假校验被放过） |
| 修复后回归 | `python review/redteam/fix_verify.py --tool-root <repo> --phase regression` | 期望 `PASS`：R-NET-01 的 notes 中**含** `checkServerTrusted` 条目 |

**修复前实际（0.1.6 / `6276391`）**：R-NET-01 notes 由 4 条降为 3 条，`X509TrustManager.checkServerTrusted 空实现（证书校验被跳过）` **消失**。总体 R-NET-01 仍"已确认"（getAcceptedIssuers 空数组、HostnameVerifier 恒真仍在），单点漏报被掩盖——判据缺陷不因样本巧合而不存在。

---

## 2. F-02 · `uses-permission-sdk-23` 声明的敏感权限（漏报）

| 项 | 内容 |
|---|---|
| 样本 | `review/redteam/samples/a02.apk` |
| sha256 | `cc1a7084243073914e3f236ca601b1ca94087bf6085291e8efbe29981390fb18` |
| 规则 | R-MAN-02 |

**构造步骤**（基准 `bad03.apk`）：

1. `apktool d bad03.apk`；
2. 改 `AndroidManifest.xml` **第 4 行**：`<uses-permission android:name="android.permission.RECORD_AUDIO"/>` → `<uses-permission-sdk-23 android:name="android.permission.RECORD_AUDIO"/>`。**只改这一行**，ACCESS_FINE_LOCATION 等保持原样；
3. `apktool b` + 签名。

**判定条件**：

| 相位 | 判定 |
|---|---|
| 修复前复现 | 期望 `REPRODUCED`：R-MAN-02 的 notes **不含** `RECORD_AUDIO`（只剩 ACCESS_FINE_LOCATION） |
| 修复后回归 | 期望 `PASS`：R-MAN-02 的 notes **含** `RECORD_AUDIO` |

**修复前实际**：R-MAN-02 命中 2 → 1，RECORD_AUDIO 消失且无任何提示；R-PERM-03 同步"无法判定"（声明与使用比对也漏了该权限）。`<uses-permission-sdk-23>` 是标准 manifest 标签，语义等价 `<uses-permission>`。

---

## 3. F-03 · `enabled="false"` 的静态 Receiver（误报）

| 项 | 内容 |
|---|---|
| 样本 | `review/redteam/samples/a04.apk` |
| sha256 | `c0fb952800ec19478072a42d233d46addb1b29cb1ad1b49a85649332e28523b0` |
| 规则 | R-MAN-05 |

**构造步骤**（基准 `bad03.apk`，bad03 本身无静态 Receiver）：

1. `apktool d bad03.apk`；
2. `AndroidManifest.xml` 的 `<application>` 内新增（约 9—14 行）：
   ```xml
   <receiver android:enabled="false" android:exported="false" android:name="com.synth.bad03.BootReceiver">
       <intent-filter>
           <action android:name="android.intent.action.BOOT_COMPLETED"/>
       </intent-filter>
   </receiver>
   ```
3. 新增 `smali/com/synth/bad03/BootReceiver.smali`：继承 `BroadcastReceiver`，`onReceive` 空方法体；
4. `apktool b` + 签名。

**判定条件**：

| 相位 | 判定 |
|---|---|
| 修复前复现 | 期望 `REPRODUCED`：R-MAN-05 状态 = `已确认`（且 notes 未提 disabled） |
| 修复后回归 | 期望 `PASS`：R-MAN-05 状态 ≠ `已确认`，或 notes/结论中明确标注 `enabled=false` |

**修复前实际**：R-MAN-05 `已确认`，location `AndroidManifest.xml:10-14 [receiver com.synth.bad03.BootReceiver]`，notes"静态注册监听敏感事件：BOOT_COMPLETED（开机完成）"——**全文未提 `enabled="false"`**。组件明确不生效却报为敏感广播监听。

---

## 4. F-05 · Runnable 跨方法调用链（漏报 + 声明缺失）

| 项 | 内容 |
|---|---|
| 样本 | `review/redteam/samples/v2_crossmethod.apk` |
| sha256 | `3464015c37b913c544ffc4c210c8f39d22be5d97666e03b1d851e8add7290e93` |
| 规则 | R-PERM-01 |

**构造步骤**（基准 `bad03.apk`，目标：只留跨方法链）：

1. `apktool d bad03.apk`；
2. 删除 `smali/com/synth/bad03/MainActivity.smali` 的 `scheduleRecordingAlarm()` 整个方法（原 144—191 行，含 `setRepeating` + `const-class RecordingService`）；
3. 注释 onCreate 内对该方法的调用（原 267 行）：`#invoke-direct {p0}, ...->scheduleRecordingAlarm()V`；
4. 保留 onCreate 的 `Handler.postDelayed(Runnable)` 链（约 230 行）→ `MainActivity$1.run()` → `startRecordingService()` → `RecordingService` 内 `MediaRecorder`（3 方法、2 类的真实链路）；
5. `apktool b` + 签名。

**判定条件**（两个子条件，修复需至少满足其一，推荐全满足）：

| 相位 | 判定 |
|---|---|
| 修复前复现 | 期望 `REPRODUCED`：R-PERM-01 状态 = `待复核` **且** `missing_evidence` 为空 **且** notes 无链路说明 |
| 修复后回归 | 期望 `PASS`：R-PERM-01 升 `已确认`；**或** `missing_evidence`/notes 明确声明"存在跨方法链，未解析" |

**修复前实际**（纯 A 通道核对，排除 B 通道干扰后确认）：R-PERM-01 `待复核`，notes 仅"调度原语：postDelayed"+"敏感 API：录音"，`missing_evidence: []`——**两条期望全落空**：链不解析、能力边界也不声明。

**附**：`const-class` 跨类变体已证伪（`a05.apk`，sha256 `9cb29683…`，判据支持、直接已确认），不在本次修复范围。防串链反例 `v4_isolated.apk` 见 E2 验收材料。

---

## 5. 与 0.1.7 修复的衔接

- 对面规则包 bump 到 **0.1.7** 后，回归跑法不变：`fix_verify.py --phase regression`；
- 脚本按样本内容判定，**不依赖规则包版本号**；请在修复后的 RUN/report 里带上 `本测试基于 commit <hash>`（产出物写一句即可）；
- 修复涉及判定条件变化的（F-01/F-02/F-03 是判据缝隙，F-05 涉及链解析能力），按对面纪律 `RULE_PACK_VERSION` 加号 + 记 `changes.md` + 重跑 84 判点——84 判点回归是底线，本次 4 个样本不进真值表（它们是对抗样本，不是标定样本）；
- **本文件不含任何通过结论**。修复未发生前，全部状态为"待验收"。
