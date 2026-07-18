---
name: macos-display-management
description: "macOS display configuration — rotation, resolution, arrangement, HiDPI scaling — via command line."
version: 1.0.0
platforms: [macos]
metadata:
  hermes:
    tags: [macOS, display, rotation, resolution, monitor, arrangement]
    category: apple
---

# macOS Display Management

CLI-driven display configuration on macOS: rotation, resolution, arrangement, HiDPI scaling. No GUI needed.

## When to Use This Skill

User wants to rotate a display, change resolution, set a new main display, configure multi-monitor arrangement, or enable HiDPI scaling — from the terminal.

## Tool of Choice: `displayplacer`

**displayplacer** is a Homebrew-installed CLI tool for precise macOS display control. It supersedes older tools (cscreen, BetterDisplay CLI for rotation).

### Install

```bash
brew install displayplacer
```

### Step 0 — Detect displays (before installing anything)

When given full authorization to set up displays without prior knowledge, first enumerate what's connected:

```bash
system_profiler SPDisplaysDataType 2>/dev/null | grep -A 20 "Displays"
```

This shows display type, resolution, rotation support, and whether it's the main display — useful even before `displayplacer` is installed. The output also reveals a built-in display's current rotation state when diagnosing a misconfigured setup.

### Core Workflow

**Step 1 — List current state**

```bash
displayplacer list
```

This outputs each display with its:
- `Persistent screen id` — use this in commands (stable across reboots)
- `Contextual screen id` — alternative, not stable
- `Serial screen id` — hardware serial
- Current `Resolution`, `Rotation`, `Origin`

**Step 2 — Apply configuration**

```bash
displayplacer "id:<persistent_id> res:<WxH> hz:60 color_depth:4 enabled:true scaling:off origin:(x,y) degree:<N>"
```

- `degree:0` = landscape, `degree:90` = portrait (clockwise)
- When rotating to portrait, **swap W and H** in `res:` — e.g. 1680×1050 landscape → 1050×1680 portrait
- `origin:(x,y)` sets position; the display with origin `(0,0)` is the **main display**
- Multiple displays: space-separate each display's config block

**Step 3 — Verify**

```bash
displayplacer list | grep -E "Type:|Resolution:|Origin:|Rotation:"
```

## Rotation Patterns

### Restore landscape (rotate back from portrait)

```bash
# MacBook built-in restored to landscape as main display
displayplacer "id:<internal_id> res:2880x1800 color_depth:4 enabled:true scaling:off origin:(0,0) degree:0"
```

### Set external monitor to portrait

```bash
# External monitor rotated 90° clockwise, positioned to the left of main
displayplacer "id:<external_id> res:1050x1680 hz:60 color_depth:4 enabled:true scaling:off origin:(-1050,0) degree:90"
```

Note: swap resolution WxH → HxW when rotating to portrait mode.

### Rotate all displays

```bash
displayplacer "id:<id1> ... degree:90" "id:<id2> ... degree:0"
```

## Resolution & HiDPI

### Set a specific resolution

```bash
displayplacer "id:<id> res:2560x1440 hz:60 color_depth:4"
```

### Enable HiDPI (scaled) mode

Use a scaled resolution from `displayplacer list` output — those marked `scaling:on` are HiDPI:

```bash
displayplacer "id:<id> res:1440x900 scaling:on color_depth:4"
```

## Multi-Monitor Arrangement

The display with `origin:(0,0)` is the **menu bar / main display**. Others use relative offsets.

Example: Dell on left (portrait), MacBook built-in on right (landscape, main):

```bash
displayplacer \
  "id:B95FD604-7CFD-1C86-A7EA-CD7E962BE497 res:1050x1680 hz:60 color_depth:4 enabled:true scaling:off origin:(-1050,0) degree:90" \
  "id:46FA2088-5175-1712-04A4-8183272CF248 res:2880x1800 color_depth:4 enabled:true scaling:off origin:(0,0) degree:0"
```

## BetterDisplay (GUI Alternative)

BetterDisplay.app provides a menu bar icon for rotation/resolution control. Its CLI (`bd_info`, `bd_list_titles`, `bd_splice`) does **not** expose rotation — use displayplacer for rotation commands.

```bash
brew install betterdisplay
```

## Gotchas

- **Swap W×H when rotating** — a 1680×1050 display rotated 90° becomes `res:1050x1680`, not `res:1680x1050`
- **Persistent IDs are stable** — always use the `Persistent screen id` from `displayplacer list`, not the contextual ID
- **Origin (0,0) = main display** — only one display can have `origin:(0,0)`; others must have negative offsets on that axis
- **Rotation applies instantly** — in practice, `displayplacer` rotates take effect immediately without a restart. The "restart may be needed" caveat applies only if the session is unstable (e.g. remote access with display state inconsistency).
- **BetterDisplay CLI has no rotation** — `bd_info`/`bd_list_titles`/`bd_splice` don't support rotation; use `displayplacer` instead