---
name: android-eth-static-ip
description: 在已 Root 的 Android 设备上给 USB-C 转以太网稳定生产静态 IP，避免 WiFi/ADB 断线，且无需修改系统分区。
author: 土同学
---

# Android USB-C 以太网静态 IP

## 适用场景
- USB-C 转以太网
- Root 已确认
- ADB 可用
- 已 Root 设备上跑 Linux 服务栈，proot 不够稳时，切真 chroot

## 一、有线静态 IP 模板
- 脚本：`/data/local/tmp/eth-setup/eth-static.sh`
- 自愈：`/data/adb/service.d/eth-static.sh`
- 默认目标 IP：`192.168.1.26/24`
- 默认网关：`192.168.1.1`
- DNS：`223.5.5.5`、`8.8.8.8`

### ⚠️ 关键陷阱：subnet 切换导致 TCP ADB 不可达

脚本硬编码 `192.168.1.x` 网段。**换了网络环境（如学校→家里，家里是 192.168.2.x）后，手机拿到错误 IP，TCP ADB 连不上。**

症状：ping 通 192.168.1.26，端口 5555 nc 通，但 `adb connect` 报 `No route to host`——ADB 协议层不握手。

**修复方案：**
1. **DHCP 优先**：进新网络后先让 DHCP 给 IP，再手动改脚本中的目标 IP 为当前网段
2. **动态检测**：在 `eth-static.sh` 中加默认网关检测，自动适配同网段 IP
3. **现场修复**：通过 USB ADB 连上后修改脚本 IP 段再重启
4. **长期**：改为 `ip route` 检测默认网关后自动选择同网段静态 IP

**模板内容（已修复空接口问题 + 默认网关缺失问题）**
```sh
#!/system/bin/sh
set -e
IFACE=$(ls /sys/class/net/ | grep -E '^eth|^en' | head -n 1)
[ -z "$IFACE" ] && exit 0
ifconfig "$IFACE" 192.168.1.26 netmask 255.255.255.0 up
ip route replace default via 192.168.1.1 dev "$IFACE"
mkdir -p /data/local/tmp/eth-setup
echo nameserver 223.5.5.5 > /data/local/tmp/eth-setup/resolv.conf
echo nameserver 8.8.8.8 >> /data/local/tmp/eth-setup/resolv.conf
```

## 二、Magisk Root 后的 Linux 服务栈选型
- proot：适合轻量实验，但 ptrace 伪造 uid 会导致 apt `_apt sandbox` EPERM、daemon 追踪断裂。
- 真 chroot：优先选。`mount --bind + chroot` 是内核级隔离，apt/daemon 更稳，不需要 `APT::Sandbox::User=root` 绕过。
- 标准 chroot mount 序列：
```bash
mount --bind <rootfs> /data/local/tmp/chroot/distro
mount -t proc proc /data/local/tmp/chroot/distro/proc
mount -t sysfs sysfs /data/local/tmp/chroot/distro/sys
mount --rbind /dev /data/local/tmp/chroot/distro/dev
chroot /data/local/tmp/chroot/distro /bin/bash
```

## 执行步骤
1. 创建静态 IP 脚本
2. 创建自愈 service.d 脚本
3. 确认有线网卡名 `eth0` 或 `enp*`
4. 固定地址写入
5. 如需稳定 Linux 服务栈，优先做 Magisk `service.d` 自启脚本，把 chroot mount + 服务保活都放进去

