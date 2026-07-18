# Evaluation Examples — cumulative

## 2026-07-11 Session

| Tool | Category | Verdict | Reasoning |
|------|----------|---------|-----------|
| Hermes Kanban | Hermes built-in | ✅ 有用 | 初始化运行中，演示了 P1/P2/P5 模式 |
| TencentDB Agent Memory | Memory system | ❌ 卸载 | 不兼容共享记忆场景，回退 Hindsight |
| n8n-mcp | Workflow MCP | ❌ 暂不 | 不跑 n8n 实例，走 Python CLI |
| Obsidian CC | Obsidian AI | ❌ 不需要 | 已有 Hermes 生态，超出单插件范畴 |
| Browser-BC (Journey Forge) | Browser skill | ✅ 已装 | 补上浏览器操作知识层，配合 OpenBridge |
| Hermes Kanban P1-P8 | Collaboration pattern | ✅ 方法论 | 八种协作姿势可以跨框架迁移 |
| Hermes Skill 多层路径 | Architecture | ✅ 已具备 | 已有 31 分类 254 skills，不需大改 |

### Key lessons from 2026-07-11

- **Demonstration first**: "开始演示我看着呢" "我都没看到" — user needs to see it work, not just read about it
- **Proof across machines**: "我没看到火同学做任何事情" — multi-machine setups need concrete per-machine evidence (different CPU, uptime, produced files)
- **Try before assess**: User prefers to install and test rather than read; uninstalls cleanly if doesn't fit
- **Compatibility trumps features**: "可以并存么" is always the first question
- **Clean teardown**: When something doesn't fit, user wants complete removal ("那就卸载吧")

## 2026-07-10 Session

### Hermes Kanban Article (看板协作)
**Verdict**: 有用 — 直接能套你的 5 agent 工作流
**Key insight**: P1-P8 协作模式（P1 Fan-out / P2 Pipeline / P5 Human-loop）完全适用于五行舰队

### TencentDB Agent Memory
**Verdict**: 没用 — 你已有 Hindsight 共享记忆，这个只跑本地 Mac，其他 agent 访问不到
**Key blocker**: 不能共存（需替换 memory.provider），仅单机可用
**Action**: 安装→测试→用户确认无用→卸载

### n8n-mcp（21.7k stars）
**Verdict**: 有条件 — 如果你用 n8n 有用，但你走 Python CLI 路线，不适用

### Hermes Kanban 8 种姿势（协作模式库）
**Verdict**: 有用 — 实操手册，和之前初始化的 Kanban board 配套
**Key insight**: P1+P2+P5 cover 90% 场景
