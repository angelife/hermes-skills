---
name: hermes-opencli-integration
description: OpenCLI + Hermes 工作流集成 — 用 OpenCLI 的 1257+ 命令替代 Hermes 自身 web_search，节省 token 消耗。覆盖安装、配置、Android 避坑、常用命令速查。
trigger: 用户要求省 token、用 OpenCLI 搜索、微信文章提取、知乎热榜、手机端集成
---

# OpenCLI + Hermes 集成工作流

## 前置条件

### Mac 端
- OpenCLI v1.8.5+（`npm install -g @jackwener/opencli`）
- Chrome + **OpenCLI 扩展**（不是 Browser Bridge！）
  - Web Store ID: `ildkmabpimmkaediidaifkhjpohdnifk`
  - 链接：https://chromewebstore.google.com/detail/opencli/ildkmabpimmkaediidaifkhjpohdnifk
- 验证：`opencli doctor` → 全部绿灯（Daemon + Extension + Connectivity）

### 手机端（Mi6/Mi8/坚果Pro3）
- Termux + Node.js 已安装
- 手机 Chrome 不支持扩展 → 不走 OpenCLI，改用 Hermes 原生 web_search
- 安装 Termux Hermes 时注意（详见下方避坑表）

## 验证连接

```bash
opencli doctor
# 预期输出：
# [OK] Daemon: running on port 19825
# [OK] Extension: connected (v1.0.21)
# [OK] Connectivity: connected in 1.xs
```

如果显示 `Extension: disconnected`，先重启 daemon：
```bash
opencli daemon restart
```

## 常用命令速查

### 微信文章
```bash
# 下载微信公众号文章 → Markdown
opencli weixin download --url "https://mp.weixin.qq.com/s/..."

# 搜狗微信搜索
opencli weixin search "关键词"
```

### 知乎
```bash
# 知乎热榜
opencli zhihu hot

# 知乎搜索
opencli zhihu search "关键词"

# 知乎文章下载为 Markdown
opencli zhihu download --url "https://zhuanlan.zhihu.com/p/..."
```

### 通用网页
```bash
# 任意 URL → Markdown
opencli web read --url "https://..."
```

### 输出格式控制
```bash
# JSON 输出（给 AI 吃）
opencli zhihu hot -f json

# YAML 输出（人类可读）
opencli zhihu hot -f yaml
```

## 与 Hermes web_search 对比

| 维度 | web_search | OpenCLI |
|---|---|---|
| 成本 | 每次 0.002-0.02 元 | **0 元** |
| 速度 | 3-30s | 8-18s |
| 输出结构 | 非结构化 | JSON/YAML/MD |
| 站点深度 | 通用搜索 | 162 个站点专属适配器 |
| 登录态 | 不需要 | 部分需 Chrome 登录态 |

**使用策略：**
- 通用信息查询 → **web_search**（更快，不需要浏览器）
- 特定站点深度提取 → **OpenCLI**（结构化，零 token 成本）
- 微信公众号文章 → **OpenCLI weixin download**（唯一可靠方案）

## 每日知识流水线（OpenCLI + Hermes cron + Obsidian）

OpenCLI 可配合 Hermes cron + Obsidian 实现全自动知识采集、编译、存储。详见 `references/daily-knowledge-pipeline.md`。

核心流程：
1. 脚本用 OpenCLI 从知乎/微信/GitHub 采集原始数据
2. Hermes cron（script + prompt）清洗、去重、摘要、分类
3. 写入 Obsidian 编译后的结构笔记
4. Telegram 推送当日报摘要

每天 9:00 自动运行，零人工干预。适合把"临时检索"变成"提前编译"的知识管理场景。

## Android Hermes 安装避坑表

从公众号文章《只要三步，把Hermes装进旧手机》总结：

| 问题 | 原因 | 解决方案 |
|---|---|---|
| Termux 闪退 | Android 12+ 幽灵进程限制 | 从 F-Droid 下载 Termux，或 ADB 关闭限制 |
| 后台被杀 | 系统省电策略 | 电池白名单 + `termux-wake-lock` |
| 安装编译错误 | 缺少编译工具链 | 装 `clang rust make pkg-config libffi openssl` |
| `jiter`/`maturin` 报错 | 缺少 `ANDROID_API_LEVEL` | `export ANDROID_API_LEVEL=$(getprop ro.build.version.sdk)` |
| `uv pip install` 失败 | uv 在 Android 兼容性不佳 | 改用 `python -m pip install` |
| 存储不可写 | 未授权 | `termux-setup-storage` 并点「允许」 |
| SSH 连不上 | 服务未启动 | 执行 `sshd` 或装 `termux-services` |

## 自更新工作流（文章 3 方法论）

借鉴《调教Hermes第三弹：扔一条链接，它自己打怪升级》：

1. **喂材料** — 扔一个新工具/文档链接给 Hermes
2. **自行对比** — 读文档 → 对照自己缺什么
3. **排优先级** — 自动分 P0/P1/P2
4. **打补丁** — 自修技能文档（版本化：v2.0.0 → v2.1.0）

### 对新工具的独立评估
不要盲从描述 → 自己去查数据（GitHub Stars、最后更新、社区活跃度）→ 出结论 → 设 cron 持续跟踪。

## 已知问题
- `opencli daemon` 监听 19825 端口，**不能改**（OpenCLI 扩展固定连这个端口）
- 安装的是 `OpenCLI` 扩展，不是普通 `Browser Bridge` 扩展（后者连 3210 端口导致失联）
- 手机端不推荐装 OpenCLI（需要 Chrome + 扩展，违背省内存原则）
