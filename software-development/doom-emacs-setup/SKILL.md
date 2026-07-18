---
name: doom-emacs-setup
description: Install, configure, and maintain Doom Emacs on macOS (brew). Covers init.el/config.el/packages.el, system deps, font setup, doom sync/doctor, and the Emacs 30+ 'emacs-lsp-booster' landscape.
trigger:
  - User asks to install or set up Emacs or Doom Emacs
  - User asks to optimize or configure Doom config files
  - doom sync, doom doctor, or doom upgrade needs troubleshooting
  - Non-obvious Doom path or macro issues arise (PATH, --no-env, hook macros)
---

# Doom Emacs Setup (macOS)

## Installation

### 1. Install Emacs and system deps

```bash
brew install emacs
```

System dependencies for full `doom doctor` clearance:

```bash
# fd — file search acceleration for Doom
HOMEBREW_NO_AUTO_UPDATE=1 brew install fd shellcheck
```

### 2. Install Doom Emacs

```bash
git clone --depth 1 https://github.com/doomemacs/doomemacs ~/.config/emacs
~/.config/emacs/bin/doom install
```

This creates the starter config skeleton at `~/.config/doom/`.

### 3. PATH

The `doom` binary lives at `~/.config/emacs/bin/doom`. Add to PATH or use the full path:

```bash
export PATH="$HOME/.config/emacs/bin:$PATH"
```

This is NOT on PATH by default after brew install.

## Configuring

Doom's config lives in `~/.config/doom/` with three files:

| File | Purpose |
|------|---------|
| `init.el` | Module enable/disable (which languages, tools, UI to load) |
| `config.el` | User settings, keybindings, hook functions |
| `packages.el` | Extra packages beyond Doom's defaults |

### init.el — module selection

Enable modules by uncommenting/adding lines. Key modules for a developer macOS setup:

```elisp
;; Languages
:lang
(python +lsp)      ; with eglot LSP support
json
yaml
data               ; TOML config files (hugo.toml etc)
markdown
org
sh
web                ; HTML/CSS for frontend/site work

;; Tools  
:tools
editorconfig
eval +overlay
lsp                 ; only if using eglot (Doom's default)
magit               ; Git integration

;; Editor
:editor
(file-templates)
fold
(format +onsave)   ; auto-format Python/MD on save
snippets

;; UI
:ui
doom                ; Doom theme
modeline
(hl-todo)
ligatures           ; => → ➡, != → ≠ (needs Nerd Font)
;;(spell +flyspell)  ; spell-check on blog/MD writing (needs aspell system dep)

;; Checkers
(checkers syntax)

;; OS
:os
macos               ; macOS-specific compatibility

;; App
:app
(telegram)          ; if you use telega.el

;; Config
:config
(default +bindings +smartparens)
```

### packages.el — extra packages

For packages not in MELPA, use `:recipe` with `:host :github :repo`. 

```elisp
;; All-the-icons for modeline/tab-bar icons  
(package! all-the-icons)

;; Ruff — fast Python formatter (replaces black)
;; (ensure `ruff` is on PATH; install via brew or `uv tool install ruff`)

;; Example: GitHub-hosted package
(package! some-package
  :recipe (:host github :repo "user/repo"
           :files ("*.el")))
```

**KNOWN PITFALL:** `eglot-booster` (GitHub `jdtsmith/eglot-booster`) is NOT in MELPA. The repo is archived (as of 2025) because Emacs 30+ built-in JSON parsers solve the same performance problem. Do NOT attempt to install it — Emacs 30.2+ handles eglot JSON natively.

**KNOWN PITFALL:** `emacs-lsp-booster` (GitHub `blahgeek/emacs-lsp-booster`) also has its `.el` file removed from the upstream repo. The binary alone does nothing without the Emacs Lisp integration. On Emacs 30+, neither package is needed.

### config.el — user preferences

