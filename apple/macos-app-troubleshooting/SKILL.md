---
name: macos-app-troubleshooting
description: >-
  Diagnose macOS apps that won't open, crash on launch, or appear stuck.
  Covers stale background processes with --no-startup-window, SingletonLock
  conflicts, launchd-managed zombie processes, and login item issues.
version: 1.1
---

# macOS App Troubleshooting — 应用打不开/窗口不出/卡死的系统排查

## 触发条件

用户说以下任意一种情况时加载本 skill：
- "X 打不开 / 无法正常打开 / 点图标没反应"
- "X 在后台但没窗口"
- "X 刚启动就闪退"
- "点 X 图标跳一下就没然后了"

## 前置检查

### 0. 确认应用是否已安装

```bash
ls -la "/Applications/<AppName>.app" 2>/dev/null
# 也检查 ~/Applications/
ls -la ~/Applications/*.app 2>/dev/null
```

### 1. 进程状态排查（最常发现问题）

```bash
# 看是否有进程在跑（排除 Helper / crashpad 等子进程）
pgrep -fl "<AppName>" | grep -v Helper | grep -v crashpad
```

关键模式：
- **进程在跑但没有窗口参数** → 应用可能只是没显示
- **进程有 `--no-startup-window`** → 后台模式卡住了（最常见原因）
- **进程 PPID=1（launchd）** → 作为后台/登录项启动，可能不是正常启动
- **完全无进程** → 可能是闪退或安装损坏

### 2. SingletonLock / 用户数据锁排查

许多应用（Chrome, Slack, VS Code 等）使用锁文件防止多实例冲突：

```bash
ls -la ~/Library/Application\ Support/<App>/SingletonLock 2>/dev/null
# 如果是符号链接，看指向哪个 PID
readlink ~/Library/Application\ Support/<App>/SingletonLock
# 看该 PID 是否还活着
ps -p <PID> 2>/dev/null
```

- SingletonLock 指向一个已死的 PID → 锁残留，需要手动删除锁文件
- SingletonLock 指向一个活着的 `--no-startup-window` 进程 → 卡住的后台进程

### 3. 崩溃日志检查

```bash
ls -lt ~/Library/Logs/DiagnosticReports/ | grep -i "<app>" | head -5
ls -lt ~/Library/Application\ Support/<App>/Crashpad/reports/ 2>/dev/null | head -5
```

## 常规修复步骤

### 步骤 A：杀旧进程并强制新实例

```bash
# 找到主进程 PID
pgrep -x "<AppName>"

# 如果确认是卡住进程，杀掉
kill <PID>

# 确认已释放锁
ls ~/Library/Application\ Support/<App>/SingletonLock 2>/dev/null || echo "锁已释放"

# 强制新实例（跳过锁检查）
open -n -a "<AppName>"
```

### 步骤 B：验证恢复

```bash
# 确认新进程参数干净
ps -o args= -p <新PID>

# 确认窗口可用
osascript -e 'tell application "<AppName>" to count every window'
```

## Chrome 特有排查（最常见案例）

Chrome 有一个特殊的「关闭后继续运行后台应用」设置：
- 开启后，关掉最后一个窗口 → Chrome 转为后台进程（`--no-startup-window`）
- 再点图标 → 系统试图复用无窗口进程 → 打不开
- SingletonLock 指向 `macosdeMacBook-Pro.local-<PID>`

**特有问题：**
- PPID=1（launchd 管理），不是普通进程
- 后台进程会在系统启动时自动拉起（通过 `application.com.google.Chrome...` 注册）
- 用 `kill` 杀掉后需要 `open -n` 强制新实例

**LaunchServices 冲突（Headless 实例阻塞）：**

Hermes browser tool / Playwright 等工具可能启动 `--headless=new` 的 Chrome/Chromium 实例。它们虽用独立用户数据目录，但 macOS LaunchServices 仍将其归类为「Chrome」。点 Dock 图标时：

```
open -a "Google Chrome" → LS 找到 headless Chrome → 发"创建窗口"消息
                         → headless 无法创建 GUI 窗口 → 用户看不到反应
```

**诊断：**
```bash
# 找所有 Chrome/Chromium 进程（含 headless）
ps aux | grep -iE "chrome|chromium" | grep -v Helper | grep -v crashpad
# 看是否有 --headless= 参数的进程
```

