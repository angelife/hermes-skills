---
name: memory-7layer-architecture
description: >-
  memory-os 7层记忆架构在 Hermes 上的完整实现方案。
  包含：L1 CREATIVE.md 隔离、L2 自动注入、L3 Structured Facts (SQLite)、
  L4 Fabric 经验卡片、L5 语义检索、L7 Ground Truth 权威层级。
  从概念框架到可运行的脚本和 cron job。
tags: [memory, hermes, architecture, memory-os, fact_store, fabric]
---

# 7层记忆架构 for Hermes

基于 `memory-os` (GitHub: esaradev/memory-os) 的设计，在 Hermes Agent 上的完整实现。

## 架构总览

| 层 | 名称 | 生命周期 | 存储 | 实现 | 自动化 |
|---|------|---------|------|------|--------|
| L1 | Workspace | 每轮对话 | MEMORY.md + CREATIVE.md | CREATIVE.md 文件 | SOUL.md 规则自动加载 |
| L2 | Sessions | 跨会话 | state.db + session_search | state-restore skill | 自动恢复 + fabric 注入 |
| L3 | Structured Facts | 持久 | SQLite | ~/.hermes/scripts/fact_store.py | cron 每天 02:00 自动采集 |
| L4 | Fabric | 持久 | Markdown 经验卡片 | ~/.hermes/scripts/fabric.py | cron 自动重建 |
| L5 | Qdrant | 持久 | 轻量语义索引 | ~/.hermes/scripts/semantic_search.py | cron 自动重建 |
| L6 | LLM Wiki | 持久 | Markdown 知识库 | 待实现 | — |
| L7 | Ground Truth | 概念层 | SOUL.md 权威链 | SOUL.md 规则 | 固化到身份锚定 |

## L1: Workspace — CREATIVE.md

### 目标
volatile 记忆（学习进度、开放问题、迭代状态）与 MEMORY.md（稳定事实）隔离，避免双 Writer 冲突。

### 文件位置
`~/.hermes/CREATIVE.md`

### 模板
```markdown
# CREATIVE.md — 活跃上下文

## 当前学习课题
- 正在学习：...

## 开放问题
- Q: ...

## 迭代状态
- 上次更新：YYYY-MM-DD
- 当前阶段：...
```

### SOUL.md 集成
```
**同时加载 `~/.hermes/CREATIVE.md`** 获取活跃上下文和开放问题。
```

### 更新时机
- 会话结束时(state-save 时)更新"迭代状态"部分
- 新知识学习时更新"当前学习课题"

---

## L2: Sessions — 跨会话连续性

### 机制
1. state-restore skill 恢复 Working State
2. 自动加载 CREATIVE.md
3. 自动读取 `~/.hermes/fabric/*.md` 经验卡片
4. 如果 fact_store.db 存在，记录总事实数

### SOUL.md 中的规则
```
新会话启动时，立即加载 state-restore skill 检查 ~/.hermes/state/ 下的 Working State...
同时加载 ~/.hermes/CREATIVE.md...
如果 ~/.hermes/fabric/*.md 存在，逐一读取注入作为 L3/L4 记忆上下文
```

### state-restore skill 补充步骤
在恢复 Working State 后，增加 4c 步骤：
1. `ls ~/.hermes/fabric/*.md` 检查卡片存在
2. 如果存在，读取每张卡片的内容
3. 注入 `## L3/L4 Memory Context` 和 `### Experience Cards` 块
4. 检查 `~/.hermes/fact_store.db` 是否存在

---

## L3: Structured Facts — fact_store

### 数据库
- **路径**: `~/.hermes/fact_store.db`
- **引擎**: SQLite (WAL mode)
- **脚本**: `~/.hermes/scripts/fact_store.py`

### 表结构
```sql
CREATE TABLE facts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity TEXT NOT NULL,          -- 实体名（如 "用户偏好"、"Mi8"）
    category TEXT NOT NULL,        -- 类别（style/network/config/infrastructure/auto）
    content TEXT NOT NULL,         -- 事实内容
    trust_score REAL DEFAULT 0.5,  -- 信任评分 [0, 1]
    retrieved INTEGER DEFAULT 0,   -- 被检索次数
    helpful INTEGER DEFAULT 0,     -- 被认为有用的次数
    unhelpful INTEGER DEFAULT 0,   -- 被认为无用的次数
    source TEXT DEFAULT 'manual',  -- 来源（manual/auto/"extract"）
    created_at TEXT,
    updated_at TEXT,
    status TEXT DEFAULT 'active'  -- active / deprecated / merged
);

CREATE INDEX idx_facts_entity ON facts(entity);
CREATE INDEX idx_facts_trust ON facts(trust_score DESC);
```

### 信任评分公式
```
trust = 0.5 + (helpful / max(retrieved, 1)) * 0.3
上界 0.95, 下界 0.0
```

### CLI 命令
```bash
# 初始化
python3 ~/.hermes/scripts/fact_store.py init

# 添加事实（基础）
python3 ~/.hermes/scripts/fact_store.py add "<entity>" "style" "事实内容" 0.7

# 添加事实（带自检置信度，受 Belief Entropy 启发）
# --conf N: 1-10 的置信度, 1-3→trust=0.2, 4-6→0.4, 7-8→0.6, 9-10→0.8
# --gap: 记录"还不知道什么"（锚点问题中的"缺口"探测）
python3 ~/.hermes/scripts/fact_store.py add "Mi8" "network" "事实" --conf 8 --gap "未验证的假设"

# 查询
python3 ~/.hermes/scripts/fact_store.py query "关键词"

# 标记有用/无用 (自动更新 trust_score)
python3 ~/.hermes/scripts/fact_store.py helpful 42
python3 ~/.hermes/scripts/fact_store.py unhelpful 42

# 清理低分旧事实
python3 ~/.hermes/scripts/fact_store.py prune 30

# 统计
python3 ~/.hermes/scripts/fact_store.py stats
```

