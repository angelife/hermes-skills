# Hermes Diagnostic Discipline — Session Reflections

Date: 2026-06-30
Context: Mi8 (dipper) Telegram bot "金同学" mute — 6+ rounds before resolving actual root cause.

## Diagnosis cascade

| Round | Visible symptom | I treated it as | Actual role |
| ----- | --- | --- | --- |
| 1 | `socks5://192.168.1.8:1080` in logs | config format bug | internal scheme conversion, irrelevant |
| 2 | `curl: (35) Recv failure: Connection reset by peer` | proxy/network issue | downstream effect of retries |
| 3 | `Agent cache invalidated...message_count changed` | race condition | unrelated |
| 4 | Node.js download failure | network bug blocking agent | Hermes install.sh loop |
| 5 | `No module named 'jiter.jiter'` | import bug | **ROOT CAUSE** |
| 6 | jiter patched but `send_path_degraded` | same jiter issue | different domain |

## User-corrections landing points

### Correction 1: "已修复" must wait for end-to-end success
Lesson: only "已修复" after the feedback loop closes.

### Correction 2: chain symptoms under root cause
Lesson: a causation chain is not a list of problems.

### Correction 3: confirm hardware config before reasoning
User: "小米6 屏幕坏了 小米8 无线网坏了 屏幕是好的"
Lesson: getprop/fastboot before assuming.

## Discipline checklist

- [ ] Earliest error log explains the others? Fold.
- [ ] NEW evidence or re-read?
- [ ] End-to-end observed or only process signals?
- [ ] Status word matching reality.
- [ ] Hardware assumptions verified.

## Common false-positives

- `send_path_degraded` post-jiter — cross-domain.
- `Lazy-installing edge-tts` — TTS, not text blocker.
- Telegram fallback IPs — normal.
- `module not found` from .so — DLOPEN.
