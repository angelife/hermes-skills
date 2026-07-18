# v2rayN SQLite 数据库操作

## 数据库位置

```
~/Library/Application Support/v2rayN/guiConfigs/guiNDB.db
```

## 核心表结构

### ProfileItem — 代理节点

```
IndexId    TEXT PRIMARY KEY  — 节点唯一ID
ConfigType INTEGER          — 5=CF优选(Cloudflare WARP), 10=自定义入口
Remarks    TEXT              — 节点显示名称
Address    TEXT              — 服务器地址/IP
Port       INTEGER           — 端口
Security   TEXT              — 加密/安全类型
```

ConfigType=5 的节点走 **Cloudflare WARP**，部分境外域名（如 x.ai/Grok）无法路由。
ConfigType=10 通常是自定义入口（如 iPhone 代理），可能有不同路由。

### SubItem — 订阅分组

```
Id                 TEXT PRIMARY KEY — 订阅ID
Remarks            TEXT             — 订阅名称
Url                TEXT             — 订阅链接
MoreUrl            TEXT             — 备用订阅链接
Enabled            INTEGER          — 1=启用
Sort               INTEGER          — 排序序号
AutoUpdateInterval INTEGER          — 自动更新间隔(小时)
UpdateTime         INTEGER          — 最后更新时间(unix时间戳)
ConvertTarget      TEXT             — 转换目标格式
```

### SubIndexId 与当前活动节点

guiNConfig.json 中的 `SubIndexId` 指向活跃的订阅分组 ID。
当前活跃节点由 guiNConfig.json 的 `IndexId` 指向 ProfileItem.IndexId。

## 常用查询

```sql
-- 所有节点
SELECT IndexId, ConfigType, Remarks, Address, Port FROM ProfileItem ORDER BY ConfigType;

-- 按类型统计
SELECT ConfigType, COUNT(*) as cnt FROM ProfileItem GROUP BY ConfigType;

-- 所有订阅
SELECT * FROM SubItem;

-- 当前活跃节点 (IndexId 来自 guiNConfig.json)
SELECT * FROM ProfileItem WHERE IndexId = '5615807202981575677';
```

## 添加订阅到 v2rayN

```bash
SUB_URL="https://example.com/sub?token=xxx"
SORT=$(sqlite3 guiNDB.db "SELECT MAX(Sort)+1 FROM SubItem")
ID=$(python3 -c "import uuid; print(str(uuid.uuid4().int)[:19])")

sqlite3 guiNDB.db "INSERT INTO SubItem (Id, Remarks, Url, Enabled, Sort, AutoUpdateInterval, UpdateTime) VALUES ('$ID', '订阅名称', '$SUB_URL', 1, $SORT, 0, $(date +%s));"
```

添加后需要在 v2rayN GUI 中点击 **订阅分组 → 更新订阅** 拉取节点。拉取后节点会出现在 ProfileItem 表中。

### 从 Telegram 导出数据中获取代理订阅

当需要访问被当前代理路由阻断的域名时，可从 `~/.hermes/telegram_exports/` 的 JSON 导出文件中搜索。

搜索关键词：
```
订阅链接:           — 多数免费代理附带的链接
subscribe?token     — 机场订阅格式
vmess:// / vless://  — 单节点分享
trojan://            — Trojan 协议节点
```

使用系统 curl 验证订阅有效性（通过当前代理）：
```bash
curl -s -x http://127.0.0.1:10808 --max-time 10 "订阅URL" | head -5
# 返回 base64 节点列表 = 有效
# 空或 token is error = 已过期或失效
```

找到有效订阅后，按本节方法添加到 SubItem 表。

注意：多数免费订阅使用 Cloudflare WARP，对部分目标（如 x.ai/Grok）同样无法路由。但仍可能有非 CF 节点，值得试。

### 私享/自建节点订阅

用户可能持有**自建节点**的订阅（raw GitHub URL 等），这类节点通常是非 CF 的真实服务器（HK/US/SG/NL 等地）。

特征：
- URL 格式类似 `https://raw.githubusercontent.com/用户名/仓库/分支/文件名`
- 节点协议常见 VLESS + Reality（xtls-rprx-vision）或 VLESS + TLS/WebSocket
- 服务器 IP 非 Cloudflare 段（非 104.x/172.x/162.x/188.x/198.x）

添加方式与普通订阅相同，通过 SubItem 表 INSERT。

### 独立测试私享节点（无需 GUI）

1. 先用 socket 测端口开放：`python3 -c "import socket; s=socket.socket(); s.settimeout(5); s.connect(('IP',端口)); print('OPEN')"`
2. 再用 ssl 测 TLS 握手：`python3 -c "import ssl,socket; ctx=ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE; s=ctx.wrap_socket(socket.create_connection(('IP',端口)), server_hostname='SNI'); print('TLS OK')"`
3. 最后配独立 xray config 测试（见主 SKILL.md「xray 独立实例测试」章节）

## 切换当前活动节点

- 应用：`/Applications/v2rayN.app`
- 配置目录：`~/Library/Application Support/v2rayN/`
- GUI 配置：`guiConfigs/guiNConfig.json`
- 内核配置：`binConfigs/`（xray/sing-box 运行时的 `-c config.json` 在此）
- 内核日志：`guiLogs/`
- 核心二进制：`bin/xray/xray`, `bin/sing_box/sing-box`

## 进程与端口

- xray: PID 可通过 `lsof -ti tcp:10808` 获取
- sing-box: 通常以 root 运行，PID 通过 `ps aux | grep sing-box` 查找
- 端口 10808: SOCKS5 + HTTP CONNECT 混合监听

## 代理域名可达性

不同代理节点的路由规则不同。测试方法：

```bash
curl -s -x http://127.0.0.1:10808 --max-time 5 -o /dev/null -w "%{http_code}" https://target-domain.com
# 200=通, 000=不通(代理路由拦截)
```

也可直接解析 IP 后用 `--resolve` 参数定向测试特定出口 IP 的连通性：

```bash
curl -s -x http://127.0.0.1:10808 --max-time 5 \
  --resolve "accounts.x.ai:443:128.242.240.91" \
  -o /dev/null -w "%{http_code}" https://accounts.x.ai
```
