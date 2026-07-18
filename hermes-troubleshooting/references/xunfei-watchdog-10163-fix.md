# Gateway Watchdog Cron Job 与 Xunfei 10163 错误

## 现象
gateway-watchdog 定时任务每 5 分钟跑一次，每次返回：
```
code: 10163, msg: RequestParamsError:Invalid Params
```
Gateway 状态显示 Telegeram connected 但最终被 SIGTERM 停止。

## 根因
Watchdog cron job 是 LLM 驱动的 agent 任务（非 no-agent 模式）。Hermes 向模型发送完整工具定义（`tools` 参数数组）。**Xunfei API 不支持 OpenAI 格式的 `tools`/function calling 参数**，返回 10163。

Xunfei 直测成功（简单 curl 不带 tools 参数），confirm 是 tools 参数不兼容问题。

## 排查步骤
1. 检查 cron job 列表：`hermes cron list` — 找 gateway-watchdog
2. 检查是否 agent 模式（无 script、no_agent=false）
3. 查 gateway 日志：`tail -f ~/.hermes/logs/gateway.log` — 看报错是否重复出现
4. 直测 Xunfei API 排除网络问题：`curl -X POST` 简单对话

## 修复
```bash
# 1. 修改 watchdog 模型到一个支持 function calling 的
hermes cron update <job_id> \
  --model @cf/qwen/qwen3-30b-a3b-fp8 \
  --provider cloudflare-workers-ai

# 2. 重启 gateway
hermes gateway restart
```

## 预防
LLM 驱动的 cron job（非 no-agent 模式）必须使用支持 function calling 的模型：
- Cloudflare Workers AI ✅
- OpenCode Zen (deepseek-v4-flash-free) ✅
- NVIDIA Nemotron ✅
- **Xunfei ❌** — 不支持 tools/function calling 参数
