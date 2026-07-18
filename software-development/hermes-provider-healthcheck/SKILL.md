---
name: hermes-provider-healthcheck
description: "Hermes provider 健康检查与可用性验证。覆盖 CLI 子命令复用、env 渲染一致性检查、并发探活、状态分类、密钥脱敏输出，以及非 OpenAI 兼容 provider 的特殊处理。"
tags:
  - hermes
  - provider
  - healthcheck
  - env-vars
  - secrets
  - config
---

# Hermes Provider Healthcheck

## 触发条件

以下任一情况触发本技能：
- 需要验证 `config.yaml` 已配置 provider 的 `api_key` / endpoint 是否真实可用
- 刚完成 `.env` 与 `config.yaml` 单一数据源归整，要确认 `${VAR}` 被正确加载且非空
- 需要判断 provider 是鉴权失败、网络/地址异常、非 OpenAI 兼容，还是响应正常

## 强制前置检查

开始 provider check 前，必须先确认：
1. `~/.hermes/.env` 与 `~/.hermes/config.yaml` 无明文 `api_key` 残留
2. 已运行：
```bash
comm -23 \
  <(grep -oE '\$\{[A-Z0-9_]+\}' ~/.hermes/config.yaml | tr -d '${}' | sort -u) \
  <(cut -d '=' -f1 ~/.hermes/.env | sort -u)
```
**空输出** 才说明变量齐全。

## 外部 key 文件落地规则
- 若存在外部 key 清单（如 `key.txt`），**禁止先追加一堆临时变量名**再让用户确认归属
- key 写入 `.env` 之前，必须先拿到**权威映射表**：`provider -> line number/value`
- 若用户未直接给出映射，不要猜；可要求一行一 provider 的明确对应关系
- 只能按映射覆盖/写入命名规范的变量；无法归属的 key，要么继续保留待确认，要么在用户确认后删除，不由脚本自行打散成临时变量
- 映射完成后必须先选出**一个 key** 写入，并只对这一把 key 做最小 probe；不要批量写多个未验证 key 进 `.env`

## 标配 fallback 模式（类级复用）
当同一个 endpoint 有多把 key，需做 provider 级容灾时，标准做法是：
1. `.env` 里用命名变量分开放：`OPENCODE_ZEN_API_KEY_PRIMARY`、`OPENCODE_ZEN_API_KEY_BACKUP` 等
2. `providers:` 下对应建 alias provider：`opencode-zen-primary`、`opencode-zen-backup`
3. `fallback_providers:` 列表按优先级排列，全是 provider -> model 对
4. Hermes 在 primary 故障时自动切换，新消息时自动回切

若 Hermes `.env` 只支持单值变量，同 provider 的 key 轮换只能靠 alias provider 实现，不是靠 credentialpool。不要试图给同一 provider 配多把 key 指望自动轮换。

## 401/403 定位顺序
- 先确认 `.env` 里目标变量是否为空；空值 = 缺 key，不是 key 坏了
- 若 `.env` 为空但实际有 key 清单，按权威映射把 ONE key 写回 `.env`，再做最小 probe
- **某些 provider 对请求头做隐性风控**：一样 key、一样 endpoint，不同 `User-Agent` 可能返回 200 vs 403。遇到“多个 key 都 403 但用户坚信 key 正常”时，用 `User-Agent: curl/<version>` 复测一次，不要把 key 误判为失效
- 不要在没有 probe 前把 401 归因给 Hermes config、provider 路径、或网络抖动
- 若最小 probe 仍返回 401/403，再进入 AUTH_FAIL 分支处理

## 用户明确删除规则
- 当用户说“测试失败就删”，执行方应对 AUTH_FAIL/不可用 provider **直接执行删除**，不再二次确认
- 删除范围必须覆盖：白名单、`config.yaml` 段、引用点、`.env` 对应变量
- 删除后立即重跑自检，确认结果中不再出现该 provider，避免 stale 输出
- 若用户已表述“再说一遍，我自己手动澄清配置规范”（实际含义：他现场看配置，之后你再执行），此时仍必须遵循“只报告事实+事实并入证据”的方式；若用户要求“pings，ping一个测一个，测不准就 dump”，应把验证步骤从“先给结论再执行”改为“有证据再给结论”。**不询问“是否要我测”，直接做。**

## 实现/调用原则

1. 优先复用现有实现，不要新写解析器
   - 读取 provider 配置优先走 `hermes_cli.config.load_config()`
   - 读取 `.env` 优先走 `get_env_value_prefer_dotenv()`；只验证 key 非空，不打印原文
