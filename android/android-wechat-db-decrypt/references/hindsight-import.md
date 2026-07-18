# Hindsight 导入规则 ⚠️

**被用户严厉纠正过：外部文章链接不进记忆层。**

## 什么可以存 / 不可以存

| ✅ 可存 | ❌ 不可存 |
|---------|----------|
| 个人经验、决策、判断 | 公众号文章链接 |
| 技术方案选择、踩坑记录 | 文章标题+URL 摘要 |
| 用户行为模式、偏好 | 微信消息原文 |
| **读文章后提炼的洞察** | 任何不确定是否相关的原始数据 |

## 数据流向（严格顺序）

```
解密 DB → 提取文章链接 → 列给用户选
                              ↓
                         用户选几篇
                              ↓
                         读文章内容 → 提炼洞察 → 存 Hindsight
```

## 正确存储示例

```python
# ✅ 存的是提炼后的洞察，不是原文
requests.post("http://127.0.0.1:8888/v1/default/banks/hermes/memories", json={
    "items": [{
        "content": "Skill 蒸馏方法：核心是反复加和删，AI 能帮你加但删要靠人。目标是越来越短而不是越来越全。",
        "context": "读《Skill不是越写越长是越蒸越准》后提炼",
        "tags": ["insight", "skill-writing"]
    }]
})

# ❌ 不要存文章链接（被用户严厉纠正过）
# { "content": "文章: xxx | 链接: https://mp.weixin.qq.com/s/xxx" }
```

## 操作流程

1. 解密 DB → 提取 type=49 含 `mp.weixin.qq.com` 的消息
2. 列出文章标题+时间给用户（最多 20 条即可）
3. 用户选择要看哪几篇（这个步骤不能跳过）
4. 读选定文章的内容
5. 提炼有价值的洞察
6. 洞察存入 Hindsight，**不存原始链接**

## 技术细节

```python
# 提取文章
import re
url = re.search(r'<url>(https?://mp\.weixin\.qq\.com/s/[^<]+)</url>', content)
title = re.search(r'<title>([^<]+)</title>', content)

# 时间比较用 Python 算毫秒，不要在 sqlcipher 里用 strftime
from datetime import datetime, timezone, timedelta
cutoff = int((datetime.now(timezone.utc) - timedelta(hours=24)).timestamp() * 1000)
```
