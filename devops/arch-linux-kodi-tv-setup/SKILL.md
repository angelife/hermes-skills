---
name: arch-linux-kodi-tv-setup
description: 把一块 Arch Linux 机器设为 Kodi 电视播放器 — 开机自启、中文界面、中文字幕、SSH 维护。覆盖 Intel 核显笔记本场景（旧电脑改电视盒）。
triggers:
  - "装 Kodi"
  - "电视盒子"
  - "Kodi 配置"
  - "Arch 电视"
  - "旧电脑改电视"
  - "老人看电视"
---

# Arch Linux Kodi TV Box Setup

把一台 Arch Linux 旧电脑/笔记本设为 Kodi 电视播放器。开机自动进 Kodi 全屏中文界面，SSH 后台可维护。

## 安装

```bash
# 安装 Kodi + 音频
sudo pacman -S kodi pulseaudio pulseaudio-alsa
```

## 自动登录 + Kodi 自启

### 1. getty 自动登录

```bash
sudo mkdir -p /etc/systemd/system/getty@tty1.service.d
cat << EOF | sudo tee /etc/systemd/system/getty@tty1.service.d/autologin.conf
[Service]
ExecStart=
ExecStart=-/usr/bin/agetty --autologin <用户名> --noclear %I $TERM
EOF
```

### 2. .xinitrc — Kodi 替代窗口管理器

```bash
cat > ~/.xinitrc << "EOF"
#!/bin/sh
exec kodi-standalone
EOF
chmod +x ~/.xinitrc
```

### 3. .bash_profile — tty1 自动启动 X + Kodi

```bash
cat >> ~/.bash_profile << "EOF"

if [ "$(tty)" = "/dev/tty1" ]; then
    exec startx
fi
EOF
```

### ⚠️ 关键陷阱：不要创建 systemd kodi 服务

如果你用 `.bash_profile` + `startx` 路径启动 Kodi，**不要同时创建 `kodi.service` systemd unit**。两者冲突会导致：
- Kodi 启动失败
- SSH 被拒接（连接被关闭）
- 系统卡在 kext/key-exchange

**选一个路径即可。** 推荐 `.bash_profile` 路径（更可控）。

## 中文界面

### 1. 下载中文语言包

```bash
curl -L -o /tmp/zh_cn.zip \
  "https://mirrors.kodi.tv/addons/omega/resource.language.zh_cn/resource.language.zh_cn-11.0.101.zip"
mkdir -p ~/.kodi/addons
cd ~/.kodi/addons && unzip -qo /tmp/zh_cn.zip
```

### 2. 修改 Kodi 配置

```bash
# ⚠️ 关键：先设字体为 Arial，再切语言
sed -i \
  -e 's|<setting id="lookandfeel.font" default="true">Default</setting>|<setting id="lookandfeel.font">Arial</setting>|' \
  -e 's|<setting id="locale.language" default="true">resource.language.en_gb</setting>|<setting id="locale.language">resource.language.zh_cn</setting>|' \
  -e 's|<setting id="locale.country" default="true">USA (12h)</setting>|<setting id="locale.country">China</setting>|' \
  -e 's|<setting id="screensaver.mode" default="true">default</setting>|<setting id="screensaver.mode"></setting>|' \
  ~/.kodi/userdata/guisettings.xml
```

**font → Arial 必须在 zh_cn 之前**。Kodi 默认字体（Default）不含中文字形，先切语言再改字体，界面会显示乱码方块，无法操作。

### 3. 重启 Kodi 生效

重启后界面即为简体中文。

## 中文字幕插件

```bash
cd /tmp && git clone --depth=1 https://github.com/qzydustin/service.subtitles.chinesesubtitles.git
cp -r /tmp/service.subtitles.chinesesubtitles ~/.kodi/addons/service.subtitles.chinesesubtitles
# 也装仓库源（方便更新）
cp -r /tmp/service.subtitles.chinesesubtitles/repository.chinesesubtitles ~/.kodi/addons/
```

支持 SubHD 和 Zimuku 字幕源。

