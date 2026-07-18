---
name: doom-emacs-macos-setup
description: Set up, configure, and optimize Doom Emacs on macOS for a developer with a specific project (Hugo, Python, etc.). Covers brew install, module selection by project type, macOS config patterns, straight.el corruption fix, vterm compilation, and verification.
trigger:
  - User asks to install/setup/configure Doom Emacs on macOS
  - User asks to optimize Emacs for a specific project
  - User reports doom sync errors (git HEAD corruption)
  - User sees ligature warnings or vterm not working
---

# Doom Emacs (macOS) — Setup & Project Optimization

## Installation

```bash
# Stable Emacs via brew
brew install emacs

# Doom
git clone --depth=1 https://github.com/doomemacs/doomemacs ~/.config/emacs
~/.config/emacs/bin/doom install
```

## Module Selection by Project Profile

**Before editing init.el**, inspect the user's project to pick relevant modules:

| Project type | Enable these modules |
|---|---|
| Python + scripts | `(python +lsp +eglot)`, `(format +onsave)` |
| Hugo/Markdown blog | `markdown`, `(spell +flyspell)`, `yaml`, `data` (TOML), `web` |
| Web/JS/HTML/CSS | `web`, `(format +onsave)` |
| Shell scripts | `sh` |
| General | `(evil +everywhere)`, `json`, `(format +onsave)` |

Also create a `.dir-locals.el` in the project root:

```elisp
;; .dir-locals.el example for Hugo project
((nil
  (projectile-project-root . "/path/to/project/")
  (projectile-project-type . "hugo"))
 (python-mode
  (python-interpreter . "python3"))
 (markdown-mode
  (markdown-enable-yaml-frontmatter . t)))
```

## macOS-Specific Config (`config.el`)

```elisp
;; PATH: add ~/.local/bin first
(add-to-list 'exec-path (expand-file-name "~/.local/bin/"))

;; Font: prefer JetBrainsMono Nerd Font (brew cask)
(setq doom-font (font-spec :family "JetBrainsMono Nerd Font" :size 14 :weight 'regular))

;; macOS key handling
(setq mac-option-modifier 'meta
      mac-command-modifier 'hyper)
(setq ns-use-native-fullscreen t
      ns-use-thin-smoothing t)

;; Python formatter: prefer ruff over black
(after! python
  (setq-hook! 'python-mode-hook
    +format-with-lsp nil
    +format-with 'ruff))

;; Spell checking
(setq ispell-program-name "aspell")
```

## System Dependencies (brew)

```bash
brew install fd shellcheck cmake libvterm aspell ruff
```

## Straight.el HEAD Corruption — Known Recurring Issue

Doom's package manager (`straight.el`) occasionally clones repos that end up with **no git HEAD**. Manifestation:

```
fatal: ambiguous argument 'HEAD': unknown revision or path not in the working tree
```

**Fix** — find all broken repos and delete them, then re-sync:

```bash
cd ~/.config/emacs/.local/straight/repos
for d in */; do
  (cd "$d" && git rev-parse HEAD 2>/dev/null) || rm -rf "$d"
done
```

Notable repos that have failed this way: `projectile`, `emacs-libvterm`, `sass-mode`, `apheleia`, `eglot-booster`.

## Vterm Manual Compilation

If `doom sync` can't build vterm (repo empty after clone, cmake timeout):

```bash
# Install system libvterm + cmake first
brew install libvterm cmake

# Clone manually and compile
cd /tmp
git clone --depth=1 https://github.com/akermu/emacs-libvterm.git
cd emacs-libvterm && mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j4

# Copy the .so to straight's repo
cp vterm-module.so ~/.config/emacs/.local/straight/repos/emacs-libvterm/
```

Then `doom sync --no-env` to rebuild init.el.

## Brew Emacs Limitations

| Issue | Cause | Fix |
|---|---|---|
| No native-comp | brew formula default | Accept (cosmetic) |
| No Harfbuzz | brew formula default | **Disable ligatures module** in init.el |
| Ligatures warning | Consequence of above | `;;(ligatures +hugs)` → `;;ligatures` |
| `doom sync` timeout (>2min) | Zsh gitstatus plugin | Prefix: `GITSTATUS_ENABLE=0 ...` or use `/bin/sh` |

## Verification

```bash
# After changes
doom sync --no-env
# Check health
doom doctor
```

Expected output: `✓ Initialized Doom Emacs X.Y.Z` with **0 errors**.
Non-blocking warnings (ignore): ~/.emacs.d coexistence, no native-comp, missing Symbola font.
