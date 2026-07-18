# IPTV Simple + Kodi 21.3 崩溃修复记录

## 环境
- 设备：Celeron T3500 笔记本（赛扬 2.1GHz / 2GB RAM）
- OS：Arch Linux, kernel 7.1.3, Xorg modesetting
- GPU：Intel Mobile 4 Series (GMA 4500M)，LVDS 内置屏
- Kodi：21.3.0 Omega (arch extra 源)
- 连接：无线 wlp4s0b1，双 IP（192.168.0.104/107）

## 问题
Kodi 每隔 ~45 秒崩溃一次，`kodi-standalone` 自动重启，用户看到"反复重启"。

## 诊断路径

### 1. 别只看 kodi.log — 真相在 coredump
kodi.log 里没有崩溃信息（因为崩溃时来不及写日志）。必须查：
```bash
coredumpctl list | grep kodi       # 列出所有 Kodi core dumps
coredumpctl info <PID> --no-pager  # 看具体崩溃栈
```

### 2. 崩溃特征（100% 一致，每个 crash 完全相同）
```bash
Signal: 11 (SEGV), si_code: SEGV_MAPERR
#0  TiXmlAttributeSet::Find() (libtinyxml.so.0)
#1  TiXmlElement::Attribute()
#2  CAddonSettings::Load(CXBMCTinyXML const&)
#3  CAddon::SettingsFromXML()
#4  CAddon::LoadUserSettings()
#5  CAddon::HasSettings()
#6  CAddon::CanHaveAddonOrInstanceSettings()
#7  CContextMenuItem::CAddonSettings::IsVisible()
#8  CContextMenuManager::GetItems()
#9  CGUIMediaWindow::OnPopupMenu()
```

⚠️ 所有 crash 的 #0-#2 栈帧完全相同 → 这是确定性 C++ bug，不是随机闪退。

### 3. kodi-standalone 自动重启脚本分析
```sh
# 包装脚本结构：
while true; do
  kodi --standalone
  RET=$?
  if [ $RET -ge 64 ] && [ $RET -le 66 ] || [ $RET -eq 0 ]; then
    break  # 正常退出
  else
    if [ $DIFF -gt 60 ]; then reset counter
    else
      if [ $CRASHCOUNT -ge 3 ]; then break; fi
    fi
  fi
done
```

### 4. 尝试的修复及结果
- 清理旧 IPTV 配置 → ❌ 仍崩溃
- 删除 Addons33.db + 全部用户插件 → ❌ 机器随后离线，未验证
- **断电重启机器** → ✅ Kodi 恢复正常

### 5. 教训
当 core dump 显示确定性 C++ bug（所有 crash 100% 一致的栈帧），不要再试 workaround。这是 Kodi 21 的源码级问题（TinyXML NULL 指针），修不了源码就停手，告诉用户去问 AI。

## 鼠标诊断
USB 鼠标（PixArt USB Optical Mouse）被系统识别：
```
I: Bus=0003 Vendor=093a Product=2510 Version=0111
N: Name="PixArt USB Optical Mouse"
H: Handlers=event12 mouse1
```
Xorg 正确加载 libinput 驱动。
Kodi 21 鼠标支持本身很弱，推荐键盘/遥控器/Kodi Remote App 替代。

## 系统时间修复
CMOS 电池耗尽导致 RTC 回到 2007-01-01 → SSL 证书验证失败。
```bash
date -s "2026-07-16 19:48:00"
hwclock -w
timedatectl set-ntp true
```

## pacman 镜像修复
单阿里云镜像从图书馆网络超时，改为 7 个镜像兜底：
```bash
Server = https://mirrors.sjtug.sjtu.edu.cn/archlinux/$repo/os/$arch
Server = https://mirrors.hit.edu.cn/archlinux/$repo/os/$arch
Server = https://mirrors.ustc.edu.cn/archlinux/$repo/os/$arch
Server = https://mirrors.tuna.tsinghua.edu.cn/archlinux/$repo/os/$arch
Server = https://mirrors.aliyun.com/archlinux/$repo/os/$arch
Server = https://mirror.0x.sg/archlinux/$repo/os/$arch
Server = https://mirrors.kernel.org/archlinux/$repo/os/$arch
```

## IPTV Simple 安装
- `kodi-addon-pvr-iptvsimple-debug` 包只含调试符号，不含主包
- 从 AUR 编译安装：`makepkg -si kodi-addon-pvr-iptvsimple`（赛扬编译约 15-20 分钟）
- 编译后需重启 Kodi 才能识别插件