```elisp
;; macOS font: JetBrains Mono Nerd Font (install via brew cask or manual download)
(setq doom-font (font-spec :family "JetBrainsMono Nerd Font" :size 14))

;; PATH for user-installed tools
(add-to-list 'exec-path (expand-file-name "~/.local/bin/"))

;; macOS specific
(setq mac-option-modifier 'meta
      mac-command-modifier 'super
      ns-use-thin-smoothing t
      frame-resize-pixelwise t)

;; Relative line numbers (Doom default: absolute; toggle with M-m t l)
(setq display-line-numbers-type 'relative)

;; Evil window navigation: right split goes right
(setq evil-vsplit-window-right t
      evil-split-window-below t)
```

**KNOWN PITFALL:** Doom macros like `set-hook!` and `add-hook!` are NOT available in `doom doctor`'s non-interactive context. Use plain Emacs:

```elisp
;; WRONG — causes error during doom doctor:
(set-hook! 'python-mode-hook (setq python-indent-offset 4))

;; RIGHT:
(add-hook 'python-mode-hook
  (lambda ()
    (setq-local python-indent-offset 4
                tab-width 4)))
```

## Running doom sync

```bash
# ALWAYS use --no-env to avoid piped-input hang on brew Emacs
export PATH="$HOME/.config/emacs/bin:$PATH"
cd ~/.config/emacs && doom sync --no-env
```

**Known issue:** `doom sync` without `--no-env` can hang waiting for piped stdin on brew-installed Emacs. `doom sync --no-env` skips the shell env dump and proceeds directly.

If sync times out during large package pulls:
```bash
# Just run again — it's idempotent
doom sync --no-env
```

## Verification

```bash
doom doctor
```

**Expected output:** 0 errors. Non-blocking warnings (4-5 typical):
- `~/.emacs.d` coexists — harmless, chemacs users ignore
- No native compilation — brew Emacs ships without it; minor perf difference
- Symbola font missing — legacy fallback, non-critical if Nerd Font installed
- markdown compiler / pipenv / nosetests — non-blocking dev tool warnings

## Font Setup

Nerd Font (for modeline/icons):
```bash
# Direct download (brew cask often times out)
cd /tmp
curl -sL "https://github.com/ryanoasis/nerd-fonts/releases/download/v3.3.0/NerdFontsSymbolsOnly.zip" -o nf.zip
unzip -qo nf.zip -d nf-syms
cp nf-syms/*.ttf ~/Library/Fonts/
```

Symbola (legacy Emacs fallback — **not available as of 2026**):
All known sources (housecleaning.org, GitHub mirrors, fontlibrary.org) return 404. The font is a legacy Emacs fallback no longer distributed. `Symbols Nerd Font` (installed above) clears the critical icon rendering path. `doom doctor` will permanently list Symbola as missing — acknowledge as an unsolvable warning in reports.

Fonts are picked up immediately by running Emacs; no cache flush needed on macOS.

## Post-setup: project-specific tailoring

After basic setup + doctor clearance, **inspect the user's actual projects** and tailor config. Generic "developer macOS" config is not enough.

### 1. Profile the project

```bash
find ~/project -maxdepth 3 \( -name "*.py" -o -name "*.go" -o -name "*.rs" -o -name "*.md" \) | sed 's/.*\.//' | sort | uniq -c | sort -rn | head -10
```

Detect: Hugo site vs Python project vs full-stack vs shell-heavy.

### 2. Enable relevant modules

| Project type | Modules to enable |
|---|---|
| Hugo/blog | `markdown`, `yaml`, `web`, `data`, `(spell +flyspell)` |
| Python project | `python +lsp`, `(format +onsave)` |
| Full-stack/web | `web`, `javascript`, `css` |

### 3. Add `.dir-locals.el` to project root

