# 统一 ADB 连接管理

## 背景

多套脚本各自硬编码手机 IP/串号。ADB 连接状态变化（主动插拔、路由器分配不同 IP、授权过期）导致每套脚本独立故障。最典型就是手机 IP 从 `192.168.1.26` 变为 `192.168.2.106`，`pull_wechat.sh` 用旧 IP 连不上，但 `wechat-group-monitor.py` 仍有自己的硬编码，各自失败没有统一恢复。

## 解决方案

**集中一处管理 ADB 发现逻辑，所有脚本通过 source 导入使用。**

### adb-connect.sh

路径：`~/.hermes/scripts/adb-connect.sh`

```
USAGE:
  source adb-connect.sh && get_adb_device   # 获取可用设备串号
  bash adb-connect.sh status                 # 显示ADB状态
  bash adb-connect.sh proxy                  # 开启USB代理隧道
  bash adb-connect.sh noproxy                # 关闭代理隧道
```

### 设备发现策略
1. **USB 优先** — 用固定串号 `a6520fa3` 匹配 `adb devices` 输出
2. **已有 TCP 连接** — 扫描已连的 TCP 设备
3. **端口探测** — 快速探测已知候选 IP 的 5555 端口（0.8s timeout）
4. **全部失败** — 返回空，调用方走本地缓存备用

### 通信隧道（USB 反向代理）
`adb reverse tcp:10808 tcp:10808` 让手机使用 Mac 的 v2rayN 代理上网，零流量费。

启用：`bash adb-connect.sh proxy`
关闭：`bash adb-connect.sh noproxy`

### 已接入脚本
| 脚本 | 修改日期 | 说明 |
|------|----------|------|
| `pull_wechat.sh` | 2026-07-17 v4 | 微信自动拉取 |
| `wechat-group-monitor.py` | 2026-07-17 | 群监控 |

### 注意事项
- adb reverse 隧道在 USB 断开/ADB 重启后失效，重新连接后需要再跑一次
- 离线 adb 状态（`offline`）无法自动化修复——需要手机端确认 RSA 授权
- USB 串号 `a6520fa3` 不变，比 TCP IP 稳定
