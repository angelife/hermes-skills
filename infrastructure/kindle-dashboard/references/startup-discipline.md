# 面板启动纪律（用户纠正 2026-07-17）

**原话：「启动服务器啊 你生成放到桌面啥意思」**

交付 = 进程在听端口，不是桌面截图 / 离线 HTML。

## 做 / 不做

| 做 | 不做 |
|----|------|
| `python3 ~/.hermes/scripts/dashboard_server.py --port 28080 --bind 0.0.0.0` 后台跑 | 把 HTML 另存桌面当交付物 |
| HTTP 200 验证 `http://127.0.0.1:28080/` | 只报「语法正确」就停 |
| 改完代码先杀旧进程再启 | 假装「文件已生成」= 服务已开 |

## 记忆健康检测

勿用 `pgrep hindsight` 判死。见 `daemon-detection-patterns.md`：端口 8888 → exports 回退 → 才报异常。
