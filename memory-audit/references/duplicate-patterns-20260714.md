# MEMORY.md ↔ USER.md 重复对照表

审计日期: 2026-07-14 | Day 2

## 高严重度重复 (需合并)

### 外部链接不进记忆
| 文件 | 条目 | 字数 |
|------|------|------|
| MEMORY.md [16] | User strongly corrected: external article links must NOT be stored in Hindsight memory... | 219 |
| USER.md [9] | 强约束：外部文章链接不进记忆系统... | 237 |
| USER.md [10] | 强约束：外部文章链接不进 Hindsight 记忆层... | 196 |

→ 保留 USER.md [9] (中文, 更简洁), 删除 MEMORY[16] 和 USER[10]

### 查 skill+history 再动手
| 文件 | 条目 | 字数 |
|------|------|------|
| USER.md [8] | 核心指令：遇到已解决过的技术问题...先查 skill 和 session history... | 194 |
| USER.md [11] | 核心指令：已解决过的技术问题...先查 skill 和 session history... | 179 |
| MEMORY.md [22] | 用户纠正：当声称"没有配置/没有找到"时，先翻 session history 确认... | 181 |

→ 保留 USER.md [8], 删除 USER[11], MEMORY[22] 合并到 [8]

### 网络拓扑
| 文件 | 条目 | 字数 |
|------|------|------|
| MEMORY.md [6] | 办公网 192.168.1.0/24，家网 192.168.2.0/24... | 155 |
| USER.md [7] | Home network: 192.168.2.0/24. Mac .125, Mi8 .127. Office: 192.168.1.0/24. | 73 |

→ 保留 USER.md [7] (更简洁), 删除 MEMORY[6]

## 中严重度重叠 (可精简)

### "极简/装上看看/完全授权"偏好群
| 文件 | 条目 | 字数 |
|------|------|------|
| MEMORY.md [3] | 用户对空工具输出/重复结果/无日志实证的推测非常反感... | 264 |
| MEMORY.md [8] | Tool eval: verdict first, demo with real execution... | 90 |
| MEMORY.md [10] | Prefer '装上看看' over discussion... | 102 |
| MEMORY.md [14] | 当用户说'完全授权'...无需逐一征求同意... | 168 |
| USER.md [1] | 极简指令+短句推进。回应只说序号/结果，不解释过程... | 174 |
| USER.md [5] | 先扫环境再动手。遇已解决技术问题先查skill+memory... | 90 |
| USER.md [6] | 排障：结果不要过程，日志写了自读... | 75 |

→ 保留 USER.md [1] (涵盖极简/结果导向), 删除 MEMORY[8],[10],[14]
→ MEMORY[3] 保留但建议缩短到 150字内
→ USER[5],[6] 合并到 USER[1]

## 执行建议 (进入 execution phase 后)

删除列表:
- MEMORY.md: [3](缩短), [6], [8], [10], [14], [16]
- USER.md: [5], [6], [7], [8], [9], [10], [11]

缩短列表:
- MEMORY.md [3]: 264→150字
- USER.md [4]: 434→200字 (移除敏感信息)

保留列表:
- MEMORY.md: [1],[2],[4],[5],[7],[9],[11],[12],[13],[15],[17],[18],[19],[20],[21]
- USER.md: [1](合并后), [2], [3], [4](缩短), [12]
