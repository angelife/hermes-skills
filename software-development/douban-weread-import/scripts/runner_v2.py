#!/usr/bin/env python3
"""
Douban → WeRead batch mapping runner v2.
Features: state.json resume, cache.json dedup, match_confidence, query_source, last_checked.
"""
import subprocess, json, time, csv, os, signal
from pathlib import Path
from datetime import datetime, timezone

BASE = Path('/Users/macos/douban_import_batches')
OUT = BASE / 'output'
OUT.mkdir(exist_ok=True)
STATE_FILE = BASE / 'state.json'
CACHE_FILE = BASE / 'cache.json'

# === CONFIG ===
PROFILE = 'Thomas.Xie'          # douban username
PAGE_SIZE = 15                  douban items per page
BATCH_TARGET = 50               # books per batch
MAX_START = 8460                # douban max start index (8461 books / 15 per page)
SLEEP_OPEN = 1.5                # seconds after opening douban page
SLEEP_BETWEEN_BOOKS = 3         # seconds between each book query
SLEEP_BETWEEN_PAGES = 8         # seconds between douban pages
CACHE_TTL_DAYS = 90             # cache validity period

# === HELPERS ===
def load_json(p, default):
    try:
        return json.loads(p.read_text(encoding='utf-8'))
    except Exception:
        return default

def save_json(p, data):
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

def cli(args):
    return subprocess.run(['opencli','browser','browser']+args, capture_output=True, text=True, timeout=30).stdout or ''

def weread(payload):
    import urllib.request
    key = ''
    with open('/Users/macos/key.txt') as f:
        key = ''.join([line.strip() for line in f if line.startswith('wrk-')])
    body = json.dumps({'skill_version':'1.0.4', **payload}).encode()
    req = urllib.request.Request('https://i.weread.qq.com/api/agent/gateway', data=body, headers={
        'Authorization': 'Bearer '+key,
        'Content-Type': 'application/json'
    })
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read())
    except Exception:
        return {'_err': 'timeout_or_blocked'}

def search_book(title, author=''):
    k = (title + ' ' + (author or '')).strip()
    if not k:
        return None
    data = weread({'api_name':'/store/search','keyword':k,'count':5})
    if data.get('errcode') not in (None, 0):
        return None
    for res in data.get('results', []):
        if res.get('title') == '电子书':
            bs = res.get('books', [])
            if not bs:
                continue
            return bs[0].get('bookInfo', {})
    return None

def confidence(douban_title, douban_author, weread_info):
    if not weread_info:
        return 'LOW'
    wt = (weread_info.get('title') or '').strip()
    wa = (weread_info.get('author') or '').strip()
    if douban_title.strip() == wt and douban_author.strip() == wa:
        return 'HIGH'
    if douban_title.strip() == wt:
        return 'MEDIUM'
    return 'LOW'

def parse_page(raw):
    try:
        data = json.loads(raw)
    except Exception:
        return []
    rows = []
    for item in data:
        sid = item.get('id')
        title = item.get('title', '')
        author = item.get('author', '')
        pub = item.get('pub', '')
        rating = item.get('rating', '')
        if sid:
            rows.append((sid, title, author, pub, rating))
    return rows

