---
name: triple-ai-nlm-synthesis
title: "三AI问诊 + NLM 合成 — 问题诊断工作流"
description: "遇到技术问题时：同时问 Gemini/Claude/ChatGPT → 汇总回复 → 喂 NotebookLM 深度分析 → 拿回合成结论。适合需要多视角诊断的复杂问题。"
category: research
tags: [moa, notebooklm, openbridge, diagnosis, synthesis]
---

# 三AI问诊 + NLM 合成 — 五步问题解决法

## 核心原则（基于 2026-07-16 用户强行纠正）

### NLM 是唯一决策中心

> **所有原始材料→ NLM → NLM 出最终方案 → 执行 → 存档 Obsidian**
>
> **所有信息源（三AI/Grok/搜索/MoA/文档）都是「原材料收集器」**，不是决策者。
> **我不做任何手动综合、对比、合并**——NLM 的合成「非常高效精准」，手动综合反而遗漏视角。
>
> **NLM 是商业完整版**（用户已购买，账号 thomasx.xie@gmail.com），无需考虑用量限制，大胆用。
>
> 用户原话：**「因为我这个花钱了，我是商业版买了它的是完整功能的，知道吗？所以你大胆用就好了，你不用白不用啊」**

### 三通道模型（信息收集层）

遇到问题时**先选收集通道**，不是默认走 OpenBridge：

```
         ┌──────────────┐
         │   发现问题    │
         └──────┬───────┘
                ▼
    ┌───────────┴───────────┐
    │   选信息收集通道       │
    ├───────────────────────┤
    │ A. 问三AI (最精准)     │
    │ B. 搜+喂NLM (自包含)   │
    │ C. MoA (结构化)        │
    │ D. Grok API (快速)     │
    └───────────┬───────────┘
                ▼
    ┌───────────────────────┐
    │   全部喂 NotebookLM   │ ← 唯一决策中心
    │   (不做手动综合)       │
    └───────────┬───────────┘
                ▼
    ┌───────────────────────┐
    │ NLM 输出执行方案       │
    ├───────────────────────┤
    │ 共识+分歧+优先级       │
    │ 具体可执行命令          │
    └───────────┬───────────┘
                ▼
    ┌───────────────────────┐
    │ 按方案执行 → 存档      │
    │ Obsidian 工作档案      │
    └───────────────────────┘
                ▼
       有问题 → 回到收集
```

| 通道 | 方法 | 条件 | 优点 |
|------|------|------|------|
| **A — 问三AI** | OpenBridge → Gemini/Claude/ChatGPT | 浏览器已开+已登录 | 直接诊断，有推理过程 |
| **B — 搜+喂NLM** | web_search → web_extract → NLM | 任何网络 | 不依赖浏览器，自包含 |
| **C — MoA** | 多模型 API 交叉验证 | API Key 可用 | 结构化，多视角自动对比 |
| **D — Grok API** | curl 直调 xhahlf.top/v1/chat | API Key 在 config | 问答不用等浏览器 |

**优先级规则：**
- 能走 A 优先走 A（最精准）
- A 不通（OpenBridge/CDP 故障）→ 走 B
- 需要结构化多模型对比 → 走 C 或 D
- **所有通道的结果都喂 NLM 合成**，不自己手动对比

### 3个独立渠道，任意可用

用户原话：**「你可以搜索信息，也可以从 AI 获取信息，也可以从 MoA 获取信息。3个渠道你任意选」**
- 搜索渠道不通 → 换 AI
- AI 渠道不通 → 换搜索
- 不要把时间耗在修复某一个渠道上

**核心流程：**
```
问题 → 选通道 → 收集信息 → 全部喂 NLM → NLM 出方案 → 执行 → 存档
```

## 五步问题解决法（通用流程）

这是一套**解决所有问题的流程**，不限于技术诊断。适用于任何需要多视角验证的场景。

```
第1步 ── 收集关键信息（尽可能具体）
  │  现象、日志、环境、版本、已尝试的操作
  │  越具体，AI 回复越有效
  ▼
第2步 ── 问三个 AI 分析判断
  │  Gemini → Claude → ChatGPT（逐一，不并发，不等同开）
  │  问完一个存一个，记在 /tmp/ai-responses/
  │  ⚠️ 不要重复问——问之前先检查已有文件
  ▼
第3步 ── NLM 分析提出方案
  │  合并三份回复 → 创建 NLM 笔记本 → 让 nlm query 合成
  │  ⚠️ 必须喂三份，不能只喂一份（2026-07-16 session 犯过此错）
  ▼
第4步 ── 拿回方案执行
  │  按 NLM 给出的优先级顺序执行
  │  先跑隔离诊断确认根因，再修
  ▼
第5步 ── 成功→存档 / 失败→循环
  │  ✅ 成功 → 写 Obsidian 备忘（土同学工作档案/）
  │  ❌ 失败 → 回到第2步，带上 NLM 报告再问
```

