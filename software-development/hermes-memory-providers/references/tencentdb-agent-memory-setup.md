# TencentDB Agent Memory 插件安装与配置

腾讯云开源的四层记忆系统（L0→L3），作为 Hermes 插件与 Hindsight 共存。

## 架构

```
Hermes Agent (Python)
  └── memory_tencentdb plugin (hermes-plugin/memory/memory_tencentdb/)
        └── HTTP → TDAI Memory Gateway (Node.js TypeScript, :8420)
              └── SQLite + sqlite-vec (本地嵌入向量)
```

- **Hermes 插件**：Python 客户端，hooks: `on_memory_write` + `on_session_end`
- **Gateway**：Node.js 服务，处理 L1/L2/L3 提取、BM25 + 向量混合检索
- **LLM 需求**：Gateway 需要 LLM API 做记忆提取/用户画像（L1→L3 pipeline）

## 与 Hindsight 的共存关系

| 维度 | Hindsight | TencentDB Agent Memory |
|------|-----------|----------------------|
| 定位 | 跨会话情节记忆 | 任务内短期卸载 + 长期画像 |
| 接入方式 | memory provider | Hermes 插件（hooks） |
| 工具 | `hindsight_retain/recall/reflect` | `tdai_memory_search/conversation_search` |
| 存储 | 云端 API | 本地 SQLite |
| 冲突 | — | 无冲突，可同时启用 |

两个系统在不同层工作，Agent 根据场景选择合适的工具。

## 安装步骤

### 前置

- Node.js >= 22（Gateway 运行时）
- npm（依赖国内镜像：`--registry https://registry.npmmirror.com`）
- LLM API Key（用于 Gateway 的 L1/L2/L3 提取）

### 1. 克隆/安装包

```bash
# 方案 A：从 GitHub 克隆（推荐，中国网络走 ghproxy 或直连）
git clone https://github.com/TencentCloud/TencentDB-Agent-Memory.git ~/.memory-tencentdb/tdai-memory-openclaw-plugin

# 方案 B：npm 安装（注意国内网络走 npmmirror）
npm install @tencentdb-agent-memory/memory-tencentdb \
  --registry https://registry.npmmirror.com
```

### 2. 安装 npm 依赖

```bash
cd ~/.memory-tencentdb/tdai-memory-openclaw-plugin
npm install --production --registry https://registry.npmmirror.com
```

### 3. 链接 Hermes 插件

```bash
HERMES_PLUGIN_DIR=~/.hermes/hermes-agent/plugins/memory/memory_tencentdb
PLUGIN_SRC=~/.memory-tencentdb/tdai-memory-openclaw-plugin/hermes-plugin/memory/memory_tencentdb
ln -sf "$PLUGIN_SRC" "$HERMES_PLUGIN_DIR"
```

目录**必须**命名为 `memory_tencentdb`（下划线），不能用连字符。

### 4. 配置 Gateway

创建 `~/.memory-tencentdb/memory-tdai/tdai-gateway.json`：

```json
{
  "llm": {
    "apiKey": "sk-your-deepseek-key",
    "baseUrl": "https://api.deepseek.com/v1",
    "model": "deepseek-chat"
  }
}
```

也可以用环境变量覆盖：`TDAI_LLM_API_KEY`、`TDAI_LLM_BASE_URL`、`TDAI_LLM_MODEL`。

### 5. 启动 Gateway

```bash
cd ~/.memory-tencentdb/tdai-memory-openclaw-plugin
npx tsx src/gateway/server.ts &
```

默认监听 `127.0.0.1:8420`。验证：

```bash
curl http://localhost:8420/health
```

### 6. 配置 Hermes 启用插件

在 `~/.hermes/config.yaml` 中添加：

```yaml
memory:
  provider: memory_tencentdb   # 设为 memory_tencentdb 启用，留空则仅以 hooks 形式运行
```

**注意**：`memory.provider` 设为 `memory_tencentdb` 会**替换**当前 memory provider（如 Hindsight）。如果只想让 TencentDB 以 hooks 形式共存而不替换主 provider，将 `memory.provider` 留空（保持现有 Hindsight），插件仍然会捕获对话（通过 `on_memory_write`/`on_session_end` hooks）。

### 7. 验证

新 Hermes session 中会出现两个新工具：
- `tdai_memory_search` — 语义搜索记忆
- `tdai_conversation_search` — 搜索历史对话

## 国内网络避坑

- **Docker build 超时**：`Dockerfile.hermes` 从 Ubuntu 源码编译 Hermes + Node.js，build 需 10-20 分钟。在外面 （如代理不可用）超时是正常现象。回家直连即可。
- **npm install 慢**：npm 不走系统代理（macOS 的 HTTPS/SOCKS 代理），但 Docker 代理配置在 Docker Desktop 层面（`http.docker.internal:3128`）。`curl registry.npmmirror.com` 可达但大包下载可能因代理不稳定中断。加 `--registry` 指向国内镜像后通常能成功。
- **GitHub raw 文件可达**：`github.com` 在本网络环境（macOS 全局代理 127.0.0.1:10808）下 curl 返回空，但 `registry.npmmirror.com` 正常。此特征可作为网络诊断的快速判断。

## 文件结构

```
~/.memory-tencentdb/
├── tdai-memory-openclaw-plugin/     # 源码（npm package 解压目录）
│   ├── hermes-plugin/memory/memory_tencentdb/  # Hermes 插件（Python）
│   ├── src/gateway/                 # Gateway（Node.js TypeScript）
│   └── node_modules/                # npm 依赖（npm install 后生成）
└── memory-tdai/                     # 数据目录
    ├── tdai-gateway.json            # Gateway 配置（LLM key 等）
    └── ...                          # L0/L1/L2/L3 产物（自动生成）
```

## 已知限制

- Gateway 需要 LLM API 做记忆提取，纯本地无模型时不工作
- L1/L2/L3 pipeline 有 token 消耗（但相比全量上下文已缩减 61%）
- `memory.provider: memory_tencentdb` 会替换当前 memory provider，不能同时选两个 provider
- 安装时需要 Node.js 编译 tsx，容器内若缺 Node.js 需额外安装

## 回滚

```bash
# 1. 关 Gateway
pkill -f "tsx src/gateway/server.ts"

# 2. 删插件 symlink
rm ~/.hermes/hermes-agent/plugins/memory/memory_tencentdb

# 3. 恢复 memory.provider
hermes config set memory.provider hindsight

# 4. 删数据（可选）
rm -rf ~/.memory-tencentdb
```
