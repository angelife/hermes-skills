# Kodi 21 崩溃排查 — Core Dump 诊断法

## 什么时候不是随机闪退

如果 Kodi 反复崩溃重启，不要只查 kodi.log（它不记崩溃）。用系统级工具：

### 诊断顺序

```
1. coredumpctl list | grep kodi     # 列出所有 Kodi core dump
2. coredumpctl info <PID> --no-pager | grep "#0\|#1\|#2"  # 看崩溃栈
3. dmesg | grep -iE "segfault|kodi"  # 内核确认
4. journalctl -xe | grep -iE "kodi|segfault"  # systemd 兜底
5. kodi.log  # 最后参考（正常退出才有记录）
```

### 关键信号：crash 栈帧是否一致

- **每次 #0-#2 不同** → 随机 bug/内存损坏
- **每次 #0-#2 完全一致** → 确定性 bug，直接找源码或问 AI，不要试 workaround

### 2026-07-16 实测

Kodi 21.3 Omega 在 Celeron T3500 上的崩溃：
- 所有 crash `#0 TiXmlAttributeSet::Find() (libtinyxml.so.0)` 
- 调用链：CAddonSettings::Load → CAddon::HasSettings → CContextMenuManager
- 根因：Kodi 21 读取 addon.xml 时遇到 NULL 属性指针
- workaround 无效（清理配置 / nuke 数据库全试过）
- **断电重启后恢复正常**

## 如果 AI 连不上

OpenBridge 浏览器扩展需 Chrome 配对才能工作。如果 `hermes bridge status` 显示 "Extension: Not connected"：
1. 检查浏览器是否开了 Chrome，且 Hermes 扩展已配对
2. 如果用户远程不在电脑前 → 告诉用户 AI 暂时不可用，给出已知结论
3. 不要轮询 4+ 种不同方法都试一遍
