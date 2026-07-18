# USB 插盘端到端修到可用 — 2026-07-17 下午

## 触发
用户：「我连到电脑上了 你帮我改吧 调试到可以用为止 完全授权」

## 现场
- `/Volumes/Kindle` 已挂载；Lab126 `G001PX1114150KMW`
- FW 5.16.2.1.1；KOReader v2026.03；Hotfix marker 2.5.0
- 插件配置**已经是** `duckduckgo` + `cre`（不能据此停手）
- 插件 history：多次 `https://192.168.0.171:8081`（错误）
- 日志仍有 x509 / TEE 0xffff3024 / DHAv2 / JwtSigner
- 无 usbnet 目录；SSH keys 在 `koreader/settings/SSH/authorized_keys`
- `192.168.15.244` 路由仍走 Docker `utun15`（假在线）

## 写盘清单（做完才算交付）
1. 确认/强制 `webbrowser_configuration.lua`：`engine=duckduckgo`、`render_type=cre`（可盖 `-- hermes-forced` 戳）
2. 校验 Mac `~/.ssh/id_rsa.pub` 在 `koreader/settings/SSH/authorized_keys`
3. 写 `documents/HOW_TO_USE_BRIDGE.txt`（http 桥地址 + KOReader 路径 + 禁止 15.244）
4. 写 `documents/net_diag.sh`（含 ping Mac + curl bridge）
5. `sync`
6. `diskutil eject /Volumes/Kindle`
7. 重启 Bridge：`terminal(background=true)` → `python3 ~/kindle-bridge/proxy.py`
8. Mac 侧验收：`curl http://127.0.0.1:8081/` 与 `/?url=http://example.com` 都 200

## 给用户的最短验收（3 步）
1. Experimental Browser → **`http://192.168.0.171:8081`**（禁止 https）→ 点 example.com
2. 完全退出再进 KOReader → Search → Web Browser → 搜索
3. 不通则插回读 `documents/net_report.txt`（先跑 net_diag.sh）

## 不要做
- 不为已可用桥再刷 Hotfix
- 不 ssh/scp 假在线 15.244
- 不把「配置已正确」当成任务完成
