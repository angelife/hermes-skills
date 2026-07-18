# PVR IPTV Simple v21 Bug: PVR Manager 卡"Starting"

> **2026-07-16 更新：** v21.11.0 在 Kodi 21.3 (Omega) 上已验证正常工作，不再卡 Starting。如果已装 dkmsd 版本（含 debug 符号），仍需装主包 `kodi-addon-pvr-iptvsimple`（详见主 SKILL.md）。以下降级方案的上下文保留，供旧版参考。

## 现象

Kodi 21 (Omega) + PVR IPTV Simple Client v21.x
- Kodi 日志：`PVR Manager: Starting` → 永不继续
- 不报错、不崩溃、不超时——就是卡死
- 删除 PVR 数据库、用极简 m3u（5个频道）都不管用
- 即使 m3u 为空也卡住（说明 bug 在 addon 初始化本身）

## 根因

IPTV Simple Client v21.x 与 Kodi 21 的 PVR 框架存在初始化死锁。
（GitHub Issues [#862](https://github.com/kodi-pvr/pvr.iptvsimple/issues/862) 和 [#929](https://github.com/kodi-pvr/pvr.iptvsimple/issues/929)）

ChatGPT 分析：这不是单纯"找不到入口点"的 segfault。Kodi 的 PVR addon 初始化过程中，v21.x 对 Kodi 21 的 PVR ABI 变化没有正确处理，导致 CreateInstance 完成后无法正常返回控制权给 PVR Manager，产生了死锁。

## 💀 铁律：不要远程卸载 Kodi 的包

**绝对不要**在 Kodi 运行时通过 `pacman -R` 卸载任何 Kodi addon 包（如 `kodi-addon-pvr-iptvsimple`）。

为什么崩溃？ChatGPT 分析：
1. `pacman -R` 删除了 PVR addon 的 `.so` 二进制文件
2. 但 Kodi 的 addon 数据库（`~/.kodi/userdata/Database/addons*.db`）仍保留着 addon.xml 里的注册信息
3. 下次 Kodi 启动：扫描 addon 数据库 → 发现 pvr.iptvsimple → 尝试加载其 binary → binary 不存在 → **崩溃**
4. `.xinitrc` / kodi-standalone 检测到退出 → 自动重启 → 再崩溃 → **死循环**
5. 用户看到 Kodi 不断黑屏重启，鼠标都卡死，反馈"又重启了" / "又重启了几十次了"

**恢复方案（如果不慎远程卸载了）：**

```bash
# 重装回 v21（虽然 PVR 功能卡死但至少不崩）
sudo pacman -S kodi-addon-pvr-iptvsimple

# 清残留（可选，保险起见）
rm -f ~/.kodi/userdata/Database/pvr*.db
rm -rf ~/.kodi/userdata/addon_data/pvr.iptvsimple

# 然后用户拔电重启一次笔记本，就能正常进 Kodi 了
# IPTV 后面用降级或替代方案处理
```

## 正确降级方案

Kodi addon ABI 是绑定 Kodi 主版本的。不能只降级 pvr.iptvsimple 而不降 Kodi 本体（Arch 上 pacman 管理的系统）。

### 方案 A：手动 zip 覆盖

```bash
# 1. 先重装 v21 确保 Kodi 不崩溃
sudo pacman -S kodi-addon-pvr-iptvsimple

# 2. 从 Nexus 仓库下 v20.13.0 zip
curl -sL -o /tmp/pvr-20.13.0.zip \
  "https://mirrors.kodi.tv/addons/nexus/pvr.iptvsimple/pvr.iptvsimple-20.13.0.zip"

# 3. 用 v20 覆盖 ~/.kodi/addons/pvr.iptvsimple/
unzip -qo /tmp/pvr-20.13.0.zip -d ~/.kodi/addons/

# 4. 通过 JSON-RPC 安全重启（或让用户手动重启）
curl -s -X POST -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"System.Reboot","id":1}' \
  http://127.0.0.1:9090/jsonrpc
```

**风险：** 二进制 ABI 可能不兼容（v20 的 .so 是给 Kodi 20 编译的），可能在 Kodi 21 上加载失败。

### 方案 B：Arch Archive（ChatGPT 推荐）

```bash
# 从 Arch Archive 找历史版本的 kodi + 匹配的 addon
# https://archive.archlinux.org/packages/k/kodi-addon-pvr-iptvsimple/
# 然后在 pacman.conf 中 pin 住旧版本
```

但电视盒子场景不建议降整个 Kodi（可能引入其他 regressions）。

### ✅ 方案 C：不用 PVR（ChatGPT 强烈推荐）

不要再用 PVR IPTV Simple。Kodi 21 上用 PVR 体系本身就是和架构较劲。

改用非 PVR 的视频插件：
- **`plugin.video.iptv`** — 最简单的 IPTV 视频插件，直接读 m3u，在"视频"菜单中播放
- **`plugin.video.simpleplayer`** — 轻量级视频播放器插件，不走 PVR
- 自己写 100 行 Python addon — 读 m3u 文件 → 生成频道列表，在视频菜单显示

**为什么更好：**
- 无 PVR Manager，不会有死锁
- 纯 Python，没有二进制 ABI 依赖
- Kodi 21 上稳定运行
- 调试简单

**安装方式：** Kodi → 设置 → 插件 → 从仓库安装 → 视频插件 → IPTV / Simpleplayer

## 正确操作 Kodi（不要 pkill）

**仅通过 JSON-RPC 安全操作（需要先启用 Web 服务器）：**

```bash
# 启用 webserver（一次配置）
sed -i 's|<setting id="services.webserver" default="true">false</setting>|<setting id="services.webserver" default="true">true</setting>|' \
  ~/.kodi/userdata/guisettings.xml

# 然后通过 JSON-RPC 操作（需要重启 Kodi 一次让配置生效）
curl -s -X POST -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"System.Reboot","id":1}' \
  http://127.0.0.1:9090/jsonrpc

# 查询 PVR 状态
curl -s -X POST -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"PVR.GetProperties","params":{"properties":["available","channels","isconnectedtoserver"]},"id":1}' \
  http://127.0.0.1:9090/jsonrpc
```

**绝对不要** `pkill -f kodi-standalone`。电视机前可能有人在看。

## 鉴别日志

```bash
grep -E "PVR|iptvsimple|channel|m3u" ~/.kodi/temp/kodi.log

# 正常：PVR Manager: Starting → PVR Manager: Started → Loaded X channels...
# 故障：PVR Manager: Starting（后面就没了）
```

## 另一个已知 bug：Timeshift 死锁 (#760)

除了"卡 Starting"问题，Kodi 21 + IPTV Simple 还有一个独立 bug：

### 症状
- Timeshift 开启时
- 暂停频道流，等 15+ 分钟
- 尝试快进 → **Kodi 完全冻结或崩溃**
- 日志无有效错误

### 根因
IPTV Simple 的 Timeshift 实现存在 mutex 死锁。
Ref: https://github.com/kodi-pvr/pvr.iptvsimple/issues/760

### 修复
在 IPTV Simple 设置中关闭 Timeshift（设置 → Live TV → 回放 → Timeshift → 关闭）。
之后 PVR 正常工作，只是不能暂停/回退直播。

## 用户偏好的 IPTV 源（优先级降序）

用户明确给过以下 GitHub 项目链接，表示它们经过研究值得尝试：
1. `github.com/cs3306/IPTV-Sources` — `data/output/iptv_collection.m3u`（8070 个国际频道，需过滤中文）
2. `github.com/best-fan/iptv-sources` — `cn_cctv.m3u8` / `cn_province.m3u8`（每日检测）
3. `github.com/hujingguang/ChinaIPTV` — 中国电视专用但 token 常过期
4. `github.com/vbskycn/iptv` — `tv/iptv4.txt`（CSV 格式需转 m3u，源稳定但每个频道 5 个源必须去重）

**约束：**
- 老人看电视用，稳定第一，不要常维护
- Kodi 中文界面已配好
- 不走代理（中国频道直连）
- 约 40-50 个频道足够（CCTV 全套 + 各省卫视）
