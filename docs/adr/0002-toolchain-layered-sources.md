# ADR-0002 · 工具链与数据源分层：apktool + 自研 AXML/dex 直读

- 状态：已采纳（2026-10-14）
- 决策人：周宗正
- 关联：总档 §3.3/§10、`specification.md` §1

## 背景

解析 APK 需要 manifest、dex 字符串、smali 三个层面的数据。常见选项：
jadx（反编译失败率）、apktool 单源（重依赖 Java）、纯自研（工作量巨大）。

## 决策

**四层数据源，各自独立降级**：

| 数据源 | 生产者 | 不依赖 |
|--------|--------|--------|
| `manifest` | 自研 AXML 直读 `core/axml.py` | 零外部依赖 |
| `dex_strings` | 自研 dex 扫描 `core/dexscan.py` | 零外部依赖 |
| `smali_src` | apktool 反汇编 | 需 Java（`.tools/` 随仓库） |
| `res_decoded` | apktool 资源解码 | 同上 |

语义类规则**以 smali 实现**（字节码 1:1 直译，不存在反编译失败率），不用 jadx。

## 理由

- 自研直读保证"没有 apktool 也能跑 M/S 类"——工具链缺席时报告仍有一半价值，且覆盖声明如实；
- apktool 修 Java 生态的成熟性，随仓库携带 15.5MB jar，任何机器克隆即跑；
- 两份独立证据源（自研直读 vs apktool 重建）可交叉核对 manifest 事实。

## 后果

- 正面：降级路径清晰；smali 定位可给「文件:行号 + 原始行号」双坐标；
- 负面：需要自维护 AXML/DEX 二进制解析（已用合成夹具测试保障，见 tests/）；
- 实测：apktool 3.0.3 + Java 8，解码 2MB APK 约 5 秒；解码产物写工作区外（ADR-0005）。

## 替代方案（被否）

- jadx：反编译失败率不可控，违反"全输入受理"；
- 只用 apktool：Java 缺席即全盲，M/S 类本可零依赖完成。
