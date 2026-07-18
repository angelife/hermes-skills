# Douban pagination findings — 2026-07-05

- `start=1245` returned HTTP 200 with empty parsed items via requests, but live `opencli browser` DOM eval returned valid subjects. Use live DOM eval; requests/curl alone is unreliable here.
- Logs showed `PAGE_ERR ... HTTP Error 404` from `idx=1245` to `1830`, but rerunning the page returned 200. Those 404s were transient/soft-block signals, not true absence.
- Stable extraction continued from `start=840` through at least `start≈2490`.
- From `start≈2145-2490` pages still returned titles, but weread matched 0. This is match-rate decay, not pagination end.
- End-of-list signal: only treat it as ended after **30 consecutive pages with zero new douban_subject_id and zero matched**.
