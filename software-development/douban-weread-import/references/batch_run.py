import subprocess, json, time, csv
from pathlib import Path

PROFILE='Thomas.Xie'
OUT_DIR=Path('/Users/macos/douban_import_batches')
OUT_DIR.mkdir(exist_ok=True)
PAGE_SIZE=15
MAX_START=285
DELAY_BOOK=25
DELAY_PAGE=10

def cli(args):
    return subprocess.run(['opencli','browser','browser']+args, capture_output=True, text=True, timeout=30).stdout or ''

def weread(payload):
    import urllib.request
    key=''
    with open('/Users/macos/key.txt') as f:
        key=''.join([line.strip() for line in f if line.startswith('wrk-')])
    body=json.dumps({'skill_version':'1.0.4', **payload}).encode()
    req=urllib.request.Request('https://i.weread.qq.com/api/agent/gateway', data=body, headers={
        'Authorization': 'Bearer '+key,
        'Content-Type': 'application/json'
    })
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read())
    except Exception:
        return {'_err':'timeout_or_blocked'}

def search_book(title, author=''):
    k=(title+' '+(author or '')).strip()
    if not k:
        return None
    data=weread({'api_name':'/store/search','keyword':k,'count':5})
    if data.get('errcode') not in (None,0):
        return None
    for res in data.get('results', []):
        if res.get('title')=='电子书':
            bs=res.get('books', [])
            if not bs:
                continue
            info=bs[0].get('bookInfo',{})
            author0=(author or '').strip().split()[0]
            if author0 and author0 in (info.get('author','') or ''):
                return info
            return info
    return None

def parse(raw):
    try:
        data=json.loads(raw)
    except Exception:
        return []
    rows=[]
    for item in data:
        sid=item.get('id')
        title=item.get('title','')
        author=item.get('author','')
        pub=item.get('pub','')
        rating=item.get('rating','')
        if sid:
            rows.append((sid, title, author, pub, rating))
    return rows

# Resume support
seen=set()
for p in OUT_DIR.glob('batch_*.tsv'):
    try:
        for row in csv.reader(p.open('r',encoding='utf-8'), delimiter='\t'):
            if row and row[0].isdigit():
                seen.add(row[0])
    except Exception:
        pass
print('resume seen', len(seen), flush=True)

header=['douban_subject_id','douban_title','douban_author','douban_pubDate','douban_rating','weread_bookId','weread_title','weread_author','weread_rating','readingCount','status','deepLink','best_mark_count','best_mark_preview']
out=OUT_DIR / 'batch_latest.tsv'
with open(out,'w',newline='',encoding='utf-8') as f:
    csv.writer(f, delimiter='\t').writerow(header)

rows=0; matched=0
cli(['open', f'https://book.douban.com/people/{PROFILE}/collect?start=0&sort=time&rating=all&filter=all&mode=grid'])
time.sleep(3)

for start in range(0, MAX_START+1, PAGE_SIZE):
    cli(['open', f'https://book.douban.com/people/{PROFILE}/collect?start={start}&sort=time&rating=all&filter=all&mode=grid'])
    time.sleep(1.2)
    raw=cli(["eval","(() => { const items=[...document.querySelectorAll('.item, .subject-item')].slice(0,20); return JSON.stringify(items.map(n => { const a=[...n.querySelectorAll('a')].find(a => a.title && a.href.includes('/subject/')); const meta=(n.querySelector('.pub')||{}).textContent||''; const rating=(n.querySelector('.rating_nums')||{}).textContent||''; return a ? { id: a.href.split('/')[4], title: a.title.trim(), author: meta.split('/')[0].trim(), pub: meta, rating: rating.trim() } : null; }).filter(Boolean)); })()"])
    page=parse(raw)
    if not page:
        time.sleep(2)
        continue
    with open(out,'a',newline='',encoding='utf-8') as f:
        w=csv.writer(f, delimiter='\t')
        new_on_page=0
        for sid, title, author, pub, rating in page:
            if sid in seen:
                continue
            seen.add(sid)
            new_on_page += 1
            m=search_book(title, author)
            if m:
                bid=m.get('bookId')
                bm=weread({'api_name':'/book/bestbookmarks','bookId':str(bid),'count':5}) if bid else {}
                marks=(bm.get('bestBookmarks') or bm.get('bookmarks') or bm.get('items') or [])
                first=(marks[0].get('markText') if isinstance(marks,list) and marks else '') or (marks[0].get('text') if isinstance(marks,list) and marks else '') or ''
                w.writerow([sid, title, author, pub, rating, str(bid), m.get('title',''), m.get('author',''), m.get('newRating',''), m.get('readingCount',''), 'matched', m.get('deepLink') or ('weread://reading?bId='+str(bid) if bid else ''), str(len(marks)), first[:100]])
                matched += 1
            else:
                w.writerow([sid, title, author, pub, rating, '', '', '', '', '', 'not_found', '', '0', ''])
            rows += 1
            f.flush()
            time.sleep(DELAY_BOOK)
    print(f'PAGE {start} new={new_on_page} rows={rows} matched={matched} seen={len(seen)}', flush=True)
    if rows >= 50:
        print('TARGET_REACHED', rows, flush=True)
        break
    time.sleep(DELAY_PAGE)

print('BATCH_DONE rows=', rows, 'matched=', matched, 'seen=', len(seen), flush=True)
