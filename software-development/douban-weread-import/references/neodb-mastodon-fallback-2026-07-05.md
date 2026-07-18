# neodb.social / Mastodon fallback notes

User indicated previous Douban work likely flowed through a decentralized/export-style pipeline, consistent with neodb.social (a Mastodon instance oriented toward books/reading).

## Reachability probe (2026-07-05)

- DNS resolves to `104.244.43.234`
- TCP connection times out from this Mac
- HTTP returns empty/0 bytes
- `https://feizhaojun.com/?p=3813` returns 200 with content "豆瓣开发者不完全指南"
- `https://neodb.social/` times out / unreachable from this host despite valid DNS

## Implication for data recovery

If the user previously exported Douban reading history through neodb.social or a related bot, that export is:
- likely offline or hosted separately
- not recoverable from neodb.social during this session
- worth asking the user for direct file export rather than continued blind crawling

## Lesson

When the user mentions an old decentralized/export-based Douban pipeline, treat it as a potential alternate source of truth and ask for exported data files before continuing crawler-based collection.