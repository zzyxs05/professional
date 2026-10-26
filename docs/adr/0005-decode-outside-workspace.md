# ADR-0005 · 解码产物工作区外 + 工具链随仓库入库

- 状态：已采纳（2026-10-14）
- 决策人：周宗正
- 关联：总档 §10、`core/adapters.py`

## 背景

apktool 解码一个 2MB APK 会产生数千小文件（实测单样本 smali 1091 个文件）。
旧项目经验：解码产物写在工作区内时 apktool 从 30s 恶化到 480s（杀毒/索引干扰）。

## 决策

1. **解码产物放工作区外临时区**：`%TEMP%/apkaudit_decode/<sha256前16>/`（可重建、不入库）；
   `evidence/RUN-*/decode/` 只收必要片段（重建的 AndroidManifest.xml 等）；
2. **apktool jar 随仓库入库**（`.tools/apktool_3.0.3.jar`，15.5MB，GitHub 单文件限制内），
   工具链查找顺序：项目内 `.tools/` → `JAVA_HOME` → PATH；
3. apktool 调用固定 `-p .tools/framework`：framework 缓存指向项目可控路径，
   避免 `%LocalAppData%` 隐式缓存影响复现；
4. 解码目录按 sha256 命名并**复用**：同一样本重复分析不重复解码（复现性依赖确定性解码）。

## 理由

- 解码是纯函数（同 APK → 同产物），缓存复用不破坏复现性但显著提速（5s vs 每次重解）；
- `.tools/` 入库达成"克隆即跑"；framework 缓存入 `.gitignore`（可重建）；
- 证据纪律：`evidence/` 只存事实索引，几万小文件不污染仓库。

## 后果

- `cli.py reset` 可清理解码缓存（可重建产物）；
- 复现检查（e2e A-09）在缓存预热后两次运行结论逐字段一致。

## 替代方案（被否）

- 解码写工作区内 `evidence/`：违反经验结论（性能灾难 + 仓库污染）；
- 依赖系统 Java：不同机器 Java 版本差异影响复现，且"不依赖系统默认"是硬要求。
