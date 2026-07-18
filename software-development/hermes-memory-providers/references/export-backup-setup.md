# 导出与备份配置

基于 2026-06-20 配置记录。

## 环境

- Hermes Agent (deepseek-v4-flash-free / opencode-zen)
- macOS 15.7
- Hermes 工作目录: `/Users/macos/.hermes`
- hindsight-cloud 为主 memory provider

## 导出脚本

位置: `~/.hermes/scripts/hindsight_export.py`

脚本自动从 `~/.hermes/.env` 读取 `HINDSIGHT_API_KEY`，无需手动传参。

### 依赖

- 运行在 Hermes venv 的 Python 下: `/Users/macos/.hermes/hermes-agent/venv/bin/python3`
- `hindsight_client` 包（已通过 `uv pip install "hindsight-client>=0.4.22"` 安装在 Hermes venv）

脚本 shebang 已设为 `#!/usr/bin/env -S /Users/macos/.hermes/hermes-agent/venv/bin/python3`。

### 用法

```bash
# 默认：导出 JSON + Markdown 两种格式
uv run python3 ~/.hermes/scripts/hindsight_export.py

# 仅 JSON
uv run python3 ~/.hermes/scripts/hindsight_export.py --format json

# 仅 Markdown
uv run python3 ~/.hermes/scripts/hindsight_export.py --format markdown

# 自定义输出目录
uv run python3 ~/.hermes/scripts/hindsight_export.py --output /path/to/exports

# 增量导出（2026-06-15 之后的记忆）
uv run python3 ~/.hermes/scripts/hindsight_export.py --since 2026-06-15

# 首次运行后 export 目录
uv run python3 ~/.hermes/scripts/hindsight_export.py
```

### 脚本功能

- 分页拉取 memory provider 中所有 `observation`, `world`, `experience` 类型记忆
- 可选 `--since` 参数按日期过滤
- JSON 格式保留完整结构化数据（id, text, context, tags, entities, date, proof_count, state）
- Markdown 格式生成可读的归档文件，按类型分组、包含完整字段
- 输出目录: `~/.hermes/hindsight/exports/`

## Cronjob 配置

### 创建

```bash
hermes cron create \
  --name hindsight-export \
  --schedule '0 2 * * *' \
  --no-agent \
  --script hindsight_export.py \
  --workdir /Users/macos/.hermes
```

参数解释：
- `--no-agent` — 直接运行脚本，不启动 LLM agent（节省 token）
- `--script hindsight_export.py` — 相对 `~/.hermes/scripts/` 的脚本路径
- `--workdir /Users/macos/.hermes` — 脚本运行目录
- `--schedule '0 2 * * *'` — 每日凌晨 2:00 执行

### 验证

```bash
hermes cron list | grep hindsight
```

### 禁用/恢复

```bash
hermes cron pause <job_id>
hermes cron resume <job_id>
```

### 手动触发

```bash
hermes cron run <job_id>
```

## 导出文件结构

```
~/.hermes/hindsight/exports/
├── hindsight-export-2026-06-19.md          # Markdown 归档（每天一份）
├── hindsight-export-20260619_164311.json   # JSON 结构备份（每次运行一份）
└── hindsight-export-20260619_164545.json
```

## 双保险数据流

```
                        日常读写
用户对话 ──────────────────────────────────▶ hindsight cloud
                  (auto-retain, auto-recall, recall, reflect)
                                                │
                                    cron 每日 2:00
                                                │
                                                ▼
                                         ~/.hermes/hindsight/exports/
                                         ├── *.json   (结构化)
                                         └── *.md     (可读)
```

## 恢复/迁移思路

如需要将记忆从 cloud 迁移到本地或其他 bank：

1. 先完整导出 JSON：
   ```bash
   uv run python3 ~/.hermes/scripts/hindsight_export.py --format json
   ```

2. Python 处理导入逻辑：
   ```python
   import json
   with open("exports/hindsight-export-xxx.json") as f:
       data = json.load(f)
   # data["memories"]["observation"] + data["memories"]["world"]
   # 然后遍历调用 h.retain(bank_id="new_bank", content=item["text"], ...)
   ```

3. 或直接用 hindsight SDK 的文档 import API（需确认 `document_import_api` feature 的具体用法）

## 注意事项

1. **脚本对 hermes venv 有依赖** — 如更换 venv 路径需更新 shebang
2. **cron 调度在用户登录前不执行** — 确认下次运行时间：`hermes cron list`
3. **导出不删除云端数据** — 纯粹的 append-only 备份
4. **增量导出只做日期过滤** — 不记录上次导出的游标（每次全量按日期重筛）
5. **内存占满问题** — 内置 `memory` 工具有 2,200 字符上限。hindsight auto-retain 不受此限，但 export 脚本也需要定期清理旧备份
