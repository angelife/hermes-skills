# BrowserAct 评估与 ChatGPT 架构评审摘要

> 生成日期：2026-07-10
> 来源：ChatGPT 架构审查

## 核心结论

问题不是"找一个更强的浏览器工具"，而是"Hermes 缺少浏览器执行抽象和失败恢复机制"。

## 三层架构（必须拆分）

```
BrowserProvider      — navigate / click / input / screenshot
ChallengeHandler     — detect / solve / escalate (captcha)
HumanAssist          — request / wait / resume (manual override)
```

不要把它们揉成一个巨大接口。

## 优先级排序

1. **人工 CAPTCHA 兜底标准化**（★★★★★）— 收益最高，不改 CDP
2. **Playwright persistent context + stealth**（★★★★☆）— Intel Mac 可用
3. **API fallback**（★★★★☆）— 长期稳定
4. **undetected-chromedriver**（★）— 不碰，换技术栈代价太大
5. **BrowserAct**（★★★）— 可作为高级 backend，但不是第一优先级

## 关于 BrowserAct 的正确认知

- ✅ 能降低 CAPTCHA 触发概率
- ❌ 不能保证绕过 Google 风控
- ❌ 不是 CAPTCHA 解决器
- ✅ 有价值的浏览器基础设施增强器

## 最终架构判断

```
Hermes
  BrowserProvider
    ├── CDP backend
    ├── Playwright backend
    ├── BrowserAct backend
    └── API backend
  
  ChallengeManager
    ├── BrowserAct solver
    └── Manual
  
  HumanManager
    ├── Telegram
    └── Local UI
```
