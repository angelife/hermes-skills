# USBNet 假在线：Docker utun 劫持（2026-07-17）

## 表象（容易误判）

```text
ping 192.168.15.244     → 0% loss, ~0.3ms
nc -z 192.168.15.244 22 → open
nc -z … 222/2222/8022   → 也 open
```

看起来像「Kindle USBNet + dropbear 在线」。

## 实测否证

| 检查 | 结果 |
|------|------|
| `route get 192.168.15.244` | `gateway 172.18.0.1` / **`interface: utun15`** |
| `ifconfig \| grep 192.168.15` | **无** Mac 本端 `192.168.15.1` |
| `system_profiler SPUSBDataType` | 只有 **Qualcomm Mi8 `a6520fa3`**，无 Lab126/Kindle |
| `/Volumes/Kindle` | 不存在 |
| `ssh -vvv root@192.168.15.244` | TCP 建立后立刻 `kex_exchange_identification: Connection closed`，**无 SSH banner** |
| `ssh-keyscan` / banner grab | 空 |

根因：Docker Desktop 的 `utun15`（`172.18.0.1`）吞掉了 `192.168.15.0/24` 流量；TCP open 是隧道侧假象，不是 Kindle dropbear。

## 同场仍可用的路径

- Mac Web Bridge：`~/kindle-bridge/proxy.py` 监听 `0.0.0.0:8081`
- 验证：`curl -s 'http://192.168.0.171:8081/?url=http://example.com'` → 200 + Example Domain
- Jina `r.jina.ai`：仍 TLS timeout → webbrowser 必须 `render_type=cre`
- 历史 WiFi IP `192.168.0.142`：ping 通，22/2222/8022 全关（SSH 未开）

## 给用户的最短指令

1. **上网**：Experimental Browser 只开 `http://192.168.0.171:8081`（http，同 WiFi）
2. **改插件/SSH**：退出 KOReader → 插成 U 盘出现 `/Volumes/Kindle` → 再改 `webbrowser_configuration.lua` / `authorized_keys`
3. **禁止**在 utun 假路由上反复试密钥算法

## 一句话规则

**ping + port open ≠ USBNet。先看 route interface 和 Mac 是否有 192.168.15.1。**
