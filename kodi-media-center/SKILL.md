---
name: kodi-media-center
title: "Kodi 媒体中心 — 赛扬 HTPC 管理"
description: "Kodi 媒体中心管理：安装、配置、PVR IPTV、视频库、NAS 挂载、排障。赛扬小主机上管理 Kodi 的完整工作流。"
category: media
tags: [kodi, htpc, media-center, pvr, iptv, video-library]
---

# Kodi 媒体中心

## NLM 中心制工作流（2026-07-16 确立）

所有 Kodi 故障诊断走标准流程：

```
发现问题 → 多渠道收集（搜索/三AI/Grok/文档）
        ↓
    全部喂 NotebookLM
        ↓
    NLM 合成统一方案（共识+分歧+优先级）
        ↓
    按方案执行 → 存档 Obsidian
        ↓
    有问题 → 回到收集循环
```

**之前 Kodi 鼠标修复就是按此流程：** 三AI问诊 → 喂 NLM → NLM 出合成方案（seatd + 组权限 + 软件光标）→ 执行修复 → 写 Obsidian 记录。鼠标修复详情见 `~/Documents/Obsidian Vault/土同学工作档案/Kodi鼠标修复记录.md`。

## 架构概览

Kodi = 播放器核心(ffmpeg) + 插件(Addon)系统

PVR 系统：信号源 → 后端 → PVR 插件 → Kodi 界面
视频源：本地硬盘 / NAS(SMB/NFS) / HTTP 串流

## 安装方式

- macOS: brew install kodi（或从 kodi.tv 下载 dmg）
- Linux: 发行版包管理器或 LibreELEC/CoreELEC 定制系统
- Windows: 从 kodi.tv 下载安装包

## PVR / IPTV 配置

1. 安装 PVR IPTV Simple 插件（设置 → 插件 → 从仓库安装 → PVR 客户端）
2. 配置 M3U 播放列表 URL
3. 配置 EPG 节目指南 URL
4. 重启 Kodi（配置完后必须重启才生效）

## Kodi 21 Omega 已知问题

