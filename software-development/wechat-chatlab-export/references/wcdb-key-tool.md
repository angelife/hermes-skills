# wcdb-key-tool 参考

## 项目信息
- 仓库：https://github.com/TANGandXUE/wcdb-key-tool
- 用途：WeChat 4.1+ passphrase 提取 + PBKDF2 派生
- 平台：Linux / macOS / Windows
- macOS 文件：`wcdb_key_tool_macos.py`
- 依赖：Python 3.10+, LLDB（Xcode CLT），零第三方 pip 包

## 核心原理

WeChat 4.1+ 不再在进程内存中缓存明文密钥，改为：

```
内存中保留: passphrase（32 字节）
派生逻辑: enc_key = PBKDF2-SHA512(passphrase, db_salt, iterations=256000, dklen=32)
```

来源：Issue #96 (ylytdeng/wechat-decrypt)

## macOS 操作

### 首次提取（需退出重登）
```bash
sudo codesign --force --deep --sign - /Applications/WeChat.app
open /Applications/WeChat.app
sudo python3 wcdb_key_tool_macos.py extract --decrypt
```
等待提示 → 微信设置 → 退出登录 → 重新扫码登录

### 后续（缓存在 ~/.wcdb-key-tool/wechat-passphrase.json）
```bash
sudo python3 wcdb_key_tool_macos.py decrypt
```

## macOS SIP 注意事项

- `task_for_pid` 在 SIP 开启时不可用（`kr=5`）
- 脚本的 `_scan_memory_raw_key` 会失败并抛出 `SignatureInvalidError`
- **脚本有 bug**：抛出后直接 `sys.exit(1)`，不会走到 LLDB 路径
- **修正方法**：注释掉 `SignatureInvalidError` 的处理逻辑，直接跳到 LLDB
- LLDB attach 虽不需要 task_for_pid，但仍需 root

## 版本兼容性

| 版本 | 方法 | 验证状态 |
|------|------|---------|
| v4.0.6 | 内存扫描 raw key | ✅ Linux/macOS 均可用 |
| v4.1.0 ~ v4.1.9 | LLDB + PBKDF2 | ✅ 文档声称已验证 |
| ≥v4.1.10 | LLDB + PBKDF2 | ⚠️ 有新封号报告 (Issue #140) |

## 封号风险评估

wcdb-key-tool 作者声称不会封号：
- 只读一次寄存器值（<1秒）
- 不修改程序行为
- 不接触网络通信
- LLDB 是标准调试工具

对比：Frida/MinHook 注入方式被封风险更高。
