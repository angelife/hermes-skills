# AX88772D 驱动错误匹配修复记录

## 前置条件

- **设备**: Xiaomi Mi8 (dipper), SD845
- **ROM**: LineageOS 22.2, Android 15
- **内核**: 4.9.337
- **root**: MagiskSU

## 问题

AX88772D (USB ID 0b95:1790) 插入 Mi8 后，`dmesg` 显示被 `ax88179_178a` 驱动错误匹配：

```
ax88179_178a 1-1:2.0 eth0: register 'ax88179_178a'
ASIX AX88179 USB 3.0 Gigabit Ethernet
```

## 诊断步骤

### 1. 确认内核驱动配置

```bash
zcat /proc/config.gz | grep -iE "ASIX|AX8817[19]|AX88"
# 预期输出：
# CONFIG_USB_NET_AX8817X=y       ← asix 驱动（built-in）
# CONFIG_USB_NET_AX88179_178A=y  ← 错误的匹配驱动（built-in）
```

两者都是 `=y`（built-in），不是可卸载模块，不能用 `modprobe -r` 移除。

### 2. 确认 sysfs 驱动节点

```bash
ls -la /sys/bus/usb/drivers/asix/      # 应有 new_id（可写）
ls -la /sys/bus/usb/drivers/ax88179_178a/  # 应有 unbind（可写）
```

### 3. 检查 USB 控制器模式

```bash
cat /sys/devices/platform/soc/a600000.ssusb/mode
# peripheral = 设备模式（连接 Mac ADB 时）
# host = 主机模式（外接 USB 设备时）
```

### 4. 检查 dual_role_usb

```bash
cat /sys/class/dual_role_usb/otg_default/mode
# ufp = Upstream Facing Port (device/peripheral)
# dfp = Downstream Facing Port (host)
```

## 修复流程

### Phase 1: ADB USB 在线时（预准备）

```bash
# 1. 注册 AX88772D ID 到 asix 驱动
echo "0b95 1790" > /sys/bus/usb/drivers/asix/new_id

# 2. 切换 ADB 到 TCP 模式（后续通过 Ethernet 连回）
adb tcpip 5555
```

### Phase 2: 物理切换

用户断开 USB 线，通过 OTG 插入 AX88772D，网线接路由器（与 Mac 同网段）。

### Phase 3: 驱动重绑定

```bash
# 确认设备已出现
find /sys/devices/platform/soc/a600000.ssusb -name "idVendor" -exec grep -l 0b95 {} \;

# 找到错误绑定
USBIF=$(find /sys/bus/usb/drivers/ax88179_178a -mindepth 1 -maxdepth 1 -type d ! -name "*:*" 2>/dev/null | head -1)
IFNAME=$(basename "$USBIF")

# 解绑
echo "$IFNAME" > /sys/bus/usb/drivers/ax88179_178a/unbind
sleep 1

# 绑到 asix
echo "$IFNAME" > /sys/bus/usb/drivers/asix/bind
sleep 2

# 验证新驱动
readlink "$USBIF/driver" | xargs basename
# 应输出: asix
```

## 完整修复脚本

### v1: 基础 unbind/rebind（需 ADB 访问）

```bash
#!/system/bin/sh
# fix_ax88772d_basic.sh — 检测到错误驱动后解绑/重绑定
ASIX_NEWID=/sys/bus/usb/drivers/asix/new_id

# 1. 预注册
[ -w "$ASIX_NEWID" ] && echo "0b95 1790" > "$ASIX_NEWID"

# 2. 循环等待设备出现（最长 60 秒）
WAIT=0
while [ $WAIT -lt 60 ]; do
  DEVPATH=$(find /sys/devices/platform/soc/a600000.ssusb -name "idVendor" -exec grep -l 0b95 {} \; 2>/dev/null | head -1)
  if [ -n "$DEVPATH" ]; then
    DEVDIR=$(dirname "$DEVPATH")
    DRIVER=$(readlink "$DEVDIR/driver" 2>/dev/null | xargs basename 2>/dev/null)

    if [ "$DRIVER" = "ax88179_178a" ]; then
      USBIF=$(find /sys/bus/usb/drivers/ax88179_178a -mindepth 1 -maxdepth 1 -type d ! -name "*:*" 2>/dev/null | head -1)
      IFNAME=$(basename "$USBIF")
      echo "$IFNAME" > /sys/bus/usb/drivers/ax88179_178a/unbind 2>/dev/null
      sleep 1
      echo "$IFNAME" > /sys/bus/usb/drivers/asix/bind 2>/dev/null
      echo "Fixed: $DRIVER → asix"
    elif [ "$DRIVER" = "asix" ]; then
      echo "Already correct driver: asix"
    fi
    exit 0
  fi
  WAIT=$((WAIT + 2))
  sleep 2
done
echo "Timeout: device not found"
```

### v3: 无值守自动修复（nohup + OTG + Magisk service.d）