| 问题 | 现象 | 解决 |
|------|------|------|
| Timeshift 死锁 | 暂停/快进后 Kodi 冻结 | 关闭 Timeshift（设置 → Live TV → 回放） |
| IPTV Simple v20→v21 不工作 | 升级后频道消失 | 更新插件到 ≥ 21.8.4 或重装 |
| PVR Manager 卡在 0% | IPTV Simple v21.x bug (#929) / ABI 不匹配 / m3u 路径 | 见下方"PVR 0% 三步修复" |
| 调试包 vs 主包混淆 | `-debug` 包不包含插件本体 | 必须装 `kodi-addon-pvr-iptvsimple`（不含 -debug） |

### PVR Manager 卡在 0%（三步修复）

Via NLM 三 AI 合成分析（notebook `8c88ae52`），按概率排序：

**第 1 步：重装插件（最常见 — ABI 不匹配）**
```bash
yay -Rns kodi-addon-pvr-iptvsimple && yay -S kodi-addon-pvr-iptvsimple
```
AUR 编译的插件与 Kodi 版本 ABI 不一致导致 `.so` 加载失败。重新编译即可。

**第 2 步：m3u 路径改绝对路径**
settings.xml 不展开波浪号 `~`，必须用绝对路径：
```bash
echo "~/.kodi/tv.m3u"   # 错误
echo "/home/angelife/.kodi/tv.m3u"  # 正确
```
在 GUI 设置中重新指定绝对路径。

**第 3 步：清理 EPG 数据库（Kodi 21 已知 bug）**
EPG XMLTV URL 获取阻塞会导致 PVR 启动流程卡死：
```bash
killall -9 kodi.bin 2>/dev/null
cd ~/.kodi/userdata/Database/
rm -f TV*.db Epg*.db
```
Kodi 会自动重建这些数据库。

**验证：** 执行完以上步骤后重启 Kodi，观察 PVR Manager 能否突破 0%。
**调试日志：** `kodi --debug 2>&1 | grep -iE "pvr|iptvsimple|error|fail"`

### Kodi 21.3 SIGSEGV 崩溃（CAddonSettings::Load）

**症状**: Kodi 21.3 Omega 每隔 ~45 秒崩溃一次，自动重启。`kodi-standalone` 包装脚本设计为崩溃后自动拉起，形成崩溃循环。

**崩溃特征**:
```
Signal: 11 (SEGV), si_code: SEGV_MAPERR
#0  TiXmlAttributeSet::Find() (libtinyxml.so.0)  [NULL pointer]
#1  TiXmlElement::Attribute()
#2  CAddonSettings::Load(CXBMCTinyXML const&)
#3  CAddon::SettingsFromXML()
#4  CAddon::LoadUserSettings()
#5  CAddon::HasSettings()
```

**根因**: CAddonSettings::Load 在解析 addon.xml 时遇到 NULL 属性指针。所有 addon.xml 文件经 xmllint 验证正常，表明是 Kodi 21 自身的 XML 处理 bug（addon 安装/卸载后上下文菜单检查时触发）。

**尝试的修复**:
1. ✅ 清理旧 pvr.iptvsimple 配置 → 仍崩溃
2. ✅ 删除 Addons33.db + 所有用户安装的插件 → 需要验证是否修复（系统随后离线）

**修复建议** (未验证):
- 完全重置 Kodi 配置 (`rm -rf ~/.kodi/userdata/`) 后重新配置
- 或降级到 Kodi 20 (Nexus) 稳定版
- 或升级到 Kodi 22 及以上版本（如可用）

**如果上述方法无效 → 停手问 Claude/ChatGPT。** 这是 Kodi 21 的 C++ 层 bug，改不了源码就不要再硬试，把完整崩溃栈 + 系统信息发给 AI 拿建议。

## 鼠标/触摸板不工作

Kodi 21 的鼠标支持很有限（10-foot 界面设计，不是鼠标优先）。

### 诊断步骤

1. 确认系统检测到鼠标：
   ```
   cat /proc/bus/input/devices | grep -A3 "Mouse"
   ls /dev/input/mouse*
   ```

2. 确认 Xorg 识别鼠标：
   ```
   grep -i "mouse\|pointer" /var/log/Xorg.0.log
   ```

3. 确认 Kodi 开启鼠标：
   ```
   grep "enablemouse" ~/.kodi/userdata/guisettings.xml
   ```

### 综合修复方案（2026-07-16 三AI+NLM 验证通过）

当 Kodi 独立模式（GBM/KMS）下 USB 鼠标被系统识别但 Kodi 无光标：

```bash
# 1. 加设备组权限
sudo usermod -aG input,video,render,seat $USER

# 2. 安装并启动 seatd（独立 Kodi 必需）
sudo pacman -S --needed seatd
sudo systemctl enable --now seatd

# 3. 启用软件光标（Intel GMA 4500M 老显卡必需）
export KODI_SOFTWARE_CURSOR=1

# 4. 重启 Kodi
kodi-standalone
```

**验证：**
```bash
systemctl is-active seatd  # → active
ls -l /dev/input/event*    # → crw-rw---- root:input
libinput list-devices      # → 可看到鼠标
```

**根因：** Kodi 独立模式（GBM/KMS）独占输入设备，普通用户无权读 `/dev/input/`。

### 已知问题

| 问题 | 原因 | 解决 |
|------|------|------|
| USB 鼠标插入 Kodi 无反应 | 鼠标光标默认隐藏 | 移动鼠标看是否出现 |
| 触摸板不灵敏 | Kodi 对触摸板支持极弱 | 用键盘方向键 + 回车操控 |
| USB 鼠标显示 "device removed" | USB 口接触/省电策略 | 换 USB 口 |
| Kodi 检测到鼠标但不响应 | Kodi 21 鼠标支持有 bug | 用 Kodi Remote App 替代 |

### 最佳替代方案（推荐顺序）

1. **键盘** — 方向键 + 回车 + ESC（最稳）
2. **Kodi Remote App** — iOS/Android 官方遥控器
3. **USB MCE 遥控器** — 几十块即插即用
4. **Web 界面** — 开启 Kodi Web 服务器（端口 8080），浏览器控制

## kodi-standalone 自动重启机制

```sh
/usr/bin/kodi-standalone 包装脚本：
  LOOP=1
  while [ $LOOP -eq 1 ]; do
    $APP      # 运行 kodi --standalone
    RET=$?
    if [ $RET -ge 64 ] && [ $RET -le 66 ] || [ $RET -eq 0 ]; then
      LOOP=0  # 正常退出 → 停止循环
    else
      # 60秒内连续崩溃3次才放弃，否则一直重启
      if [ $DIFF -gt 60 ]; then
        CRASHCOUNT=0  # 重置计数器
      else
        CRASHCOUNT++
        if [ $CRASHCOUNT -ge 3 ]; then
          LOOP=0  # 3次崩溃 → 放弃
        fi
      fi
    fi
  done
```

**含义**: Kodi 崩溃后包装脚本会在 1 秒内自动重启，用户看到的就是 "反复重启"。
**诊断路径（按优先级）:**
1. `coredumpctl list | grep kodi` — 直接看系统级 core dump（kodi.log 不记录崩溃）
2. 确认 crash #0-#2 栈帧 100% 一致 → 确定性 bug，不是随机闪退
3. `dmesg | grep -iE "segfault|kodi"` — 内核级确认
4. `journalctl -xe | grep -iE "kodi|segfault"` — systemd 日志兜底
5. kodi.log 作为最后参考（崩溃来不及写日志）
**修复**: 修好崩溃原因，或者临时禁用 `kodi-standalone` 改为手动启动。

## 赛扬 Celeron HTPC（Arch Linux）实战记录

### 系统规格
- CPU: Celeron T3500 @ 2.10GHz | RAM: 2GB | DISK: 284G (260G 空余)
- 网络: 无线 wlp4s0b1 (双 IP 模式)
- Arch Linux, kernel 7.1.3, Kodi 21.3.0 Omega

### 常见故障及修复
1. **系统时钟错误** → `date -s "YYYY-MM-DD HH:MM:SS"` + `timedatectl set-ntp true`
   - 根因：CMOS 电池没电，RTC 重置到 2007-01-01
   - 症状：SSL 证书验证失败 ("certificate is not yet valid")
   - 影响：pacman、git clone 全部报 SSL 错

2. **pacman 镜像不可达** → 多镜像兜底
   - 不要只配一个阿里云，图书馆/移动网络可能超时
   - 建议：交大/哈工/中科大/清华/阿里/新加坡/Kernel.org 七个镜像
   - `pacman -Sy` 失败时先换镜像再排查其他

3. **IPTV Simple 插件缺失** → AUR 编译安装
   - `kodi-addon-pvr-iptvsimple-debug` 只含调试符号，不含主包
   - AUR 安装：`curl -L http://aur.archlinux.org/cgit/aur.git/snapshot/kodi-addon-pvr-iptvsimple.tar.gz | tar xz && cd kodi-addon-pvr-iptvsimple && makepkg -si`
   - 注意：赛扬 T3500 编译需要 ~15-20 分钟

4. **SSH 密码认证** → 使用 sshpass + PreferredAuthentications=password
   - 加 `-o PreferredAuthentications=password` 避免公钥失败直接退出
   - su -c 配 piped password 会破坏 heredoc → 单行命令用 echo password | su -c

5. **反复崩溃循环** → 见上面 "Kodi 21.3 SIGSEGV 崩溃"
   - 先停：`killall -9 kodi.bin kodi-standalone`
   - 查日志：`coredumpctl list | grep kodi` 确认 SIGSEGV
   - 清理：删除 Addons33.db 和 ~/.kodi/addons/ 下的用户插件
   - 重启：`nohup /usr/bin/kodi-standalone > /dev/null 2>&1 &`

### RTC/CMOS 电池耗尽
赛扬旧笔记本 CMOS 电池没电，每次断电重启后系统时间回到 2007-01-01。
- 修正：`date -s` + `timedatectl set-ntp true`
- 根治：换 CMOS 电池（CR2032）
- 临时缓解：NTP 同步在断电后失效，每次开机要手动对时

## 视频库设置

1. 视频 → 文件 → 添加视频 → 选择源（本地/NAS）
2. 文件命名规范：电影名 (年份).扩展名
3. 自动刮削元数据（封面、简介）

## 网络视频源

- SMB: smb://nas-ip/共享目录/
- NFS: nfs://nas-ip/导出目录/
- 本地: 直接挂载硬盘路径

## 配置目录

- Linux/macOS: ~/.kodi/userdata/
- macOS (brew): ~/Library/Application Support/Kodi/userdata/
- LibreELEC: /storage/.kodi/userdata/

## 排障步骤

1. 查看日志：~/.kodi/temp/kodi.log
2. 查看崩溃：`coredumpctl list | grep kodi`
3. 检查插件版本是否兼容
4. 关闭 Timeshift（IPTV 崩溃主要原因）
5. 重启 Kodi（配置变更后必须）
6. 清理插件缓存

## 参考文档

- kodi.wiki — 官方 Wiki
- github.com/xbmc/xbmc — Kodi 源码
- github.com/kodi-pvr/pvr.iptvsimple — PVR IPTV Simple 插件
- ~/Documents/Obsidian Vault/土同学工作档案/Kodi学习笔记.md — 当日详细笔记