## Mi8 稳定部署序列（已实测）
```bash
# 1. 本地准备
mkdir -p /tmp/eth-setup
cat > /tmp/eth-setup/eth-static.sh << 'EOF'
#!/system/bin/sh
set -e
IFACE=$(ls /sys/class/net/ | grep -E '^eth|^en' | head -n 1)
[ -z "$IFACE" ] && exit 0
ifconfig "$IFACE" 192.168.1.26 netmask 255.255.255.0 up
route add default gw 192.168.1.1 dev "$IFACE" >/dev/null 2>&1 || true
mkdir -p /data/local/tmp/eth-setup
echo nameserver 223.5.5.5 > /data/local/tmp/eth-setup/resolv.conf
echo nameserver 8.8.8.8 >> /data/local/tmp/eth-setup/resolv.conf
EOF
chmod 755 /tmp/eth-setup/eth-static.sh

# 2. 推送并接 service.d
adb push /tmp/eth-setup/eth-static.sh /data/local/tmp/eth-setup/eth-static.sh >/dev/null
adb shell 'su 0 -c "chmod 755 /data/local/tmp/eth-setup/eth-static.sh"
adb shell 'su 0 -c "
ln -sf /data/local/tmp/eth-setup/eth-static.sh /data/adb/service.d/eth-static.sh
chmod 755 /data/adb/service.d/eth-static.sh
echo linked
"'

# 3. 手动首跑
adb shell 'su 0 -c "sh /data/local/tmp/eth-setup/eth-static.sh && echo APPLIED || echo SKIPPED"'
```
- `APPLIED`：接口已存在，静态 IP 已写入
- `SKIPPED`：有线网卡尚未枚举；网卡后续插入或重启后 `service.d` 会自动重试

## Mi8 USB-C 单口限制（关键）
- 插以太网适配器后会立刻断开 USB ADB，不是软件问题
- 稳定操作顺序：**USB 操作期间先开 TCP ADB → 拔 USB → 插网卡 → TCP ADB 维持**
- 抓 USB 窗口命令：
```bash
adb start-server && adb shell 'su 0 -c "setprop service.adb.tcp.port 5555; stop adbd; start adbd"'
adb connect 192.168.1.26:5555
```
- 若 TCP ADB 也连不上：先确认 `192.168.1.26` 是否真的出现在 `ip -4 addr show`；若 IP 没起来，回到 USB 窗口修 `eth-static.sh`；若 IP 存在，查 `iptables` / AP 隔离

## 多设备同网段 IP 可达性预检
- 记忆 IP（`Mi6 192.168.1.15`、`Mi8 192.168.1.26`）不一定当前仍有效
- 决策树：`ping` → `/proc/net/arp` → `adb devices` → 现场 `cat /sys/class/net/`
- 三跳中有一跳失败即判定**不可达**：先恢复设备在线（WiFi / USB 临时连接），再继续网络配置
- 不边走后续静态 IP 操作，避免把阻塞混入网络配置流程

## 常用命令
- `adb connect 192.168.1.26:5555`
- 查 MAC：`cat /sys/class/net/eth0/address`

## 支撑文件
- `templates/eth-static.sh`：已修复默认网关缺失问题的静态 IP 模板
- `templates/adb-tcp-service.sh`：Magisk service.d 持久化 TCP ADB 模板
- `scripts/verify-network.sh`：Mi8 有线网络一键验证脚本

## 三、服务栈上线检查清单
- 重启 chroot 前先清理挂载：`umount -R /data/local/tmp/chroot/debian 2>/dev/null || true`
- 验证清理完成：`cat /proc/mounts | grep chroot || echo clean`
- 重新执行标准 mount 序列，不要跳过 `/dev`
- 进入 chroot 后先做本机自测：`curl -sI http://127.0.0.1:5244/` 和 `http://192.168.1.26:5244/`
- 若两跳都通但 Mac 不通，再查 iptables/路由器，不要先假设网络设备问题

## 三之一、chroot 内命令执行 PATH 陷阱
- 通过 `su 0 -c "chroot ... /bin/sh -c ..."` 进入 chroot 后，**PATH 不会继承宿主机完整 PATH**
- 症状：`cat`、`apt-get`、`ss` 等命令报 `command not found`
- 修复：在 chroot 命令前显式声明完整 PATH
```bash
chroot /data/local/tmp/chroot/debian /bin/sh -c \
  'export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin && your_command'
```
- 单引号包裹整段命令时，外部 shell 不会展开变量；chroot 内的 `$VAR` 不受宿主机环境污染，但默认 PATH 极窄

