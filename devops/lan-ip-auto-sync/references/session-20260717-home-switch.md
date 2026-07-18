# 会话沉淀：回家 IP 变 + OPDS 传书（2026-07-17）

## 用户信号
- OPDS 验收通过后问：图书馆 IP ≠ 家里 IP 怎么办？
- 纠正方向：不是只记一条 OPDS，而是「回家了 → 所有写死局域网 IP 的服务入口自动改」
- 技能：`lan-ip-auto-sync` + 脚本 `~/kindle-bridge/sync-lan-ip.sh`

## OPDS 失败根因（本会话）
- Mac calibre-server :8089 /opds 本机与 LAN 均 200
- 8089 连接来源仅本机 → Kindle 从未打到服务
- 不是目录格式坏；是同网/地址/菜单

## 机制
| 件 | 路径 |
|----|------|
| 同步脚本 | `~/kindle-bridge/sync-lan-ip.sh` |
| launchd | `com.angelife.lan-ip-sync` 每 5min |
| 状态 | `~/.hermes/state/lan-ip.json` |
| 入口卡 | `~/kindle-bridge/CURRENT_URLS.txt` |
| 桥动态 IP | `proxy.py` `lan_ip()` 展示用 |

## 安全边界
- Kindle 展示文件：可 bootstrap 旧馆 IP（如 192.168.0.171）
- 舰队 state（如 192.168.1.8）：**仅** lan-ip.json 有明确 old→new 才替换
- 永不替换 192.168.15.x USBNet

## 用户交付口径
纯中文最短：跑脚本 → 给三个 URL（桥/OPDS/书单）→ OPDS 改那条目录。
