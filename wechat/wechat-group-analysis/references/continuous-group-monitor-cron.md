# 微信群监控：Cron 轮询 + MBTI 人物画像

## 适用场景

对一个微信群进行长期（数周~数月）持续监控，自动采集消息并构建参与者行为画像。

## 架构

```
Cron（每10分钟）
    │
    ├─ ADB拉取微信DB
    ├─ sqlcipher查询新消息
    ├─ 追加到 messages.jsonl
    ├─ 更新 profiles.json（MBTI分类）
    └─ 上报摘要
```

## 解密Key记忆

Mi8（a6520fa3）WeChat EnMicroMsg.db 解密：
- IMEI=867252038607635, UIN=-185082944
- 计算 key: MD5(IMEI+UIN)[:7] = `0273023`
- 必须 `PRAGMA cipher_compatibility=1;`
- DB 路径: `/data/data/com.tencent.mm/MicroMsg/d65f989d7e35cd4b56910fb8d96d4ec5/EnMicroMsg.db`

## MBTI 分类算法

基于消息行为模式自动推算四维性格：

| 维度 | 计算方式 | 活跃 | 平衡 | 内向 |
|:----:|---------|:---:|:---:|:---:|
| E/I | 日均消息量 | >10条→E | 3-10→平衡 | <3→I |
| S/N | 平均消息长度 | <30字→S | 30-80→平衡 | >80→N |
| T/F | 关键词匹配（感觉词vs逻辑词） | 逻辑词多→T | 平衡 | 感觉词多→F |
| J/P | 活跃时段分散度 | ≤6小时段→J | 7-11→平衡 | ≥12→P |

## 脚本位置（以本机实测为准）

**主路径（cron 用）：** `~/.hermes/scripts/wechat-group-monitor.py`  
**技能备份副本：** `~/.hermes/skills/wechat/wechat-group-analysis/scripts/wechat-group-monitor.py`

### 自修复（cron 自动恢复）

cron 会话发现脚本缺失时，优先 `cp` 从技能目录复制（最可靠，无转义问题）：

```text
1. skill_view(name='wechat-group-analysis', file_path='scripts/wechat-group-monitor.py')
2. cp ~/.hermes/skills/wechat/wechat-group-analysis/scripts/wechat-group-monitor.py \
     ~/.hermes/scripts/wechat-group-monitor.py
3. terminal(background=true, notify_on_complete=true) → process wait
```

备选：若 `cp` 不可用（技能目录路径不对等），用 `write_file` 写回。但注意 `write_file` 的 lint 检查器可能将 Python 代码中的 `"` 误报为转义问题，导致文件内容被破坏（`"` → `\"`）。若 `write_file` 后脚本报 SyntaxError，改用 `cp` 重试。

### 手动恢复（主会话）

```bash
cp ~/.hermes/skills/wechat/wechat-group-analysis/scripts/wechat-group-monitor.py \
  ~/.hermes/scripts/wechat-group-monitor.py
```

本机验证（主会话 terminal，别信 cron 会话空输出误诊）：
```bash
python3 ~/.hermes/scripts/wechat-group-monitor.py
# 正常例：{"new":0,"members":4,...}
ls ~/.hermes/group-monitor/   # messages.jsonl profiles.json last_sync.txt
```

如果 ADB 设备序列号变更，需同步更新脚本中的 `adb -s <serial>` 参数。

## 数据文件结构

```
~/.hermes/group-monitor/
├── messages.jsonl       # 原始消息流（追加）
├── profiles.json        # 人物画像（持续更新）
├── last_sync.txt        # 最后同步时间戳
└── reports/             # 定期报告（可选）
```

## Cron 配置

现役：`job_id=99ccc2038487` 名「驭智AI群监控」  
- 每 10 分钟；跑 `python3 ~/.hermes/scripts/wechat-group-monitor.py`  
- **`new>0` 才中文总结推送；`new=0` 安静**  
- 必须 **pin 当前可用 model**（用户：有啥用啥，不挑 free/付费）  
  - 漂移跳过：`Skipped to prevent unintended spend… unpinned`  
  - 修：`cronjob action=update job_id=99ccc2038487 model={"model":"grok-4.5"}`

```bash
cronjob action=create name="驭智AI群监控" schedule="every 10m" \
  model={"model":"<当前可用>"} \
  prompt="运行 python3 ~/.hermes/scripts/wechat-group-monitor.py；new>0 才中文总结，不要 JSON"
```

### Cron 自报「脚本不在」时先本机核实

cron agent 可能误报 scripts 目录不存在、echo 也空。**不要立刻软链**——主会话先 `ls` + 直接跑脚本 + 看 `group-monitor/` 时间戳。本机通 → 上次是 cron 环境抽风。

## 关键SQL

```sql
-- 增量查询（按createTime过滤）
SELECT createTime, isSend, content, type
FROM message
WHERE talker='<chatroom_id>' AND createTime > <last_sync>
ORDER BY createTime;

-- 群列表
SELECT c.chatroomname, r.nickname, c.memberCount
FROM chatroom c
LEFT JOIN rcontact r ON c.chatroomname = r.username
ORDER BY c.memberCount DESC;
```

## 注意

- ADB拉DB约3-5秒，160MB文件；频率勿过高（10分钟以上间隔）
- 群消息量大的话 `messages.jsonl` 会持续膨胀，建议每月归档一次
- MBTI 分类基于有限行为特征，仅供参考，非真实心理学分类
- 发送者wxid需通过 `rcontact` 表交叉查询才能解析为显示名