## 三之二、adb push 到 chroot rootfs 权限陷阱
- `adb push <local_file> <chroot_root_path/filename>` 当目标目录属 root:root 时会失败：`error: remote couldn't create file: Permission denied`
- 根因：adb push 使用 shell 用户的 mkfd，chroot 挂载后路径权限仍属 root
- 修复：先 push 到宿主机普通路径 `/data/local/tmp/<filename>`，再 `su 0 -c "mv /data/local/tmp/<filename> <chroot_path>"`

## 三之三、Aria2 save-session 文件不自动创建
- 若 `aria2.conf` 里 `save-session=/path/to/session.session`，aria2c **不会**自动创建该文件
- 启动时报错：`Failed to open the file ... cause: File not found or it is a directory`
- 修复：先 `touch <session_path>`，再 `chown root:root <session_path>` 后启 daemon

## 三之四、Nginx duplicate default_server
- Debian 装完 nginx 后 `/etc/nginx/sites-enabled/default` 已包含 `listen 80 default_server`
- 新建 site 时重复指定 `default_server` 报错：`duplicate default server for 0.0.0.0:80`
- 修复：`rm -f /etc/nginx/sites-enabled/default` 后再载入自定义 site
- 先 `nginx -t` 校验，再 `killall -9 nginx; nginx`

## 三之五、静态 binary 部署到 chroot
- chroot 内 apt 依赖网络频繁断网时不稳，优先走**宿主机路径下载 → adb push → mv** bins
- 标准流程：
```bash
# Mac 下载静态 binary
curl -L -o /tmp/openlist <binary_url>

# adb push 到宿主机普通路径（避免 chroot 权限问题）
adb push /tmp/openlist /data/local/tmp/services/bin/openlist

# 宿主机移动 + chown
adb shell 'su 0 -c "mkdir -p /data/local/tmp/services/bin && mv /data/local/tmp/openlist /data/local/tmp/services/bin/openlist && chmod 755 ..."'

# chroot 内通过 mount --bind 挂载宿主机服务目录
adb shell 'su 0 -c "mount --bind /data/local/tmp/services /data/local/tmp/chroot/debian/opt/services"'
```
- `mount --bind` 是幂等的：重复执行不报错，适合放 service.d
- OpenList 首次初始化会生成随机密码并只输出一次，需及时记录或改掉

## 四、根因排查：mount 计数不是“手动执行次数”
- `grep -c chroot/... /proc/mounts` 得到的是 **mount propagation 展开后的总条目数**，不是脚本执行次数。
- `mount --rbind /dev` 会把 `/dev/pts`、`/dev/mqueue`、`/dev/binder` 等子挂载点递归复制进目标树；每一个子挂载点都占一条 `/proc/mounts` 记录。
- 在 `shared:` 传播域里，任意 peer 重复 mount 都会被其他 peer 看到；脚本即使只执行几轮，也会因为 propagation 风暴膨胀到几千/数万条。
- 诊断三方：先看计数，再看 `grep "shared:" /proc/1/mountinfo | sort -u` 里有没有相同 ID，再看是否还有活跃脚本。

## 五、Mount 污染恢复顺序
1. 杀占用进程：先查 `/proc/*/root` 和 `/proc/*/mountinfo`，把 `root=.../chroot/debian` 相关的 pid 杀掉。
2. 反向卸载：```bash
   for i in 1 2 3 4 5; do
     umount -R /data/local/tmp/chroot/debian/dev 2>/dev/null || true
     umount -R /data/local/tmp/chroot/debian/sys 2>/dev/null || true
     umount -R /data/local/tmp/chroot/debian/proc 2>/dev/null || true
     umount -R /data/local/tmp/chroot/debian 2>/dev/null || true
   done
   ```
3. 未清净时的处理：
   - `umount -l` 惰性卸载
   - 如果 `umount` 无效且传播风暴仍在累加，直接隔离到新挂载点
   - **更稳**：用 `unshare --mount` 建独立 mount namespace，切掉 shared propagation 后再做 chroot mount 序列

