# Group Content Deep Analysis Guide

When the user says "分析一下 [群名]", go beyond statistics. This guide covers the narrative/thematic analysis methodology that produces the kind of output users expect.

## Analysis Pipeline

### Phase 1: Group Profile
```
Queries: chatroom table → memberCount, displayname, roomowner
Members: rcontact → nicknames for all wxid
Stats:   message count per table, time range, message type breakdown
```

### Phase 2: Participant Profiling
```
Top talkers: who sends how many text messages
Role assignment: owner, main interlocutor, occasional contributors, lurkers
Member profile: infer life context from content (job, interests, economic status, tech level)
```

### Phase 3: Content Mining
```
Long text extraction: messages > 40 chars, filter out XML/media/emoji
  → read actual content, not just counts

Link analysis: type 49 messages → extract title + ts
  → categorize links by topic domain

Message type distribution: text vs image vs link vs video vs emoji
  → tells you whether it's a chat group or a link-sharing channel
```

### Phase 4: Thematic Timeline
```
Bucket by time period (weeks/months):
  For each period, identify:
    - Dominant topic (what was the main conversation thread)
    - Key quotes (capture representative messages)
    - Participant dynamics (who was talking to whom)
    - Emotional tone

Output as a timeline table:
  Period | Topic | Key Events | Participants
```

### Phase 5: Group Character Judgment
```
Synthesize into a one-paragraph assessment:
  - What IS this group? (chat group / thought diary / Q&A / link feed)
  - Who drives the conversation? (single person / pair / everyone)
  - What is the group's essential nature?
  - Is there a relationship dynamic worth noting?

Example from 半神之路:
  "这不是一个群，是你的外部脑皮层。你在里面做三件事：
   1. 记录体系思考 — 社会/政治/AI/人性的底层逻辑推演
   2. 与宽建对话 — 一个底层挣扎但求知欲强的群友
   3. 技术笔记 — 把玩 AI 工具的实时记录"
```

## Key Queries for Narrative Analysis

### Extracting text samples by date range (for timeline building)

```sql
-- Get representative text samples per day
SELECT 
  strftime('%Y-%m-%d', createTime/1000, 'unixepoch', 'localtime') as day,
  COUNT(*) as msgs,
  MIN(CASE WHEN isSend=1 AND type=1 AND length(content) BETWEEN 10 AND 200 
      THEN content END) as sample_text
FROM message 
WHERE talker = '<chatroom_id>'
  AND type = 1
  AND substr(content,1,5) NOT IN ('<?xml', '<msg>')
GROUP BY day
ORDER BY day;
```

### Getting ALL substantive messages for offline reading

```sql
SELECT datetime(createTime/1000,'unixepoch','localtime') as ts,
       CASE WHEN isSend=1 THEN 'me' 
            ELSE substr(content, 1, instr(content, ':')-1) 
       END as who,
       CASE WHEN isSend=1 THEN content 
            ELSE substr(content, instr(content, ':')+1) 
       END as msg,
       type
FROM message 
WHERE talker = '<chatroom_id>'
  AND type = 1
  AND length(content) > 5
  AND substr(content,1,5) NOT IN ('<?xml', '<msg>')
ORDER BY createTime
LIMIT 2000;
```

### Article link extraction with titles

```sql
SELECT 
  CASE 
    WHEN instr(content, '<title>') > 0 
    THEN substr(content, instr(content, '<title>') + 7, 
                instr(content, '</title>') - instr(content, '<title>') - 7)
    ELSE '(no title)'
  END as title,
  datetime(createTime/1000,'unixepoch','localtime') as ts
FROM message 
WHERE talker = '<chatroom_id>' AND type = 49
ORDER BY createTime DESC
LIMIT 50;
```

### Message type distribution with numerical breakdown

```sql
SELECT type, 
  CASE type 
    WHEN 1 THEN 'text'
    WHEN 3 THEN 'image'
    WHEN 34 THEN 'voice'
    WHEN 42 THEN 'contact_card'
    WHEN 43 THEN 'video'
    WHEN 47 THEN 'emoji'
    WHEN 48 THEN 'location'
    WHEN 49 THEN 'link/article'
    WHEN 10000 THEN 'system'
    WHEN 436207665 THEN 'red_packet'
    ELSE 'other('||type||')'
  END as type_name,
  COUNT(*) as count,
  ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 1) as pct
FROM message 
WHERE talker = '<chatroom_id>'
GROUP BY type
ORDER BY count DESC;
```

### Daily activity pattern (useful for understanding engagement)

```sql
SELECT 
  strftime('%Y-%m-%d', createTime/1000, 'unixepoch', 'localtime') as day,
  COUNT(*) as msgs,
  COUNT(DISTINCT CASE WHEN type=1 THEN substr(content,1,40) END) as text_threads
FROM message 
WHERE talker = '<chatroom_id>'
GROUP BY day
HAVING msgs > 20
ORDER BY day DESC
LIMIT 30;
```

## Common Pitfalls

### Content Column for Received Messages
For `isSend=0` (received from others), the `content` field format is:
- `wxid_xxxx:<message_text>` — simple format for text messages
- `<msg>...XML...</msg>` — XML-wrapped for rich messages
- For XML messages, the actual sender and content are embedded in the XML

Use `instr(content, ':')` heuristic but expect edge cases:
```sql
-- This query skips XML/wrapped messages for sender extraction
CASE 
  WHEN isSend=1 THEN 'me'
  WHEN substr(content,1,5) = '<?xml' OR substr(content,1,5) = '<msg>' THEN '(wrapped)'
  WHEN instr(content, ':') > 0 THEN substr(content, 1, instr(content, ':')-1)
  ELSE '(unknown)'
END as sender
```

### Display Name Resolution
The `rcontact` table's `nickname` may be stale (set when first added, never updated). The current display name in-chat may differ. Cross-reference with the `chatroom` table's `displayname` field (first few names shown in group list).

### Link Truncation
WeChat links are often wrapped in redirect URLs (`mp.weixin.qq.com/s?__biz=...`). Extract only the actual article URL when needed.

## Delivery Format for "分析一下"

Structure the output as:

1. **基本信息** — table: members, timespan, message count, daily avg
2. **成员画像** — who's who with contribution stats
3. **主题演变时间线** — period | topic | key content
4. **文章分享图谱** — categorized link topics
5. **一句话总结** — the group's essential nature

Use Markdown tables, emoji indicators, and concise Chinese.