2. `load_config()` 不要盲信，同一文件不同调用路径可能不同
   - 本次经验：`~/.hermes/config.yaml` 文件内容已改为 `${VAR}`，但 `load_config()` 仍返回明文
   - 说明 Hermes 内部可能从默认配置、安装包 config、或 profile bridge 合并了隐藏配置
   - provider health check 里**必须忽略 config 里的 `api_key` 字段**，强制从 env 解析
   - 对于 provider name，不要机械做 `UPPER("-"_to"_") + "_API_KEY"`；必须维护显式 `_ENV_VAR_MAP`
3. 内部 Hermes 鉴权链必须排除出 provider 自检范围（新增）
   - Hermes 内置的 Nous/Vertex/Anthropic/Copilot/xAI/Codex 鉴权链属于运行时内部集成
   - `agent/conversation_loop.py` 中的 `🔐 ... key refreshed after 401. Retrying request...` 是内部自动刷新，不是用户配置的 provider
   - 对应本地凭证文件：`~/.hermes/shared/nous_auth.json`、`~/.hermes/auth.json`
   - **provider 自检只做用户配置的 provider，不把这些内部链当外部 provider 遍历**
4. provider 枚举必须显式白名单，不要按结构猜（新增）
   - `providers:` 区块下可能混入内部工具字段（如 `camofox`），白名单是唯一可靠方式
   - 白名单只包含盘点过的 provider；新增用户可见 provider 时手动加一行，防止结构字段误判
   - 遵循“测试失败就删”：AUTH_FAIL 的 provider 要立即从白名单、`config.yaml`、`.env` 三处移除，不留无效段
   - 白名单来源不限于 `providers:`：还需要覆盖 `image_gen.<name>` 这类变体型
   - 删除后立刻重跑自检，确认 stale 输出被清掉
5. provider 条目来源不限于 `providers:`（新增）
   - `agnes` 实际存储在 `config.yaml` 的 `image_gen.agnes`，不在 `providers:` 下
   - 对于 `image_gen.<name>` 类的 provider，必须从顶层继承 `base_url` 和 `model` 字段
   - 读取顺序：`providers.<name>` → `image_gen.<name>` → 继承顶层字段
6. 启用健康检查前，先用可观测代码确认 provider 列表和实际值
   - 先打印 provider 名 + base_url + key 前缀，确认有可检查项后再发请求
   - 如果一轮全量检查“无 stdout”，先 debug entries list，不要直接重试全量
7. 401/403 分类必须基于响应码，不要依赖异常（新增）
   - `requests.get()` 对 401/403 返回正常响应，不会抛 `HTTPError`
   - 分类代码里必须显式写 `if resp.status_code == 200: OK elif resp.status_code in (401, 403): AUTH_FAIL else: UNKNOWN`
8. `/v1/models` 不是所有 provider 都通用
   - 遇到 404 后，退化到最小真实调用：`POST /v1/chat/completions`，`max_tokens=1`
   - 如果该 provider 没有更轻量接口，**不要硬套 OpenAI 路径**
   - 非 OpenAI 兼容 provider 退化成最小调用时，必须在报告里写明 `check_method`，避免用户误以为做了计费对话
9. 默认并发度 = provider 数量，不做无意义限流
   - 仅在“已知该厂商有严格速率限制/风控”时才降并发
10. 超时独立控制，单 provider 超时不影响其余 provider
11. ENDPOINT_ERROR 前先做 base_url re-check
    - label 前确认 base_url 理论上是否指向 inference endpoint；若只是门户站/平台页，标成 ENDPOINT_ERROR 前要注明地址不像 inference endpoint
12. 不要求 Hermes 配置完全消除明文才做健康检查
    - 如果 config.yaml 仍残留明文字段，但 health check 子命令能独立从 .env 取 key，仍然允许继续端侧验证
    - 但最终仍必须枚举 provider 名的 env var 依据，而不是盲目拼接

