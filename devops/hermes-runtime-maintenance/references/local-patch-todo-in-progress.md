# 本地 patch：todo 单 in_progress（2026-07-17）

## 文件

| 文件 | 改动 |
|------|------|
| `tools/todo_tool.py` | `write()` 后 `in_progress>1` 拒绝并回滚；schema 写明硬拒 |
| `tests/tools/test_todo_tool.py` | 双 in_progress / merge 冲突用例 |

## 升级后验证

```bash
cd ~/.hermes/hermes-agent
python3 -m pytest tests/tools/test_todo_tool.py tests/tools/test_todo_tool_type_coercion.py -q
```

当前 session 可能仍用旧 todo 实例；**新会话 / 重启 gateway** 后硬校验才生效。

stash pop 冲突时保留：snapshot 回滚 + ValueError 闸门 + todo_tool 的 try/except。
