# Key Pool Audit Patterns

## Scanning Locations

Keys are typically scattered across these locations:

| Location | Typical content | How to scan |
|----------|---------------|-------------|
| `~/.hermes/config.yaml` | Main provider keys | `grep 'api_key\|base_url' ~/.hermes/config.yaml` |
| `~/.hermes-docker/{name}/.env` | Docker container env | `cat ~/.hermes-docker/{name}/.env` |
| `~/.hermes-docker/{name}/config.yaml` | Container provider config | `grep 'api_key' ~/.hermes-docker/{name}/config.yaml` |
| `~/.hermes-memory/.env` | NVIDIA proxy etc. | `cat ~/.hermes-memory/.env` |
| Provider-specific yamls | Custom provider keys | `ls ~/.hermes-docker/{name}/providers/` |

## Known Key Prefix Patterns

| Prefix | Provider | Notes |
|--------|----------|-------|
| `sk-`... | OpenAI-compatible (Agnes, generic) | Standard OpenAI format |
| `nvapi-`... | NVIDIA | For integrate.api.nvidia.com |
| `om-`... | OpenModel | api.openmodel.ai |
| `fe_oa_`... | FreeModel | api.freemodel.dev |
| `wrk-`... | WeRead | WeChat Read API |
| `hsk_`... | Hindsight | Memory server Bearer token |
| `074bcc`... | Xunfei | Custom format (id:key) |
| DeepSeek key | DeepSeek | OpenAI compatible |
| Firecrawl key | Firecrawl | API key for web scraping |
| Telegram token | Bot API | Numeric:alphanumeric format |

## Categorization Template

```
来源                           数量    协议          状态
NVIDIA (integrate.api.nvidia.com)  2   OpenAI 兼容  高频, 走SOCKS5, 会429
Agnes AI (apihub.agnes-ai.com)     2   OpenAI 兼容  高频(主模型)
OpenCode Zen (opencode.ai/zen)     0*  OpenAI 兼容  免费层无key, 偶尔429
Xunfei (maas-api.cn-huabei-1)      1   自定义格式    备用fallback
OpenModel (api.openmodel.ai)       2   OpenAI 兼容  fallback用
FreeModel (api.freemodel.dev)      1   OpenAI 兼容  fallback用
DeepSeek                           1   OpenAI 兼容  在.env中用途不明
Firecrawl                          1   API key      网页抓取
WeRead (微信读书)                   1   专用格式
Hindsight                          1   Bearer token 记忆服务认证
Telegram Bot Token                 2   专用格式
```

## Key Usage Frequency Classification

- **高频**: 主模型每天数百次调用
- **中频**: 主模型备选/fallback，每天数十次
- **低频**: 仅fallback时触发，每周几次
- **备用**: 已配置但很少或从未使用

## Key Management Issues to Flag

1. **分散管理**: keys scattered across multiple files with no inventory
2. **No expiration tracking**: no way to know which keys are about to expire
3. **No failure detection**: 429s and 401s appear in logs but no alert
4. **Shared across containers**: same key used by multiple containers = shared rate limits
5. **No centralized gateway**: no New API / One API layer for routing, quotas, or statistics
6. **Hardcoded proxies**: NVIDIA keys behind SOCKS5 (Xray) is a second-order failure point