```bash
#!/system/bin/sh
# fix_ax88772d.sh — v3: 依赖硬件 OTG 检测，不写 mode 文件
LOG=/tmp/fix.log
ASIX_NEWID=/sys/bus/usb/drivers/asix/new_id

log() { echo "[$(date +%H:%M:%S)] $*" >> $LOG; }

log "=== AX88772D 修复 v3 ==="
log "内核: $(uname -r)"

# Step 1: 注册 ID 到 asix
log "Step 1: 注册 0b95:1790 → asix"
if [ -w "$ASIX_NEWID" ]; then
  echo "0b95 1790" > $ASIX_NEWID 2>&1 && log "  OK" || log "  FAIL"
else
  log "  new_id 不可写"
fi

# Step 2: 记录当前 USB 状态
BEFORE=$(ls /sys/bus/usb/devices/ 2>/dev/null | wc -w)
log "Step 2: 当前 usb_devices=$BEFORE (等待 OTG 插入)"

# Step 3: 等待 AX88772D — 硬件 OTG 自动触发
log "Step 3: 等待 0b95:1790 (120s 超时)..."
WAIT=0
while [ $WAIT -lt 120 ]; do
  for d in /sys/bus/usb/devices/*/; do
    [ -d "$d" ] || continue
    V=$(cat "$d/idVendor" 2>/dev/null)
    [ "$V" = "0b95" ] || continue
    P=$(cat "$d/idProduct" 2>/dev/null)
    DRV=$(readlink "$d/driver" 2>/dev/null | xargs basename 2>/dev/null)
    IFACE=$(find "$d" -name "net" -type d 2>/dev/null)
    ETH=""
    [ -n "$IFACE" ] && ETH=$(ls "$IFACE/" 2>/dev/null)
    log "  ★ 找到 0b95:$P 驱动=$DRV 接口=$ETH 设备=$(basename $d)"

    # Step 4: 修正绑定
    if [ "$DRV" = "ax88179_178a" ]; then
      log "  ⚠ 错误驱动! 执行 unbind..."
      BNAME=$(basename "$d")
      echo "$BNAME" > /sys/bus/usb/drivers/ax88179_178a/unbind 2>&1 && log "  ✔ unbind" || log "  ✗ unbind FAIL"
      sleep 1
      echo "$BNAME" > /sys/bus/usb/drivers/asix/bind 2>&1 && log "  ✔ bind → asix" || log "  ✗ bind FAIL"
      sleep 2
      NEWDRV=$(readlink "$d/driver" 2>/dev/null | xargs basename 2>/dev/null)
      log "  新驱动: $NEWDRV"
    elif [ "$DRV" = "asix" ]; then
      log "  ✔ 已在正确驱动"
    fi

    # Step 5: 静态 IP
    if [ -n "$ETH" ]; then
      log "  ifup $ETH..."
      ip link set "$ETH" up 2>&1
      sleep 2
      ip addr add 192.168.1.217/24 dev "$ETH" 2>&1
      sleep 1
      ip route add default via 192.168.1.1 dev "$ETH" 2>&1
      IP=$(ip addr show "$ETH" 2>/dev/null | grep 'inet ' | head -1)
      log "  IP=$IP"
      log "  ► adb connect 192.168.1.217:5555"
    fi
    log "=== 完成 ==="
    exit 0
  done

  WAIT=$((WAIT + 2))
  if [ $((WAIT % 20)) -eq 0 ]; then
    DEVS=$(ls /sys/bus/usb/devices/ 2>/dev/null | wc -w)
    log "  wait ${WAIT}s devices=$DEVS"
  fi
  sleep 2
done
log "✗ 120s 超时 — 未检测到 0b95 设备"
exit 1
```

**部署方式**：
```bash
# 推送到设备
adb push /tmp/fix_ax88772d.sh /tmp/fix_ax88772d.sh
adb shell "su -c 'chmod 755 /tmp/fix_ax88772d.sh'"

# 启动（nohup 保持 ADB 断连后继续运行）
adb shell "su -c 'nohup /system/bin/sh /tmp/fix_ax88772d.sh > /dev/null 2>&1 &'"

# 开机持久化
adb shell "su -c 'mkdir -p /data/adb/service.d'"
adb shell "su -c 'cp /tmp/fix_ax88772d.sh /data/adb/service.d/fix_ax88772d'"
adb shell "su -c 'chmod 755 /data/adb/service.d/fix_ax88772d'"
adb shell "su -c 'chown root:shell /data/adb/service.d/fix_ax88772d'"
```

## 限制

- `remove_id` 不能移除 `ax88179_178a` 编译时内置的 ID（只对动态添加的 ID 有效）
- 单 USB-C 口设备无法同时连接 ADB 和外接 USB，必须分阶段操作
- 错误驱动如果无法使 Ethernet 部分工作，则无法通过 TCP ADB 连回修复，需要本地 Termux 执行脚本
