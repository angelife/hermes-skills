# ylytdeng/wechat-decrypt 参考

## 项目信息
- 仓库：https://github.com/ylytdeng/wechat-decrypt
- Stars: 4.5k, Forks: 2.3k, Commits: 138
- 语言：Python 93% + C 6%
- 状态：活跃维护

## 核心能力
| 功能 | 文件 | 说明 |
|------|------|------|
| macOS 密钥扫描 | `find_all_keys_macos.c` | Mach VM API，需 sudo，支持 4.x |
| 数据库解密 | `decrypt_db.py` | 用密钥解密所有 SQLCipher DB |
| 消息导出 | `export_all_chats.py` / `export_chat.py` | 导出为可读格式 |
| 朋友圈解密 | `decrypt_sns.py` / `export_sns.py` | 支持朋友圈数据 |
| 图片解密 | `find_image_key_macos.py` | 提取图片加密参数 |
| 实时监控 | `monitor.py` / `monitor_web.py` | Web UI 监控新消息 |
| MCP Server | `mcp_server.py` | 支持 MCP 协议接入 |

## macOS 密钥扫描器编译
```bash
cc -O2 -o find_all_keys_macos find_all_keys_macos.c -framework Foundation
sudo ./find_all_keys_macos [pid]  # 输出到 all_keys.json
```

## 版本兼容性
- 已验证可用：v4.0.6（可扫码登录、可提取密钥、无封号）
- 当前目标：v4.1.10.53（2025-06-22 发布，暂未验证效果）
- 封号风险：Issue #140 用户报告 ≥v4.1 被封（推测反外挂检测在新版更严）
- 太老版本：3.8.x 服务端拒绝登录
- 降级来源：zsbai/wechat-versions (GitHub)

## macOS DMG 下载陷阱
腾讯 CDN 返回的 `.dmg` 文件实际上是 **XZ 压缩**（magic: `fd37 7a58`）：
```bash
# ❌ brew unxz 报 corrupt
brew unxz WeChatMac-4.0.6.dmg  # → "Compressed data is corrupt"

# ✅ Python lzma 能正常解压
python3 -c "
import lzma, shutil
with lzma.LZMAFile('WeChatMac-4.0.6.dmg') as fin:
    with open('WeChatMac-4.0.6.dmg_raw', 'wb') as fout:
        shutil.copyfileobj(fin, fout, length=16*1024*1024)
"
# 解压后 ~1.3GB，`hdiutil convert` 后挂载
hdiutil convert -format UDZO -o /tmp/WeChat_converted.dmg /tmp/WeChat._raw.dmg
hdiutil attach /tmp/WeChat_converted.dmg
```