### 自检置信度 (Belief Entropy 模式)

从 Belief Entropy 论文(arxiv: 2605.30159) 引入的自检机制:

| --conf | trust_score | 含义 |
|--------|-------------|------|
| 1-3 | 0.2 | 低确信度，存疑 |
| 4-6 | 0.4 | 中等确信度，可能有误 |
| 7-8 | 0.6 | 高确信度，已验证 |
| 9-10 | 0.8 | 极高确信度，源可靠 |

`--gap` 对应论文中的"缺口探测"模式——记录还缺少什么信息比记录"已经答了什么"更有价值。fabric 卡片会自动包含缺口信息。

### 典型分类
| category | 存储什么 |
|----------|---------|
| style | 用户偏好、写作风格、交互习惯 |
| network | IP 地址、端口、协议、设备连接 |
| config | 配置参数、环境变量 |
| infrastructure | 团队架构、服务拓扑 |
| auto | 自动采集的未分类事实 |

### 自动采集 cron job
- **名称**: `fact-auto-collect`
- **时间**: 每天 02:00 (cron: `0 2 * * *`)
- **prompt**: 用 session_search 查最近对话，提取偏好/配置/工作流模式，写入 fact_store，然后重建 fabric 和语义索引
- **toolsets**: terminal, web, file

---

## L4: Fabric — 经验卡片

### 目录
`~/.hermes/fabric/`

### 脚本
`~/.hermes/scripts/fabric.py`

### 卡片格式
```markdown
# 经验卡片: <entity> (<category>)

> 自动生成于 YYYY-MM-DD HH:MM
> 来源: fact_store (trust >= 0.5)

## 关键事实
- [0.85] 事实内容1
- [0.70] 事实内容2

## 操作指南
基于上述事实，处理 <entity> 时注意:
1. 最高信任事实
2. 次高信任事实

## 变更记录
- 2026-07-12: 首次记录
- 2026-07-12: 最后更新
```

### CLI 命令
```bash
# 构建所有经验卡片
python3 ~/.hermes/scripts/fabric.py build

# 构建特定实体的卡片
python3 ~/.hermes/scripts/fabric.py build "Mi8"

# 列出已有卡片
python3 ~/.hermes/scripts/fabric.py list
```

### 注入机制
新会话启动时，SOUL.md 和 state-restore skill 负责逐一读取 fabric 卡片并注入上下文作为 `## L3/L4 Memory Context` 块。

---

## L5: 语义检索 (轻量 Qdrant)

### 方案
用 TF-IDF 风格的词频向量 + 余弦相似度实现语义搜索，无需安装 Qdrant 服务。

### 数据库
`~/.hermes/semantic_store.db`

### 脚本
`~/.hermes/scripts/semantic_search.py`

### CLI 命令
```bash
# 初始化
python3 ~/.hermes/scripts/semantic_search.py init

# 添加文档
python3 ~/.hermes/scripts/semantic_search.py add "category" "文档内容"

# 搜索
python3 ~/.hermes/scripts/semantic_search.py search "查询关键词"

# 从 fact_store 重建索引
python3 ~/.hermes/scripts/semantic_search.py rebuild
```

### 算法
- 分词: 中英文混排，长度 > 1 的 token
- 向量: 词频归一化 (count / total)
- 相似度: 余弦相似度
- 搜索: 遍历所有文档计算相似度，取 top-5

---

## L6: LLM Wiki (待实现)

目前空缺。可用品质技能（如 site-audit, hermes-troubleshooting）替代。

---

## L7: Ground Truth — 权威层级

### 规则
```
当前对话用户说的 > 记忆注入的历史 > 官方文档 > 模型训练知识
```

### 在 SOUL.md 中的实现
```markdown
## 信息权威层级 (Ground Truth)

当信息冲突时，按以下优先级裁决：
**当前对话用户说的 > 记忆注入的历史 > 官方文档 > 模型训练知识**

- 引用信息时标注来源层级
- 不确定的明确标注"未验证"
- SOUL.md 的规则高于一切注入记忆
```

---

## 部署清单

### 本机部署
1. ✅ CREATIVE.md 创建 (L1)
2. ✅ SOUL.md 更新 + state-restore 更新 (L2 + L7)
3. ✅ fact_store.py + 10 条初始事实 (L3)
4. ✅ fabric.py + 4 张经验卡片 (L4)
5. ✅ semantic_search.py (L5)
6. ✅ fact-auto-collect cron job (自动采集)
7. 🔲 远程设备部署 (火/金/水)

### 日常使用
- 发现新知识 → `fact_store.py add` → 数据自动持久化
- cron 每天 02:00 自动采集 session 中的事实
- 新会话自动加载 fabric 卡片 + CREATIVE.md

---

## 参考资料
- `~/.hermes/scripts/fact_store.py` — CLI 事实管理
- `~/.hermes/scripts/fabric.py` — 经验卡片构建器
- `~/.hermes/scripts/semantic_search.py` — 语义索引
- `~/.hermes/CREATIVE.md` — volatile 记忆
- `~/.hermes/SOUL.md` — 跨会话连续性 + 权威层级
- `~/.hermes/skills/workflow/state-restore/SKILL.md` — 状态恢复 + L3/L4 注入
- `references/openviking.md` — OpenViking AGFS 虚拟文件系统记忆（潜在 L4/L5 替代方案）
- GitHub: esaradev/memory-os
