# KOReader 无线传书方法

在 KOReader 中直接传书，不用退出回 Kindle 原生系统。

## 1. Calibre 无线推送（首选）

KOReader 内置 Calibre 无线设备协议支持：

KOReader 侧：
- 菜单 → Tools → Calibre → Start Calibre wireless
- 记下显示的 IP:端口（默认 `192.168.15.244:9090` 或 WiFi IP）

Mac 侧：
- 安装 Calibre → Connect/share → Connect to device
- 选择无线设备 → 输入 KOReader 显示的地址
- 直接拖拽文件推送

## 2. WebDAV

KOReader 支持 WebDAV 云存储（在 File manager → Cloud storage 中配置）。
配置后直接在 KOReader 内浏览/下载远端文件。

## 3. SSH / SCP（需要配密钥）

Kindle USBNet 默认 SSH 到 `192.168.15.244`，但 dropbear（SSH 服务器）拒绝
密码登录，只允许密钥认证。

### 首次配置：
1. 插 USB → Kindle 挂载为存储盘
2. 在 `/Volumes/Kindle/` 下找到 `etc/ssh/authorized_keys`（或 dropbear 的 
   `authorized_keys` 文件）
3. 把 Mac 公钥追加进去

### 常规传书：
```bash
scp book.pdf root@192.168.15.244:documents/
```

### USBNet 端口备忘：
| 端口 | 服务 | 状态 |
|------|------|------|
| 22 | SSH (dropbear) | 开放但拒绝密码登录 |
| 2222 | 备用 SSH | 同上 |
| 8022 | 备用 SSH | 同上 |
| 80 | HTTP | 开放（Kindle Web 服务器） |
| 8080 / 9090 | HTTP | 开放（用途待确认） |

## 4. USB 存储（需退 KOReader）

传统方式：退出 KOReader → 插 USB → 拖拽文件 → 弹出 → 回 KOReader 刷新。
优点是无需配网，缺点是打断阅读。

## 对比

| 方法 | 是否退 KOReader | 需配网 | 需配密钥 | 推荐度 |
|------|-----------------|--------|----------|--------|
| Calibre 无线 | 否 | WiFi | 否 | ★★★★★ |
| WebDAV | 否 | WiFi | 否 | ★★★★ |
| SSH | 否 | USBNet | 是 | ★★★ |
| USB 存储 | 是 | 否 | 否 | ★★★ |
