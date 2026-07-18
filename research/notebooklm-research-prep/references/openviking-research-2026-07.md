# OpenViking 研究结论 — 2026-07-16

## 来源
NotebookLM 笔记本 `281bcf82-7096-4c22-9bdc-21967f09cfdb`（OpenViking 上下文数据库深度消化，19 个来源）

## 许可证
- 服务端主项目: AGPLv3 — 个人用无限制；公开 API 服务需开源全部修改
- CLI / SDK / examples: Apache 2.0

## 核心价值
- L0/L1/L2 三层加载 → 省 80-91% token
- 文件系统范式（viking://）→ 路径定位比纯语义召回准
- Hermes 原生集成 → `hermes config memory` 即配

## 已知 Bug（集成前必读）

### #5721 — 永久断连
- 现象：Hermes 启动时若 OpenViking 服务不可达，`_client = None` 且永不重连
- 即使服务恢复，当前会话也永久失效，必须新建会话
- 状态：未修复（NousResearch/hermes-agent#5721）

### #50133 — 记忆作用域硬编码
- 现象：记忆默认写入 peer 命名空间（viking://user/peers/{AGENT}/），非用户命名空间
- 多 bot 共享时可能写错位置/权限拒绝
- 状态：Feature request，未实现（NousResearch/hermes-agent#50133）

## Cloudflare 可行性
- 核心服务端：❌ 不可行（四语言架构，需要 Python 运行时 + Rust 本地库，Workers 环境不兼容）
- CF R2：✅ 可作为 S3 兼容存储后端
- CF AI Workers：✅ 可作为 embedding/VLM 提供者（包装为 OpenAI 兼容端点）
- 实际需要一台传统 VPS 或物理机跑服务端

## 2GB Linux 部署要点
- `pip install openviking`（不要源码编译 → OOM）
- 必须用云 API 做 embedding（本地跑不动 Ollama）
- 调低并发：`embedding.max_concurrent=4`, `vlm.max_concurrent=8`
- 文档参数名跟代码不一致：文档说 `target`，代码用 `to`

## 实验策略
1. 在木同学上装 OpenViking server
2. 用 CLI 跑通基本功能（存/取/搜/查），暂不接 Hermes
3. 验证召回质量和稳定性
4. 确认可靠后再配 `hermes config memory` 切换
