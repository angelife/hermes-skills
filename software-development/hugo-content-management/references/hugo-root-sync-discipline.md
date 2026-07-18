# Hugo 根目录同步纪律 — angelife.github.com 版

## 核心认知

`angelife.github.com` 仓库根目录就是 GitHub Pages publish source。
Hugo 在 `hugo-site/public/` 生成的 `categories/`、`series/`、`tags/`、`posts/`、`images/`、`sitemap.xml`、`search/`、`index.xml`、`index.json` 等 taxonomy/listing 产物，在正确同步后必须由根目录承载。

**产物目录 = 站点的发布面，不是旧站残留。**

## 允许清理的手工产物

只清明确的人工产物：
- `.github/workflows`、`PUBLISHING.md`、`tools/` 这类开发元数据脚本/工作流
- `old-site/` 这类显式归档目录
- 临时脚本、备份脚本、异常文件

## 同步纪律

```bash
cd /Users/macos/angelife.github.com
hugo --minify
rsync -av --delete \
  hugo-site/public/ ./
```

- 先明确**保护名单**（根目录必须保留的非 Hugo 产物）
- 再同步 `public/ -> ./`
- 只排除保护名单，不要把生成目录归入手工产物删掉

## 兜底恢复

如果清理过头，用以下命令按 HEAD 恢复：
```bash
git checkout HEAD -- .github tools PUBLISHING.md
```
但 `categories/`、`tags/`、`series/`、`posts/`、`images/` 若未 git 跟踪，只能重新 `hugo` + `rsync`，不能 `git checkout` 回来。

## 症状

- 用户说“一堆 404”
- 根目录链接到 `posts/`、`series/`、`tags/`、`categories/` 却返回 404
- `hugo build` 成功，但 `grep -c '<title>' public/tags/` 远大于 `ls tags/`

这几乎都是 taxonomy 产物被错误清理的经典信号。
