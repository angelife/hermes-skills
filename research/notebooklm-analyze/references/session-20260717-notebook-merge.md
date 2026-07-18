# 2026-07-17 — NLM 笔记本合并 / 清壳（含落地执行）

## 问题
用户问：两个 notebook 内容相似，可以合并么？后确认 **C = 合并 Agent 两本 + 清空壳**。

## CLI 事实
- `nlm notebook` **无** `merge` / `copy`
- 合并 = 源重加到目标 + `nlm notebook delete <源本> --confirm`
- 跨本问：`nlm cross query` / `nlm batch query`（不必物理合并）
- 上传文件：`nlm source add <target_id> --file "/abs/path.epub" --title "..." --wait`

## 当日列表与处置

| 本 | 源 | 处置 |
|----|----|------|
| AI Agent 设计原理与工程实践 `93c7e6f7-…` | 3→**4** | **目标本**：并入 Design Patterns |
| Agentic Design Patterns - 全书分析 `ea460062-…` | 1（epub, type=unknown, 无 url） | 重加到目标后 **delete** |
| OpenViking 深度消化 | 20 | 留 |
| OpenViking 说明书消化 | 0 | **delete** |
| x.ai-TLS握手-PMTUD诊断（有源） | 4 | 留（ChatGPT/Grok 可后续去重） |
| 同名 / PMTUD 多模型 空壳 | 0 | **delete** |

## 落地步骤（已跑通）

```bash
TARGET=93c7e6f7-eafb-4771-9370-199a7ba610dd
SRC_NB=ea460062-b5f2-497e-9a3d-aa75ce3668ca

# 1) 看源：无 URL 的 epub 必须找本地文件
nlm source list $SRC_NB
# title 形如 Agentic_Design_Patterns_..._1lib_sk,.epub

# 2) 本机定位（Calibre / Kindle / mdfind）
mdfind 'kMDItemFSName == "*Agentic*Design*"c'
# 实测命中：
# ~/Calibre Library/Unknown/Agentic Design Patterns A Hands On Gu z library sk, 1lib sk, (384)/*.epub
# ~/Calibre Library/Antonio Gulli/Agentic Design Patterns_.../*.epub

# 3) 上传到目标并 wait 到 ready
nlm source add "$TARGET" \
  --file "/Users/macos/Calibre Library/Unknown/Agentic Design Patterns A Hands On Gu z library sk, 1lib sk, (384)/Agentic Design Patterns A Hands On Gu z li - Unknown.epub" \
  --title "Agentic Design Patterns - A Hands-On Guide (Antonio Gulli)" \
  --wait --wait-timeout 600
# → Source ID c099b6c7-… (ready)

# 4) 确认目标 4 源后再删源本（不可逆）
nlm source list "$TARGET"
nlm notebook delete "$SRC_NB" --confirm

# 5) 空壳：source list 为 [] 才删
nlm notebook delete 395dfcab-c4f5-492d-a7a2-dcb8ff249c33 --confirm  # OpenViking 说明书
nlm notebook delete 36dfc4e9-6a3d-4ae0-a96f-1c0b4008c737 --confirm  # PMTUD 多模型空
nlm notebook delete f5c85285-8b1a-4cb4-9b7d-d0278f9e17cf --confirm  # TLS 空壳
```

## 原则
- 空壳先删，不谈合并
- 主题相近但材料不同 = 互补，不是重复；可并（交叉问）或 cross query
- 源 `type=unknown` 且 `url=null` → 必找本地 Calibre/Downloads，不能 `source add --url`
- **用户选定 A/B/C 后必须执行到 delete 闭环**；只列清单不算完成（见 angelife-minimal-execution-style M68）
- 不可逆删除前必须 `nlm source list` 确认

## 合并后目标本源（终态）
1. Agentic Design Patterns - A Hands-On Guide (Antonio Gulli) — `c099b6c7-…`
2. Angelife architecture — `c882176c-…`
3. 李博杰 AI Agent PDF — `f7ff69e4-…`
4. small Rust Hermes 三刀法 — `f9b246e7-…`
