# Group Overview Scan — Quick Inventory from Decrypted.db

Use this as the **first step** when asked about "有哪些群" or "抓群信息".
Lists all chatrooms, identifies names, message counts, type distribution, last activity.

## Single-pass Overview Query

```sql
SELECT 
  c.chatroomname,
  r.nickname,
  c.displayname,
  c.memberCount,
  c.roomowner,
  (SELECT COUNT(*) FROM message m WHERE m.talker = c.chatroomname) AS msg_count,
  (SELECT MAX(m.createTime) FROM message m WHERE m.talker = c.chatroomname) AS last_msg_ts
FROM chatroom c
LEFT JOIN rcontact r ON c.roomowner = r.username
ORDER BY msg_count DESC;
```

## Per-Group Message Type Distribution

```sql
SELECT 
  c.displayname,
  m.type,
  CASE m.type 
    WHEN 1 THEN '文字' WHEN 3 THEN '图片' WHEN 34 THEN '语音'
    WHEN 42 THEN '名片' WHEN 43 THEN '视频' WHEN 47 THEN '表情'
    WHEN 49 THEN '链接' WHEN 10000 THEN '系统' WHEN 436207665 THEN '红包'
    ELSE CAST(m.type AS TEXT)
  END AS type_name,
  COUNT(*) AS cnt
FROM message m
JOIN chatroom c ON m.talker = c.chatroomname
GROUP BY c.chatroomname, m.type
ORDER BY c.displayname, cnt DESC;
```

## Last N Messages Per Group

```sql
SELECT t.* FROM (
  SELECT c.displayname,
         m.createTime,
         CASE WHEN m.isSend=1 THEN '我'
              ELSE SUBSTR(m.content, 1, INSTR(m.content, ':')-1)
         END AS sender,
         SUBSTR(m.content, 1, 150) AS snippet,
         ROW_NUMBER() OVER (PARTITION BY m.talker ORDER BY m.createTime DESC) AS rn
  FROM message m
  JOIN chatroom c ON m.talker = c.chatroomname
  WHERE m.type = 1 AND m.content > ''
) t WHERE t.rn <= 5
ORDER BY t.displayname, t.createTime DESC;
```

## Python Wrapper (for quick run)

```python
import sqlite3, time
db = '/tmp/Decrypted.db'
con = sqlite3.connect(db)
groups = con.execute("""
  SELECT chatroomname, COALESCE(displayname,chatroomnick,'') AS name,
         memberCount, modifytime, chatroomnotice
  FROM chatroom ORDER BY modifytime DESC
""").fetchall()
for r in groups:
    name = r[1].strip() or (r[0].split('@')[0] if '@' in r[0] else r[0])
    cnt = con.execute("SELECT COUNT(*) FROM message WHERE talker=?", (r[0],)).fetchone()[0]
    last = con.execute("SELECT createTime FROM message WHERE talker=? ORDER BY createTime DESC LIMIT 1", (r[0],)).fetchone()
    t = time.strftime('%Y-%m-%d %H:%M', time.localtime(last[0])) if last else '?'
    print(f"{name[:30]:30s} {r[2]:>3d}人  {cnt:>5d}条  最后:{t}")
```

## Search Groups by Name Keyword

```python
kw = '半神'
rows = con.execute("""
  SELECT chatroomname, displayname, chatroomnick, memberCount
  FROM chatroom 
  WHERE displayname LIKE ? OR chatroomnick LIKE ?
  ORDER BY memberCount DESC
""", (f'%{kw}%', f'%{kw}%')).fetchall()
```

## Key Fields in chatroom Table

| Column | Type | Meaning |
|--------|------|---------|
| chatroomname | TEXT | Unique room ID (e.g. `43155769439@chatroom`) |
| displayname | TEXT | Display name (may be empty if chatroomnick is the primary name) |
| chatroomnick | TEXT | Nickname set by user |
| memberCount | INTEGER | Current member count |
| roomowner | TEXT | Owner's wxid |
| chatroomnotice | TEXT | Group announcement text |
| modifytime | LONG | Last modification timestamp (ms) |
