# Hermes Cron 命令真相（2026-06~07 期间观察）

`hermes cron` 子命令子集：**没有 `show`**，只能 `list` / `status` / `create` / `add` / `edit` / `pause` / `resume` / `run` / `remove` / `rm` / `delete` / `status` / `tick`。

要查某个 cron（id / job_id）的详情（schedule / last_run / 报错 stderr）：

```bash
hermes cron list           # 列出所有 + 每个的最近 error 摘要
hermes cron list | grep -A8 '<name>'    # 拿出某一段
```

注意 `hermes cron list` 的输出是**多 cron 联排**，不是分页 → 用 `-A8` 取某一段再 grep `stderr:` 拿原始报错非常有用。

---

# `hermes config set` 对 dual-registered provider 不自动同步

config.yaml 里同一个 provider name 出现在两段：

- `providers:`（line 2 附近）
- `custom_providers:`（line 649 附近）

——**两段都可能在生效**。`hermes config set providers.X.base_url "..."` **只改 `providers:` 那一段**，`custom_providers.X.base_url` 不会被改。

正确流程：

```bash
# 1. 找出 provider 在 config.yaml 里两段是否都出现
grep -n '<provider_name>:' ~/.hermes/config.yaml
# 2. 两段都要 set（如果两段都出现）
hermes config set providers.<p>.base_url "..."
hermes config set custom_providers.<p>.base_url "..."
```

否则会出现"只修了一处，结果另一处的旧 base_url 还被 client 抓到"——容易表现为"问题偶发"。

---

# Cron label（脚本里的名字）≠ 用户叙事里的"金/木/火"

session transcript 里经常用 "金同学"、"木同学" 这类叙事标签指代某个 gateway。**但 cron 列表里的实际名字不一定对齐**——可能是 `gateway-watchdog`（很泛），也可能是 `火同学 gateway watchdog`、`土·每日工作日志` 这种混合拼写。

错误假设"cron 名字 = transcript 描述"的代价：

1. 推断修对 cron 段但实际修的是无关的 cron
2. 修完汇报"问题 1 已闭环"，实际 cron 下次触发仍报错（因为根本不是同一个）
3. 会去查完全不相关的 session log 来"找证据"

正确做法（每次提到"cron X 报错了"时强制两步）：

```bash
# 1. 拿全列
hermes cron list

# 2. 对照 transcript 里 infer 出来的 cron 名字 vs 列里出现的真名字
#    若不直接命中，按 schedule ( */5 vs */10 ) / mode (no-agent vs agent) / script 路径综合判断
hermes cron list | grep -A8 '<可推断的关键词>' | grep -E 'Name|Schedule|Last run|stdout:|stderr:|Script'
```

——必须看到 **stderr / stdout 真文本**才算真凭据。仅靠 transcript 里的间接描述，等价于在 moa-sourcing-rules 框架下"未核实"。

---

# 关于"命名错位→推断错位→修复错位"的三层陷阱

session 里偶尔出现这种链路：

1. **叙事层**：用户上一句提到 "金同学"、"木同学"、"火同学"——这次对话上下文的指代
2. **运行时层**：具体进程（Mi8 dipper PID 12596、Mac 本机 PID 30246 等）真实在跑什么
3. **配置层**：config.yaml / .hermes-docker / 不同 cron 之间，**同一标签指向不同实体**的概率不低

如果三层两两不一致，最坏情况：

- 用户说"修金同学"
- assistant 推断"修 gold profile 配置"
- 实际脚本/cron 里"金同学"是 Mi8 dipper 上的 IPC 任务

——修了一整天跟金同学毫无关系的东西，**还以为是修同一件事**。

最低限度的核查（每次有人提到"金/木/火"`类叙事标签时）：

```bash
# A. Mac 本机 hermes 进程到底跑哪些
pgrep -af 'hermes' | grep -v grep

# B. 当前每个 listener 在跑什么
lsof -nP -iTCP:8888 -sTCP:LISTEN    # hindsight 通常在这
adb devices -l                       # dipper / Mi6 / 坚果

# C. 配置层
grep -n -B5 -A2 'base_url' ~/.hermes/config.yaml | head -30
```

写报告前，把这三层的结果和"用户提到的标签"并排列出来核对 → **比 transcript 里相信某个标签指 X 强 10 倍**。
