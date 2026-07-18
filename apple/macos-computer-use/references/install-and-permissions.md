# cua-driver 安装与权限授权

## 安装

```bash
hermes computer-use install
```

验证安装：
```bash
cua-driver --version
cua-driver list-tools | head -5
```

## macOS 权限授权

安装后必须授予两项权限：

### 方式 1：自动授权（推荐）

```bash
cua-driver permissions grant
```
会弹出 CuaDriver 窗口请求权限，去系统设置里打勾确认。注意：这个命令可能会因等待弹窗确认而超时，但实际上权限可能已经部分授予了。

### 方式 2：手动授权

去 **系统设置 → 隐私与安全性**：
1. **辅助功能（Accessibility）** → 添加 `/Applications/CuaDriver.app` 并勾选
2. **屏幕录制（Screen Recording）** → 添加并勾选同一个 App

### 检查权限状态

```bash
# 先启动 daemon（否则 status 报告的是 terminal 的授权状态）
open -n -g -a CuaDriver --args serve
sleep 2
cua-driver permissions status
```

### 故障排除：Accessibility 授权失败或卡住

如果 Screen Recording 已授权但 Accessibility 显示未授权：

```bash
# 1. 先重置 TCC 记录
sudo tccutil reset Accessibility com.trycua.driver

# 2. 重新发起授权
cua-driver permissions grant
```

### 故障排除：Screen Recording 也未授权

```bash
sudo tccutil reset Accessibility com.trycua.driver
sudo tccutil reset ScreenCapture com.trycua.driver
cua-driver permissions grant
```

## 验证全部就绪

```bash
open -n -g -a CuaDriver --args serve && sleep 2 && cua-driver permissions status
```

期望输出：
```
Accessibility:    ✅ granted
Screen Recording: ✅ granted
```

## 权限数据库直接查看（需要 root）

```bash
sudo sqlite3 /Library/Application\ Support/com.apple.TCC/TCC.db \
  "SELECT client, auth_value FROM access WHERE service='kTCCServiceAccessibility' AND client LIKE '%Cua%';"
```

- `auth_value=0` = 拒绝/未授权
- `auth_value=1` = 已授权
- `auth_value=2` = 已授权（明确允许）