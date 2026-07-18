# Hermes Gateway API Server + Browser Extension 设置

## 用途

Hermes Gateway 的 API Server 让 Chrome/Edge 侧边栏扩展（hermes-browser-extension）直接连到本地或远程 Hermes runtime。扩展读取当前网页内容、选中文字、标签页，通过 Gateway 发送到 Hermes 处理。

**和 Telegram gateway 的关系：** 同一进程。API Server 监听另一个端口(8642)，CORS 控制浏览器来源，不干扰 Telegram bot 轮询和消息收发。

## 快速安装步骤

### 1. 启用 API Server

在 `~/.hermes/.env` 添加：

```bash
API_SERVER_ENABLED=true
API_SERVER_HOST=127.0.0.1
API_SERVER_PORT=8642
API_SERVER_KEY=your-secret-key-here
# 扩展 ID 装好后再填
API_SERVER_CORS_ORIGINS=chrome-extension://
```

### 2. 重启 Gateway

```bash
hermes gateway run --replace
```

验证端口：

```bash
curl -s http://127.0.0.1:8642/health
# 预期：{"status": "ok", "platform": "hermes-agent", "version": "X.X.X"}
```

### 3. 构建浏览器扩展

```bash
git clone https://github.com/abundantbeing/hermes-browser-extension.git
cd hermes-browser-extension
npm install
npm run build
# dist/ 目录即为 Chrome 可加载的未打包扩展
```

需要 Node.js >= 20 和 npm。

### 4. 加载到 Chrome

1. 打开 `chrome://extensions/`
2. 右上角开启 **Developer mode**
3. 点 **Load unpacked** → 选择 `dist/` 目录
4. 装好后复制 **扩展 ID**（卡片下面的长串字母）

**文件路径问题：** macOS 的 `/tmp/` 在 Chrome 文件选择器不可见。把 `dist/` 拷贝到桌面再加载：

```bash
cp -r /tmp/hermes-browser-extension/dist ~/Desktop/hermes-extension
```

或者在文件选择器中按 `Cmd+Shift+G`，输入 `/private/tmp/hermes-browser-extension/dist`。

### 5. 配置 CORS + 连接

更新 .env 中的 CORS origins 为实际扩展 ID：

```bash
API_SERVER_CORS_ORIGINS=chrome-extension://mhgmkbnoeiaondjkiejblhbbhghcmpea
```

重启 Gateway。然后在 Chrome 右上角扩展图标 → 打开侧边栏 → Connect to Hermes：

| 字段 | 值 |
|---|---|
| Gateway URL | `http://127.0.0.1:8642` |
| API Key | （.env 中设置的 API_SERVER_KEY） |
| Setup 模式 | **Local gateway** |

点 Test connection，成功后保存。

### 6. 使用

在任意网页打开侧边栏，输入指令如 `Summarize this page in one sentence.` 或分析当前可见内容。

## 注意事项

- **扩展只读：** 当前版本仅读取页面上下文，不能代点网页、填表或操作终端
- **远程模式风险：** API Server 裸暴露在公网会让任意能访问端口的人获得 Hermes 工具权限。远程模式必须放在 HTTPS 反向代理或受信网络后面
- **页面内容可达性：** Chrome 的 WebView 内容不一定通过 macOS Accessibility API 暴露。扩展通过 content_script 读取 DOM，不受此限制
- **终端交互限制：** 扩展无法直接向页面终端注入命令。要操作远程终端，仍需要用户手动粘贴，或通过 cua-driver 等桌面自动化工具

## 故障排查

| 现象 | 原因 | 修复 |
|---|---|---|
| `curl :8642/health` 超时 | API Server 未启动 | 确认 `.env` 配置正确，`hermes gateway run --replace` |
| 扩展 test connection 返回 403 | CORS 来源不匹配 | 更新 `.env` 的 `API_SERVER_CORS_ORIGINS` 为正确的扩展 ID，重启 gateway |
| 扩展能连但读不到页面 | content_script 未注入（企业页面限制） | 确认页面不是 chrome:// 或 about: 协议，检查扩展权限 |
| build 后扩展不更新 | Chrome 缓存旧版本 | 在 `chrome://extensions/` 点卡片上的 Reload |

## 参考

- 扩展仓库：https://github.com/abundantbeing/hermes-browser-extension
- API Server 文档：https://hermes-agent.nousresearch.com/docs/user-guide/features/api-server
- Hermes Browser 自动化（browser_inspect/browser_style）：https://hermes-agent.nousresearch.com/docs/user-guide/features/browser