```
┌─────────┐  ┌─────────┐  ┌─────────┐
│ Gemini  │  │ Claude  │  │ChatGPT  │
└────┬────┘  └────┬────┘  └────┬────┘
     │            │            │
     └────────────┼────────────┘
                  ▼
         ┌────────────────┐
         │  NotebookLM    │ ← 统一分析引擎
         │  (nlm query)   │
         └───────┬────────┘
                 ▼
         ┌────────────────┐
         │  合成分析报告   │
         └────────────────┘
```

不手动做三份对比/合并，那个工作交给 NLM。

### 心法

> **少就是多，慢就是快。**
> **每一步都极其扎实，所以可以复用，反而大大提高效率。**
>
> 虽然一问三 AI 再喂 NLM 比直接查资料慢，但每步产出可复用的诊断档案，
> 下次同类问题直接查，不用重走。每解决一个问题，知识库就厚一层。
> 长期看，非常稳。
>
> **稳比快重要。宁可慢，不能断。**

### 流程定式

```
问三AI（逐一，不并发）→ 等回复 → 喂 NLM → 拿合成方案 → 执行 → 留档 Obsidian
```

## 触发条件

- 技术问题卡住，需要多模型诊断
- 需要交叉验证不同 AI 的方案
- 问题复杂，单一 AI 可能漏视角

## 前置条件

| 项目 | 要求 |
|------|------|
| **OpenBridge** | `cd ~/.openbridge/repo && node packages/daemon/dist/cli/index.js status` → Extension: Connected |
| **Gemini** | 浏览器登录 gemini.google.com |
| **Claude** | 浏览器登录 claude.ai |
| **ChatGPT** | 浏览器登录 chatgpt.com |
| **NLM** | `nlm doctor` → Authentication OK |
| **代理** | 国内需 socks5://127.0.0.1:10808 访问 Google |
| **ask-ai.js** | `scripts/ask-ai.js` — 永久安装在技能目录下，无需每次创建 |

## 技能支持文件

本技能包含以下辅助文件：

| 文件 | 用途 |
|------|------|
| `scripts/ask-ai.js` | OpenBridge 浏览器自动化脚本，用于向三个 AI 发送问题并抓取回复 |
| `references/kodi-mouse-case-study.md` | 实战案例：Kodi 鼠标修复全流程记录 |
| `references/wifi-international-bottleneck-case-study.md` | 实战案例：免费 WiFi 国际出口慢诊断 |
| `references/openbridge-browser-evaluate.md` | browser_evaluate 操作模式（替代被禁止的 browser_press） |
| `references/graphify-integration.md` | Graphify 知识图谱集成与用法 |
| `references/kindle-pw5-3ai-partial-channel-20260717.md` | OpenBridge partial + NVIDIA 幻觉过滤 + 流行方案交付案例 |

## 完整工作流

### 第 0 步：编制问题清单（用户强化的前置步骤）

不要等用户指派才开工。**主动编译当天所有未解决的问题**，形成结构化清单：

```markdown
## 问题清单 YYYY-MM-DD
| 优先级 | 问题 | 状态 | 需用户决策？ |
|--------|------|------|-------------|
| 🔴 Q1 | 描述 | 诊断中/待执行 | 是/否 |
| 🟡 Q2 | 描述 | 阻塞 | 是/否 |
```

然后按昼夜分工推进：
- **🌙 晚上（用户睡觉）**：推所有不需要用户决策的事。搜资料、跑诊断、归档。
- **☀️ 白天（用户在线）**：整理需要用户拍板的事项，集中汇报。

每解决一个问题 → 写一篇 Obsidian 笔记到 `~/Documents/Obsidian Vault/土同学工作档案/`。

### 第 0 步：8 小时无人化成熟度（2026-07-16 核心教训）

**每晚 8 小时无人化是成熟度检验。** 具体标准：

```
1. 不等人派活——发现问题自己排优先级
2. 工作量填满——8小时排14小时的工作量，宁愿做不完不能没事做
3. 明日事提前做——把接下来一周的准备工作往前提
4. 每件事闭环——解决→存档Obsidian，不留手尾
5. 技能主动完善——所有"好像没问题的东西"拿来重新审查
```

