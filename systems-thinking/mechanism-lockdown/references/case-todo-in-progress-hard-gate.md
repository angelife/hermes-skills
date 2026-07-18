# 案例：Todo 单 in_progress 硬校验（2026-07-17）

## 问题

schema 文案写「Only ONE item in_progress」，模型仍可写入 2+ 项。行为规范在工具描述里，概率执行。

## 错误方案

- 再写进 SOUL / 分析笔记「记得只开一项」
- 整包改 NLM 三刀（缓存 + 记忆门槛 + todo），但主路径是 Grok、prompt caching 上游已有

## 正确方案（机制锁死）

在 `TodoStore.write()` 提交前计数：

- `in_progress > 1` → `ValueError` + **整表回滚**（snapshot previous items）
- `todo_tool()` 捕获后 `tool_error(...)` 返回 JSON
- 测试锁死 replace / merge 双路径

## 原则

口号在 description；闸门在 write 路径。  
NLM/外文建议必须对照本地现状再收敛——**方向对 ≠ 全改**。

## 本地补丁

- `~/.hermes/hermes-agent/tools/todo_tool.py`
- `~/.hermes/hermes-agent/tests/tools/test_todo_tool.py`
- 升级必迁；新会话 / 重启 gateway 后生效
