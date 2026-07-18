# 讯飞 xunfei 视觉能力

## 概述

讯飞（xunfei）作为 OpenAI 兼容的 inference provider，其 `xopqwen36v35b` 模型**支持图片输入**，可用于图片理解/视觉问答。不需要切换默认模型——通过 `hermes_tools` 的 `terminal` 或 `execute_code` 直接调用其 API 即可。

## 配置信息

| 项 | 值 |
|---|---|
| 模型 | `xopqwen36v35b`（基于 Qwen3.6 35B） |
| 端点 | `https://maas-api.cn-huabei-1.xf-yun.com/v2/chat/completions` |
| 鉴权 | `Bearer {APPID}:{APISECRET}`（组合 key，中间冒号分隔） |
| API 模式 | OpenAI-compatible `chat_completions` |

## 调用格式

标准 OpenAI 图片输入格式，支持 `image_url`（base64）：

```json
{
  "model": "xopqwen36v35b",
  "messages": [{
    "role": "user",
    "content": [
      {"type": "text", "text": "描述这张图片"},
      {"type": "image_url", "image_url": {
        "url": "data:image/jpeg;base64,<base64编码>"
      }}
    ]
  }],
  "max_tokens": 512
}
```

## Python 调用示例

```python
import json, urllib.request, base64

api_key = "APPID:APISECRET"  # 从 config.yaml providers.xunfei.api_key 获取

with open('/path/to/image.jpg', 'rb') as f:
    b64 = base64.b64encode(f.read()).decode()

data = {
    'model': 'xopqwen36v35b',
    'messages': [{
        'role': 'user',
        'content': [
            {'type': 'text', 'text': '描述这张图片'},
            {'type': 'image_url', 'image_url': {
                'url': f'data:image/jpeg;base64,{b64}'
            }}
        ]
    }],
    'max_tokens': 256
}

req = urllib.request.Request(
    'https://maas-api.cn-huabei-1.xf-yun.com/v2/chat/completions',
    data=json.dumps(data).encode(),
    headers={
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
)
resp = urllib.request.urlopen(req, timeout=30)
result = json.loads(resp.read())
print(result['choices'][0]['message']['content'])
```

## 已知限制

| 限制 | 详情 |
|------|------|
| **图片大小** | base64 后建议 < 1MB 总 payload（实测 165KB jpg 正常，7.8MB png 导致 Broken pipe） |
| **分辨率** | 建议缩放至 ≤ 1024px 宽（`sips -Z 1024 input.jpg --out output.jpg`） |
| **格式** | jpg / png 均支持 |
| **响应速度** | 约 10-30 秒（取决于图片大小和队列） |
| **可用性** | 当前 API key 有权限，free/paid 状态取决于 key 的类型 |

## 相关资源

- 讯飞图片理解 WebSocket API: `https://www.xfyun.cn/doc/spark/ImageUnderstanding.html`
- 当前配置路径: `config.yaml` → `providers.xunfei`
- API Key 位置: `config.yaml` → `providers.xunfei.api_key`

## 跨 agent 共享 xunfei 视觉能力

当需要给另一个 Hermes agent（如金同学，运行在 Docker 中）也加上 xunfei 视觉能力时：

### 最佳路径

在宿主机通过 `docker exec` 操作目标容器的 config，而不是SSH/远程。

### 实操记录（给金同学配 xunfei）

```
# 背景：hermes-minimaxlab Docker 容器，默认 model: minimax-m3 via nvidia
# 目标：添加 xunfei provider 支持 vision，不改默认 model

# 1. 查看当前 config
docker exec hermes-minimaxlab cat /opt/data/config.yaml

# 2. 备份
docker exec hermes-minimaxlab cp /opt/data/config.yaml /opt/data/config.yaml.bak

# 3. 添加 xunfei provider 块（空 providers: {} → 替换）
docker exec hermes-minimaxlab sh -c '
sed -i "s/providers: {}/providers:\n  xunfei:\n    model: xopqwen36v35b\n    base_url: https:\/\/maas-api.cn-huabei-1.xf-yun.com\/v2\n    api_key: APPID:APISECRET\n    timeout: 300\n    max_tokens: 16384/" /opt/data/config.yaml
'

# 4. 重启容器
docker restart hermes-minimaxlab
```

### 他如何调用

其他 agent 切换使用 xunfei 模型有两种方式（取决于 Hermes 版本支持）：

- **临时切换**：在对话中明确指定 "用 xunfei 模型看这张图"
- **配置级切换**：`hermes model set xunfei`（如果支持）

### 注意事项

- 容器内 API key 直接写在 `config.yaml` 中（和土的主机配置方式一致），无需额外 .env
- 容器重启后需确认状态：`docker ps --filter name=<容器名> --format "{{.Names}} {{.Status}}"` → 应为"Up"
- 默认 model 不变，xunfei 作为附加 provider 供按需调用

## 与其他 provider 对比

| Provider | 免费视觉模型 | 调用方式 | 状态 |
|----------|-------------|---------|------|
| xunfei (xopqwen36v35b) | 有权限 | OpenAI 兼容 HTTP | ✅ **实测可用** |
| OpenCode Zen (mimo-v2.5-free) | 理论上免费 | OpenAI 兼容 HTTP | ❌ 403 (key 无权限) |
| OpenCode Zen (qwen3.6-plus-free) | 预览期免费 | OpenAI 兼容 HTTP | ❌ 403 (key 无权限) |