```elisp
((nil
  (projectile-project-root . "/absolute/path/to/project")
  (projectile-project-type . "hugo"))   ; or "python" / "emacs" / nil
 (python-mode
  (python-interpreter . "python3")
  (python-check-command . "ruff check"))
 (markdown-mode
  (markdown-enable-yaml-frontmatter . t)))
```

This makes Emacs auto-detect the project type, set correct interpreter, and enable frontmatter syntax for Hugo posts.

### 4. Preconfigure Python formatter

Ruff replaces black as the default Python formatter (10x faster, same ruleset):

```elisp
;; config.el
(after! python
  (setq-hook! 'python-mode-hook
    +format-with-lsp nil    ; don't rely on LSP for formatting
    +format-with 'ruff))    ; use ruff directly
```

Install ruff: `brew install ruff` or `uv tool install ruff`.

### 5. Spell checker deps

If `(spell +flyspell)` is enabled in init.el, install a system dictionary:

```bash
brew install aspell
```

No config needed — Emacs detects it automatically.

## Upkeep

```bash
# Update packages
doom upgrade

# Rebuild after config changes
doom sync --no-env

# Health check
doom doctor
```

## Pitfalls

- **PATH**: `doom` binary at `~/.config/emacs/bin/`, NOT on default PATH after brew install
- **sync --no-env**: Required to avoid piped-input hang on brew Emacs. `doom install` and `doom upgrade` also benefit from this flag
- **Hook macros**: `set-hook!` / `add-hook!` are Doom macros, not available in `doom doctor` or batch Emacs; use plain `(add-hook 'mode-hook (lambda () ...))`
- **emacs-lsp-booster**: Archived upstream, .el file removed, NOT in MELPA. Emacs 30+ built-in JSON parsers make it unnecessary. Do NOT install
- **eglot-booster**: Also NOT in MELPA, repo archived. Same rationale — don't bother
- **Brew slowness**: Set `HOMEBREW_NO_AUTO_UPDATE=1` to suppress auto-update on single commands. For large installs that may still timeout (90s+), use the **background terminal pattern**: `terminal(command="HOMEBREW_NO_AUTO_UPDATE=1 brew install aspell ruff", background=True, notify_on_complete=True)`. This frees the agent to continue working while brew auto-updates resolve.
- **Doom sync timeout** (foreground): `doom sync` can exceed the 120s foreground timeout on slow networks or large package pulls. Use background sync: `doom sync --no-env` via `background=True, notify_on_complete=True`.
- **Nerd Font via brew cask**: Often times out due to brew auto-update; direct download is faster
- **Empty git repos (silent straight.el clone failure)**: If `doom sync --no-env` exits 255 and the error log (`~/.config/emacs/.local/state/logs/cli.doom.*.error`) shows `git rev-parse HEAD` returning fatal 128, straight.el silently cloned an empty repo (no HEAD commit). Known pattern: projectile, emacs-libvterm. Recovery: `rm -rf ~/.config/emacs/.local/straight/repos/<name>` then re-run `doom sync --no-env`. Straight re-clones and the sync completes normally.
- **vterm native module: cmake required + silent build failure**: The `:term vterm` module needs `cmake` to compile `vterm-module.so`. If cmake missing or build fails silently (empty repo), vterm shows as enabled in doctor but doesn't work. Fix: `brew install cmake`; if still failing, build manually:

  ```bash
  cd /tmp && git clone --depth=1 https://github.com/akermu/emacs-libvterm.git
  cd emacs-libvterm && mkdir build && cd build
  cmake .. -DCMAKE_BUILD_TYPE=Release && make -j4
  cp vterm-module.so ~/.config/emacs/.local/straight/repos/emacs-libvterm/
  ```

  Then `doom sync --no-env` to regenerate byte-compiled elc.
- **Symbola font (legacy fallback — not available as of 2026)**: All known sources return 404. Symbols Nerd Font covers icon rendering. `doom doctor` will permanently warn about Symbola — non-blocking. Do not spend time trying to find a download.