**修复（LS 数据库重置）：**
```bash
# 1. 杀所有 Chrome/Chromium 进程（含 headless 和 Playwright）
# 2. 重置 LaunchServices 数据库
/System/Library/Frameworks/CoreServices.framework/Versions/A/Frameworks/LaunchServices.framework/Versions/A/Support/lsregister -kill -r -domain local -domain system -domain user
# 3. 重新注册 Chrome
/System/Library/Frameworks/CoreServices.framework/Versions/A/Frameworks/LaunchServices.framework/Versions/A/Support/lsregister -f /Applications/Google\ Chrome.app
# 4. 打开 Chrome
open -a "Google Chrome"
```

**预防复发：**
```bash
defaults write com.google.Chrome "BackgroundModeEnabled" -bool false
```

## 深入排查：Profile 组件损坏（杀完进程仍 0 窗口）

当杀完所有进程、重置 LS 后，Chrome 仍然 0 窗口 → Chrome Profile 中的文件损坏。

### 诊断方法：Profile 隔离测试

```bash
# 1. 将 Default/ 之外的所有顶层文件移开
cd ~/Library/Application\ Support/Google/Chrome
mkdir -p /tmp/chrome-isolation
for f in *; do
  [ "$f" = "Default" ] && continue
  mv "$f" /tmp/chrome-isolation/ 2>/dev/null
done

# 2. 启动验证（只留 Default/）
open -a "Google Chrome"
osascript -e 'tell application "Google Chrome" to count windows'
# 期望: 1（首次会显示 chrome://whats-new/）
```

如果只留 Default/ 正常 → 通过二分法逐个恢复文件找出损坏项。

### 已知问题文件

| 文件 | 症状 | 修复 |
|------|------|------|
| `Local State` | 日志显示 `Unable to find className=(null)`，窗口创建失败 | 删除后 Chrome 自动重建。书签/历史/密码在 Default/ 无影响 |
| `Crashpad/` | 崩溃报告系统数据损坏 | 删除目录重建为空目录 |

### Local State 文件说明

`Local State` 是 Chrome 的全局状态文件（窗口布局、实验标志、变体种子等），不是用户数据。损坏时 Chrome 无法完成初始化 → 0 窗口。安全删除，Chrome 自动重建。用户核心数据全在 `Default/` 下。

### Chrome 0 窗口全流程排查

```
1. pgrep -fl "Google Chrome" → 看有哪些进程
   ├─ 有 --no-startup-window → 杀之 → open -n
   ├─ 仅有 headless → LS 冲突 → 杀所有 + lsregister reset
   └─ 无进程 → 直接下一步

2. 杀所有 Chrome/Chromium 进程
   kill $(pgrep -f -iE "chrome|chromium") 2>/dev/null

3. 重置 LaunchServices + 重新注册
   lsregister -kill -r -domain local -domain system -domain user
   lsregister -f /Applications/Google\\ Chrome.app

4. open -a "Google Chrome" → 检查窗口
   ├─ 正常 → 关闭 BackgroundModeEnabled
   └─ 仍 0 窗口 → Profile 隔离排查

5. 隔离 Default/ → 二分法找损坏文件
   (Local State / Crashpad 最常见)
```

## 其他模式的通用排查

| 症状 | 排查方向 |
|------|---------|
| 点图标跳一下没反应 | `pgrep` 看是否已有进程 → 看启动参数 |
| 闪退 | 看 `DiagnosticReports/` 下的 `.crash` / `.ips` 文件 |
| 打不开但无崩溃报告 | 检查 Gatekeeper: `spctl --assess --verbose /Applications/X.app` |
| 权限问题 | 修复权限: `chmod -R +w ~/Library/Application\ Support/X/` |

## Pitfalls

- `open -a "App"` 不加 `-n` 不会新启进程，只会向已有进程发消息。如果已有进程卡死，消息不会生效。
- `kill -9` 可能导致锁文件残留。先用 `kill`，如果锁还在再删锁文件。
- 排查前先记下当前进程的 PID、启动时间、参数，以便回滚。
- 不要上来就推荐重装。macOS 应用打不开 80% 是进程/锁问题，不是安装损坏。
