---
name: skill-factory
description: 从 Hermes 会话或文件自动生成可安装技能。分析对话提取工作流、命令、陷阱，输出完整 SKILL.md。
trigger:
  - 用户说「把这个会话做成技能」
  - 用户说「保存为 skill」
  - 用户说「生成技能」
  - 用户说「把这段工作流记下来」
  - 用户说「从对话提取步骤」
---

# Skill Factory

从 Hermes 会话或已有文件自动生成可安装 SKILL.md 的技能。

## 原理

1. 读取会话历史（state.db）或文件（JSON/纯文本）
2. 分析提取：使用的命令、涉及的工具、关键文件路径、已知陷阱、用户触发词
3. 生成完整 SKILL.md（YAML frontmatter + markdown body）
4. 输出到 stdout 或写入文件

## 两种模式

### 从 session DB 生成

```bash
python3 ~/.hermes/scripts/skill_factory.py session <session_id> [--limit 100]
```

- `session_id`: 会话 ID（支持前缀匹配）
- `--limit`: 最大消息数（默认 100）

### 从文件生成

```bash
python3 ~/.hermes/scripts/skill_factory.py file <path> [--limit 100]
```

- `path`: JSON 导出文件或纯文本文件路径
- 自动检测 JSON 格式（Telegram 导出、messages array 等）或纯文本

### 从 stdin 生成

```bash
cat conversation.txt | python3 ~/.hermes/scripts/skill_factory.py generate "技能名" --limit 50
```

## 选项

| 参数 | 简写 | 说明 |
|------|------|------|
| `--name` | `-n` | 技能名（默认自动从对话标题推断） |
| `--desc` | `-d` | 技能描述（默认自动从首句推断） |
| `--limit` | `-l` | 最大消息数 |
| `--output` | `-o` | 输出文件路径（默认 stdout） |

## 输出结构

每个生成的 SKILL.md 包含：

- **YAML frontmatter**: name, description, trigger (触发词列表)
- **工作流步骤**: 从 assistant 消息提取的关键步骤
- **命令清单**: 识别到的 shell 命令（brew, pip, git, hermes 等）
- **关键路径**: 出现的重要文件路径
- **已知陷阱**: 包含"注意/坑/不要/报错"等的语句
- **变更记录**: 生成时间戳

## 示例

```bash
# 从会话生成并安装
python3 ~/.hermes/scripts/skill_factory.py session abc123 -n my-skill | head -30

# 从 TG 导出生成
python3 ~/.hermes/scripts/skill_factory.py file ~/.hermes/telegram_exports/Emacs_中文.json -o /tmp/skill.md
```

## 依赖

- Python 3.8+
- Hermes state.db（session 模式）
- 无需额外 pip 包

## 已知陷阱

- session DB 路径自动探测，但 Hermes 自定义部署可能需要手动指定
- 中文文件名在 YAML frontmatter 中可能需手动调整
- 生成的是草案，需人工审核后再 `skill_manage(action='create')`

## 变更记录

- 2026-07-14：从会话「三大任务」生成初始版本
