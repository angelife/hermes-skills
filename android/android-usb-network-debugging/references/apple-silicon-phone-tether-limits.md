# Apple Silicon + Mi8：手机给 Mac 供网的硬限制（2026-07-17）

用户说「回家断网，用手机流量继续」时，先判拓扑，不要硬开 RNDIS/热点。

## 结论速查

| 方案 | Apple Silicon Mac + Mi8 | 原因 |
|------|-------------------------|------|
| USB RNDIS tethering（手机 → Mac） | ❌ 不可用 | macOS 无 RNDIS 主机驱动；HoRNDIS 仅 Intel |
| Mi8 WiFi 热点 | ❌ 通常不可用 | Mi8 无 `wlan0`（WiFi 硬件坏） |
| 手机移动数据自身上网 | ✅ 可能 | `svc data enable`；手机侧 curl 可达 |
| 回家后家宽 WiFi | ✅ 优先 | Mac `en0` 网关如 `192.168.1.1` |
| gnirehtet 反向（Mac → 手机） | ⚠️ 方向相反 | 解决的是手机上网，不是 Mac 用手机流量 |

## 诊断顺序

```bash
# 1) Mac 是否已有外网
route -n get default | head -12
ping -c 1 -W 2000 8.8.8.8

# 2) 手机数据
adb -s a6520fa3 shell 'su -c "settings get global mobile_data; svc data enable; curl -sI --max-time 5 https://www.baidu.com | head -3"'

# 3) 手机是否有 WiFi 接口（热点前提）
adb -s a6520fa3 shell 'ls /sys/class/net | grep wlan; dumpsys wifi | head -5'
# 无 wlan0 → 不要尝试 start-softap / 热点

# 4) RNDIS 只作观察，不指望 Mac 拿 IP
adb -s a6520fa3 shell 'su -c "svc usb setFunctions rndis; getprop sys.usb.config; ip link show rndis0"'
# Apple Silicon 上 Mac 侧不会出现可用 RNDIS 网卡
```

## 夜训/无人化策略

1. 先确认 Mac 家宽是否已通 → 通了就直接继续任务
2. 家宽断 + 需要 Mac 上网：说明硬件限制，降级为离线可做项（本地解密/编译 wiki/写交付）
3. 不要在 Apple Silicon 上反复试 RNDIS；不要在无 wlan0 的 Mi8 上反复试热点
4. 若只要 ADB：USB 直连 `a6520fa3` 足够；拉微信库不依赖手机给 Mac 供网

## 相关

- 主技能：`android-usb-network-debugging`
- 反向供网：`references/gnirehtet-reverse-tether.md`
