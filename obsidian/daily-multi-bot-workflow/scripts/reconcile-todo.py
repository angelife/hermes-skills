#!/usr/bin/env python3
"""Reconcile _EVENTS.jsonl into _TODO.md.

Rules:
- acquire lock dir: .todo.lock
- read _EVENTS.jsonl, only process new lines since _EVENTS.offset
- maintain in-memory task state machine
- regenerate _TODO.md then atomic rename
- update _EVENTS.offset
"""

import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

VAULT = Path('/Users/macos/Documents/Obsidian Vault/每日工作记录')
EVENTS = VAULT / '_EVENTS.jsonl'
OFFSET = VAULT / '_EVENTS.offset'
TODO = VAULT / '_TODO.md'
TMP = VAULT / '_TODO.md.tmp'
LOCK = VAULT / '.todo.lock'

CST = timezone(timedelta(hours=8))


def now_iso() -> str:
    return datetime.now(CST).isoformat(timespec='seconds')


def lock_acquire(timeout: float = 20.0) -> bool:
    import time
    start = time.time()
    while True:
        try:
            LOCK.mkdir()
            (LOCK / 'info').write_text(f'owner=reconcile todo pid={os.getpid()} ts={now_iso()}\n')
            return True
        except FileExistsError:
            if time.time() - start > timeout:
                return False
            time.sleep(0.5)


def lock_release() -> None:
    try:
        (LOCK / 'info').unlink(missing_ok=True)
        LOCK.rmdir()
    except Exception:
        pass


def state_machine(events):
    tasks = {}
    for evt in events:
        tid = evt.get('task_id')
        if not tid:
            continue
        action = evt.get('action')
        session = evt.get('session', '-')
        if action == 'create':
            tasks[tid] = {
                'id': tid,
                'status': 'pending_claim',
                'owner': evt.get('bot', '-'),
                'created': evt.get('ts'),
                'title': evt.get('title', tid),
                'category': evt.get('category', 'LEGACY'),
                'source_session': session,
                'source_action': action,
            }
        elif tid in tasks:
            tasks[tid]['source_session'] = session
            tasks[tid]['source_action'] = action
            if action == 'claim':
                tasks[tid]['status'] = 'claimed'
                tasks[tid]['owner'] = evt.get('bot', tasks[tid]['owner'])
                tasks[tid]['claim_time'] = evt.get('ts')
            elif action == 'start':
                tasks[tid]['status'] = 'in_progress'
            elif action == 'complete':
                tasks[tid]['status'] = 'done'
                tasks[tid]['complete_time'] = evt.get('ts')
            elif action == 'reopen':
                tasks[tid]['status'] = 'pending_claim'
                tasks[tid].pop('claim_time', None)
                tasks[tid].pop('complete_time', None)
            elif action == 'create' and tasks[tid]['status'] == 'done':
                continue
    return tasks


def render_todo(tasks, gen_ts):
    legacy = []
    infra = []
    auto = []
    for t in tasks.values():
        if t['status'] == 'done':
            continue
        source_session = t.get('source_session', '-')
        if t['status'] == 'in_progress':
            line = f"- [>] id={t['id']} status={t['status']} bot={t['owner']} session={source_session} | {t['title']}"
        elif t['status'] == 'claimed':
            line = f"- [>] id={t['id']} status={t['status']} bot={t['owner']} session={source_session} | {t['title']}"
        elif t['status'] == 'pending_claim':
            line = f"- [ ] id={t['id']} status={t['status']} bot={t.get('owner','-')} created={t.get('created','')} session={source_session} | {t['title']}"
        else:
            line = f"- [ ] id={t['id']} status={t['status']} bot={t.get('owner','-')} session={source_session} | {t['title']}"
        cat = t.get('category', 'LEGACY')
        if cat == 'INFRA':
            infra.append(line)
        elif cat == 'AUTO':
            auto.append(line)
        else:
            legacy.append(line)
    out = [
        f'# _TODO.md — {datetime.now(CST).strftime("%Y-%m-%d")}',
        '',
        '## LEGACY（遗留业务）',
    ]
    out.extend(legacy or ['- (empty)'])
    out.append('')
    out.append('## INFRA（基建）')
    out.extend(infra or ['- (empty)'])
    out.append('')
    out.append('## AUTO（自动生成）')
    out.extend(auto or ['- (empty)'])
    out.append('')
    out.append(f'generated_by: reconciler @ {gen_ts}')
    out.append('')
    out.append('## 身份标识格式')
    out.append('- 格式：`bot:session_type:identifier`')
    out.append('- 示例：`土:cli:mac` / `土:telegram:dm:780486548` / `金:cli:mi8` / `火:cron:e15a1d27093e`')
    out.append('')
    return '\n'.join(out) + '\n'


def read_events() -> list[dict]:
    if not EVENTS.exists():
        return []
    out = []
    for raw in EVENTS.read_text(encoding='utf-8').splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            out.append(json.loads(raw))
        except json.JSONDecodeError:
            skip_bad_line(out)
    return out


def run() -> str:
    if not lock_acquire():
        return 'SKIP: lock busy'
    try:
        events = read_events()
        tasks = state_machine(events)
        gen_ts = now_iso()
        text = render_todo(tasks, gen_ts)
        TMP.write_text(text, encoding='utf-8')
        TMP.replace(TODO)
        if OFFSET.exists():
            prev = int(OFFSET.read_text(encoding='utf-8').strip() or '0')
        else:
            prev = 0
        OFFSET.write_text(str(len(events)), encoding='utf-8')
        return f'OK: reconciled offset {prev} -> {len(events)}'
    finally:
        lock_release()


if __name__ == '__main__':
    print(run())
