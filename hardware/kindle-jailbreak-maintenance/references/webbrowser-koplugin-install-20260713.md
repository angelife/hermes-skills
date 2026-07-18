# webbrowser.koplugin v0.7.0 安装与排查记录

## 场景
Kindle Paperwhite 5 (5.16.2.1.1, LanguageBreak 越狱, KOReader v2026.03 已装)。
Experimental Browser 无法加载网页（网络层正常），安装 webbrowser.koplugin 作为替代。

## 安装过程

```bash
cd /tmp
curl -sL "https://github.com/omer-faruq/webbrowser.koplugin/archive/refs/tags/v0.7.0.tar.gz" -o webbrowser.tar.gz
tar xzf webbrowser.tar.gz
mkdir -p /Volumes/Kindle/koreader/plugins/webbrowser.koplugin/
cp -r /tmp/webbrowser.koplugin-0.7.0/* /Volumes/Kindle/koreader/plugins/webbrowser.koplugin/
```

## 插件注册路径

`_meta.lua`:
```lua
name = "webbrowser"
fullname = "Web Browser"
version = "0.7.0"
```

注册代码 (main.lua:1918-1927):
```lua
function WebBrowser:addToMainMenu(menu_items)
    menu_items.webbrowser = {
        sorting_hint = "search",
        text = _("Web Browser"),
        callback = function()
            self:showSearchDialog()
        end,
    }
end
```

## 配置文件

插件通过 `pcall(require, "webbrowser_configuration")` 加载配置。
仓库中只有 `webbrowser_configuration.sample.lua`，没有 `webbrowser_configuration.lua`。
当 config missing 时 `CONFIG_MISSING=true`，插件使用默认配置。

## 已知问题

- KOReader 必须**完全退出再启动**才能加载新插件，待机唤醒不够
- 配置文件缺失不影响菜单注册，插件在 CONFIG_MISSING 状态下仍正常工作（使用 DuckDuckGo HTML 搜索默认）
- 需要 DuckDuckGo HTML 端点（`https://duckduckgo.com/html/`）+ Jina AI Markdown 转换（`https://r.jina.ai/`）正常工作

## 相关资源

- GitHub: https://github.com/omer-faruq/webbrowser.koplugin
- 插件功能：DuckDuckGo/Brave/Tavily/Exa 搜索、Markdown/CRE/MuPDF 三种渲染模式、书签管理、离线保存