## 证据隔离与探针正确性（新增）
- **禁止跨 provider 串证**：一类 provider 的失败响应不能作为另一类 provider 的失效依据。按 documented `base_url` 归属判断；不要把 `localhost:3001` 的失败算进 Cloudflare provider，也不把 Cloudflare 的失败算进本地代理 provider。
- **禁止把“ probe 方法错误”当成“鉴权失败”**：如果 provider 的 `/v1/models` 返回 405/404/不支持，这只是探活方法不适用，不是 key 坏了。
- **禁止把“页面可访问”当成“API 鉴权通过”**：playground/管理页返回 200 只说明前端服务在线，不代表 `/v1/models` 或 `/v1/chat/completions` 已通。
- **禁止漏 header 就下 AUTH_FAIL**：某些本地代理在没带 `Authorization: Bearer <key>` 时，`/v1/models`/`/v1/chat/completions` 会直接返回 401；必须先带 `.env` 里的真实 key 再测一次，再判定。
- **必须修正方法后重测**：对非 OpenAI 兼容 provider，优先改用最小真实调用：`POST /v1/chat/completions` + `max_tokens=1`，再按状态码做 401/403 分类。
- **结论只报告事实，不下保留/删除建议**：单次独立复测只输出 `OK / AUTH_FAIL / 服务未运行 / 其他`，删除建议必须由用户基于多次、独立、同 endpoint 同方法、同 auth 头配置的稳定失败记录决定。\n\n## 环境变量注入验证\n\nconfig.yaml 里明文 `api_key` 会覆盖 `.env` 中的同名变量（例如 `AGNES_API_KEY`），导致 provider 端返回 401 但你已确认 `.env` 是正确的。\n\n**检查 gateway 进程实际看的环境变量**：用 `/proc/<pid>/environ` 读取真实运行时变量。详见 `references/gateway-env-injection-verification.md`。

## Hermes v0.18.0 64K 上下文硬要求

Hermes v0.18.0 在 `agent_init.py` 中硬编码了 **64,000 tokens 最小上下文窗口**。配置的 `model` 若低于此值，gateway 启动后会立即报错退出：

```
ValueError: Model <name> has a context window of <N> tokens,
which is below the minimum 64,000 required by Hermes Agent.
Choose a model with at least 64K context.
If your server reports a window smaller than the model's true window,
set model.context_length in config.yaml to the real value
```

**影响：**
- NVIDIA `meta/llama-3.1-8b-instruct`（16K）— 不通过
- OpenCode Zen 免费模型 — 需确认 context，部分可能低于 64K
- 所有 <64K 的本地/远端模型都无法用作 Hermes `model.default`

**修复方式（二选一）：**
1. 换用 context ≥64K 的模型（如 `agnes-2.0-flash` 128K、`oc/deepseek-v4-flash-free` 128K）
2. 在 `config.yaml` 中显式覆盖：
   ```yaml
   model:
     default: meta/llama-3.1-8b-instruct
     context_length: 65536  # 覆盖服务器报告的 16K
   ```

**排查：** 如果 gateway 日志中出现 `ValueError` 且 message 包含 `minimum 64,000`，不需要查 API key 或网络 — 直接看 model 的 context 窗口是否达标。

## 安全要求

- 所有输出只包含脱敏 key：前 2 位 + `***` + 后 2 位；空 key 直接显示空字符串
- key 不得拼接进 URL query；如果示踪足够，忽略 Authorization header 之外的其他可能泄露点
- 报告里禁止出现完整 key，哪怕 debug 状态

## 结果分类

| 状态 | 判定标准 |
|------|------|
| OK | 收到预期成功状态码 / 正常返回 |
| AUTH_FAIL | 401/403 |
| ENDPOINT_ERROR | DNS 失败、连接被拒绝、404 之外的地址/网络问题 |
| TIMEOUT | 超过 timeout 无响应 |
| UNKNOWN | 非预期状态码，不臆测，原样记录 |
| UNSUPPORTED_CHECK | `/v1/models` 404，已退化最小调用；或 provider 显式不支持通用探活 |

## 输出要求

- JSON：每个 provider 一条记录，至少包含：`provider`、`status`、`http_status`、`elapsed_ms`、`masked_key`、`check_method`、`message`
- 人类摘要：每行一个 provider，一眼可区分 OK / AUTH_FAIL / ENDPOINT_ERROR / TIMEOUT / UNKNOWN / UNSUPPORTED_CHECK
- 自检必须输出**全部 provider**，不只输出成功的；否则无法判断 ENDPOINT_ERROR / UNSUPPORTED_CHECK 是否是误判

## 验收标准

进入端侧验证的前置条件：
- `config.yaml` 剩余 api_key 明文数 = 0
- `.env` 引用缺口数 = 0
- YAML 解析通过

自检通过后，逐项确认：
- AUTH_FAIL：直接行动，可能 key 过期/录入错误
- UNSUPPORTED_CHECK：确认退化接口会不会产生计费/副作用，补 `check_method` 说明
- ENDPOINT_ERROR：排除“地址写错”后再确认网络/服务侧
- 高耗时但状态 OK：记录耗时，若该 provider 常被命中会影响整体响应