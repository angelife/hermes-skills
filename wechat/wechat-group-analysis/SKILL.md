---
name: wechat-group-analysis
description: "对解密后的微信 EnMicroMsg.db 进行群聊深度分析——提取消息统计、时间线、主题演变、对话脉络。适用于 10K~100K 条级别的群聊数据。"
version: 1.3.0
author: Hermes Agent
platforms: [macos, linux]
metadata:
  hermes:
    tags: [WeChat, Analysis, GroupChat, DataMining]
---

# WeChat 群聊分析

对已解密的微信数据库（`EnMicroMsg_decrypted.db`）进行群聊内容分析。

**前提**：数据库必须先解密（通过 `android-wechat-db-decrypt` skill 或其它方式）。

## 1. 概览统计

```bash
# 总消息数、联系人/群聊数、时间跨度
sqlite3 /tmp/EnMicroMsg_decrypted.db "
SELECT COUNT(*), COUNT(DISTINCT talker),
       datetime(MIN(createTime)/1000,'unixepoch','+8 hours'),
       datetime(MAX(createTime)/1000,'unixepoch','+8 hours')
FROM message;
"

# 群聊列表及消息数
sqlite3 /tmp/EnMicroMsg_decrypted.db "
SELECT substr(talker,1,25) AS group_id, COUNT(*) AS msgs
FROM message WHERE talker LIKE '%@chatroom'
GROUP BY talker ORDER BY msgs DESC;
"
```

## 2. 按群分析

### 消息构成

```bash
sqlite3 /tmp/EnMicroMsg_decrypted.db "
SELECT 
  CASE WHEN isSend=1 THEN '发出' ELSE '收到' END AS dir,
  type,
  CASE 
    WHEN type=1 THEN '文本'
    WHEN type=3 THEN '图片'
    WHEN type=34 THEN '语音'
    WHEN type=43 THEN '视频/红包'
    WHEN type=47 THEN '表情'
    WHEN type=49 THEN '公众号/链接'
    WHEN type=285212721 THEN '文章分享'
    WHEN type=10000 THEN '系统通知'
    ELSE CAST(type AS TEXT)
  END AS type_name,
  COUNT(*) AS count
FROM message WHERE talker='<群ID>'
GROUP BY isSend, type
ORDER BY isSend, count DESC;
"
```

### 活跃时间段

```bash
sqlite3 /tmp/EnMicroMsg_decrypted.db "
SELECT strftime('%H', createTime/1000, 'unixepoch', '+8 hours') AS hour,
       COUNT(*) AS msgs
FROM message WHERE talker='<群ID>'
GROUP BY hour ORDER BY msgs DESC LIMIT 10;
"
```

### 活跃日期

```bash
sqlite3 /tmp/EnMicroMsg_decrypted.db "
SELECT date(createTime/1000, 'unixepoch', '+8 hours') AS day,
       COUNT(*) AS msgs
FROM message WHERE talker='<群ID>'
GROUP BY day ORDER BY day;
"
```

## 3. 内容深度分析

### 提取全部文本消息

```bash
# 群聊文本
sqlite3 /tmp/EnMicroMsg_decrypted.db "
SELECT 
  datetime(createTime/1000,'unixepoch','+8 hours') AS t,
  CASE WHEN isSend=0 THEN substr(content,1,instr(content,':')-1) ELSE '我' END AS sender,
  CASE WHEN isSend=0 THEN substr(content,instr(content,':')+1) ELSE content END AS msg
FROM message 
WHERE talker='<群ID>' AND type=1
ORDER BY createTime;
" > /tmp/group_chat.txt

# 一次性全部分析所有群
sqlite3 /tmp/EnMicroMsg_decrypted.db "
SELECT datetime(createTime/1000,'unixepoch','+8 hours'),
       CASE WHEN isSend=1 THEN '我' ELSE '收' END,
       CASE WHEN talker LIKE '%@chatroom' THEN substr(talker,1,25) ELSE substr(talker,1,15) END,
       CASE WHEN type=1 THEN substr(content,1,150) ELSE CAST(type AS TEXT) END
FROM message
ORDER BY createTime DESC
LIMIT 30;
" | head -30
```

### 提取群友回复（收到的消息）

```bash
sqlite3 /tmp/EnMicroMsg_decrypted.db "
SELECT datetime(createTime/1000,'unixepoch','+8 hours') AS t,
       substr(content, 1, 120) AS msg
FROM message WHERE talker='<群ID>' AND type=1 AND isSend=0
ORDER BY createTime;
"
```

## 4. 核心方法论

分析时**必须通读文本内容**，不能只给统计数字。以下是被用户纠正过的记录：

### 正确做法

```
✅ 按日期提取样本 → 理解主题演变
✅ 提取群友回复 → 理解对话交互
✅ 识别时间线 → 绘制话题变化
✅ 给出实质性分析结论
✅ 全文读取后归纳（数据量不超过几万条时）
```

