---
name: unified-self-check
description: 统一自检面板 — 手动或定时巡检全组件，打分出报告
category: devops
version: 1.0.0
triggers:
  - "自检"
  - "全组件巡检"
  - "health check all"
  - "统一自检"
  - "nightly check"
---

# Unified Self-Check — 统一自检面板

## 触发方式

- **手动**：加载本 skill 后直接执行
- **定时**：通过 cronjob 每晚自动巡检

## 检查范围（7 层）

| 层 | 组件 | 检查项 | 权重 |
|----|------|--------|------|
| 🧠 Runtime | Hermes 进程 | 进程活着？版本？ | 20 |
| 💾 记忆 | Hindsight / memory | 服务通？容量？ | 15 |
| 🌐 网络 | 代理/DNS/国际出口 | 端口通？DNS 解析？ | 15 |
| 📱 设备 | Mac/Android | 在线？健康？ | 10 |
| ⚙️ 技能 | 技能库质量 | 有效性审计（第二件事） | 15 |
| 🗄️ 基础设施 | 磁盘/CPU/内存 | 水位告警 | 15 |
| 📋 看板 | Kanban 状态 | orphaned locks？ | 10 |

## 执行流程

### 1. 数据采集（并行执行）

```bash
# Runtime
hermes --version 2>&1 | head -3

# 进程
ps aux | grep -iE '(hermes|hindsight|python.*bot)' | grep -v grep

# 监听端口
lsof -iTCP -sTCP:LISTEN -P 2>/dev/null | head -20

# 网络
nc -z -w 2 127.0.0.1 10808 && echo "PROXY_OK" || echo "PROXY_DOWN"
ping -c1 -W2 8.8.8.8 2>/dev/null | grep "bytes from" && echo "INTERNET_OK" || echo "INTERNET_DOWN"
ping -c1 -W2 google.com 2>/dev/null | grep "bytes from" && echo "DNS_OK" || echo "DNS_DOWN"

# 基础设施
df -h / | tail -1
memory_pressure 2>/dev/null | head -5
uptime

# 设备
system_profiler SPHardwareDataType 2>/dev/null | grep -E "Model Name|Memory|Processor"
```

### 2. 评分规则

每层按以下标准打分（0-100）：

| 分数 | 含义 |
|------|------|
| 100 | 完美，无任何问题 |
| 80 | 正常，有小瑕疵但不影响使用 |
| 60 | 可用但有明显问题 |
| 40 | 部分不可用 |
| 20 | 基本不可用 |
| 0 | 完全不可用 |

**总分 = 各层分数 × 权重 / 100**

### 3. 报告输出格式

```
━━━ 统一自检报告 — YYYY-MM-DD HH:MM ━━━

🧠 Runtime:    85/100  (v0.18.2, 进程正常)
💾 记忆:       70/100  (Hindsight 运行中, 容量 78%)
🌐 网络:       90/100  (代理通, DNS 通, 国际出口通)
📱 设备:       80/100  (Mac 正常, ADB 设备在线)
⚙️ 技能:       75/100  (待细化审计)
🗄️ 基础设施:   85/100  (磁盘 45%, 内存压力正常)
📋 看板:       90/100  (无 orphaned locks)

━━━ 总分: 82/100 ━━━

✅ 正常: Runtime, 网络, 基础设施, 看板
⚠️ 注意: 记忆容量偏高, 技能待审计
❌ 异常: 无
```

## 与五行舰桥的关系

- 评分文件由本 skill 写入；**展示**在 `kindle-dashboard`（`:28080`）
- 舰桥另有「系统建成总进度 / 今日进度 / 架构分层 / 服务监管」——自检 7 层是其中一块，不是全部
- 机器读：`curl -s http://127.0.0.1:28080/api/status`
- 改 `scores.json` 后无需重启 dashboard（读文件渲染）
- 舰桥的"系统建成总进度"数据源：对比 `architecture-v2` 页面中的 tag-stable/tag-wip 比例，乘以实时服务健康度（端口探测）
- 舰桥的"今日进度"数据源：`~/.hermes/state/active/task.yaml`、`~/Documents/Obsidian Vault/每日工作记录/_TODO.md`、`~/.hermes/CREATIVE.md`
- 舰桥的"架构分层状态"：从 `architecture-v2` 页面解析五个分层（输入/处理/知识/输出/编辑），每层组件统计 stable/wip 数 + 实时端口探测

## 写评分文件

每次自检完成后，将评分写入供 Kindle 面板读取：

```bash
mkdir -p ~/.hermes/state/self_check
cat > ~/.hermes/state/self_check/scores.json << 'SCORE_EOF'
{
  "timestamp": "YYYY-MM-DD HH:MM:SS",
  "scores": {
    "runtime": {"score": 85, "detail": "v0.18.2, 进程正常", "weight": 20},
    "memory": {"score": 60, "detail": "Hindsight 离线", "weight": 15},
    "network": {"score": 40, "detail": "代理通, 出口不通", "weight": 15},
    "devices": {"score": 85, "detail": "Mac 正常, ADB MI8", "weight": 10},
    "skills": {"score": 50, "detail": "待审计", "weight": 15},
    "infrastructure": {"score": 70, "detail": "磁盘 5%, load 高", "weight": 15},
    "kanban": {"score": 50, "detail": "未检查", "weight": 10}
  },
  "total": 60
}
SCORE_EOF
```

## 定时任务

每晚 21:00 自动巡检，通过 cronjob 调度：

```bash
hermes cron create \
  --name "nightly-self-check" \
  --schedule "0 21 * * *" \
  --skill unified-self-check \
  --prompt "执行统一自检，输出全组件评分报告，并将评分写入 ~/.hermes/state/self_check/scores.json" \
  --deliver "origin"
```

## Hindsight / 嵌入服务评分（防假阳性）

**禁止**用 `pgrep -f hindsight` 判定「记忆层失败」。

Hindsight 常为 `local_external` / 嵌入模式：空闲约 5 分钟自动退出，下次 `hindsight_recall/retain` 再起。进程不在 ≠ 不可用。

正确判定（与 `kindle-dashboard/references/daemon-detection-patterns.md` 一致）：
1. `127.0.0.1:8888` 端口可达 → ✅ 就绪（高分）
2. 端口不通但 `~/.hermes/hindsight/exports/` 有近期导出 / 本会话 recall 成功 → ✅ 嵌入按需（中高分，detail 写「嵌入模式」）
3. 配置缺失且 API/导出皆无 → ❌ 再扣分

`scores.json` 的 memory.detail 示例：`"Hindsight 嵌入模式"` / `"Hindsight 就绪"`，不要写「无 hindsight 进程」当唯一依据。

## 注意事项

- 数据采集阶段所有独立命令应并行执行
- 评分基于客观数据，不主观臆断
- 发现异常时引用具体数据，不模糊描述
- 本技能不修改任何系统配置，只读
- 网络探测优先本机代理端口；避免在沙箱里无超时的出站 ping 卡死面板
