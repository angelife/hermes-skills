---
name: n1-troubleshooting-wizard
title: N1 盒子故障诊断与解决方案技能
description: 基于 MoA（Mixture of Agents）架构的斐讯 N1 盒子故障诊断技能。覆盖 S905D/S905X 硬件差异、USB 供电不足、apt 锁死、SSH 端口/首次登录、DTB 匹配、U 盘兼容等未覆盖痛点。支持搜索-分析-汇总-输出的完整工作流。
tags: [n1, arm64, armbian, troubleshooting, moa]
---

## Purpose
系统性地诊断斐讯 N1 盒子（S905D）刷 Armbian / OpenWrt 后的各类问题，通过 MoA 多智能体协作搜索、分析、汇总解决方案，输出精准的技术修复步骤。

## Triggers
- N1 盒子刷机后出现异常（无法开机、无法 SSH、网络不通、apt 锁死等）
- 不确定 N1 是 S905D 还是 S905X/S905L 等变种，需要确认 DTB
- USB 口无供电、插鼠标/U盘没反应
- 首次 SSH 登录密码 1234 不生效、自动退出
- apt update / dpkg 锁死、无法安装软件
- Docker 容器在网络配置后无法启动
- 双 N1 架构中一台跑 hindsight/PostgreSQL、一台跑 proxy

## MoA 工作流

### Agent 1: 问题识别与分类
输入：用户描述的症状
输出：
- 问题分类（硬件差异 / 供电 / 网络 / 系统 / 软件 / 配置）
- 最可能的 3 个原因，按概率排序
- 需要用户确认的关键信息（固件版本、USB 口位置、是否有线连接）

### Agent 2: 知识库搜索
输入：问题分类 + 用户确认的信息
输出：
- 搜索恩山论坛 / GitHub ophub / CNBlogs / ZNDS 等社区
- 提取与当前问题最相关的解决方案（至少 3 个不同来源）
- 标注每个方案的适用条件和失败记录

### Agent 3: 方案汇总与验证
输入：Agent 2 的搜索结果
输出：
- 按成功率排序的修复方案列表（含具体命令）
- 方案之间的冲突说明（如不同 DTB 的选择）
- 失败回滚方案（如果方案 N 无效，如何恢复）
- 预防措施（下次遇到同类问题怎么避免）

## 已覆盖的痛点解决方案速查

### 1. S905D vs S905X 硬件差异
**识别方法**：
```bash
cat /proc/cpuinfo | grep Hardware
```
- N1 是 S905D（无 DVB 电路），S905X 有 DVB 但不同主板
- DTB 文件不通用！刷错 DTB 会导致无网络/负载高
- ophub 镜像选择时选 `s905d` 系列

### 2. USB 供电不足
**症状**：
- 插鼠标/OTG 网卡没反应
- 频繁掉线、黑屏重启
- USB 口能供电但功率不够带外接设备

**修复方案**：
1. 换靠近 HDMI 的 USB 口（供电更强）
2. 用带供电的 USB Hub
3. 外接 USB 电源（公对公 USB 线，电脑 USB 供电到 N1）
4. 拆开 N1，在指示灯附近两个触点短接（需要电烙铁）

### 3. apt/dpkg 锁死
**症状**：
```
E: Could not get lock /var/lib/dpkg/lock-frontend
E: Unable to acquire the dpkg frontend lock
```

**修复方案**：
```bash
ps aux | grep apt
kill -9 <PID>
sudo rm /var/lib/dpkg/lock-frontend
sudo rm /var/lib/dpkg/lock
sudo rm /var/cache/apt/archives/lock
sudo dpkg --configure -a
sudo apt update
```
**预防**：刷机后先 `dpkg --configure -a` 再 `apt update`

### 4. SSH 首次登录 / 端口问题
**症状**：
- `ssh root@IP` 连不上
- 密码 1234 不对
- 改密码后自动退出 SSH

**修复方案**：
```bash
sudo systemctl status ssh
nmap -sn 192.168.1.0/24
ssh root@192.168.1.X    # 密码 1234
# 输入两遍新密码（确保英文键盘）
# 改密码后自动断开是正常的，用新密码重新连
```

### 5. DTB 不匹配
**症状**：
- 刷完 Armbian 后无网络
- CPU 负载异常高（单核 100%）
- HDMI 无输出

