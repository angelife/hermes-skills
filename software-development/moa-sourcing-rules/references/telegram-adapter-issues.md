# Telegram Adapter 出站链路: send_path_degraded 修复路径与验证准则

**记录时间：** 2026-07-01  
**触发规则：** 会话期协作完整性约束 §2 单次观察不下结论 + §5 接口通与业务流分开报  
**位置：** `~/.hermes/hermes-agent/plugins/platforms/telegram/adapter.py`

---

## 链路总览（关键代码点）

| 行号 | 作用 | 纪要 |
|------|------|------|
| `432` | `self._send_path_degraded: bool = False` | 全文 send 短路开关 |
| `1707` | `async def _handle_polling_network_error(self, error)` | 主修复入口 |
| `1727` | `self._send_path_degraded = True` | 出 NetworkError 时立即置位 |
| `1730` | `if attempt > MAX_NETWORK_RETRIES: (set fatal_error)` | 第 11 次失败触发 supervisor 重启 |
| `1722-1724` | `MAX_NETWORK_RETRIES=10, BASE_DELAY=5, MAX_DELAY=60` | 退避梯子: 5s/10s/20s/40s/60s×6 ≈ 总 6分35秒 |
| `1740` | `delay = min(BASE_DELAY * (2 ** (attempt - 1)), MAX_DELAY)` | 60s 上限 |
| `1756-1760` | `await self._app.updater.start_polling(...)` | 重连尝试 |
| `1765` | `self._polling_network_error_count = 0` | 成功后归零 |
| `1776` | `self._send_path_degraded = False` | 成功后立刻清（不等待 60s probe） |
| `1945` | `HEARTBEAT_PROBE_DELAY = 60` 防御性 probe 延迟 | |
| `1963-1964` | `bot.get_me() 成功 → _send_path_degraded = False` | probe 成功路径 |
| `1965-1970` | probe 失败 → 再跳回 1707 重连梯子 | |
| `2955-2956` | `if getattr(self, "_send_path_degraded", False): return SendResult(success=False, error="send_path_degraded", retryable=True)` | 全部 send 入口短路 |

---

## 已知死角（代码注释自承认）

adapter.py:1777-1783 注释承认：

> PTB Updater 可处于 `running=True` 但 long-poll task 卡死的状态——wedged——`error_callback` 不触发, self 不修正。

→ 即：**整个梯子存在一个 self-not-recovering 的死角**。60s probe 是补救, 但 probe 自己也 settled 在同一个 httpx 连接池, 同样会在 SOCKS5/网络抖动下挂掉。

---

## 修复方向（按代价分级）

| # | 动作 | 代价 | 风险 |
|---|------|------|-----|
| ⅰ | 让金同学 走 Mac FreeLLM-API 直转 Telegram API, 不走 SOCKS5 抖动链。改 Mi8 上 `.env` `TELEGRAM_PROXY=` 为空 | adb shell 改一行 `.env` | 0 |
| ⅱ | 提高 polling 心跳阈值: `_polling_network_error_count` 限制真实/伪信号。`adapter.py:1722` `MAX_NETWORK_RETRIES=10` → `40` | 一行代码 | 低 |
| ⅲ | 隔离 polling 和 send 的 boolean flag。复制 `adapter.py:1727` 设独立 `_send_health_good` | 几行 | 中 |

**首选 ⅰ**——零风险, 切走历史怀疑的 SOCKS5 抖动链。

---

## 实测日志参考（Mi8 / dipper, 路径: `~/.hermes/logs/agent.log`，需 `su -c` 读）

| 时间 | 事件 |
|------|------|
| 2026-07-01 03:47:12 | `WARNING [Telegram] Telegram network error (attempt 1/10), reconnecting in 5s. Error: httpx.ReadError` |
| 2026-07-01 04:28:02 | 同上, 再触发一次重连 |
| 2026-07-01 05:40:02-06 | `WARNING [Telegram] Send failed (attempt 1/2, retrying in 2.6s): send_path_degraded` × 2 重试,`ERROR [Telegram] Failed to deliver response after 2 retries: send_path_degraded` |
| 2026-07-01 05:41:39 | 又一次 NetworkError, 重连梯子又起 |
| 2026-07-01 06:23:11 | `[Telegram] Sending response (120 chars)`——可送, **同时**有独立问题:`title_generation` 走 `192.168.1.8:3001` (FreeLLM-API) 返回了 `<!doctype html>` 而非 JSON |

**金同学（Mi8 dipper, PID 12596）截至该时点属于"间歇可送, 但是间歇"**——`_handle_polling_network_error` 间歇恢复，supervisor 重启间隔时间不定。**用户可见后果**：金同学每隔一段时间能说话一句，但不能连续两句话。

**现存的 watchdogs 三条都不覆盖金同学**：
- `gateway-watchdog`（da2b5692cb9b，*/5）：监控 default profile, 当前报错 `Context length exceeded (314 tokens)`，跟 send 出错无关
- `火同学 gateway watchdog`（e15a1d27093e, */10）：监控 `phone-gateway-watchdog.sh`, 硬编码 `PHONE="8a765553"` 不在 `adb devices` 列表
- `土·每日工作日志`（每日 22:00）：讯飞 10163 错

---

## 验证准则（接口通 ≠ 业务流走通）

修复完 send_path_degraded 后, 必须**两步独立**才能宣布闭环:

| 维度 | 验证动作 | 是否能算"已修复" |
|------|---------|-----------------|
| 1. 接口层 | `curl -H "Authorization: Bearer ..." -X POST https://api.telegram.org/bot<TOKEN>/sendMessage ...` 直打 Telegram Bot API | 单这一步 **不能** 算修复完成 |
| 2. 业务流 | 让金同学端到端跑通两轮连续对话 (用户提一句 → 金同学生成 → 交付)。**不能用单次 ping/send 替代** | 必须 ≥2 个**用户可见**的端到端样本才能算闭环 |

**会话期协作完整性约束 §2 的具体落点**: 这是"单次观察不下结论"在该 issue 上的具体应用。

---

## 触发本 reference 的那次会话教训

| 错误 | 来源 |
|------|------|
| "Cloudflare 7003 已闭环"被当作"金同学就修好了"的部分证据 | 上轮 transcript 推断, 没核证 cron 归属 |
| `send_path_degraded` 在 backlog 列里被反复标 "持续低成功率, 今天不修" 长达 24 小时 | 用户最终点出"金同学说话问题还是没解决么" |

**关键**: 这条 reference 不是"修了什么 bug", 是"该 bug 现在处于什么状态 + 怎么验证它真的修了"——避免下次又走老路: 接口通了以为业务流也通了。
