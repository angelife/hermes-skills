# WeChat 版本兼容性 — 关键 Issue 记录

## Issue #96 — 4.1+ 密钥机制变更（根本原因）
https://github.com/ylytdeng/wechat-decrypt/issues/96

**结论：** 4.1+ 改用 passphrase + PBKDF2-SHA512，不再缓存 raw key
```
enc_key = PBKDF2-SHA512(passphrase, db_salt, iterations=256000, dklen=32)
```
**落地工具：** https://github.com/TANGandXUE/wcdb-key-tool

## Issue #140 — 内存扫描被封号
https://github.com/ylytdeng/wechat-decrypt/issues/140

**结论：** 用户用内存扫描工具被微信检测为"外挂"，封号
**注意版本：** 未明确具体版本号，推测是 ≥4.1.x 高版本

## Issue #143 — macOS 4.1.10 扫不到密钥
https://github.com/ylytdeng/wechat-decrypt/issues/143

**环境：** macOS Intel, WeChat 4.1.10.80, 已 codesign
**现象：** 17 个 DB 的 salt 都读到了，内存扫描 0 keys
**结论：** 4.1.10 改了密钥存储格式，现有扫描器不匹配

## Issue #152 — Windows 4.1.10.53 扫不到密钥
https://github.com/ylytdeng/wechat-decrypt/issues/152

**现象：** 图片密钥可提取，DB 密钥 0/38 salts matched
**结论：** 跨平台问题，4.1.10 全改了密钥格式

## 可破解版本
| 版本 | 状态 | 获取方式 |
|------|------|---------|
| v4.0.6 | ✅ 已验证，内存扫描可行 | zsbai/wechat-versions tag v4.0.6_20250723 |
| v4.0.3.80 | ✅ 社区验证可行 | zsbai/wechat-versions tag v4.0.3.80 |
| 4.1.0-4.1.9 | ⚠️ 需 LLDB + PBKDF2 | zsbai/wechat-versions |