## 五、服务可用性快速诊断
在 chroot 内先本地自测，不要先猜路由器：
1. `curl -sI http://127.0.0.1:5244/` → 通，说明服务正常
2. `curl -sI http://192.168.1.26:5244/` → 通，说明 host/container 网络共享正常
3. `ss -tlnp | grep 5244` → 看绑定地址是 `0.0.0.0` 还是 `127.0.0.1`
4. 手机→Mac 不通、但本机两跳都通，再查 iptables/AP 隔离

## 六、已知陷阱
```bash
mount_once() {
  local src=$1 dst=$2 type=$3
  if ! mountpoint -q "$dst" 2>/dev/null; then
    mount ${type:+-t $type} "$src" "$dst"
  fi
}

mount_once /data/local/tmp/debian/debian-rootfs /data/local/tmp/chroot/debian
mount_once proc /data/local/tmp/chroot/debian/proc proc
mount_once sysfs /data/local/tmp/chroot/debian/sys sysfs
mountpoint -q /data/local/tmp/chroot/debian/dev || mount --rbind /dev /data/local/tmp/chroot/debian/dev
```
- 每次执行前检查 `mountpoint -q`，避免重复绑定
- `--rbind /dev` 会递归绑定 `/dev/pts`、`/dev/shm` 等子挂载点；重复执行会累积到触发 **No space left on device**

## 四、Mount 污染恢复顺序
1. 杀占用进程：`for pid in /proc/[0-9]*; do ... done` 或 `lsof +D`
2. 反向卸载：```bash
   for i in 1 2 3 4 5; do
     umount -R /data/local/tmp/chroot/debian/dev 2>/dev/null || true
     umount -R /data/local/tmp/chroot/debian/sys 2>/dev/null || true
     umount -R /data/local/tmp/chroot/debian/proc 2>/dev/null || true
     umount -R /data/local/tmp/chroot/debian 2>/dev/null || true
   done
  ``` 
3. 未清净时：`umount -l` 惰性卸载，或直接隔离到新挂载点不再清理旧点

## 六、服务可用性快速诊断
在 chroot 内先本地自测，不要先猜路由器：
1. `curl -sI http://127.0.0.1:5244/` → 通，说明服务正常
2. `curl -sI http://192.168.1.26:5244/` → 通，说明 host/container 网络共享正常
3. `ss -tlnp | grep 5244` → 看绑定地址是 `0.0.0.0` 还是 `127.0.0.1`
4. 手机→Mac 不通、但本机两跳都通，再查 iptables/AP 隔离

## 四、已知陷阱
- proot daemon 不稳：前台调试模式能跑，不代表后台 `start` 能跑
- nginx 路径：Debian 包在 `/usr/sbin/nginx`，非交互 shell 可能不在 PATH
- Alist 启动：chroot 下避免 `--force-bin-dir`，先看标准 `alist server --data /data/alist`
- Magisk service.d 不适合跑 systemd；用简单 shell 保活循环即可

## 五、USB-C 有线网卡勘误
### 5.1 单口限制
- Mi8 是**单 USB-C 口**：插以太网适配器后，USB ADB 会立刻断开。
- 这不是软件问题，不是“Hub 抢端口”，而是该口物理上只能同时服务一个主设备角色。
- 实测结论：插上网卡后 `ip link show` 里无 `eth0`、`/sys/bus/usb/devices` 无新设备、`dmesg`/`logcat` 无 ethernet/adbd 相关报错，**表现为整条 USB 功能态切换，不是枚举失败**。

### 5.2 稳定操作顺序
- 默认工作流：**USB 操作 → 开 TCP ADB → 拔 USB → 插网卡 → TCP ADB 维持**
- 抓 USB 窗口执行：
  ```bash
  adb start-server && adb shell 'su 0 -c "setprop service.adb.tcp.port 5555; stop adbd; start adbd"'
  ```
- 然后立刻 `adb connect 192.168.1.26:5555`
- 再插网卡，保持有线 TCP ADB

### 5.3 若 TCP ADB 仍连不上
- 先确认设备上有线 IP 是否真的起来了：
  ```bash
  adb shell 'su 0 -c "ip -4 addr show | grep inet || true"'
  ```
