# Session Reference: 2026-06-26 — MacBook Pro + Dell 2208WFP Setup

## Hardware
- MacBook Pro (Intel Iris Pro + AMD R9 M370X)
- External: Dell 2208WFP 22" (1680×1050, CU88977B143S)

## Goal
- Mac built-in: restore landscape (was 90° portrait)
- Dell: portrait 90°, not main display

## Resolution swap rule
When rotating 1680×1050 to portrait: use `res:1050x1680` (W and H swapped).

## Working command
```bash
displayplacer \
  "id:B95FD604-7CFD-1C86-A7EA-CD7E962BE497 res:1050x1680 hz:60 color_depth:4 enabled:true scaling:off origin:(-1050,0) degree:90" \
  "id:46FA2088-5175-1712-04A4-8183272CF248 res:2880x1800 color_depth:4 enabled:true scaling:off origin:(0,0) degree:0"
```

## Key observations
- `displayplacer list` shows both displays with their persistent IDs
- BetterDisplay CLI (bd_info/bd_list_titles) does NOT support rotation — use displayplacer
- Dell's native portrait resolution is 1050×1680 (same 60Hz as landscape)
- Mac built-in's native landscape is 2880×1800 (Retina)