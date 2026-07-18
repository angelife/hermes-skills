# 守护进程检测模式

## 问题

某些服务（如 Hindsight）以嵌入模式运行——进程空闲 5 分钟后自动退出，下次调用时重启。
`pgrep -f hindsight` 返回空不代表服务不可用。

## 检测策略（优先级递减）

### 1. API 端口可达性（最可靠）
```python
import socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(1)
sock.connect(("127.0.0.1", 8888))  # hindsight 端口
sock.close()
# 通 = 服务就绪
# 不通 = 可能空闲或未启动
```

### 2. 数据痕迹回退
```python
export_dir = Path.home() / ".hermes" / "hindsight" / "exports"
recent = sorted(export_dir.glob("*"))[-1] if list(export_dir.glob("*")) else None
if recent:
    # 有最近导出 = 功能正常
```

### 3. 进程检测（仅对常驻服务有效）
```python
import subprocess
r = subprocess.run(["pgrep", "-f", "hindsight"], capture_output=True, timeout=2)
# r.returncode == 0 → 进程存在
```

## 适用场景

| 服务 | 检测方式 | 端口 | 备注 |
|------|---------|------|------|
| Hindsight | 端口可达性 | 8888 | 嵌入模式，按需启动 |
| Hermes Gateway | 进程检测 | - | 常驻 (launchd) |
| xray 代理 | 端口可达性 | 10808 | 常驻 |
| OpenBridge | 端口可达性 | 10088 | 常驻 (node) |
| ADB 服务 | 进程检测 | 5037 | 常驻 |
