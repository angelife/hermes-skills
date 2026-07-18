# 上游侦察实例 — v0.18.2 → 上游 (1030 commits)

本文件记录 2026-07-17 的一次升级评估，作为 `hermes-runtime-maintenance` Phase 0 的实例参考。

## 执行记录

```bash
# 版本
Hermes Agent v0.18.2 (2026.7.7.2) · upstream 75467998 · local 3d05d184 (+1 carried commit)

# 差距
1030 commits behind origin/main
```

## Breaking Change 检查

```bash
# 批量搜索所有 breaking 相关关键词
git log --oneline HEAD..origin/main --grep="breaking\|BREAKING\|migration\|deprecat"
# → 空 — 无 breaking change
```

## 分类统计（subsystem scale）

```
13 fix:honcho         # 记忆系统修复（最大块）
10 fix:desktop        # 桌面端
 3 fmt:js             # 格式化（无关）
 2 fix:memory         # 记忆预取守卫
 2 feat:honcho        # 记忆新功能
 1 feat:models        # 模型更新
 1 feat:gateway       # Gateway 特性
 1 feat:dashboard     # Dashboard
 1 fix:security       # 安全修复
 1 fix:update         # 更新机制
 1 fix:terminal       # 终端配置桥接
 1 fix:tui            # TUI 回退
```

**结论**：以 fix/chore 为主，没有大 feature 或重构，稳定版本。明确无 breaking。

## Config 兼容性

```bash
git diff --stat HEAD..origin/main -- config/
# → 空 — config schema 没变
```

## 本地 patch 文件（3 个）

| 文件 | 修改内容 | 上游是否也改了？ |
|------|---------|----------------|
| `plugins/model-providers/custom/__init__.py` | `default_max_tokens=28000`（上游=65536） | ✅ 是 — 需要重新改 |
| `plugins/model-providers/qwen-oauth/__init__.py` | `default_max_tokens=28000`（上游=65536） | ✅ 是 — 需要重新改 |
| `plugins/platforms/telegram/adapter.py` | backoff 5-60s → 1-16s + first retry immediate | ✅ 是 — 大量重构，需耐心重打 |

## 风险评级

**安全** — 0 breaking, config 兼容, 仅 3 个小 patch 需重打。

## 备份

3 个文件分别备份到 /tmp/：
- /tmp/hermes-custom-provider.py.bak
- /tmp/hermes-qwen-oauth.py.bak
- /tmp/hermes-telegram-adapter.py.bak