# Upgrade Audit Prompt Template

Use this when the user wants to ask an external AI (ChatGPT, Claude, etc.) for code-level upgrade risk assessment. Fill in the placeholders with actual git diff data from step 6b.

---

```
请对 [SYSTEM] v[CURRENT_VERSION]（tag [CURRENT_TAG]）→ v[TARGET_VERSION]（tag [TARGET_TAG]）做升级兼容性审计。

以下是从仓库实际拉取的 diff 和 commit 数据，请基于这些数据做具体分析，不是泛泛推测。

【仓库地址】
[REPO_URL]
[N] commits 在 [CURRENT_VERSION]→[TARGET_VERSION] 之间。

【Config schema】
- src/hermes_agent/config/ 目录：文件变化情况
- gateway/config.py：N 行新增 / N 行删除
- hermes_cli/config.py：N 行新增
- Migration 文件：是否新增或修改
- 请检查 config schema 版本是否变化、是否存在自动 migration、旧 config 是否可直接读取、是否存在静默忽略旧字段或默认值覆盖的风险

【Skill API / Hook】
- src/hermes_agent/skill/*.py：文件变化情况
- skills/ 目录：变化统计（文件数 + 变化类型）
- skill manifest / hook lifecycle / tool registration API 是否变化？

【State / Session】
- 相关 commits（从 git log --grep 输出）：
  [LIST]
- state module 是否有变更？session lifecycle / /new behavior / memory extraction 是否有变化？

【Telegram / Provider / Fallback】
- 相关 commits：
  [LIST]
- Telegram connectivity 协议变更？provider 抽象层变化？fallback 链路变化？

【Config 文件变化统计】
gateway/config.py 和 hermes_cli/config.py 是主要变化点。请检查：
- schema version 判断逻辑
- 新必填字段
- 旧字段废弃/删除
- 配置文件加载流程变化

请回答以下问题：
1. Config schema 是否有 breaking change？
2. 50+ 自定义 skill 是否需要修改才能运行在目标版本上？
3. Telegram Gateway 是否存在不兼容风险？
4. Persistent state 系统是否受影响？
5. 推荐的升级操作（git checkout [TARGET_TAG]）和回滚方式
6. 目标版本作为稳定升级目标的最终结论

输出格式：
 1. Config migration — 是否存在 migration：风险等级：具体 diff：
 2. Skill compatibility — manifest：hooks：tools API：
 3. Known issues — issue/commit/changelog：
 4. Upgrade procedure — 推荐命令：回滚方式：
 5. 最终结论 — [ACCEPT / CONDITIONAL / REJECT] 及理由
```

## Usage Notes

- The prompt forces the external AI to reference actual file-level diff data (not version numbers alone), which prevents vague "should be compatible" answers.
- If any critical diff zone shows zero file changes, explicitly state that in the prompt — it's strong evidence of no breaking changes.
- Include the `git diff --stat` summary rather than full diff to keep the prompt focused.
- For the session/state section, include the full `git log --oneline` output for the grep pattern so the AI can spot relevant commits that might not be caught by the grep filter.
- The output format at the end restricts hallucinations — the AI must produce specific answers to specific questions, not a narrative.
