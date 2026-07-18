# Chatroom Content Analysis — SQL Query Suite

Full query set for analyzing a WeChat group from a decrypted `EnMicroMsg_decrypted.db`.

## 1. Group Overview

```sql
SELECT 
  chatroomname,
  memberCount,
  displayname,
  roomowner,
  selfDisplayName,
  chatroomnotice,
  chatroomnoticePublishTime,
  modifytime
FROM chatroom 
WHERE chatroomname = '<chatroom_id>';
```

## 2. Member Nicknames (via rcontact)

```sql
SELECT DISTINCT r.username, r.nickname, r.conRemark
FROM rcontact r
WHERE r.username IN (
  SELECT value FROM json_each('<member_wxid_json_array>')
)
ORDER BY r.username;
```

Derive the member wxid list from the `chatroom` table's memberlist blob or from `substr(content, 1, instr(content, ':'))` on received messages.

## 3. All Chatrooms — Message Count & Last Activity

```sql
SELECT c.chatroomname, 
       (SELECT COUNT(*) FROM message WHERE talker = c.chatroomname) as msg_count,
       (SELECT MAX(createTime) FROM message WHERE talker = c.chatroomname) as last_msg
FROM chatroom c
ORDER BY msg_count DESC;
```

## 4. Time Range

```sql
SELECT 
  MIN(createTime) as first_msg_ts,
  MAX(createTime) as last_msg_ts,
  datetime(MIN(createTime)/1000,'unixepoch','localtime') as first_msg,
  datetime(MAX(createTime)/1000,'unixepoch','localtime') as last_msg
FROM message WHERE talker = '<chatroom_id>';
```

## 5. Message Type Distribution

```sql
SELECT type, 
  CASE type 
    WHEN 1 THEN '文字'
    WHEN 3 THEN '图片'
    WHEN 34 THEN '语音'
    WHEN 42 THEN '名片'
    WHEN 43 THEN '视频'
    WHEN 47 THEN '表情'
    WHEN 48 THEN '位置'
    WHEN 49 THEN '链接/文章'
    WHEN 10000 THEN '系统消息'
    WHEN 436207665 THEN '红包'
    ELSE '其他('||type||')'
  END as type_name,
  COUNT(*) as count
FROM message 
WHERE talker = '<chatroom_id>'
GROUP BY type
ORDER BY count DESC;
```

## 6. Top Talkers (Text Messages)

The `content` field for received messages (`isSend=0`) starts with `<sender_wxid>:<message>`. For sent messages (`isSend=1`), the content is the raw message text.

```sql
SELECT 
  CASE WHEN isSend=1 THEN '我 (群主)'
       ELSE substr(content, 1, instr(content, ':')-1)
  END as sender,
  COUNT(*) as msg_count
FROM message 
WHERE talker = '<chatroom_id>' AND type = 1
GROUP BY sender
ORDER BY msg_count DESC
LIMIT 10;
```

## 7. Daily Activity Pattern

```sql
SELECT 
  strftime('%Y-%m-%d', createTime/1000, 'unixepoch', 'localtime') as day,
  COUNT(*) as msgs
FROM message 
WHERE talker = '<chatroom_id>'
GROUP BY day
HAVING msgs > 20
ORDER BY day DESC;
```

## 8. Recent Long Text Messages (>40 chars, skip media/emoji)

```sql
SELECT substr(content, 1, 250) as excerpt, 
       length(content) as charlen,
       datetime(createTime/1000,'unixepoch','localtime') as ts
FROM message 
WHERE talker = '<chatroom_id>'
  AND type = 1
  AND length(content) > 40
  AND substr(content,1,5) NOT IN ('<?xml', '<msg>')
  AND content NOT LIKE '[%'
  AND content NOT LIKE '%<img%'
  AND content NOT GLOB '[0-9a-f][0-9a-f][0-9a-f][0-9a-f]*'
ORDER BY createTime DESC
LIMIT 20;
```

## 9. Links / Articles Shared (type 49)

```sql
SELECT 
  CASE 
    WHEN instr(content, '<title>') > 0 AND instr(content, '</title>') > 0 
    THEN substr(content, instr(content, '<title>') + 7, instr(content, '</title>') - instr(content, '<title>') - 7)
    ELSE '(无title)'
  END as title,
  datetime(createTime/1000,'unixepoch','localtime') as ts
FROM message 
WHERE talker = '<chatroom_id>'
  AND type = 49
ORDER BY createTime DESC
LIMIT 25;
```

## 10. Full Text Export for Offline Analysis

```sql
SELECT datetime(createTime/1000,'unixepoch','localtime') || '|' ||
       CASE WHEN isSend=1 THEN '我' 
            ELSE substr(content, 1, instr(content, ':')-1) 
       END || '|' ||
       CASE WHEN isSend=1 THEN content 
            ELSE substr(content, instr(content, ':')+1) 
       END
FROM message WHERE talker = '<chatroom_id>' AND type = 1
ORDER BY createTime;
```

## 11. Thematic Analysis Query (by date bucket)

```sql
-- Group messages by week with count + representative sample
SELECT 
  strftime('%Y-%m-%d', createTime/1000, 'unixepoch', 'localtime') as day,
  COUNT(*) as msg_count,
  MIN(substr(content, 1, 60)) as sample
FROM message 
WHERE talker = '<chatroom_id>' AND type = 1 AND length(content) < 200
  AND substr(content,1,5) NOT IN ('<?xml', '<msg>')
  AND content NOT LIKE '[%'
GROUP BY day
ORDER BY day;
```

## Usage Pattern for "分析一下" Requests

When user says "半神之路 分析一下" or similar:

1. **First pass — stats**: queries 1-7 for group overview, member list, activity pattern
2. **Second pass — content**: queries 8-10 for recent substantive conversations, links shared
3. **Third pass — narrative**: organize by time period (weeks/months), extract themes from long text, identify recurring topics
4. **Deliver** — thematic timeline (by period), key quotes, link topics, overall group character judgment

## Pitfalls

- **`PRAGMA table_info(chatroom)` may return exit 1** on some DB versions — work around by just `SELECT * FROM chatroom LIMIT 1`
- **`rcontact` cross-query may fail** with exit 1 — use direct memberlist from `chatroom.displayname` instead
- **Message count by sender is noisy** — the `content` field for `isSend=0` has variable format: sometimes `<wxid:N>` (XML-wrapped), sometimes `<wxid>:<text>`. Use `instr(content, ':')` heuristic but expect edge cases with XML content
- **Type 754974769** = unknown rich message (may be mini-programs, stickers, recall messages)
- **Timestamps are millisecond Unix epoch** — always divide by 1000 for SQLite datetime functions