## 关键工作流：先验证再交付

**用户明确强调："不光装上还要保证能用"**

每个组件配置后必须验证实际可用性，不能仅确认"已安装"：

```bash
# IPTV 频道直连验证（不走代理，从中国 IP 测）
curl -s --max-time 5 "http://<频道源地址>" -o /dev/null -w "%{http_code}"

# 代理隧道验证（从 Kodi 机器）
curl -s -x http://127.0.0.1:10808 https://www.youtube.com -o /dev/null -w "%{http_code}"

# Kodi 进程确认
ps aux | grep kodi.bin
```

**判断标准：** HTTP 200 = 可用。任何 4xx/5xx/000 说明有问题需要排查，不能跳过。

## 音频配置

Kodi 默认 PulseAudio 输出。确认音频设备：

```bash
pactl info
aplay -l
```

HDMI 音频无需特别配置，PulseAudio 自动检测。

## SSH 维护准备

```bash
sudo systemctl enable sshd
```

密码登录默认开启（Arch 默认）。免密 sudo 可选：

```bash
echo "<用户名> ALL=(ALL) NOPASSWD:ALL" | sudo tee /etc/sudoers.d/<用户名>
```

### ⚠️ 铁律：不要远程重启或卸载 Kodi

**绝对不要** 从 SSH 远程 `pkill -f kodi-standalone` 或任何方式杀 Kodi 进程。电视前面可能有人在看。一次杀进程 = 电视机前黑屏一次。用户反馈「又重启了」说明正在搞破坏。

**自动重启的真正原因：**
- `kodi-standalone` 包装脚本**设计上就会自动重启** Kodi（崩溃/退出后立即重新拉起），这不是 bug
- "无限重启"通常是因为：
  1. 多个 `kodi-standalone` 实例在跑（比如误操作启动了第二个 X 服务器）
  2. 赛扬 T3500 跑 2+ 个 Kodi 进程，CPU/内存耗尽导致 kodi.bin 崩溃
  3. 崩溃 → 包装脚本拉新的 → 再崩溃 → 死循环
- **修复方法：**
  ```bash
  # 1. 杀掉所有 Kodi 和多余的 X 服务器
  killall -9 kodi.bin kodi-standalone
  kill $(cat /tmp/.X1-lock)  # 杀掉第二个 X 服务器 (:1)

  # 2. 确认只剩一个 X 在跑
  ps aux | grep Xorg

  # 3. 重新启动 Kodi
  nohup /usr/bin/kodi-standalone > /dev/null 2>&1 &
  ```
- **如何判断：** `ps aux | grep kodi | grep -v grep | wc -l` 输出应 ≤3（wrapper + --standalone + kodi.bin）。≥4 说明多实例了。

**也绝对不要** 在 Kodi 运行时通过 `pacman -R` 卸载 Kodi addon 包。卸载后 addon 注册表仍有记录，下次 Kodi 启动会崩溃 -> 死循环。恢复方案：
```bash
# 先装回（即使插件有 bug 也比系统崩溃好）
sudo pacman -S kodi-addon-pvr-iptvsimple
# 然后拔电重启笔记本
```
见 `references/pvr-iptvsimple-v21-bug.md`。

**优先通过 JSON-RPC 安全操作（需先启用 Web 服务器）：**

```bash
# 先在 guisettings.xml 中启用 Web 服务器（一次配置）
sed -i 's|<setting id="services.webserver" default="true">false</setting>|<setting id="services.webserver" default="true">true</setting>|' \
  ~/.kodi/userdata/guisettings.xml

# 然后用 JSON-RPC 安全重启
curl -s -X POST -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"System.Reboot","id":1}' \
  http://127.0.0.1:9090/jsonrpc

# 或只重启 PVR 而不是整个 Kodi
curl -s -X POST -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"PVR.XXX","id":1}' \
  http://127.0.0.1:9090/jsonrpc

# 安全检查状态
curl -s -X POST -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"PVR.GetProperties","params":{"properties":["available","recording","scanning","channels","isconnectedtoserver"]},"id":1}' \
  http://127.0.0.1:9090/jsonrpc
```

