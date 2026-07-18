---
name: youtube-tutorial-search
description: Search YouTube for tutorial videos (e.g., flashing tutorials) using UI automation.
category: media
version: 0.1
trigger: |
  User wants to locate a YouTube tutorial for flashing or firmware work on a specific device (e.g., "n1 盒子 刷机教程").
  The skill applies when the task involves searching YouTube within the Hermes environment, capturing the results, and optionally opening a video.
---

## Purpose
Enable direct retrieval of YouTube tutorial videos for device flashing, firmware installation, or similar technical topics.

## Scope
- Works on macOS with the YouTube app visible.
- Uses `computer_use` to interact with the YouTube UI.
- Complements `web_search` for fallback when UI interaction fails.

## Procedure
1. **Confirm focus**: Ensure the YouTube app is frontmost. If not, focus it via `computer_use` with `action='focus_app'` (no raise).
2. **Open search**: Click the search input element (currently observed at AXTree index 5). Use `computer_use` `click` with `element=5`.
3. **Enter query**: Type the user-provided search phrase exactly, preserving spaces and punctuation. Use `computer_use` `type`.
4. **Execute search**: Send Return key to trigger search. Use `computer_use` `key` with `keys='return'`.
5. **Verify results**: Capture the resulting window (`computer_use` `capture` with `app='Google Chrome'` or `app='YouTube'`). Look for a video title that matches the query.
6. **Open video**: If a relevant video is found, click its title/link (usually the first AXButton with matching label). Use `computer_use` `click` with appropriate `element` index.
7. **Optional**: If UI interaction fails, fall back to `web_search` with the same query and open the first result URL in a browser.

## Pitfalls & Fixes
- **Element index variance**: The search field may appear at different indices across captures. Re‑capture and re‑inspect if the click fails.
- **Permission dialogs**: If a permission prompt appears, abort and ask the user for clarification; do not auto‑grant.
- **Multiple search tabs**: Ensure no extra tabs are open that could shift element indices; close extras if needed.
- **Video not found**: If the search yields no relevant video, suggest refining the query or using `web_search`.

## Verification
After completing the steps, confirm that a video window is open and playing, or that the resulting URL has been opened in the browser.

## Dependencies
- `computer_use` skill for UI automation.
- `web_search` tool for fallback search.
- `read_file`/`search_files` for debugging captured logs.

## References
- `references/n1-box-tutorial-example.md` – session‑specific transcript of the N1 box flashing tutorial search.