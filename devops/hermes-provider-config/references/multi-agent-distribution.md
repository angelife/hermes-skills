# Multi-Agent Resource Distribution

When managing a fleet of Hermes agents across multiple devices (金/水/火/土), use the **central resource center** pattern: test everything from one control machine, then distribute working configurations to each agent.

## Principles

1. **Test centrally** — The control machine (土同学) has all API keys and direct internet access. All provider endpoints are probed from here first before any agent config is changed.
2. **Verify system_prompt delivery** — Before trusting a provider for role-identity agents, confirm that `agent.system_prompt` is actually passed to the model. Use a direct API call with a system message and verify the model responds accordingly.
3. **Diversify across providers** — Don't put all agents on the same provider. If one provider goes down (key expiry, model deprecation, rate limits), not all agents are affected simultaneously.
4. **Named providers for identity** — Agents that need role identity (金/水/火/土 personas) MUST use named providers under `providers:`, NOT `model.provider: custom` inline format. The inline format silently drops `agent.system_prompt` in Hermes v0.18.0.

## Distribution Workflow

```
1. Inventory available keys on control machine
2. Probe each provider endpoint from control machine
   - Verify HTTP 200 + content returned
   - Verify system_prompt is honored
3. Assign providers to agents (diversify)
4. For each agent:
   a. Write named provider block in config.yaml
   b. Set model.provider to named provider name
   c. Add agent.system_prompt with role identity
   d. Write API key to .env
   e. Restart gateway
5. Verify each agent responds correctly
```

## Provider Assignment Strategy

| Agent | Primary Provider | Model | Backup Provider |
|-------|-----------------|-------|-----------------|
| 土 (control) | OpenCode Zen | deepseek-v4-flash-free | NVIDIA / Agnes |
| 火 | OpenCode Zen | deepseek-v4-flash-free | Agnes |
| 金 | Agnes | agnes-2.0-flash | OpenCode Zen |
| 水 | OpenCode Zen | deepseek-v4-flash-free | Agnes |

Spread across at least 2 providers so no single provider outage takes down the whole team.

## Pitfalls

- **Inline `model.provider: custom` drops system_prompt** — Always use named provider format for identity-bearing agents.
- **Model availability varies by network** — A model that works from the control machine may timeout/404 from a remote device behind a proxy. Test from the actual agent's network path.
- **Reasoning models appear empty in raw API tests but work through Hermes** — `deepseek-v4-flash-free` returns `content: ""` with `reasoning_content` filled when called via direct curl. However, Hermes gateway handles this correctly — the content is delivered properly through the session. Do NOT reject the model based on curl API tests alone; test through an actual Hermes turn.
- **`.env` redaction trap** — Terminal output auto-masks secrets as `***`. Writing `cat > .env << EOF` with values copied from terminal output writes literal `***` to the file, breaking the config. Always obtain secrets from environment variables (`${VAR}`), session history (before masking), or base64-encoded storage. Verify file bytes with `wc -c` / `xxd` / `strings`, never trust what `cat`/`grep` displays.
- **Multi-device restart PID conflict** — When restarting a remote gateway (Android chroot, SSH), the old process may still hold the Telegram bot token, causing `"bot token already in use"` even after `kill`. Fix: `kill -9 <old-PID>`, `rm -f gateway.lock gateway.pid gateway_state.json`, then start with `--replace` flag. Verify no duplicate PIDs via `/proc/<PID>/cmdline` or Python process listing.
- **Key hygiene** — Track which key is assigned to which agent. Use separate env var names (`OPENCODE_ZEN_API_KEY_PRIMARY`, `_BACKUP`, `_BACKUP2`) for each key even if they share the same `base_url`.
