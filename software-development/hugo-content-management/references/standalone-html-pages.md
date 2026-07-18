# 在 Hugo 站点中部署独立 HTML 页面

用于替换过时的 Hugo 内容页（如 about）或新增非文章类页面（如架构图）。

## 方法

1. 创建 `static/<page>/index.html` — 纯静态 HTML，Hugo 构建后直接复制到 `public/<page>/`
2. **⚠️ 关键：static 文件优先级低于 content。** 如果 `content/<page>/index.md` 存在，Hugo 会先生成 markdown 页，static 文件无法覆盖。**必须删除或重命名 content 下的对应文件**，static 才生效。
3. Hugo 菜单项照常配，`url = "/<page>/"` 即可

## 页面合并与删除（2026-07-16 更新）

**内容以新的为主，旧的淘汰了。** 当两个页面本质上是一件事（如 about = 架构介绍）时：

1. **合并内容** — 旧页面的关键信息嵌入目标页面（如架构图页顶部加「关于安知生」卡片）
2. **彻底删除旧文件** — `rm content/<path>/index.md` 和 `rm static/<path>/index.html`，不留备份
3. **更新所有链接** — 菜单 `hugo.toml`、首页 `_index.md`、自定义模板 `layouts/index.html` 中旧 URL 全部替换为目标页面
4. **不留 .bak、不留重定向、不留 git rename 追踪**

**已废弃**：`<meta http-equiv="refresh">` 重定向。用户明确纠正过 —— 重定向是半吊子方案，直接删干净。

## 重要：导航栏（必加）

独立 HTML 页面没有 Hugo 主题自动注入的导航栏。——用户已明确纠正过这一点。

模板（直接放在 `<body>` 后）：

```html
<div class="nav-bar" style="text-align:center;margin-bottom:30px;font-size:12px;">
  <a href="/" style="color:#64748b;text-decoration:none;margin:0 10px;">首页</a>
  <a href="/archives/" style="color:#64748b;text-decoration:none;margin:0 10px;">归档</a>
  <a href="/series/" style="color:#64748b;text-decoration:none;margin:0 10px;">栏目</a>
  <a href="/kindle/" style="color:#64748b;text-decoration:none;margin:0 10px;">📖 Kindle</a>
</div>
```

有 v1/v2 双版本时，加分隔符链接到另一版：
```html
<span style="color:#475569;margin:0 10px;">|</span>
<a href="/knowledge-architecture/v2/" style="color:#fb7185;">v2 含 Emacs</a>
```

## 部署与验证

每次修改后**全流程一次性完成**，不要在中途停下来等用户确认：

```bash
cd ~/angelife.github.com/hugo-site
hugo --minify
rsync -av hugo-site/public/ ~/angelife.github.com/
cd ~/angelife.github.com
git add hugo-site/static/<page>/ <page>/ hugo-site/hugo.toml hugo-site/layouts/index.html  # 精确 add，不用 -A
git commit -m "..." --no-verify
git push origin main
```

### 验证（必须）

推送后立即验证线上效果，不等用户说"没看到更新"：

```bash
# 确认 push 已完成
git log --oneline -1
# 抓线上页面确认内容
curl -s https://angelife.github.io/<page>/ | grep "关键文本片段"
```

如果线上仍显示旧内容，可能是 GitHub Pages CDN 缓存（1-3 分钟），告知用户已推送。

### Git 坑

- **`--no-verify` 必须** — gpg-sign 或 hooks 会挂死 30s+
- **`git add -A` 慎用** — `.tmp.driveupload/` 和大量 Hugo 生成的 HTML 会一起被 stage
- **分支名是 `main`，不是 `master`**
- **rsync 可能显示 `ok (synced)` 但实际有变更** — 用 `git status` 确认

## 适用场景

- 架构图/信息图等纯 SVG 页面
- 需要精确定制 CSS/JS 的页面
- **已废弃**：替换过时的 markdown 内容页（2026-07-16 起，应该直接合并删除，不保留旧路径）

## 注意事项

- 导航栏菜单项仍然在 `hugo.toml` 的 `[[menu.main]]` 中配置
- 首页（`_index.md`）需要手工添加链接；如果首页用了自定义 `layouts/index.html` 模板，则 `_index.md` 不会被渲染，链接直接写进模板
- 旧版内容页删除后不可恢复（git 历史中有），不需要额外保留