- 若 `192.168.1.26` 不存在，说明网卡/静态 IP 脚本未生效，需回到 USB 窗口修复 `eth-static.sh`
- 若 IP 存在仍超时，查 `iptables` 和路由器 AP 隔离

### 5.4 Hotplug 方案（拔线前部署，换线后自动配 IP）

当设备只有单 USB-C 口时，拔 USB ADB → 插以太网的过程中会有一段无连接的窗口期。service.d 只在开机时运行一次，热插拔不会触发。需要在拔线前部署一个后台等待脚本。

**脚本：** `scripts/eth-wait-hotplug.sh`

**部署流程：**
```bash
# 1. 推送脚本到设备（USB ADB 还连着时）
adb push ~/.hermes/skills/android/android-eth-static-ip/scripts/eth-wait-hotplug.sh /data/local/tmp/
adb shell 'su 0 -c "chmod +x /data/local/tmp/eth-wait-hotplug.sh"'

# 2. 后台启动（脚本会等待 eth 接口出现）
adb shell 'su 0 -c "sh /data/local/tmp/eth-wait-hotplug.sh &"'

# 3. 确认进程存活，父 PID 应为 1（init）— 独立于 ADB shell
adb shell 'ps -ef | grep eth-wait'

# 4. 拔 USB → 插以太网 → 脚本自动检测并设 IP
# 5. 通过 TCP ADB 连接回来验证
adb connect 192.168.1.26:5555
adb shell 'ip addr show eth0 && ip route show default'
```

**原理：** `su 0 -c "sh script.sh &"` 在 Android 上 fork 的子进程继承自 init（PID 1），ADB shell 退出后不会被 SIGHUP 杀掉。

**验证：** 插网线后 `ip route show` 应显示 `default via 192.168.1.1 dev eth0`，且 `ping 192.168.1.1` 通。

## 七、USB → TCP ADB 切换（不依赖 WiFi）
- 抓 USB ADB 窗口：`adb start-server && adb shell 'su 0 -c "setprop service.adb.tcp.port 5555; stop adbd; start adbd"'`
- 切有线：`adb connect <device_ip>:5555`
- 注意：`stop adbd` 会暂断连接；必须在**还能 USB 操作时**设属性并重启 adbd，然后立刻转 TCP。
- 若网卡未识别而无法 TCP 连接，只能重新插回 USB，再次执行上面命令。

## 八、默认网关缺失诊断（高频）
**症状**：`ip addr` 里 `eth0` 已有 `192.168.1.26/24`，但无法上外网，`ping 8.8.8.8` 超时。
**根因**：`ip route` 只有 `192.168.1.0/24 dev eth0`，**缺 default via 192.168.1.1**。
**验证**：
```bash
adb shell 'ip route show default; ping -c1 -W2 192.168.1.1'
```
`192.168.1.1` 可达但 `default via` 缺失，属于网关未注入，不是 DNS/链路问题。
**修复**：
```bash
adb shell 'su 0 -c "ip route replace default via 192.168.1.1 dev eth0"'
```
脚本模板已改为 `ip route replace ...`，不再用 `route add ... >/dev/null 2>&1 || true`。

## 九、多设备同网段下的可达性预检
同类设备（如 Mi6、Mi8 都曾在 `192.168.1.x` 出现）共享地址记忆时：
- 不要假设记忆中的 IP 当前仍有效
- 决策树：`ping` → `/proc/net/arp` → `adb devices` → 现场 `/sys/class/net/` 和环境
- 三跳都有一跳失败：判定**不可达**，先恢复设备在线（WiFi / USB 临时连接），再继续网络配置
- 不要对不可达设备继续推进有线网卡配置；把阻塞状态明确写回报告，等设备在线后继续
- `references/chroot-service-notes.md`：Alist/aria2/nginx 在 chroot 里的真实路径、密码重置、Magisk 保活模式
- `references/mount-saturation-notes.md`：`shared:39` 传播风暴现场证据、unshare/make-rprivate 修复路径、chroot3-test.sh 经验
- `references/adbd-restart-watchdog.md`：单 USB-C 口设备 adbd 因 USB 状态变更退出后 TCP 端口空挂的诊断 + 看门狗部署
