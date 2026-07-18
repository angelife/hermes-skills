# 实战案例：Kodi 鼠标修复

> 2026-07-16 · 赛扬 T3500 / Arch Linux / Kodi 21.3 Omega

## 问题

USB鼠标系统识别（`PixArt USB Optical Mouse`），
Kodi 日志显示 `Register - new mouse device registered`，
`input.enablemouse=true`，但光标不出现，点击无响应。
触摸板同样不工作。

## 流程记录

### 1. 问三个AI

同一问题发给 Gemini / Claude / ChatGPT：

```
Kodi 21.3 on Arch Linux, Celeron T3500, Intel GMA 4500M.
USB mouse (PixArt) detected at /dev/input/event12,
Kodi log shows 'Register - new mouse device registered',
input.enablemouse=true, but cursor never appears and clicks do nothing.
Touchpad (ETPS/2 Elantech) also doesn't work.
Give exact shell commands to fix, ordered by likelihood of success.
```

### 2. NLM 合成分析

Notebook: `9aa62674-370f-4f41-9333-d67cce169d0d`

查询语句：
```
分析这三份诊断的共识和分歧：
1. 三个AI确认的根因是什么？
2. 修复步骤的优先级建议（按共识度排序）
3. 哪个AI遗漏了什么关键点？
4. 给出一个合并的修复方案
```

### 3. NLM 合成结论

**根因共识：** 权限/seat 问题，非 Kodi 配置。
Kodi GBM 独占模式无窗口管理器，普通用户无权读 `/dev/input/`。

**AI 互评：**
- Claude 最全面（seatd + 组权限 + i915 渲染 Bug）
- Gemini 漏了 seatd 服务
- ChatGPT 漏了 i915 光标渲染 Bug

**合并修复：**
```bash
sudo usermod -aG input,video,render,seat $USER
sudo pacman -S --needed seatd && sudo systemctl enable --now seatd
export KODI_SOFTWARE_CURSOR=1
kodi-standalone
```

## 教训

1. 不要同时开多个 AI 窗口（回复混淆）
2. 确认每个 AI 已登录再问（否则拿回空壳）
3. 不手动合并三份回复——NLM 做这个
4. 修复后留档到 Obsidian（`土同学工作档案/`）
5. "少就是多，慢就是快"——流程虽慢但结果可靠

## 参考

- NLM notebook ID: `9aa62674-370f-4f41-9333-d67cce169d0d`
- Obsidian: 土同学工作档案/Kodi鼠标修复记录.md
