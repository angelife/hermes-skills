# ADB 无线吞吐不对称诊断

## 症状

通过 ADB TCP 向 Android 设备 push 大文件很快，但设备通过 HTTP 从同一局域网主机下载同等大小文件极慢。速度差距可达 780x（32.8 MB/s vs 42 KB/s）。

## 排除链

### 1. HTTP 服务器排除
```bash
# Mac 本地 loopback 测试
curl -s -o /dev/null http://localhost:19999/file.apk
# → 快速 ✅
```

### 2. 代理/隧道排除
```bash
# 经代理测试吞吐
curl -s -x http://127.0.0.1:10808 -o /dev/null http://localhost:19999/file.apk
# → 也快 ✅
# 检查 xray 路由：geoip:private 是否 direct
```

### 3. Mac 网络接口排除
```bash
curl -s --interface en0 -o /dev/null http://192.168.1.8:19999/file.apk
# → 快 ✅
```

### 4. 链路总带宽确认
ADB push 达到 32.8 MB/s → 物理链路有能力。

### 5. 物理接口识别
```bash
arp -a | grep <device_ip>
# MAC OUI 识别芯片类型：00:E0:4C=Realtek，非手机内置WiFi常见芯片
```

### 6. 方向对比（核心证据）
| 方向 | 速度 | 方式 |
|------|------|------|
| Mac→设备（下行） | 32.8 MB/s | adb push |
| 设备→Mac（上行） | 42 KB/s | 设备 curl 拉文件 |
| 差距 | **780x** | 同一链路 |

### 7. 4G 排除
确认 4G 未开启 → 仅 WiFi/LAN，排除多宿主路由绕路。

## 根本原因

设备 WiFi 上行（TX）严重受限。具体可能：
1. 信号强度不对称（设备 RX 好但 TX 弱）
2. WiFi 省电模式（屏幕灭后降上行功率）
3. AP 上行调度不公或 rate limiting
4. USB 网卡上传通道限速

## 结论
- 780x 差距不是正常 WiFi 行为
- 大文件传设备时用 ADB push 而非从设备发起拉取
- 验证：连上后用 iperf3 双向测速对比 upload/download
