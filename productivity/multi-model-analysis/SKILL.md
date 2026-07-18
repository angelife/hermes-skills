---
name: multi-model-analysis
description: 多模型并行分析 — 三个模型同时点评同一内容，MoA 聚合输出，覆盖观点/亮点/局限/风险等多个维度
triggers:
  - "分析一下这篇文章"
  - "你怎么看"
  - "帮我审稿"
  - "三个模型一起看"
  - 微信文章 / URL / 文本需要多视角点评
  - /moa 命令
---

# Multi-Model Analysis — 多模型并行分析

## 核心工作流

当用户发来文章/链接/内容，要求分析、评价、审稿时：

1. **提取内容** — 用 `web_extract` 抓取文章正文
2. **构造摘要** — 把文章压缩成 300-500 字的摘要段落（核心步骤、关键数字、结论）
3. **并行调用三个模型** — Python `urllib` 同时发请求
4. **聚合输出** — 按维度（观点/亮点/风险）分行对比展示，不做二次综合

## 为什么用三个模型

单一模型有立场盲区。三个模型各有侧重：
- **讯飞**：工程视角强，擅长方法论提炼
- **NVIDIA (llama)**：结构化表达，擅长分点列举
- **知乎直答**：背景知识丰富，擅长风险评估

## 标准 Prompt 模板

```
你是技术审稿人。请分析这篇文章：①核心观点与价值 ②亮点 ③局限/风险 每点2-3句话，简洁有力。

文章：
{摘要内容}
```

## Python 并行调用模板

```python
import urllib.request, json, time

TS = str(int(time.time()))
ZHIHU_KEY = '你的知乎key'
XF_KEY = '你的讯飞key'
with open('/Users/macos/.hermes/.env') as f:
    for line in f:
        if 'NVIDIA' in line and ('API' in line or 'KEY' in line):
            NV_KEY = line.split('=', 1)[1].strip()
            break

PROMPT = f"你是技术审稿人。请分析这篇文章：①核心观点与价值 ②亮点 ③局限/风险 每点2-3句话，简洁有力。\n\n文章：\n{摘要}"

results = {}

# 讯飞
try:
    body = json.dumps({"model":"xopqwen36v35b","messages":[{"role":"user","content":PROMPT}],"max_tokens":350}).encode()
    req = urllib.request.Request(
        "https://maas-api.cn-huabei-1.xf-yun.com/v2/chat/completions",
        data=body, headers={"Authorization":f"Bearer {XF_KEY}","Content-Type":"application/json"}
    )
    with urllib.request.urlopen(req, timeout=25) as r:
        results['讯飞'] = json.loads(r.read())['choices'][0]['message']['content']
except Exception as e:
    results['讯飞'] = f"ERROR: {e}"

# NVIDIA
try:
    body = json.dumps({"model":"meta/llama-3.1-8b-instruct","messages":[{"role":"user","content":PROMPT}],"max_tokens":350}).encode()
    req = urllib.request.Request(
        "https://integrate.api.nvidia.com/v1/chat/completions",
        data=body, headers={"Authorization":f"Bearer {NV_KEY}","Content-Type":"application/json"}
    )
    with urllib.request.urlopen(req, timeout=25) as r:
        results['NVIDIA'] = json.loads(r.read())['choices'][0]['message']['content']
except Exception as e:
    results['NVIDIA'] = f"ERROR: {e}"

# 知乎直答
try:
    body = json.dumps({"model":"zhida-thinking-1p5","messages":[{"role":"user","content":PROMPT}],"max_tokens":350}).encode()
    req = urllib.request.Request(
        "https://developer.zhihu.com/v1/chat/completions",
        data=body, headers={"Authorization":f"Bearer {ZHIHU_KEY}","X-Request-Timestamp":TS,"Content-Type":"application/json"}
    )
    with urllib.request.urlopen(req, timeout=25) as r:
        results['知乎'] = json.loads(r.read())['choices'][0]['message']['content']
except Exception as e:
    results['知乎'] = f"ERROR: {e}"

for k, v in results.items():
    print(f"\n{'='*40}")
    print(f"【{k}】")
    print(v)
```

## 知乎直答的特殊认证

知乎 API 必须动态时间戳，每次请求前重新生成：

```python
TS = str(int(time.time()))  # 必须每次请求前更新，不能硬编码
```

硬编码时间戳会导致 `400 invalid character '\n'` 错误。

## 输出格式

按维度分行对比，不做二次综合：

```
## 🔍 MoA 三模型审稿：《文章标题》

### ① 核心观点与价值
| 模型 | 点评 |
|---|---|
| **讯飞** | ... |
| **NVIDIA** | ... |
| **知乎** | ... |

### ② 亮点
（同上）

### ③ 局限/风险
（同上）
```

## 诊断类任务（非审稿）

用户要求「推给 3AI / 按流行方案分析」且 OpenBridge 不可用时，本技能是 **triple-ai-nlm-synthesis 的通道 C 主备**：

1. 实测事实写 **硬约束** 置顶（禁止假设已挂载 Kindle、禁止 ssh 假在线 IP）
2. 并行调 讯飞 / NVIDIA / 知乎（失败标 ERROR，不重试死磕）
3. **Partial OK**：1/3 有用即可；对照实测剔除危险命令后再交付
4. 与 `web_search` / 已有 skill 文档交叉验证；能喂 NLM 则喂，不能则写 `final-synthesis.md`

### 硬约束 prompt 头

```
硬约束（必须遵守）：
1) …已证实否定事实…
禁止：与上述冲突的 ssh/scp/删证书/重刷 建议
输出：根因分层 + 立刻可用 + 插盘后 + 不要做 + 验收清单
```

### 幻觉过滤

- 建议 SSH `192.168.15.244` 但 Mac 无 `192.168.15.1` / 路由 `utun*` → **删**
- 建议 `rm -rf /etc/ssl` 修浏览器 → **删**（流行方案是 HTTP 桥）
- 建议 `render_type=markdown` 而 Jina TLS 超时 → **改 cre**

## 已知坑

1. **知乎 key 有效但返回 404**：端点路径是 `/v1/chat/completions`，不是 `/api/v1/...`
2. **macOS `nc -W` 语法错误**：用 `-w` 替代 `-W`
3. **hermes `-z` MoA 超时**：120s 限制，MoA 需要聚合三个模型回答，容易超时。直接用 Python 并行调用更稳定。
4. **讯飞 500 / 知乎 554 mid-origin**（2026-07-17）：标 ERROR 继续，不把整次 3AI 判失败；NVIDIA 常仍可用。
5. **NVIDIA 会编造标准 Kindle SSH 教程**：诊断任务必须硬约束 + 人工过滤，不能原样执行。