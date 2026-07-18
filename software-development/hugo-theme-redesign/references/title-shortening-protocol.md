# Title Shortening Protocol

## Rule

When asked to shorten titles to ≤10 chars, do NOT blindly truncate the first N characters.

## Why

Blind truncation collapses distinct articles into identical short titles. Example: 19 articles in the 教会史 series all become `轨迹` if you only keep the first 2 characters.

## Required Tie-Breaker

Use an existing unique identifier from the article itself:
- slug suffix
- sequence number already present in frontmatter/slug
- second meaningful keyword from title
- date segment if it adds no value to shorten

Format: `head + identifier`, not just `head`.

## Examples

| original | bad | good |
|---|---|---|
| 历史的轨迹 -- 二千年教会史（续2） | 轨迹 | 轨迹1 |
| 历史的轨迹 -- 二千年教会史（续10） | 轨迹 | 轨迹9 |
| Cloudflare Workers AI 零成本接入 Hermes Agent 完整教程 | Cloudflare | WorkerAI指南 |
| 小米 8（SD845）外接 USB 网卡全面踩坑：四款芯片无一幸免 | 小米 8(SD845 | USB调试 |

## Workflow

1. Derive short titles.
2. Group by intended short title.
3. Any group with >1 candidate is a collision; apply tie-breaker before editing.
4. Edit frontmatter `title:` and regenerate/verify rendered output.
