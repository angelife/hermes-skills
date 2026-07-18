# Chrome 后台进程导致打不开窗口 — 复现 + 诊断记录

## 场景

用户说「Chrome 无法正常打开」。点 Dock 图标跳一下没反应。

## 诊断步骤（真实会话记录）

### 1. 确认安装和进程

```console
$ ls -la "/Applications/Google Chrome.app/"
$ pgrep -fl Chrome
```

### 2. 发现关键线索

```console
$ ps aux | grep -i "Google Chrome$" | grep -v grep | grep -v headless
74526 /Applications/Google Chrome.app/Contents/MacOS/Google Chrome
  --user-data-dir=/Users/macos/Library/Application Support/Google/Chrome
  --no-startup-window
```

核心问题：`--no-startup-window` 标志 → Chrome 在后台跑但不显示窗口。

### 3. 确认背景运行时间

```console
$ ps -o lstart= -p 74526
Thu  9 Jul 16:37:04 2026
```

进程从昨天跑到现在。

### 4. 查出启动方式（PPID=1 → launchd 后台应用）

```console
$ ps -o ppid= -p 74526
1
```

PPID=1 意味着它是被 launchd 管理的后台进程（Chrome「关闭后继续运行后台应用」功能）。

### 5. 检查 SingletonLock

```console
$ ls -la ~/Library/Application\ Support/Google/Chrome/SingletonLock
lrwxr-xr-x@ ... SingletonLock -> macosdeMacBook-Pro.local-74526
```

锁文件指向 PID 74526，这个 PID 活着但不会响应窗口请求。

### 6. 修复（基本版）

```console
# 杀掉卡住的后台进程
$ kill 74526

# 确认锁释放
$ ls ~/Library/Application\ Support/Google/Chrome/SingletonLock
SingletonLock 已释放

# 用 -n 强制新实例（绕过同名应用检测）
$ open -n -a "Google Chrome"

# 验证窗口存在
$ osascript -e 'tell application "Google Chrome" to count every window'
1

# 关闭后台运行防复发
$ defaults write com.google.Chrome "BackgroundModeEnabled" -bool false
```

## 复杂场景：杀完旧进程依然 0 窗口

### 场景 7a：LaunchServices 冲突（Headless 实例阻塞）

Hermes browser tool / Playwright 等工具可能启动 `--headless=new` 或 `--headless=old` 的 Chrome/Chromium 实例。这些 headless 实例虽然使用独立用户数据目录，但 macOS LaunchServices 仍然将其归类为「Chrome」进程。当用户点击 Dock 图标时：

```
open -a "Google Chrome"  →  LaunchServices 查找注册的 Chrome 实例
                           → 找到 headless Chrome (PID xxxx)
                           → 向 headless 进程发送"创建新窗口"消息
                           → headless 无法创建 GUI 窗口
                           → 用户看不到任何反应
```

**诊断方法：**

```bash
# 找所有 Chrome 进程（含 headless）
ps aux | grep -iE "chrome|chromium" | grep -v Helper | grep -v crashpad

# 关键模式：headless 进程虽用不同 user-data-dir，但 LS 仍视其为 Chrome
/Applications/Google Chrome.app/.../Google Chrome --remote-debugging-port=9222 --headless=new --user-data-dir=/tmp/xxx

# 检查 launchd 是否注册了前台 Chrome 进程
launchctl list | grep -i chrome
```

**修复方法：**

```bash
# 1. 杀掉所有 Chrome/Chromium 进程（含 headless 和 Playwright）
kill $(pgrep -f "Google Chrome" 2>/dev/null)
kill $(pgrep -f "chrome-headless" 2>/dev/null)

# 2. 重置 LaunchServices 数据库（核心步骤！）
/System/Library/Frameworks/CoreServices.framework/Versions/A/Frameworks/LaunchServices.framework/Versions/A/Support/lsregister -kill -r -domain local -domain system -domain user

# 3. 重新注册 Chrome
/System/Library/Frameworks/CoreServices.framework/Versions/A/Frameworks/LaunchServices.framework/Versions/A/Support/lsregister -f /Applications/Google\ Chrome.app

# 4. 打开 Chrome
open -a "Google Chrome"
```

### 场景 7b：Corrupted Local State 或 Crashpad

即使杀完所有进程并重置 LS，Chrome 可能仍然启动后 0 窗口。此时是 Chrome Profile 中的文件损坏。

**诊断：隔离 Default/ 目录测试**

```bash
# 1. 确认 Default/ 目录结构存在
ls ~/Library/Application\ Support/Google/Chrome/Default/

# 2. 将 Default/ 之外的所有顶层文件移开
cd ~/Library/Application\ Support/Google/Chrome
mkdir -p /tmp/chrome-isolation
for f in *; do
  [ "$f" = "Default" ] && continue
  [ "$f" = ".DS_Store" ] && continue
  mv "$f" /tmp/chrome-isolation/
done

# 3. 启动 Chrome 验证
open -a "Google Chrome"
osascript -e 'tell application "Google Chrome" to count windows'
# 期望: 1

# 4. 如果只留 Default/ 正常 → 问题在顶层文件之一
# 用二分法逐个恢复文件找出祸首
```

**已知问题文件：**

| 文件名 | 原因 | 修复方法 |
|--------|------|----------|
| `Local State` | Chrome 全局状态文件损坏，导致启动时无法创建窗口 | 删除后 Chrome 自动重建。书签/历史/密码在 Default/ 中，不受影响 |
| `Crashpad/` 目录 | 崩溃报告系统数据损坏 | 删除目录重建为空目录 |

**Local State 损坏的症状：**

```console
$ log show --predicate 'process == "Google Chrome"' --last 30s --style compact | grep -i "restore"
... Unable to find className=(null)
... heuristicsWindow=0x0
... window=0x0
```

Chrome 试图恢复 NSApplication 窗口状态，但 className 为 null，窗口创建失败。

## 全流程：0 窗口问题的系统排查步骤

当用户说 Chrome 打不开时，按以下顺序排查：

```
1. pgrep -fl "Google Chrome" → 看有哪些进程
   ├─ 有 --no-startup-window 进程 → 杀之 → open -n
   ├─ 仅有 headless 进程 → LS 冲突，杀所有 + lsregister reset
   └─ 完全无进程 → 跳到 2

2. 杀所有 Chrome/Chromium 相关进程
   kill $(pgrep -f -iE "chrome|chromium")

3. lsregister -kill -r -domain local -domain system -domain user
   lsregister -f /Applications/Google\ Chrome.app

4. open -a "Google Chrome" → 检查窗口
   ├─ 正常 → 结束
   └─ 仍 0 窗口 → 跳到 5

5. 隔离排查：只留 Default/，移开其他顶层文件
   用二分法找出损坏文件（最多见：Local State, Crashpad）

6. 修复后：关闭 BackgroundModeEnabled 防复发
```

## 预防方法

Chrome 设置 → 系统 → 「关闭 Google Chrome 后继续运行后台应用」→ 关闭

或此命令等效：
```bash
defaults write com.google.Chrome "BackgroundModeEnabled" -bool false
```

## 可验证指标

- `ps aux | grep "no-startup-window" | grep -v grep` → 应为空
- `SingletonLock` → 不应指向死 PID
- Chrome 窗口数 > 0
- `lsregister -dump | grep com.google.Chrome` → 应只注册正常的 Chrome 实例
