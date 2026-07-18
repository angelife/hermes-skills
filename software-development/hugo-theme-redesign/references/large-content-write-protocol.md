# 大内容写入协议（Large-Content Write Protocol）

适用于：任何需要在 macOS 文件系统上落地 **> 1000 字中文 / > 2000 token** 的 Markdown、文章、笔记、文档。

## 核心问题：False-Success Hallucination

LLM 在长输出时有两种失败模式：

1. **Stream 截断** — Hermes 网关在 generator 中途切断（token 上限、网络、context 满），工具调用没机会执行
2. **伪完成幻觉** — 即使工具没执行，模型仍会输出"✅ 已写入/已发布"这类的成功文案

这次会话里，agent 重复 5+ 次声明「文章已发布」但 `ls ~/angelife.github.com/hugo-site/content/series/anti-populism/` 始终只有 3 个文件。这是典型的伪完成幻觉。原因是 write_file 调用在 stream 中途被 Hermes gateway 截断。

## 强制协议 v1.0

### Step 0：任务启动公告

接到写文件任务时，**先**输出一行：

```
[WRITE TASK] 目标路径：[路径] / 预估字数：[N] / 分段数：[N] / 使用模型：[模型名]
```

不公告，不开工。

### Step 1：分段策略

| 字数 | 策略 |
|---|---|
| < 800 字 | 单段 write_file，wc -c 验证 |
| 800–1500 字 | 单段 write_file，wc -c 验证 |
| 1500–5000 字 | 拆 2–3 段，第 1 段 write_file，后续 append_file |
| 5000–15000 字 | 拆 5–10 段，逐段 wc -c 监控 |
| > 15000 字 | **强烈建议拆分多篇**（用户偏好 2000–2500 字一篇，与本项目系列文一致） |

每段上限：**≤ 1000 字中文 / ≤ 2000 token**。

### Step 2：每段写完后立即验证

```bash
ls -la <target_dir>
wc -c <target_file_path>
```

**必须**确认：
- 文件名出现在 ls 输出中
- wc -c 显示字节数 > 0
- 多段任务：字节数**单调递增**

### Step 3：最终验证

```bash
cat <target_file_path>
```

整篇读出，做心智比对（字数、行数、关键段落是否存在）。

### Step 4：Git 集成

只在 cat 验证通过后做：

```bash
git -C ~/angelife.github.com add <specific_file>
git -C ~/angelife.github.com commit -m "..."
git -C ~/angelife.github.com status
```

不要 `git add .`。

## 禁止的行为

- ❌ 在 ls 验证前输出任何形式的成功声明（「已发布」「已完成」「已写入」「任务完成」）
- ❌ 把 stream 截断当作已完成
- ❌ 单次 write_file 超过 1500 字而不分段
- ❌ 把已失败的任务当成功状态汇报
- ❌ 用「我期望」「我相信」代替实际 ls 输出

## Stream 截断后的自检

如果响应在中途被截断（你看到 `[Response truncated]` 或响应末尾异常），**下一条消息里**：

1. 第一句必须承认：「上次 stream 被截断，未确认文件状态。下面重新验证。」
2. 跑 `ls <target_dir>` 看真实状态
3. 文件不存在 → 按 Step 1 重新写
4. 文件存在但不完整 → 用 append_file 续写剩余段

不要装作它是成功的。

## 模型选择

| 字数 | 推荐模型 |
|---|---|
| < 800 字 | 任意可用模型 |
| 800+ 字 | 优先 `xopqwen36v35b` 或 NVIDIA DeepSeek |
| 1500+ 字 | **绝对不要用** `minimax-m3` fallback（截断率高） |

## 备份模式：写文件前先副本保护

对于不可恢复的内容（比如草稿、笔记），写作前先：

```bash
cp <target_file> <target_file>.bak
```

写完后比对再决定 `.bak` 是否保留。

## 元学习：为什么这个协议存在

这不是工具的问题。Python `write()` 调用是同步且原子的；write_file 是确定性操作。这个协议解决的是 **agent 行为问题**——具体是 agent 在长 stream 下与 tool-call 之间出现的一致性裂缝。

所以，这个协议属于 **agent self-discipline**，不是工具补丁。

相关技能：angelife-mobile-remote-workflow（HTTPS fetch 失败重试）、systematic-debugging（4 阶段调试）。
