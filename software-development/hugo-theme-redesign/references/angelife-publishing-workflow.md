# Angelife GitHub Pages 发布工作流

来源: `CODEX_HANDOFF.md`（仓库根目录 `/Users/macos/angelife.github.com/`）

## 完整发布步骤

```bash
# 1. 本地构建（生成 hugo-site/public/）
cd /Users/macos/angelife.github.com/hugo-site
hugo --minify

# 2. 同步生成文件到仓库根目录
cd /Users/macos/angelife.github.com
rsync -av hugo-site/public/ ./

# 3. 确认改动范围
git status --short
git diff --stat

# 4. 精确定位要 add 的文件（不要 git add .）
git add <明确文件列表>

# 5. Commit + push
git commit -m "posts: 文章标题"
git push origin master

# 6. 创建并推送 tag
git tag -a VERSION -m "VERSION: 版本描述"
git push origin VERSION
```

## 关键规则

- **不要 `git add .`** — 必须精确指定文件列表
- **不要提交 `_incoming/` 目录下的文件**
- **rsync 前先确保 hugo build 成功**（0 errors, 0 warnings）
- **`hugo-site/public/` 在 `.gitignore` 之外** — 生成文件需要同步到根目录
- **不要修改** `old-site/`, `themes/`, `_incoming/`
- **谨慎修改** `layouts/`, `static/css/`

## Workflow 的执行顺序

按 CODEX_HANDOFF.md 的定义，发布分三个连续阶段：

1. **Build phase** — `cd hugo-site && hugo --minify`
2. **Sync phase** — `rsync -av hugo-site/public/ ./`（从子目录复制到仓库根）
3. **Git phase** — 精确 add → commit → push → tag

**缺少任意一个阶段，发布都不完整。** 只做 git push 源码（不做 rsync）会导致仓库根目录的生成文件与源码版本不匹配。

## 关键: 域名记忆

**仓库名是 `angelife.github.com`，但实际域名是 `angelife.github.io`。** Hugo 配置 `baseURL = "https://angelife.github.io/"`。

发布验证时，访问的是 `curl https://angelife.github.io/slug/`，**不是** `.com`。每次告诉用户文章地址时，必须用 `.io`。

## 注意事项

- **第一次发布新文章**：需要在 `hugo-site/content/posts/` 下创建文章目录和 `index.md`
- **文章 frontmatter 需要有 slug 字段**，否则 Hugo 会用中文标题生成 URL
- **文章 date 必须正确**，Hugo 默认只显示过去/当前日期的文章（`buildFuture: true` 已启用）
- **发布后等待 GitHub Actions 完成**（约 1-2 分钟），然后 curl 验证 HTTP 200
- **Tag 版本号**格式参考已有 tags（`git tag -l` 查看历史）
- **如果发布后 GitHub Pages 404**：检查 GitHub Actions 是否成功、slug 是否正确、`hugo --minify` 是否通过