**用户原话：**
- "如果你说没事做，那就把后面的事情提到前面来嘛"
- "你宁愿是这些事情做不掉，也不要没事做"
- "你提前准备，总比遇到事情的时候再准备"
- "晚上这8小时，就是没有人监督你，你自己在推动自己做事情"

### 第 0 步：确认 ask-ai.js 可用

脚本已永久安装在技能目录下：

```bash
ls ~/.hermes/skills/research/triple-ai-nlm-synthesis/scripts/ask-ai.js
```

### 第 0 步：确认 ask-ai.js 可用

**原则：**
- 自包含：不给对方"看上下文"的期望，把所有关键信息写进去
- 具体：硬件型号、OS 版本、软件版本、现象日志关键词
- 要求明确：**"给出具体 shell 命令"**，不要泛泛建议

**模板：**
```
[问题简述] on [OS/硬件]
症状：[现象]，[日志关键词]  
已确认：[已检查的设置/配置]
请给出诊断和修复的 shell 命令，按可能性排序。
```

### 第 2 步：逐一询问（不要同时开多个窗口）

⚠️ **一次只问一个 AI**，等回复后再问下一个。用户明确强调过。

⚠️ **跟踪已问过的 AI**——问一个在 `/tmp/ai-responses/` 存一个，
不要重复问同一个 AI（本 session 犯过此错）。

```bash
# 问 Gemini（等回复后再问下一个）
node ~/.hermes/skills/research/triple-ai-nlm-synthesis/scripts/ask-ai.js gemini "你的问题" 2>&1 | tee /tmp/ai-responses/001-gemini.md

# 问 Claude（等回复后再问下一个）
node ~/.hermes/skills/research/triple-ai-nlm-synthesis/scripts/ask-ai.js claude "你的问题" 2>&1 | tee /tmp/ai-responses/002-claude.md

# 问 ChatGPT（等回复后再结束）
node ~/.hermes/skills/research/triple-ai-nlm-synthesis/scripts/ask-ai.js chatgpt "你的问题" 2>&1 | tee /tmp/ai-responses/003-chatgpt.md
```

**建议用 background 模式**（`background=true` + `notify_on_complete=true`）让回复在后台等，不阻塞对话。

### 第 2b 步：Grok API 备选（当 OpenBridge 不可用或需要快速问一轮）

当 OpenBridge 浏览器不可用，或者 Grok 模型适合当前问题时，直接用 Grok API：

```bash
API_KEY=$(grep 'api_key: sk-' ~/.hermes/config.yaml | head -1 | sed 's/.*api_key: //')
PAYLOAD=$(python3 -c "
import json
with open('/tmp/question.txt') as f:
    prompt = f.read()
print(json.dumps({'model':'grok-4.5','messages':[{'role':'user','content':prompt}],'max_tokens':2000}))
")
curl -s --max-time 120 -x http://127.0.0.1:10808 \
  https://api.xhahlf.top/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d "$PAYLOAD" | python3 -c "
import sys,json
d=json.load(sys.stdin)
if 'choices' in d:
    print(d['choices'][0]['message']['content'])
else:
    print(d)
"
```

注意：Grok API 的 `/v1/models` 端点返回 403（token 不共享），但 `/v1/chat/completions` 正常工作。需通过 v2rayN 代理（10808）访问。

Grok 回复存入 `/tmp/ai-responses/004-grok.md`，和三 AI 回复一起喂 NLM。

```
tail -5 /tmp/ai-responses/001-gemini.md  
tail -5 /tmp/ai-responses/002-claude.md
tail -5 /tmp/ai-responses/003-chatgpt.md
```

如果某个 AI 返回的是登录页/空壳（如"跳至内容 升级 生成图片"），说明未登录，标注 `[未登录]` 跳过。

**关键：必须将三份回复都喂给 NLM，不能只喂一份。** 只有全部三份在一起，NLM 才能做完整的共识/分歧分析。用户明确强调过。

### 关键：怎么处理网络慢导致的问题回声

> 本 session 核心教训（2026-07-16）：脚本抓到的可能是问题回显而非 AI 回复。

**判断方法：**
- 如果输出内容和你提的问题前几个词完全一样 → 误抓了问题回声
- 脚本显示 `✓ XXX chars` 但内容看着像你输入的问题 → 误抓
- 此时**用户可能在浏览器里已经看到真正回复了**

**正确做法（不要重新问）：**
1. 用户说「AI 已经回复了」而你脚本没抓到 → **让用户复述要点**，你手动补进回复文件
2. 或者重新抓一次（用更长的 TIMEOUT），但注意不要开新窗口
3. **绝对不要重新问同一个 AI**——浪费窗口，用户会批评

