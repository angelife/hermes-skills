#!/usr/bin/env python3
"""驭智AI群监控 - 每10分钟轮询 + MBTI式人物画像"""
import json, os, subprocess
from datetime import datetime, timezone, timedelta
from collections import defaultdict

GROUP_ID = "43155769439@chatroom"
KEY = "0273023"
OUTPUT_DIR = os.path.expanduser("~/.hermes/group-monitor")
os.makedirs(OUTPUT_DIR, exist_ok=True)
SQLCIPHER = "/usr/local/bin/sqlcipher"

def sql_query(sql):
    full_sql = f"PRAGMA key='{KEY}';\nPRAGMA cipher_compatibility=1;\n{sql}"
    r = subprocess.run([SQLCIPHER, "/tmp/EnMicroMsg.db"],
        input=full_sql, capture_output=True, text=True, timeout=30)
    lines = [l.strip() for l in r.stdout.strip().split("\n") if l.strip() and l.strip() != "ok"]
    return lines

# 1. Pull DB
subprocess.run("adb -s a6520fa3 shell 'su -c \"cp /data/data/com.tencent.mm/MicroMsg/d65f989d7e35cd4b56910fb8d96d4ec5/EnMicroMsg.db /data/local/tmp/\"'",
    shell=True, capture_output=True, timeout=30)
subprocess.run("adb -s a6520fa3 pull /data/local/tmp/EnMicroMsg.db /tmp/EnMicroMsg.db 2>/dev/null",
    shell=True, capture_output=True, timeout=30)

if not os.path.exists("/tmp/EnMicroMsg.db"):
    print('{"error": "DB not found"}'); exit(1)

state_file = f"{OUTPUT_DIR}/last_sync.txt"
last_sync = 0
if os.path.exists(state_file):
    with open(state_file) as f:
        try: last_sync = int(f.read().strip())
        except: last_sync = 0

lines = sql_query(f"""
SELECT createTime, isSend, content, type
FROM message WHERE talker='{GROUP_ID}' AND createTime > {last_sync} ORDER BY createTime;""")

new_rows, participants = [], defaultdict(lambda: {"msg_count": 0, "types": set(), "times": [], "texts": [], "msg_lens": []})
for line in lines:
    parts = line.split("|")
    if len(parts) < 4: continue
    try: create_time, is_send, content, msg_type = int(parts[0]), int(parts[1]), "|".join(parts[2:-1]), int(parts[-1])
    except: continue
    sender = "我" if is_send else (content.split(":")[0] if ":" in content else "unknown")
    text = "" if is_send else (content.split(":", 1)[1] if ":" in content else content or "")
    participants[sender]["msg_count"] += 1; participants[sender]["types"].add(msg_type); participants[sender]["times"].append(create_time); participants[sender]["msg_lens"].append(len(text))
    if msg_type == 1: participants[sender]["texts"].append(text[:200])
    new_rows.append({"ts": create_time, "time": datetime.fromtimestamp(create_time/1000,tz=timezone(timedelta(hours=8))).isoformat(), "type": msg_type, "sender": sender, "text": text[:200]})

if new_rows:
    with open(f"{OUTPUT_DIR}/messages.jsonl", "a") as f:
        for row in new_rows: f.write(json.dumps(row, ensure_ascii=False) + "\n")
    with open(state_file, "w") as f: f.write(str(max(r["ts"] for r in new_rows)))

# --- Update profiles + MBTI ---
profile_file = f"{OUTPUT_DIR}/profiles.json"
existing = json.load(open(profile_file)) if os.path.exists(profile_file) else {}
for sender, data in participants.items():
    if data["msg_count"] == 0: continue
    p = existing.get(sender, {"sender": sender, "total_msgs": 0, "type_dist": {}, "hourly_dist": {}, "text_samples": [], "last_active_ts": 0, "active_days": [], "avg_msgs_per_day": 0, "mbti": {"E/I": "N/A", "S/N": "N/A", "T/F": "N/A", "J/P": "N/A"}, "summary": ""})
    p["total_msgs"] += data["msg_count"]
    if data["times"]: p["last_active_ts"] = max(p["last_active_ts"], max(data["times"]))
    for t in data["types"]: p["type_dist"][str(t)] = p["type_dist"].get(str(t), 0) + 1
    for ts in data["times"]:
        day = datetime.fromtimestamp(ts/1000,tz=timezone(timedelta(hours=8))).strftime("%Y-%m-%d")
        found = False
        for d in p["active_days"]:
            if d["date"] == day: d["msg_count"] += 1; found = True; break
        if not found: p["active_days"].append({"date": day, "msg_count": 1})
        h = datetime.fromtimestamp(ts/1000,tz=timezone(timedelta(hours=8))).hour
        p["hourly_dist"][f"{h:02d}:00"] = p["hourly_dist"].get(f"{h:02d}:00", 0) + 1
    for t in data["texts"]:
        if len(p["text_samples"]) < 30: p["text_samples"].append(t)
    if p["active_days"]: p["avg_msgs_per_day"] = round(p["total_msgs"] / len(p["active_days"]), 1)
    
    avg_len = round(sum(data["msg_lens"])/len(data["msg_lens"]),0) if data["msg_lens"] else 0
    all_text = " ".join(data["texts"])
    msgs_per_day = p.get("avg_msgs_per_day", 0)
    p["mbti"]["E/I"] = "E" if msgs_per_day > 10 else ("I" if msgs_per_day < 3 else "平衡")
    p["mbti"]["S/N"] = "S" if avg_len < 30 else ("N" if avg_len > 80 else "平衡")
    f_count = sum(1 for w in ["感觉","觉得","喜欢","好看","不错","开心","哈哈","😊","👍","谢谢","好"] if w in all_text)
    t_count = sum(1 for w in ["应该","逻辑","原因","分析","对比","参数","配置","代码","性能","报错","问题"] if w in all_text)
    p["mbti"]["T/F"] = "T" if t_count > f_count*1.5 else ("F" if f_count > t_count*1.5 else "平衡")
    p["mbti"]["J/P"] = "J" if len(p["hourly_dist"]) <= 6 else ("P" if len(p["hourly_dist"]) >= 12 else "平衡")
    m = p["mbti"]
    p["mbti_type"] = "".join(m[k] for k in ["E/I","S/N","T/F","J/P"] if m.get(k) in ["E","S","T","J"]) or "N/A"
    p["classification"] = "核心成员" if p["total_msgs"] >= 100 else ("活跃" if p["total_msgs"] >= 30 else ("偶尔发言" if p["total_msgs"] >= 5 else "潜水"))
    existing[sender] = p
json.dump(existing, open(profile_file, "w"), ensure_ascii=False, indent=1)

top = sorted(existing.items(), key=lambda x: x[1]["total_msgs"], reverse=True)[:5]
report = {"time": datetime.now(tz=timezone(timedelta(hours=8))).isoformat(), "new": len(new_rows), "members": len(existing), "active_now": len([s for s in participants.values() if s["msg_count"] > 0]), "top5": []}
for s, p in top:
    report["top5"].append(f"{s[:15]}: {p['total_msgs']}条, {p['mbti_type']}, {p['classification']}")
print(json.dumps(report, ensure_ascii=False))
