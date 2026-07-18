---
name: kodi-iptv-simple-pvr-fix
description: Kodi 21 + PVR IPTV Simple v21 导致 PVR Manager 卡死在 Starting 的修复方法
---

# Kodi 21 PVR IPTV Simple 已知问题

## 问题 A：PVR Manager 卡在 "Starting"

### Symptom
PVR Manager stays stuck at "Starting" on Kodi 21 with IPTV Simple Client v21.x.
Log shows:
- `UpdateClients: Creating PVR client: pvr.iptvsimple`
- `AddOnLog: pvr.iptvsimple: Create starting IPTV Simple PVR client...`
- `PVR Manager: Starting`
- No further PVR logs, never shows "Started" or loaded channels.
Kodi doesn't crash, just hangs.

### Root cause
Known bug in pvr.iptvsimple v21.x on Kodi 21 (Omega).
Ref: https://github.com/kodi-pvr/pvr.iptvsimple/issues/929
Ref: https://github.com/kodi-pvr/pvr.iptvsimple/issues/862

### Fix

#### Option A: Downgrade to v20.13.0
```bash
# Uninstall broken v21
sudo pacman -R kodi-addon-pvr-iptvsimple
# Download v20.13.0 from Nexus repo
curl -sL -o /tmp/pvr.zip \
  "https://mirrors.kodi.tv/addons/nexus/pvr.iptvsimple/pvr.iptvsimple-20.13.0.zip"
# Install via Kodi addon manager (install from zip)
```

#### Option B: Use IPTV Merge addon instead (no PVR)
`plugin.video.iptvmerge` reads m3u files as a video addon, not PVR — no hang issue.

#### Option C: Use VLC standalone for IPTV
```bash
vlc ~/tv.m3u
```

## 问题 B：Timeshift 导致 Kodi 冻结/崩溃

### Symptom
Kodi 21 (Omega) 在使用 IPTV Simple 时，开启 Timeshift 功能后：
- 暂停频道流
- 等待 15+ 分钟
- 尝试快进或拖动
→ Kodi 无响应或崩溃，日志无有效错误

### Root cause
IPTV Simple v21.x 的 Timeshift 实现存在 mutex 锁死（死锁 bug）。
Ref: https://github.com/kodi-pvr/pvr.iptvsimple/issues/760

### Fix
**关闭 Timeshift：**
Kodi 设置 → Live TV → 回放 → Timeshift → 关闭

### 验证
关闭 Timeshift 后重启 Kodi，PVR 正常工作，频道可以播放（只是不能暂停/回退直播）。
