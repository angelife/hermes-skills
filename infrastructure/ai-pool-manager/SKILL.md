---
name: ai-pool-manager
description: "统一 AI Provider 连接池管理器。自动检测各 Provider 健康状态、配额余量，卡死自动切换、故障自动恢复。"
version: 1.0.0
author: Hermes Agent
platforms: [macos, linux]
metadata:
  hermes:
    tags: [AI, Provider, Pool, Failover]
---

# AI Provider Connection Pool Manager

统一管理多个 AI Provider 的连接池、健康检查、自动故障切换。

## 脚本位置

```
~/.hermes/scripts/pool_manager.py
```

## 使用方式

```bash
# 查看所有 Provider 状态
python3 ~/.hermes/scripts/pool_manager.py status

# 持续监控（每5分钟自动检查）
python3 ~/.hermes/scripts/pool_manager.py monitor

# 强制切换到指定 Provider
python3 ~/.hermes/scripts/pool_manager.py switch deepseek-flash

# 测试指定 Provider
python3 ~/.hermes/scripts/pool_manager.py test deepseek-pro

# 恢复所有失败 Provider
python3 ~/.hermes/scripts/pool_manager.py recover
```

## 支持 Provider

| Provider | 环境变量 | 优先级 |
|----------|----------|--------|
| hermes-default | - | 0 |
| deepseek-flash | DEEPSEEK_API_KEY | 1 |
| deepseek-pro | DEEPSEEK_API_KEY | 2 |
| glm-5 | ZHIPU_API_KEY | 3 |
| qwen-3 | DASHSCOPE_API_KEY | 4 |

## 故障恢复策略

1. 3次连续失败 → 标记为不可用
2. 自动选最低 priority 的健康 Provider 作为活跃 Provider
3. `recover` 命令重置所有 fail_count
4. `switch` 命令强制锁定到指定 Provider

## 状态文件

- 状态: `~/.hermes/pool_state.json`
- 日志: `~/.hermes/pool.log`
- 监控间隔: 300秒