**原则：** 宁可等用户有空了再操作，也不要 `pkill`。如果没开 webserver，不要强行操作。

## 完整配置清单

| 项目 | 方法 |
|------|------|
| 开机自启 | autologin → .bash_profile → startx → .xinitrc → kodi-standalone |
| 中文界面 | resource.language.zh_cn + Arial font |
| 中文字幕 | service.subtitles.chinesesubtitles (GitHub) |
| 音频 | PulseAudio 默认 |
| SSH 维护 | sshd enable + 免密 sudo |
| IPTV 直播 | pvr.iptvsimple (AUR) + m3u 节目源 |
| YouTube | plugin.video.youtube (Kodi mirror) + 反向代理隧道 |
| 反向隧道 | launchd (Mac端) + SSH key 自动维护 |
| Kodi 代理 | proxysettings.xml 指向隧道端口 |

## IPTV 直播

### IPTV Simple — Debug 包 vs 主包

Arch Linux 中 PVR IPTV Simple 分为两个包：
- `kodi-addon-pvr-iptvsimple` — 主包（含 .so 插件文件）
- `kodi-addon-pvr-iptvsimple-debug` — 调试符号包（仅含 .debug 文件）

**只装 debug 包 = 插件不存在。** Kodi 不会加载只有调试符号的插件。必须装主包。

**当前（Kodi 21.3 Omega）验证：** IPTV Simple v21.11.0 在 21.3 上正常工作。如果还遇到卡 Starting，检查：
1. m3u 频道是否重复（见去重章节）
2. Timeshift 是否关闭（设置 → Live TV → 回放 → Timeshift 关闭）

### 安装 IPTV Simple Client