### ⚠️ 三份回复必须全部喂 NLM（本 session 核心教训）

> **2026-07-16 session 犯的致命错误：只喂了 Claude 的回复给 NLM。**
> 用户批评：「实际上你6个窗口都有答案 为啥你只给了一个」
>
> NLM 只有在同时看到三份回复时，才能做完整的共识/分歧分析。
> 只喂一份等于让 NLM 只看到一家的说法，无法交叉验证。

**流程锁死：**
- 在合并前检查 `/tmp/ai-responses/` 下是否三个文件都有内容
- 如果某个文件为空或只有 `[等待回复]` → 从用户那里询问要点，或重新抓取
- **就算某个 AI 的回复抓取不完整，也必须记录"未获取到"并注明原因**，不能瞒报

### 不要重复提问（本 session 反复踩过的坑）

**正确的检查方法：**
```bash
ls -la /tmp/ai-responses/
# 如果已有 001-gemini.md → 不要再问 Gemini
# 如果 002-claude.md 存在且有内容 → 不要再问 Claude
```

**错误的循环：脚本没抓到→重新问→又没抓到→又重新问 → 用户：**
- 「你在重复提问了」
- 「你开了六个窗口全是有答案的 其实你开三个就够了」
- 「你不是已经有三个答案了 为啥还要问一遍」

### 第 4 步：合并到 NLM

```bash
# 创建 NLM 笔记本
nlm create notebook "问题简述-三模型分析"

# 合并三个回复
cat /tmp/ai-responses/001-*.md /tmp/ai-responses/002-*.md /tmp/ai-responses/003-*.md \
  > /tmp/ai-responses/combined.md

# 添加为 NLM 文本源（--wait 等待处理完成）
CONTENT=$(cat /tmp/ai-responses/combined.md)
nlm add text <notebook_id> "$CONTENT" --title "三AI对XXX问题的诊断" --wait
```

### 第 5 步：让 NLM 消化分析

```bash
nlm query notebook <notebook_id> "分析这三份诊断的共识和分歧：
1. 三个AI确认的根因是什么？
2. 修复步骤的优先级建议（按共识度排序）
3. 哪个AI遗漏了什么关键点？
4. 给出一个合并的修复方案"

# 导出完整报告
nlm export report --format markdown > /tmp/ai-responses/nlm-analysis.md
```

### 第 6 步：执行修复 + 归档

拿到 NLM 的合成方案后，按步骤执行。先跑隔离诊断命令确认根因，再进行修复。

**⚠️ 执行铁律：不熟悉的底层配置不要改。**
- 代理协议参数（MTU、Mux、流控）、系统内核参数、网络栈配置
- 如果对某项参数只知其一不知其二 → 先问三 AI + NLM 了解清楚
- 每次只改一项，小步验证，确认稳定再改下一项
- **宁可慢，不能断。** 服务断联的代价远大于慢几分钟。

### ⭐ 安全线：改配置前必须先确认备用通道（2026-07-16 核心教训）

**本 session 犯的致命错误：**
- 改了 MTU 和 Mux 后 kill xray 重启
- xray 没能启动，代理全断
- **没有备用通道**，用户被迫切手机热点才能爬上来
- 用户批评：「你都没设置备用 太有自信了」

**流程锁死：**
```
要改关键配置（代理/网络/系统参数）
  → ❌ 不直接动手
  → ✅ 确认备用通道可用
       ├─ 金同学(Mi8) USB ADB 在线？
       ├─ 手机热点能切？
       └─ 回滚方案准备好了？
  → ✅ 确认通过后再改
```

**改配置的铁律：**
1. **先确保自己永远在线** — 备用通道必须确认可用
2. **一次只改一项** — 改完测试，确认正常再改下一项
3. **有问题先回滚** — 不要试图在原配置上修，先还原到刚才还能用的状态
4. **不熟悉的配置不动** — 对参数含义不确定时，先走三 AI + NLM 流程了解清楚

> **用户原话：「宁慢不断」**
> 「先保证自己永远在线 才能解决问题」
> 「平时你可以不用 但是用到的时候不能没有」

**修复后必须存档到 Obsidian：**
```
~/Documents/Obsidian Vault/土同学工作档案/<问题名>-修复记录.md
```
包含：问题现象、三个AI的差异、NLM合成方案、执行命令、最终结果。

这让每次问题排查留下可追溯的档案，避免下次重走。

## 实战案例

