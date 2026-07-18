# 外部 Agent/Harness 文章 → NLM → 落地评估

## 顺序（NLM 中心制）

1. 全文备份（微信等不可只丢 URL）
2. `nlm add text` 喂正文 → `nlm query notebook` 要可执行建议
3. **对照本地现状**（主模型、已有功能、是否主路径）
4. 人拍板收敛 → 再改代码
5. 分析笔记追加 NLM 结论

## 2026-07-17 样例：small Rust Hermes 三刀

| 刀 | NLM 优先级 | 本地对照结果 | 决策 |
|----|-----------|-------------|------|
| Prompt Caching | 高 | 上游已有 `_anthropic_prompt_cache_policy`；默认 grok-4.5 | **不做**（非主路径） |
| 记忆 conf+查重 | 高 | Hindsight auto_retain + observation 去重已在；再加易成第三套 | **不改内核**；审计侧强化即可 |
| Todo 单 in_progress | 中 | schema 有口号、write 无硬闸 | **做** — `TodoStore.write` 硬拒 |

## 评估清单（每次外文建议复用）

- [ ] 主推理路径是哪家 API？（改 Anthropic-only 特性对 Grok/DS 无效）
- [ ] 上游/本地是否已实现？（搜关键字，避免假工单）
- [ ] 是加法还是减法？是否违背「少就是多 / 不用=不存在」
- [ ] 能否放在必经路径（代码闸门）而不是再写一条口号
- [ ] 收益是否落在当前账单/痛点上

## 关联

- 技能：`wechat-obsidian-pipeline` Phase 6、`mechanism-lockdown` 案例 5
- 补丁：`hermes-agent/tools/todo_tool.py`
