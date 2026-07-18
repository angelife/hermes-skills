# 2026-07-17 — 不要用 webbrowser 下书

## 纠正
用户：「浏览器问题 之前不是没解决么」

## 错误方案
Mac 起 `python -m http.server 8000`，让用户在 KOReader/系统浏览器打开 `http://192.168.0.171:8000/` 下 PDF。

## 为何错
- Experimental Browser：x509/TEE 已知坏
- webbrowser.koplugin：依赖 cre/Jina，不是稳定传文件通道
- 同 WiFi 只保证 L3，不恢复浏览器

## 正确
见 `kindle-diagnostics`「传文件到 KOReader」：Calibre 无线 > SSH.koplugin > USB 挂盘。