完整的一次运行记录请见 `references/kodi-mouse-case-study.md`。

## 已知陷阱

| 陷阱 | 现象 | 解决 |
|------|------|------|
| **OpenBridge 未连线** | `Failed to open tab` | 检查 Chrome 扩展→检查 `status`→Extension: Connected |
| **AI 未登录** | 返回首页"升级/登录" | 用浏览器手动登录一次，或让用户登录 |
| **抓取到问题回声**（非AI回复） | 输出是你问题的前几个词 | 让用户复述要点，手动补进回复文件 |
| **同时开多个窗口** | 回复混淆/脚本冲突 | ⚠️ **一次只问一个 AI**，等回复再问下一个 |
| **NLM 网络不通** | `nlm` 命令超时 | 测代理：`curl -x socks5://127.0.0.1:10808 https://www.googleapis.com/` |
| **抓到的回复不完整** | 只有几行 UI 文字 | 增加 `stableCount` 等待轮次，或延长 TIMEOUT |
| **只喂了一份给 NLM** | NLM 分析不完整 | ⚠️ **必须将三份回复都喂进同一笔记本**，NLM 才能做共识/分歧分析 |
| **重复问同一个 AI** | 浪费窗口和 token | 每次问完存 `/tmp/ai-responses/`，下次先检查 |
| **执行阶段改不理解的配置** | 改了 MTU 和 Mux 后代理断连 | ⚠️ 不熟悉的底层配置不要盲目修改。逐项小步验证，**稳比快重要** |
| **改配置没留备用通道** | 改坏 xray 后代理全断 | 改之前先检查备用通道（Mi8 USB/手机热点） |
| **browser_press 不被 OpenBridge 允许** | ask-ai.js 按 Enter 不生效，页面没反应 | 改用 `submitViaJS` 函数：通过 `browser_evaluate` 执行 `document.querySelector('[contenteditable=\"true\"]').dispatchEvent(new KeyboardEvent('keydown',{key:'Enter'}))` 或点 send button。ask-ai.js V3 已内置此 fallback |
| **OpenBridge partial fail（2026-07-17）** | Gemini 空欢迎页；ChatGPT click/evaluate 400；ask-ai 超时 | **2 次失败立刻切通道 C/D**，不修浏览器。用 `multi-model-analysis`（讯飞/NVIDIA/知乎）+ `web_search` 社区材料 |
| **三AI 输出危险幻觉** | 建议 `ssh root@192.168.15.244` 而现场是 Docker 假在线 | 提问注入**硬约束**；交付前剔除与实测冲突的命令（见下节） |
| **NLM 合成跳过** | nlm 命令形态/网络慢 | 仍可交付：通道表 + 社区共识 + 过滤后 AI 建议；事后补 NLM，不卡死 |
| **Grok/relay 403** | hetaosu/xhahlf 多 key 403 | 换 NVIDIA/讯飞/知乎或通道 B；不在 403 上连试一堆 key |

## 硬约束 + 幻觉过滤（2026-07-17 锁死）

问任何模型前，把**已证实的否定事实**写进 prompt 顶部：

```
硬约束（必须遵守）：
1) 当前 USB 是 XXX，无 /Volumes/Kindle → 禁止假设已挂载
2) 192.168.15.244 路由走 Docker utun → 禁止建议 ssh/scp 该地址
3) Mac Bridge :8081 实测可用 → 优先走桥
4) Jina TLS 超时 → webbrowser 必须 cre，禁止 markdown
5) 系统浏览器 x509/TEE → 不修系统证书，走 HTTP 桥
```

交付前对照实测表剔除冲突命令。NVIDIA 等常会「补全」成标准 Kindle 教程（重启 dropbear、update-ca-certificates）——与假在线现场冲突时一律删。

**Partial 通道成功也算完成 3AI：** OpenBridge 0/3 → 立刻 multi-model + 社区；API 1/3 有用即可；含危险建议则剔除后交付。

案例：`references/kindle-pw5-3ai-partial-channel-20260717.md`

## 相关技能

- `multi-model-analysis` — API 直连讯飞/NVIDIA/知乎；**OpenBridge 失败时的主备通道**
- `notebooklm-analyze` — 单文章喂 NLM 深度分析
- `notebooklm-research-prep` — 项目前期研究：搜资料→喂 NLM→拿结论
- `web-ai-cdp-bridge` — OpenBridge 浏览器自动化基础
- `mao-search-workflow` — MoA 搜索工作流（通道 B/C 执行层）
- `kindle-troubleshooting` — Kindle 双路径上网/假 USBNet；3AI 流行方案落地
