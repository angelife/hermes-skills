# macOS USB WiFi 网卡驱动安装与 kext 审批

## 典型场景

插入 USB WiFi 网卡后，系统识别为 **"USB Disk autorun"**（154MB CD-ROM），不出现网络接口。

**原因**：Realtek 等厂商的 USB WiFi 网卡内置一个 CD-ROM 分区存放 Windows 驱动程序。macOS 只看到了这个虚拟光驱，WiFi 芯片未被激活。需要装第三方 macOS 驱动才能唤醒网卡。

## 驱动选择

- **chris1111/Wireless-USB-Big-Sur-Adapter** — GitHub 上维护最活跃的 Realtek USB WiFi 驱动，支持 macOS Sequoia 15+ 至 Tahoe 26，覆盖 RTL8188/8192/8811/8821 等常见芯片
- 下载：https://github.com/chris1111/Wireless-USB-Big-Sur-Adapter/releases

## 安装流程

```bash
# 1. 下载最新 release zip
curl -L -o /tmp/usbwifi.zip \
  "https://github.com/chris1111/Wireless-USB-Big-Sur-Adapter/releases/download/V18/Wireless.USB.Big.Sur.Adapter-V18.zip"

# 2. 解压
cd /tmp && unzip -o /tmp/usbwifi.zip -d usbwifi

# 3. 安装 pkg（用 osascript 弹出 GUI 密码框）
osascript -e 'do shell script \
  "installer -pkg \"/tmp/usbwifi/Wireless USB Big Sur Adapter-V18/Wireless USB Big Sur Adapter.app/Contents/Resources/.Files/Wireless USB Big Sur Adapter.pkg\" -target /" \
  with administrator privileges'
```

## kext 审批（关键步骤）

macOS Sequoia 15+ 默认阻止未签名的内核扩展。安装后必须：

### 方法 A：重启后手动允许（推荐）

1. 重启电脑
2. 打开 **系统设置 → 隐私与安全性**
3. 往下翻到 **安全性** 部分
4. 看到 "系统软件来自开发者 Realtek 被阻止载入" → 点 **允许**
5. 输入密码 → 再次重启

### 方法 B：手动触发审批（不重启）

若安全设置中没有提示，用 kextutil 强制触发：

```bash
osascript -e 'do shell script \
  "kextutil /Library/Extensions/RtWlanU.kext 2>&1" \
  with administrator privileges'
```

这会在系统设置中生成待审批项，然后去 **系统设置 → 隐私与安全性** 中允许。

## 验证驱动加载

```bash
kextstat | grep -i realtek
# 正常输出：
# com.realtek.driver.RtWlanU (1830.32.b27)
# com.realtek.driver.RtWlanU1827 (1827.4.b36)
```

## ⚠️ 关键限制：2.4GHz 单频芯片

**这是最常见的误判来源。** 很多便宜的 USB WiFi 网卡（如使用 RTL8188CU、RTL8192CU 芯片的）**物理上只支持 2.4GHz**，不支持 5GHz。装了驱动能扫到 2.4G 信号但扫不到 5G，不是驱动问题，是芯片限制。

### 如何判断芯片是否支持 5G

```bash
# 查 Product ID
system_profiler SPUSBDataType 2>/dev/null | grep -B 2 -A 5 "0x0bda"
```

常见芯片识别：

| Product ID | 芯片 | 频段 | 协议 |
|-----------|------|------|------|
| 0x1a2b | 未知 Realtek 单频 | **2.4GHz only** | 802.11n |
| 0x8176 / 0x8178 | RTL8188CU | **2.4GHz only** | 802.11n |
| 0x8192 | RTL8192CU | **2.4GHz only** | 802.11n |
| 0x0811 | RTL8811CU | **双频** | 802.11ac |
| 0x0821 | RTL8821CU | **双频** | 802.11ac |

**Product ID 0x1a2b** 是单频网卡的典型值——设备在 macOS 上显示为 154MB "USB Disk"（内置驱动 CD 分区），装了驱动也只能扫到 2.4GHz。

### 5G 信号排查

```bash
# airport 只扫 Apple 内置 Wi-Fi（en0），**不扫 USB 网卡**
# 所以 airport -s 无输出是正常的，不等于网卡坏了
/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport -s

# USB 网卡需要用自己的扫描方式
# 装好驱动后，Realtek 状态栏 app（Wireless USB Big Sur Adapter.app）会显示可用网络
# 或观察第三方 app（如 WiFi Explorer）看到的频段
```

## 故障排查

| 现象 | 原因 | 处理 |
|------|------|------|
| USB 设备出现，但只有 CD-ROM 分区 | 驱动未装或未加载 | 装驱动 + kext 审批 |
| kextstat 有 realtek，但无新 enX 接口 | 重插 USB 网卡触发 | 拔插一次 |
| 安全设置没有允许提示 | kext 未尝试加载过 | `kextutil` 手动触发 |
| 装了驱动还是只有 CD-ROM | 芯片不兼容 | 查 Product ID 确认芯片型号 |
| **能扫到 2.4G 但扫不到 5G** | **芯片物理限制（单频网卡）** | **换双频网卡，非驱动问题** |
| `airport -s` 无输出 | airport 不扫 USB 网卡 | 用驱动自带 app 或第三方扫描工具 |

## 驱动文件位置

```
/Library/Extensions/RtWlanU.kext          # 主驱动
/Library/Extensions/RtWlanU1827.kext      # RTL8827 分支
```

## 注意事项

- 安装后不能立即生效——需要加载 kext 或重启
- USB 网卡创建的接口可能不会显示在 `networksetup -listallhardwareports` 中
- 一些 Realtek USB 网卡实际上是 2.4GHz only 的单频设备，改不了
- 设备 Product ID `0x1a2b` 通常是 2.4GHz 单频网卡 + 内置驱动 CD，在 macOS 上无法作为 5G WiFi 使用