**⚠️ Kodi 21 (Omega) 老版本用户注意：PVR IPTV Simple v21.0.x 有已知 bug，PVR Manager 会永远卡在 "Starting" 无法加载频道。**  
详见 `references/pvr-iptvsimple-v21-bug.md` 以及 GitHub Issues [#862](https://github.com/kodi-pvr/pvr.iptvsimple/issues/862) 和 [#929](https://github.com/kodi-pvr/pvr.iptvsimple/issues/929)。

解决方案二选一：

**方案 A：手动安装旧版 v20.13.0（推荐）**

```bash
# 卸载新版
sudo pacman -R kodi-addon-pvr-iptvsimple
# 从 GitHub 下 v20.13.0 的 zip
curl -sL -o /tmp/pvr-20.13.0.zip \
  "https://mirrors.kodi.tv/addons/nexus/pvr.iptvsimple/pvr.iptvsimple-20.13.0.zip"
# 手动解压到 ~/.kodi/addons/
unzip -qo /tmp/pvr-20.13.0.zip -d ~/.kodi/addons/
```

**方案 B：从 AUR 编译旧版**

```bash
git clone --depth=1 https://aur.archlinux.org/kodi-addon-pvr-iptvsimple.git /tmp/pvr-iptvsimple
cd /tmp/pvr-iptvsimple
# 注意：AUR PKGBUILD 默认拉最新，需要先编辑 PKGBUILD 指定 tag 为 20.13.0-Omega
sudo pacman -S --noconfirm cmake kodi-platform kodi-dev pugixml
makepkg -si --noconfirm
```

**验证加载正常：** 装好后进 Kodi → 电视 → 应能顺利看到频道列表，不再卡 "Starting"。

### 配置中文节目源

**源的选择：** 不是所有声称"中国频道"的 m3u 列表都真含中国台。优先用用户指定的源——当用户给出 GitHub 项目链接时，那是他们研究过的答案，优先使用。

- `raw.githubusercontent.com/vbskycn/iptv/refs/heads/master/tv/iptv4.txt` — 每日验证的国内源，含 CCTV1-17、各卫视，但格式为 CSV 需转 m3u
- `github.com/cs3306/IPTV-Sources` — 用户优先推荐的整合项目，`data/output/iptv_collection.m3u` 含 8070 个国际频道，需过滤中文部分
- `github.com/best-fan/iptv-sources` — 用户优先推荐的精选源，`cn_cctv.m3u8`/`cn_province.m3u8` 含每日检测的中文频道
- `github.com/hujingguang/ChinaIPTV` — `cnTV_AutoUpdate.m3u8`，中国电视专用源但 token 常过期

**频道去重关键（重要）：** 这些源通常每个频道有多个 URL 副本。如果 m3u 中同一频道名出现多次，PVR IPTV Simple 会解析每个副本作为独立频道，导致 PVR 初始化极慢、频道列表冗余甚至卡死。**必须每个频道只保留一个 URL。**

```bash
# 推荐：vbskycn 源 + Python 去重转 m3u
curl -sL -o ~/tv_raw.txt \
  "https://raw.githubusercontent.com/vbskycn/iptv/refs/heads/master/tv/iptv4.txt"

# Python 去重脚本（保留第二个源，因为第一个常返回 302）
python3 << 'PYEOF'
channels = {}
for line in open("/home/angelife/tv_raw.txt"):
    if "," in line:
        n, u = line.strip().split(",", 1)
        n, u = n.strip(), u.strip()
        if n and u.startswith("http"):
            channels.setdefault(n, []).append(u)

with open("/home/angelife/tv.m3u", "w") as f:
    f.write("#EXTM3U\n")
    for name in sorted(channels.keys()):
        urls = channels[name]
        url = urls[1] if len(urls) > 1 else urls[0]
        f.write(f'#EXTINF:-1 group-title="电视",{name}\n')
        f.write(url + "\n")
PYEOF
```

```bash
# 创建 PVR 设置
mkdir -p ~/.kodi/userdata/addon_data/pvr.iptvsimple
cat > ~/.kodi/userdata/addon_data/pvr.iptvsimple/settings.xml << "EOF"
<settings version="2">
    <setting id="m3uPath" default="true">special://profile/../tv.m3u</setting>
</settings>
EOF
```

**验证方法：** 抽测几个频道地址，确认直连返回 200。

IPTV 节目源会随时间失效。Mac 端关闭也不影响 IPTV（不走代理隧道，直连国内源）。

## YouTube 插件

```bash
# 从 Kodi 官方仓库下 YouTube 插件
VER=$(curl -sL "https://mirrors.kodi.tv/addons/omega/plugin.video.youtube/" | \
  grep -oP "plugin.video.youtube-[0-9.]+\.zip" | sort -V | tail -1)
curl -sL -o /tmp/yt.zip "https://mirrors.kodi.tv/addons/omega/plugin.video.youtube/$VER"
unzip -qo /tmp/yt.zip -d ~/.kodi/addons/
```

## 反向代理隧道（看 YouTube 等外网内容）

当 Kodi 机器需要代理访问外网内容（如 YouTube）但 Kodi 机器无法直接访问 Mac 端代理时，用 SSH 反向隧道由 Mac 端主动建连开。

### 架构

```
Mac (xray :10808)  ──SSH-R──→ Kodi 机器 (:10808)
                                    ↕
                               Kodi (YouTube/IP TV)
```

Mac 端主动建连，Kodi 机器只需接受入站 SSH（Kodi 可 NAT 后）。

### Mac 端配置

```bash
# 1. 生 SSH key
ssh-keygen -t ed25519 -f ~/.ssh/id_reverse_tunnel -N ""

# 2. 公钥装到 Kodi 机器
ssh-copy-id -i ~/.ssh/id_reverse_tunnel angelife@<KODI_IP>

# 3. launchd 守护（自动重连）
cat > ~/Library/LaunchAgents/com.hermes.reverse-tunnel.plist << "PLIST"
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.hermes.reverse-tunnel</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/ssh</string>
        <string>-NT</string>
        <string>-i</string>
        <string>/Users/<MAC_USER>/.ssh/id_reverse_tunnel</string>
        <string>-o</string>
        <string>StrictHostKeyChecking=no</string>
        <string>-o</string>
        <string>ServerAliveInterval=30</string>
        <string>-R</string>
        <string>10808:localhost:10808</string>
        <string>angelife@<KODI_IP></string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
PLIST

launchctl load ~/Library/LaunchAgents/com.hermes.reverse-tunnel.plist
```

### Kodi 机器代理配置

```bash
# 系统环境变量（sshd 登录时生效，Kodi 本身不读）
echo "export http_proxy=http://127.0.0.1:10808" | sudo tee /etc/profile.d/proxy.sh
echo "export https_proxy=http://127.0.0.1:10808" | sudo tee -a /etc/profile.d/proxy.sh

# Kodi 自身代理配置
cat > ~/.kodi/userdata/proxysettings.xml << "XML"
<proxysettings>
    <proxysetting>
        <type>HTTP</type>
        <host>127.0.0.1</host>
        <port>10808</port>
    </proxysetting>
</proxysettings>
XML

# ⚠️ 关键：proxysettings.xml 只是声明，guisettings.xml 必须把开关打开
sed -i \
  -e 's|<setting id="network.usehttpproxy" default="true">false</setting>|<setting id="network.usehttpproxy">true</setting>|' \
  -e 's|<setting id="network.httpproxytype" default="true">0</setting>|<setting id="network.httpproxytype">1</setting>|' \
  -e 's|<setting id="network.httpproxyserver" default="true" />|<setting id="network.httpproxyserver">127.0.0.1</setting>|' \
  -e 's|<setting id="network.httpproxyport" default="true">8080</setting>|<setting id="network.httpproxyport">10808</setting>|' \
  ~/.kodi/userdata/guisettings.xml
```

**陷阱：** `proxysettings.xml` 必须搭配 `guisettings.xml` 的 `network.usehttpproxy=true` 一起用。只写 proxysettings.xml 不生效，Kodi 不会读代理配置。

### 验证

```bash
# Mac 端测试
curl -s -x http://127.0.0.1:10808 https://www.youtube.com -o /dev/null -w "%{http_code}"

# Kodi 机器测试
curl -s -x http://127.0.0.1:10808 https://www.youtube.com -o /dev/null -w "%{http_code}"
```

### ⚠️ 代理陷阱

- **Mac IP 变化**：Kodi 机器无法主动连 Mac（跨网段/双向不可达），隧道必须由 Mac 端发起。launchd 配置中 `KeepAlive=true` 确保 Mac 重启后自动重建。
- **端口冲突**：如果手动先启动了隧道，launchd 会报 `remote port forwarding failed`。杀掉旧进程：`pkill -f "ssh.*-R 10808"`，让 launchd 接管。
- **Kodi 重启**：配置 proxysettings.xml 后需重启 Kodi（`pkill -f kodi-standalone`）使代理生效。
- **IPTV vs YouTube 代理冲突**：中国 IPTV 频道必须直连（不走代理），外网 YouTube 需要代理。解决方案：
  - Kodi 系统代理关（`network.usehttpproxy=false`），确保 IPTV 直连
  - YouTube 插件需在插件设置中独立配代理，或使用 Invidious API（免 Google Key）
  - 反向隧道仍然保持运行，方便后续通过 SSH 维护或供其他工具使用
- **Invidious API 替代 Google API**：Kodi YouTube 插件可配置使用 Invidious API（`use_invidious=true`），无需申请 Google Cloud API Key，配置在 `~/.kodi/userdata/addon_data/plugin.video.youtube/settings.xml`。

## 已知陷阱

0. **Kodi 21 反复崩溃诊断法 → 见 `references/kodi-crash-diagnosis.md`**
1. **字体 vs 语言顺序** — 先 Arial 再 zh_cn，否则乱码
2. **两种自启方式冲突** — .bash_profile 和 systemd kodi.service 二选一
3. **重启前验证 SSH** — `sudo systemctl is-enabled sshd` 确认 sshd 开机自启；重启后尝试 SSH 验证连通性
4. **HDMI 热插拔** — 开机时没插 HDMI 线，PulseAudio 可能不识别 HDMI 输出。先开显示器再接笔记本，或插着线开机
5. **PVR IPTV Simple v21 卡 Starting** — Kodi 21 + IPTV Simple v21 有初始化死锁。降级到 v20.13.0 即可。确认方式：Kodi log 中 PVR Manager 永远卡在 "Starting" 不继续
6. **vbskycn 源重复频道** — 每个频道 5 个源，PVR 因此卡死。必须去重：每个频道只保留一个 URL
7. **m3u 路径** — `special://profile` = `~/.kodi/userdata/`，所以 `special://profile/../tv.m3u` = `~/.kodi/tv.m3u`。文件要放对位置
8. **GitHub raw 下载慢** — 从中国网络下载 GitHub raw 可能超时。有两种绕过：通过代理下载（`-x http://127.0.0.1:10808`），或用镜像站

## 故障排查方法论

当遇到反复卡住的技术问题时，**不要盲目重试或猜方案**。按用户定的优先级层级操作：

```
1. ✅ 读官方说明书 / GitHub README / Wiki（第一选择！）
2. ✅ 按文档步骤自己尝试
3. ✅ 搜社区讨论（GitHub Issues、论坛）
4. ❓ 问 ChatGPT/Claude/Gemini（最后手段）
```

**不要跳过第一步。** 绝大多数问题读说明书就能解决。磨刀不误砍柴工。

### 老赛扬专用：时钟问题 → SSL 拒绝

旧电脑 CMOS 电池没电，RTC 会回到 2007 年。如果 `pacman -Syu` 报：
```
SSL certificate verify result: certificate is not yet valid or the system clock is incorrect
```
修复：
```bash
date -s "2026-07-16 19:48:00"
hwclock -w
timedatectl set-ntp true
```

### 老赛扬专用：镜像超时

只有阿里云一个镜像，从某些网络连不上：
```bash
# 至少加 3-5 个国内镜像兜底
Server = https://mirrors.sjtug.sjtu.edu.cn/archlinux/$repo/os/$arch
Server = https://mirrors.ustc.edu.cn/archlinux/$repo/os/$arch
Server = https://mirrors.tuna.tsinghua.edu.cn/archlinux/$repo/os/$arch
```

1. 先读 **Kodi 日志** `~/.kodi/temp/kodi.log`，找 **ModuleNotFoundError**、**PVR Manager**、**Exception** 等关键词
2. 如果读日志就能找到根因（如缺 Python 模块），直接修
3. 如果日志看完不明原因，**问 ChatGPT**（通过 web-ai-cdp-bridge 的 ask.js 或 OpenBridge），**不要自己硬试**
4. 等 ChatGPT 回复后再动手

**注意：** ChatGPT 通过 headless Chrome 访问可能被 Cloudflare 拦截，OpenBridge 需要 Chrome 扩展配对才能工作。如果两个都不可用，用 web_search 搜 GitHub Issues 关键词找已知 bug。详见 `web-ai-cdp-bridge` 技能的 `references/access-failure-modes.md`。

**用户方法论铁律：** 问题解决层级是：读文档 → 自己试 → 搜社区 → 最后再问AI。
**不要跳过前两步直接来问。** 磨刀不误砍柴工。

### 问题撰写规范

当终于去问 AI 时，问题必须详细、完整、包含所有上下文。不要写模糊一句：

**好的问题模板：**
```
## 环境
- 设备/系统: (Arch Linux / Kodi 21.3 / Manjaro / N5095)
- 软件版本: (具体到小版本号、包名)

## 现象
- 具体报什么错？（日志关键行）
- 正常应该是什么行为？
- 实际发生了什么？

## 已经尝试过
1. 试了什么？结果？
2. 试了什么？结果？
3. ...

## 具体问题
1）第一问...
2）第二问...
3）第三问...

## 约束
- 这台机器是给谁用的？什么场景？
- 有什么不能做的？（不能重启、不能重装、不能影响什么）
```

**反面教材：** "下一步？回复A或B" — 这种空上下文的问题会被用户批评。

**用户原话：** 「谁让你这么问了 你要把详细遇到的问题越具体越好 丢给 chatgpt」
