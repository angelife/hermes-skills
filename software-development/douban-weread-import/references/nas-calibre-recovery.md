# NAS 旧书库 / Calibre 索引找回

## 适用场景

用户有 NAS，且 NAS 上存的是**电子书文件**，不是 Zotero 库。通过文件名 `.sdr` 可判断为 **Calibre** 结构。

## 已探明的实际结构（蜗牛星际 / U-NAS）

- SMB 共享：`smb://192.168.1.24/book_book1_book`
- 顶层大量电子书文件：`.pdf` `.epub` `.mobi` `.azw3`
- 同一目录下可见大量 `.sdr` 文件夹：这是 Calibre 元数据目录
- `data/` 目录可能存在 `metadata.db`，但常见权限为只读 Unable to list。

## 总结

这里的“索引”不是 Zotero，是 **Calibre**。若 `data/metadata.db` 可读，可直接用 sqlite3 提取：
- title
- authors
- isbn
- publisher
- pubdate
- tags
- series
- rating

## 恢复路径

1. 优先确认 NAS 挂载：`/Volumes/book_book1_book`
2. 查找 `metadata.db`：`find /Volumes/book_book1_book -name 'metadata.db'`
3. 若 `data/` 无权限列表，尝试 SSH/SFTP 直接从 NAS 系统读取，或让用户在 NAS Web UI / 终端复制到可读共享
4. 解析 Calibre `metadata.db`，生成 Obsidian 书库补丁批

## 当前卡点

- macOS SMB guest 挂载后 `data/` 无列表权限
- SSH `admin@192.168.1.24` password auth denied
- 解法：让用户在 NAS 终端把 `metadata.db` 复制到 `book_book1_book` 顶层可读位置
