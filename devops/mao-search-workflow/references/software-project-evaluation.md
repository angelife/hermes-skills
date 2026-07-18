# Software Project Trustworthiness Evaluation

## 适用场景

当用户要求评估一个开源项目（工具、框架、服务）的真实性和可靠性时，走此流程。

## 标准搜索维度（六轴）

每个维度独立搜索，全部并行发起。禁止跳过任何维度。

### 1. GitHub 项目健康度

- **Stars**：绝对值 + 增长速度（是否近期上了 Trending）
- **Commits**：总数 + 近期频率（活跃 / 停滞）
- **Releases**：版本号 + 发版间隔（每日/每周/每月）
- **Contributors**：单维护者 vs 多人
- **Known Issues**：开放 issue 数 + 严重 bug 比例

**搜索方式**：
```
web_search("<project> GitHub stars issues")
web_extract("https://github.com/<author>/<project>")
web_extract("https://github.com/<author>/<project>/issues")
```

### 2. 包管理器数据

- **Download count**（npm / PyPI / crates.io 等，看周下载趋势）
- **Version count**（发布时间跨度，是否稳定迭代）
- **Dependencies**（依赖数量，是否有风险依赖）

**搜索方式**：
```
web_extract("https://www.npmjs.com/package/<package>")
# 或
web_search("<package> weekly downloads npm")
```

### 3. 社区口碑

- **Reddit**：搜索 r/ 相关版块的真实讨论
- **Developer blogs**：找独立技术博客的深度评测（非推广文）
- **YouTube**：教程视频的数量和评论质量（有真实用户演示的 > 纯概念介绍）
- **Twitter/X**：技术意见领袖的评价

**搜索方式**：
```
web_search("<project> reddit review OR experience")
web_search("<project> review OR guide OR tutorial")
web_search("<project> site:medium.com OR site:dev.to")
web_search("<project> site:youtube.com tutorial")
```

### 4. 实际 Bugs 和 Issue 质量

- 打开几个最高星号 issue，看**是否被维护者回复**、**是否已修复**
- 看 issue 内容类型：配置问题（正常） vs 安全漏洞（需关注） vs 核心功能 bug（风险）
- 注意 issue 关闭率

**搜索方式**：
```
web_extract("https://github.com/<author>/<project>/issues?q=is%3Aissue+is%3Aopen+sort%3Areactions-%2B1-desc")
```

### 5. 安全性评估

- **密钥存储方式**（明文 / 加密 / 本地 / 云端）
- **数据路径**（通过第三方代理中继 / 直连供应商）
- **审计性**（代码是否可审计，许可证类型）
- **Security Policy**（有 SECURITY.md + 披露流程 > 没有）
- **已知 CVE / advisory**

**搜索方式**：
```
web_extract("https://github.com/<author>/<project>/security")
web_extract("https://github.com/<author>/<project>/wiki/Security")
web_search("<project> security OR vulnerability")
```

### 6. 竞争对比

- 同类项目列表（至少 2-3 个竞品）
- 按核心功能对比（支持供应商数、免费线路数、路由策略、部署方式、费用模式）

**搜索方式**：
```
web_search("<project> vs <competitor1> vs <competitor2>")
web_search("alternative to <project> 2026")
```

## 免费额度真实性核查（工具类项目特有）

当项目声称 "90+ free providers" 或类似数字时：

1. **分类核实**：区分 API Key 免费 / OAuth 免费 / Web Cookie 免费
2. **样品验证**：捡 2-3 条标注"免费永远"的线路，验证其注册门槛（是否需要信用卡？是否需要浏览器 cookie？）
3. **容量声明**："~1.6B 免费 tokens/月" 是否标注了计算方法
4. **撤回风险**：免费线路由第三方供应商控制，标注此风险

## 可信度判定标准

| 等级 | 条件 |
|------|------|
| 高 | ≥3 个维度有独立可靠来源，且无重大矛盾 |
| 中 | 1-2 个维度验证通过，但项目太新（<6 个月）或单维护者 |
| 低 | 无法验证核心声明，或发现明显虚假宣传 |

## 输出模板

```markdown
## 项目健康度
| 指标 | 数据 | 信号 |
|------|------|------|
| Stars | ~9.8k（2026-07） | ⭐ 快速上升 |
| ... | ... | ... |

## 社区口碑
| 来源 | 信号 |
|------|------|
| Reddit r/... | 正面/负面 |
| ... | ... |

## 免费额度真实性
| 宣称 | 核实结果 |
|------|----------|
| 90+ free providers | 分三类评估 |
| ... | ... |

## 综合评估
| 维度 | 判断 |
|------|------|
| 不是割韭菜 | ✅/⚠️/❌ |
| 值得一装 | ✅/⚠️/❌ |
| 风险 | ... |
| 建议用法 | ... |
```
