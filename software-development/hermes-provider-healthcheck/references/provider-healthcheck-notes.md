# Hermes Provider Healthcheck Reference Notes

## Env Loading Contract

- `hermes_cli.config.get_env_value_prefer_dotenv(var)` 优先读取 `~/.hermes/.env`
- `load_config()` 会递归展开 `config.yaml` 里的 `${VAR}`，所以健康检查必须走运行期配置，而不是 raw file
- 实际 HERMES_HOME 由 `hermes_constants.get_hermes_home()` 决定；macOS 上通常是 `/Users/macos/.hermes`

## Built-in Auth Chains To Exclude From Provider Checks（新增）

Hermes 内部有多条自动刷新鉴权链，不能混入外部 provider 自检：
- Nous / Vertex / Anthropic / Copilot / xAI / Codex
- 典型信号：`agent/conversation_loop.py` 中 `🔐 ... key refreshed after 401. Retrying request...`
- 本地运行时凭证文件：`~/.hermes/shared/nous_auth.json`、`~/.hermes/auth.json`
- 这些密钥的治理单独记录，不进入 `hermes providers` 白名单结果

## Internal Config Fields That Are Not Providers（新增）

`providers:` 区块下可能混入 Hermes 内部工具配置，例如：
- `camofox`
- `cloud_provider`
- `use_gateway`
- 健康检查必须使用显式白名单，禁止按结构特征猜测

## Provider Entry Resolution（新增）

部分 provider 不在 `providers:` 下，而在 `image_gen.<name>` 下：
- 读取顺序：`providers.<name>` → `image_gen.<name>`
- 若来自 `image_gen.<name>`，必须继承顶层 `image_gen.base_url` 和 `image_gen.model`
- 当前已知例子：`agnes` 对应 `image_gen.agnes`

## Response Code Classification Pitfall（新增）

`requests.get()` 对 401/403 返回正常响应，不会抛 `HTTPError`。
如果代码只靠异常分支判断 `AUTH_FAIL`，会把 403 错标成 `UNKNOWN`。
正确做法是显式按状态码分类：
```python
if resp.status_code == 200:
    status = OK
elif resp.status_code in (401, 403):
    status = AUTH_FAIL
else:
    status = UNKNOWN
```

## Env Var Mapping Rule（新增）

必须维护显式 `_ENV_VAR_MAP`，禁止机械做 `UPPER(provider.replace('-', '_')) + '_API_KEY'`。
真实映射以 config.yaml 里 `${VAR}` 引用的 env 文件名为准。

当前映射（由白名单推导）：
- `opencode-zen` -> `OPENCODE_ZEN_API_KEY`
- `opencode-zen-free` -> `CLOUDFLARE_API_KEY`
- `nvidia-nim` -> `NVIDIA_API_KEY`
- `zhihu` -> `ZHIHU_API_KEY`
- `xunfei` -> `XUNFEI_API_KEY`
- `freellmapi` -> `FREELLMAPI_API_KEY`
- `agnes` -> `AGNES_API_KEY`

## Plaintext Cleanup Order

做 provider-check 前若发现明文 api_key，优先清理：
1. `xunfei`
2. `opencode-zen-free`
3. `zhihu`
4. `freellmapi`

清理后立即用 `grep -nE 'api_key:' ~/.hermes/config.yaml` 核对。

## Provider 探活注意事项

- 先打印 provider 名 + base_url + key 前缀，确认有可检查项后再发请求
- 全量检查无 stdout 时，先 debug entries list，不要盲目重试

## Hermes 配置读取陷阱（已发现）

1. `~/.hermes/config.yaml` 文本已改成 `${VAR}`，但 `load_config()` 仍可能返回明文
   - 原因是 Hermes 内部可能从默认配置、安装包 config、或 profile bridge 合并了隐藏配置
   - provider health check 里**必须忽略 config 里的 `api_key` 字段**，强制从 `.env` 解析
2. provider name 到 env var 不能机械做 `UPPER("-"_to"_") + "_API_KEY"`
   - 真实依赖：/provider key source 在 config yaml 引用/env 文件（严禁不做记录就直接使用）
   - 若 provider 的 api_key 来自另一 provider 的 config reference，不能捏造 env var
   - 不要机械做 `UPPER("-"_to"_")`；必须从 provider YAML 里真实引用的 env 名称取值
3. 不要求 Hermes 配置完全消除明文才做健康检查
   - 如果 `config.yaml` 仍残留明文字段，但 healthcheck 子命令能独立从 `.env` 取 key，仍可继续端侧验证

## xunfei 探活结果

- base_url: `https://maas-api.cn-huabei-1.xf-yun.com/v2`
- GET `/v1/models` 返回 403
- 讯飞 Dify/MaaS 的 `/v1/models` 不一定返回 200，只能说明按 OpenAI 兼容路径验证行不通
- 最终判断要回到“最小真实调用”或官方文档确认更稳妥

## zhihu 探活结果

- base_url: `https://developer.zhihu.com`
- 该地址更像开放平台门户，不像 OpenAI-compatible inference endpoint
- `extra_headers` 里有模板元字符，不能直接当作探活地址
- 仅 `/v1/models` 或 `/v1/chat/completions` 都不能直接推断 key 状态

## 自检输出要求

- `--provider x` 在探活失败/404/不支持时可能无 stdout，必须显式要求代码 retain fallback result
- 全量 7 provider 检查必须全部列出；缺省不要只给通过项

## 低风险运行时凭证文件（新增）

- `~/.hermes/shared/nous_auth.json`
- `~/.hermes/auth.json`
- `~/.hermes/google_client_secret.json`
- 只做权限收紧和位置记录，不把内容混入 provider 自检结果

## 证据归属与单次复测报告规则

- **禁止跨 provider 串证**：一类 provider 的失败响应不能作为另一类 provider 的失效依据。
- **禁止把“探针方法错误”当成“鉴权失败”**：`405/404` 只说明探活方式不适用，不是 key 失效。
- **单次独立复测只报告事实**：输出 `OK / AUTH_FAIL / 服务未运行 / 其他`，明确写出请求方法、状态码、响应摘要；**不要附带“建议删除/保留”**。
- **删除/保留结论必须来自稳定失败记录**：单次结果不足以作为删除依据，必须基于多次独立复测后由用户决定。