# === MAIN ===
if __name__ == '__main__':
    state = load_json(STATE_FILE, {
        'next_index': 0, 'current_batch': 1, 'finished_batches': [],
        'total_seen': 0, 'total_matched': 0, 'last_run_ts': 0
    })
    cache = load_json(CACHE_FILE, {})

    # resume seen from all existing output files
    seen = set()
    for p in OUT.glob('batch_*.tsv'):
        try:
            for row in csv.reader(p.open('r', encoding='utf-8'), delimiter='\t'):
                if row and row[0].isdigit():
                    seen.add(row[0])
        except Exception:
            pass

    batch_num = state.get('current_batch', 1)
    out_file = OUT / f'batch_{batch_num:02d}.tsv'
    header = [
        'douban_subject_id', 'douban_title', 'douban_author', 'douban_pubDate', 'douban_rating',
        'weread_bookId', 'weread_title', 'weread_author', 'weread_rating', 'readingCount',
        'status', 'deepLink', 'best_mark_count', 'best_mark_preview',
        'match_confidence', 'query_source', 'last_checked'
    ]
    with open(out_file, 'w', newline='', encoding='utf-8') as f:
        csv.writer(f, delimiter='\t').writerow(header)

    start_index = state['next_index']
    rows_done = 0; matched = 0; not_found = 0; errors = 0
    t_batch = time.time()

    print(f'BATCH_{batch_num:02d}_START start_index={start_index} seen={len(seen)} target={BATCH_TARGET}', flush=True)

    for start in range(start_index, MAX_START+1, PAGE_SIZE):
        cli(['open', f'https://book.douban.com/people/{PROFILE}/collect?start={start}&sort=time&rating=all&filter=all&mode=grid'])
        time.sleep(SLEEP_OPEN)
        raw = cli(["eval","(() => { const items=[...document.querySelectorAll('.item, .subject-item')].slice(0,20); return JSON.stringify(items.map(n => { const a=[...n.querySelectorAll('a')].find(a => a.title && a.href.includes('/subject/')); const meta=(n.querySelector('.pub')||{}).textContent||''; const rating=(n.querySelector('.rating_nums')||{}).textContent||''; return a ? { id: a.href.split('/')[4], title: a.title.trim(), author: meta.split('/')[0].trim(), pub: meta, rating: rating.trim() } : null; }).filter(Boolean)); })()"])
        page = parse_page(raw)
        if not page:
            time.sleep(3); continue

        with open(out_file, 'a', newline='', encoding='utf-8') as f:
            w = csv.writer(f, delimiter='\t')
            for sid, title, author, pub, rating in page:
                if sid in seen:
                    continue
                seen.add(sid)
                t0 = time.time()
                now = datetime.now(timezone.utc).isoformat()

                # check cache
                if sid in cache:
                    c = cache[sid]
                    row = [sid, title, author, pub, rating,
                           c.get('weread_bookId',''), c.get('weread_title',''), c.get('weread_author',''),
                           c.get('weread_rating',''), c.get('readingCount',''),
                           c.get('status','matched'), c.get('deepLink',''), c.get('best_mark_count','0'),
                           c.get('best_mark_preview',''), c.get('match_confidence','HIGH'),
                           'cache', c.get('last_checked', now)]
                    w.writerow(row); rows_done += 1
                    if c.get('status') == 'matched': matched += 1
                    else: not_found += 1
                    print(f'BOOK {sid} {title[:20]} status=cache rows={rows_done} dt={time.time()-t0:.1f}s', flush=True)
                    continue

                # query API
                m = search_book(title, author)
                if m:
                    bid = m.get('bookId')
                    bm = weread({'api_name':'/book/bestbookmarks','bookId':str(bid),'count':5}) if bid else {}
                    marks = bm.get('bestBookmarks') or bm.get('bookmarks') or bm.get('items') or []
                    first = ''
                    if isinstance(marks, list) and marks:
                        first = marks[0].get('markText','') or marks[0].get('text','') or ''
                    conf = confidence(title, author, m)
                    row = [sid, title, author, pub, rating,
                           str(bid) if bid else '', m.get('title',''), m.get('author',''),
                           m.get('newRating',''), m.get('readingCount',''),
                           'matched', m.get('deepLink') or ('weread://reading?bId='+str(bid) if bid else ''),
                           str(len(marks)), first[:100], conf, 'api', now]
                    w.writerow(row); matched += 1; rows_done += 1
                    cache[sid] = {
                        'weread_bookId': str(bid) if bid else '', 'weread_title': m.get('title',''),
                        'weread_author': m.get('author',''), 'weread_rating': m.get('newRating',''),
                        'readingCount': m.get('readingCount',''), 'status': 'matched',
                        'deepLink': m.get('deepLink',''), 'best_mark_count': str(len(marks)),
                        'best_mark_preview': first[:100], 'match_confidence': conf, 'last_checked': now
                    }
                elif m is None and '_err' in (m or {}):
                    row = [sid, title, author, pub, rating, '', '', '', '', '', 'timeout', '', '0', '', 'LOW', 'api', now]
                    w.writerow(row); errors += 1
                    print(f'BOOK {sid} {title[:20]} status=timeout rows={rows_done} dt={time.time()-t0:.1f}s', flush=True)
                    time.sleep(SLEEP_BETWEEN_BOOKS); continue
                else:
                    row = [sid, title, author, pub, rating, '', '', '', '', '', 'not_found', '', '0', '', 'LOW', 'api', now]
                    w.writerow(row); not_found += 1; rows_done += 1
                    cache[sid] = {'status': 'not_found', 'match_confidence': 'LOW', 'last_checked': now}

                f.flush(); save_json(CACHE_FILE, cache)
                print(f'BOOK {sid} {title[:20]} status={\"matched\" if m else \"not_found\"} rows={rows_done} dt={time.time()-t0:.1f}s', flush=True)

                if rows_done >= BATCH_TARGET:
                    break
                time.sleep(SLEEP_BETWEEN_BOOKS)

        state['next_index'] = start + PAGE_SIZE
        state['last_run_ts'] = int(time.time())
        save_json(STATE_FILE, state)

        if rows_done >= BATCH_TARGET:
            break
        time.sleep(SLEEP_BETWEEN_PAGES)

    state['finished_batches'] = state.get('finished_batches', []) + [batch_num]
    state['current_batch'] = batch_num + 1
    state['total_seen'] = len(seen)
    state['total_matched'] = state.get('total_matched', 0) + matched
    state['last_run_ts'] = int(time.time())
    save_json(STATE_FILE, state)
    save_json(CACHE_FILE, cache)

    elapsed = time.time() - t_batch
    print(f'BATCH_{batch_num:02d}_END books={rows_done} matched={matched} not_found={not_found} timeout={errors} elapsed={elapsed:.0f}s', flush=True)