### 错误做法（被严厉纠正过）

```
❌ 只给统计数字（消息数、类型分布）
❌ 不做内容读取就下结论
❌ 漏掉群友的回复不看
❌ 不按时间线梳理话题演变
```

## 快速刷新（增量读取）

已有解密库时，只需重新拉取 + 解密，再用 timestamp 过滤新增消息：

```bash
# 1. 拉新
adb exec-out "su -c 'cat .../EnMicroMsg.db'" > /tmp/EnMicroMsg_encrypted.db

# 2. 解密（同key）
/tmp/sqlcipher/sqlite3 /tmp/EnMicroMsg_encrypted.db <<'EOF'
PRAGMA key = '<key>';
PRAGMA cipher_compatibility = 1;
ATTACH DATABASE '/tmp/EnMicroMsg_decrypted.db' AS decrypted KEY '';
SELECT sqlcipher_export('decrypted');
DETACH DATABASE decrypted;
EOF

# 3. 只看新增（按createTime DESC取前N条）
sqlite3 /tmp/EnMicroMsg_decrypted.db "
SELECT datetime(createTime/1000,'unixepoch','+8 hours') ... 
FROM message
ORDER BY createTime DESC
LIMIT 30;
"
```

## 持续监控（Cron 轮询）

需要长期监控群聊动态时（数周~数月），见 `references/continuous-group-monitor-cron.md`：
- 每10分钟拉新消息 → 更新人物画像；**new=0 安静（仅 [SILENT]），new>0 才中文摘要**
- 脚本主路径：`~/.hermes/scripts/wechat-group-monitor.py`（技能目录有备份副本）
- LLM cron 必须 pin 当前可用 model（用户：有啥用啥）；漂移跳过 ≠ 脚本坏
- cron 自报「路径不在」时先主会话核实，勿盲软链
- **cron 空 stdout / 恢复路径**：见 `references/cron-terminal-empty-stdout.md`（foreground terminal 常空 → background+process wait；脚本用 skill_view 恢复）

### Setup：确保监控脚本在 cron 路径

首次使用或脚本缺失时，从技能目录复制到 cron 预期路径：

```bash
# 检查脚本是否在 cron 路径
test -f ~/.hermes/scripts/wechat-group-monitor.py && echo "EXISTS" || echo "MISSING"

# 若缺失，从技能目录复制
cp ~/.hermes/skills/wechat/wechat-group-analysis/scripts/wechat-group-monitor.py \
  ~/.hermes/scripts/wechat-group-monitor.py

# 验证可执行
python3 ~/.hermes/scripts/wechat-group-monitor.py
# 正常输出：{"new":0,"members":N,...}
```

如果 `~/.hermes/scripts/` 目录不存在，先创建：`mkdir -p ~/.hermes/scripts/`。

### Cron 自修复（脚本缺失时自我恢复）

**绝不因脚本缺失或 terminal 空输出就直接 `[SILENT]`。** 优先自修复再尝试。

```text
1. search_files 检查 ~/.hermes/scripts/wechat-group-monitor.py 是否存在
2. 若 MISSING:
   a. skill_view(name='wechat-group-analysis', file_path='scripts/wechat-group-monitor.py')
   b. 首选：cp 从技能目录复制（最可靠，无转义问题）
      cp ~/.hermes/skills/wechat/wechat-group-analysis/scripts/wechat-group-monitor.py \
        ~/.hermes/scripts/wechat-group-monitor.py
   c. 备选：若 cp 不可用（路径不对等），用 write_file 写回
      write_file(path='~/.hermes/scripts/wechat-group-monitor.py', content=上一步内容)
      ⚠️ write_file 的 lint 检查器可能将 Python 代码中的 " 误报为转义问题，
         导致文件内容被破坏（" → \"）。若 write_file 后脚本报 SyntaxError，
         改用 cp 重试。
   d. terminal(background=true, notify_on_complete=true) 跑脚本 → process wait 取输出
3. 若 EXISTS → terminal(background=true, notify_on_complete=true) → process wait
4. 若 cp 和 write_file 都失败 → 障碍汇报，不安静跳过
```

注意：`~/.hermes/scripts/` 目录可能不存在，write_file 会自动创建。

### Cron 执行注意事项

- **foreground terminal 常空输出**：cron 会话下 foreground terminal 返回空字符串（exit_code=0 也空）。不要据此判定脚本不存在或失败。
- **可靠取输出**：`terminal(command=..., background=true, notify_on_complete=true)` → `process(action='wait')`，stdout 在 process 结果里。
- **execute_code 被拦**：cron 下 `execute_code` 被 `BLOCKED: Cron jobs run without a user`。只用 terminal/process + 文件工具。
- **脚本权威正文**：`skill_view(name='wechat-group-analysis', file_path='scripts/wechat-group-monitor.py')`。主路径缺失时，优先 `cp` 从技能目录复制；`write_file` 备选但注意转义问题。
