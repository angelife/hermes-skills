# OPDS 无线传书 + IP 漂移（2026-07-17 验收）

## 已验收路径
- Mac：`calibre-server --port 8089 --listen-on 0.0.0.0 "/Users/macos/Calibre Library"`
- OPDS：`http://<Mac-LAN-IP>:8089/opds`（http only，末尾 `/opds`）
- Kindle：KOReader → Search → OPDS catalog → Add catalog → Newest/搜书 → Download
- 备用书单：`http://<IP>:8091/`；Web Bridge：`http://<IP>:8081/`（禁止 https）

## 查/同步当前地址（换网必做）
```bash
~/kindle-bridge/sync-lan-ip.sh
~/kindle-bridge/sync-lan-ip.sh --status
~/kindle-bridge/current-opds-url.sh
```
- 状态 `~/.hermes/state/lan-ip.json`；入口卡 `~/kindle-bridge/CURRENT_URLS.txt`
- launchd `com.angelife.lan-ip-sync`；伞技能 **`lan-ip-auto-sync`**

## 失败时诊断顺序
1. Mac `curl` `/opds` → 200
2. 8089 连接来源只有本机、无 Kindle IP → Kindle 没连上，不是书库坏
3. 查：同 WiFi？旧 IP？https？菜单是否 OPDS catalog？
4. 禁止当真 `192.168.15.244` USBNet

## IP 漂移
- 图书馆 vs 家里 → OPDS 存 `Mac-馆` / `Mac-家`
- 回家/到馆：跑 `sync-lan-ip.sh` 或等 launchd
- 家里可 DHCP 保留；不推荐 `.local`
- bind `0.0.0.0` 服务不必因 IP 变重启；`proxy.py` 首页动态取 IP

## 相关
- 伞：`lan-ip-auto-sync`、`kindle-maintenance`
- 本机：`~/kindle-bridge/HOW_TO_WIRELESS_BOOKS.txt`、`push-book.sh`、`sync-lan-ip.sh`