**修复方案**：
```bash
ls /boot/dtb/amlogic/
# 修改 /boot/uEnv.ini 指向正确 DTB：
# dtbname=s905d-phicomm-n1.dtb
```

### 6. U 盘兼容性
- Class 10 以上 USB 2.0 U 盘（N1 只有 USB 2.0 接口）
- 品牌 U 盘（三星/闪迪/金士顿）
- 容量 8-32GB
- 不推荐杂牌/扩容盘

### 7. OpenWrt 密码遗忘恢复（密码恢复路径）
**症状**：
- SSH/Telnet 无法登录，密码遗忘
- 没有物理 Reset 键（或找不到）
- 无法通过 Web UI 进入

**⚠️ 重要前提**：本节适用于对**自己拥有的设备**进行授权测试。所有测试应在本地网络内进行，不涉及任何远程突破或未授权访问。

**诊断第一步 — 确认认证方式**：
```bash
# 用 ssh -v 连一下，观察支持哪种认证
ssh -v root@<N1_IP>
# 看输出里有没有 " Authentications that can continue: password"
# 如果有 "publickey" 在前面，说明密码认证是开启的，只是密码不对
# 如果只有 "password" 可见，则密码认证是唯一途径
```

**恢复路径（按优先级）**：

#### 路径A：本地终端（需 HDMI+键盘，5分钟）
```
1. N1 接 HDMI 显示器
2. USB 键盘接 N1
3. 启动后在本地 tty 登录（用户：root）
4. 执行 passwd root 改密码
```

#### 路径B：HTTP LuCi CSRF/Session 攻击（如果 Web 未改默认会话）
```bash
# 检查 LuCi 是否可未授权访问某些路径
curl -s http://<N1_IP>/cgi-bin/luci/admin/status/iptables
# 检查备份功能是否需要认证
curl -s -o /dev/null -w "%{http_code}" http://<N1_IP>/backup
```

#### 路径C：SMB/FTP 枚举
```bash
# 尝试 SMB 空会话
smbclient -L //<N1_IP> -N 2>&1 | head -20
# 尝试 FTP 匿名登录
ftp <N1_IP>
# 用户：anonymous，密码：空或任意邮箱
```

#### 路径D：物理 Reset（N1 闪存恢复出厂，10分钟）
```
1. 拔掉 N1 电源
2. 找到靠近 HDMI 口一侧的小孔（Reset 键）
3. 按住 Reset 不松手，插上电源
4. 等待 5 秒（黄灯闪烁）后松开
5. N1 恢复出厂 IP（通常 192.168.1.1），密码恢复为默认 root/password
```

#### 路径E：暴力破解 SSH（⚠️ 仅对自己设备、有限次尝试）
```
注意：Mac 上默认没有 sshpass，需要安装：
  brew install hxtools   # 安装 hxtools 包含 sshpass
  或者用 expect 脚本绕过 sshpass

常见 OpenWrt 密码 TOP30（优先试）：
password, admin, 123456, 12345678, 1234, 12345,
root, admin123, password123, admin888, 123456789,
000000, 111111, 222222, 333333, 666666, 888888, 999999,
abc123, abcdef, a1b2c3, pass, pass123, pass1234

如果密码已被改为简单数字组合（生日、房间号等），
可以用 crunch 生成对应位数的数字字典再试。
```

#### 路径F：重刷（最终手段，不保留配置）
```
使用 openwrt-n1-flash 技能重新刷入 OpenWrt，
默认密码恢复为 root/password，但所有配置丢失。
```

**已知 N1 OpenWrt 固件默认密码速查**：
| 固件来源 | 默认用户 | 默认密码 |
|---------|---------|---------|
| 恩山论坛大多数固件 | root | password |
| Armbian | root | 1234 |
| OpenWrt 官方 | root | password |
| 某蟹/某数字固件 | admin | admin |

## 输出格式
每个故障诊断输出包含：
1. **问题诊断**：症状 → 分类 → 原因分析
2. **修复方案**：按成功率排序，含具体命令
3. **回滚方案**：如果修复失败，怎么恢复
4. **预防建议**：如何避免再次出现

## 参考资源
- 恩山无线论坛：https://www.right.com.cn/forum/
- ophub amlogic-s9xxx-armbian：https://github.com/ophub/amlogic-s9xxx-armbian
- 博客园 N1 刷机整理：https://www.cnblogs.com/ifme/p/13201015.html
- 智能电视网 N1 专区：https://www.znds.com/tv-1160843-1-1.html
