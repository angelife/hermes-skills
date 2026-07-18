---
name: site-audit
description: Hugo Quality Engineering Pipeline — dual-layer audit (Markdown source + Playwright render), CSS design token root-cause analysis, cascade resolution (computed → source mapping), patch preview with risk levels, CSS regression snapshots, and CI gates. For Hugo sites primarily but works with any static site.
tags: [hugo, audit, ci, quality-gate, playwright, wcag, css-token-audit, cascade-resolution, patch-preview, regression]
---

# site-audit

Hugo Quality Engineering Pipeline covering: Markdown source audit → Playwright render layer → CSS Design Token root-cause → Cascade Resolution (computed→source) → Patch Preview → Regression Snapshots → CI gates.

## Trigger

- User asks to audit a static site's layout/typography
- CI pipeline needs a quality gate before deploy
- "Check if my site has visual issues"
- Pre-deploy review for Hugo/Jekyll/etc. sites
- "Why do I have N contrast issues?" → CSS token audit to find root-cause variable
- "Map these DOM colors back to CSS source" → Phase 7 cascade resolution

## Quick Start

```bash
cd ~/angelife.github.com/site_audit
.venv/bin/python -m site_audit.cli /path/to/hugo-project --max-pages 50 --output ./reports/
```

## Core Workflows

### 1. First-run Baseline (establish ground truth)

```bash
site-audit . --save-baseline .site_audit_baseline.json
```

Captures ALL current issues (both source and visual). Next runs suppress these.

### 2. Incremental Audit (CI mode)

```bash
site-audit . --baseline .site_audit_baseline.json --ci
```

Exit codes: `0` = pass, `1` = new major, `2` = new critical.

### 3. Full Scan with CSS Token Audit (root-cause)

```bash
site-audit . --max-pages 100 --output ./audit/ --css-audit
```

Produces: JSON report, HTML report, evidence screenshots, `css_token_issues` array.

### 4. CSS Cascade Resolution (Phase 7 — computed → source)

After a scan, resolve each visual issue back to its CSS source rule:

```bash
cd ~/angelife.github.com
site_audit/.venv/bin/python -c "
from site_audit.css_analyzer.cascade import CascadeResolver
resolver = CascadeResolver('hugo-site/public')
resolver.load()
# resolver.source_index → selector index
# resolver.resolved_rules → var() expanded rules
# resolver.batch_resolve(issues) → CascadeReport with accuracy %
"
```

Output: `cascade_mapping.json` + `cascade_resolution_report.md` with per-issue source file, line, selector, variable name, and risk level.

### 5. Patch Preview (read-only)

```bash
site-audit . --css-audit --patch-preview
```

Generates `site_audit_patch.md` with Before/After diffs, three candidate colors (light/balanced/strong), and risk badges. **No files are modified.**

### 6. CSS Regression Snapshot

```bash
site-audit . --css-snapshot css_snapshot.json
# Later: detect regressions
site-audit . --css-regression --css-baseline css_snapshot.json
```

JSON snapshot of all CSS variables and color tokens. Diff detects changes.

## Architecture

Pipeline as of v1.0 Release Candidate (July 2026). Architecture freeze —
no new phases beyond RC. All future work is plugin-based (add Analyzer
subclass, not core change).

**Phase 1 — Source Layer** (`scanner/scanner.py`):
Heading hierarchy, paragraph spacing (CJK-ASCII), image alt text, table formatting, link validation.

**Phase 2 — Engineered Reports** (`reporter/`):
JSON, HTML, markdown output formats with selector aggregation.

**Phase 3 — Render Layer** (`renderer/`):
Playwright sync API wrapper. Contrast check via `getComputedStyle`, overflow detection at 375px, font-size validation.

**Phase 4 — CI Gates** (`models/issue.py`, `reporter/baseline.py`):
Tiered cap scoring (critical max -50, major max -30, minor max -20). Baseline diffing. CI exit codes.

**Phase 5 — CSS Design Token Analyzer** (`css_analyzer/`):
Parses `public/**/*.css`. Builds variable graph, resolves `var(--x)` chains (depth 5), aggregates color tokens by normalized hex, generates fix suggestions with luminance scaling + 10% safety margin.

**Phase 6 — Patch Preview & Regression** (`css_analyzer/patch/`, `simulation.py`, `snapshot.py`):
Three-tier candidate colors (light/balanced/strong). Before/After simulation. Read-only patch diffs. CSS regression snapshots.

**Phase 7 — Cascade Resolution** (`css_analyzer/cascade.py`, `source_index.py`, `selector_match.py`):
Connects browser computed styles to CSS source rules via **selector-first** strategy:

- **Architecture**: Selector match → property match → cascade specificity → color-delta analysis (not a matching criterion)
- **Selector Matcher** (`selector_match.py`): tag/.class/#id/descendant/group matching with CSS specificity calculation (id=100, class=10, tag=1)
- **Variable Scope**: recursive resolution with local scope context, theme awareness (.dark, [data-theme])
- **Source Index**: selector-to-file/line/properties lookup with class/tag/id indexing
- **Dark Mode Detection**: separates light/dark theme rules via `.dark` and `[data-theme]` selectors
- **Confidence Levels**: HIGH (selector + variable trace), MEDIUM (selector + delta close), LOW (selector only, cascade-adjusted), UNKNOWN
- **Color Delta**: per-channel comparison (exact/close/different/unknown) — strictly informational, never a filter condition

**Phase 8A — DOM Evidence Export** (`models/evidence.py`, `renderer/contrast.py`):
Structured fact layer exported from Playwright. Every scanned element produces a unified `Evidence` object containing:
- `element: ElementInfo` — {tag, id, class_list, css_path}
- `ancestors` — list of `{tag, id, classes}` dicts for each DOM ancestor (NOT strings, prevents re-parsing)
- `css_path` — human-readable path like `"body > main > article.post-single > h1.post-title"` (debugging only)
- `computed: ComputedInfo` — color, bg, fontSize, fontWeight, opacity, lineHeight
- `selector` — best-effort Playwright-style selector
- `match_count` — how many elements share this selector on the page

Evidence is exported to JSON per-page when `--evidence-export` is set. This is the **facts layer** — no scoring, no inference. All downstream analyzers (cascade, patch, regression) consume this schema.

**Phase 8B — Cascade Resolution v2** (future):
Uses Phase 8A `ancestors` data to resolve CSS selectors with real DOM context instead of heuristic guessing. Introduces three-layer evidence classification:
- **Structural**: tag, class, id, ancestor, selector
- **Semantic**: property, variable trace, cascade winner
- **Rendering**: computed color, color delta, viewport, media query
Confidence uses Required+Optional pattern (not fixed weights): HIGH requires selector matched AND property matched AND cascade winner; bonuses for variable trace and color proximity.

**Key insight**: `computed_color == source_color` is not a sound assumption. Browser cascade (variable expansion, inheritance, opacity, compositing, dark mode, browser color management) means computed colors may differ from any literal value in CSS source files. Selector matching is the primary resolution path; color matching is a secondary signal only.

## CLI Reference

| Flag | Purpose |
|------|---------|
| `--max-pages N` | Limit pages scanned (default 100) |
| `--skip-render` | Source-only mode (fast, no browser) |
| `--baseline FILE` | Diff against baseline (only report new) |
| `--save-baseline FILE` | Save current state as baseline |
| `--severity-threshold` | Filter: critical/major/minor |
| `--ci` | CI exit code mode |
| `--contrast-screenshot` | Screenshot 1 per unique selector |
| `--url URL` | Use live URL instead of building |
| `--output DIR` | Report output directory |
| `--css-audit` | Run CSS Design Token Audit (default: on) |
| `--no-css-audit` | Skip CSS token analysis |
| `--patch-preview` | Generate read-only patch diffs |
| `--css-snapshot FILE` | Save CSS variable/color snapshot |
| `--css-regression` | Detect CSS variable changes vs baseline |
| `--evidence-export` | Export structured DOM evidence JSON (Phase 8A) to evidence/ directory |
| `--css-baseline FILE` | Load previous snapshot for regression |

## Key Files

- `cli.py` — entry point, orchestrates all layers
- `models/issue.py` — Issue dataclass with `.fingerprint()` method
- `models/evidence.py` — Unified Evidence model (Evidence, ElementInfo, ComputedInfo, SourceInfo, Finding, Recommendation, Report). Replaces old Issue/DOMEvidence split. See `references/evidence-schema.md`.
- `reporter/baseline.py` — save/load/diff baselines, selector aggregation
- `renderer/browser.py` — Playwright sync API wrapper
- `renderer/contrast.py` — WCAG ratio calculation + Phase 8A evidence export
- `renderer/overflow.py` — mobile overflow detection + screenshot
- `css_analyzer/parser.py` — CSS rule/selector/value extraction
- `css_analyzer/variables.py` — Enhanced variable scope (recursive depth 5, local scope, theme awareness)
- `css_analyzer/colors.py` — Color token aggregation
- `css_analyzer/source_index.py` — Selector-to-file/line index with class/tag/id lookup
- `css_analyzer/selector_match.py` — Selector matching engine with CSS specificity (id=100, class=10, tag=1)
- `css_analyzer/cascade.py` — Selector-first cascade matcher with confidence levels + color-delta analysis
- `css_analyzer/report.py` — Token issues + color suggestion algorithm
- `css_analyzer/simulation.py` — Before/After impact prediction
- `css_analyzer/snapshot.py` — CSS regression snapshot
- `css_analyzer/patch/__init__.py` — Patch data model with risk levels
- `css_analyzer/patch/preview.py` — Markdown patch diff generator
- `validate_phase7.py` — Cascade resolution accuracy validation (mapped %, confidence distribution)
- `validate_phase8.py` — Phase 8 validation (future)
- `tests/test_selector_match.py` — Selector matching + specificity tests
- `tests/test_mapping_confidence.py` — Confidence level + color-delta tests
- `tests/test_cascade.py` — Cascade integration tests
- `tests/test_variable_resolver.py` — Variable resolution tests (recursive, depth-limit, fallback)
- `tests/test_evidence.py` — Phase 8A evidence model + raw JS conversion tests

## Pitfalls

### Evidence export requires Hugo server with correct baseURL
The `--evidence-export` flag requires the Playwright render layer to discover pages via sitemap.xml.
The CLI no longer runs `hugo build` before starting the server — it relies on the Hugo server
to generate the sitemap dynamically with the correct `--baseURL http://127.0.0.1:<port>`.

Without this fix, the sitemap had production URLs (`https://angelife.github.io/`) that didn't
match the local server URL (`http://127.0.0.1:<port>`), causing `get_page_urls()` to find 0 pages.

### Playwright installation
Must use mirror for China network:
```bash
uv pip install playwright -i https://mirrors.aliyun.com/pypi/simple/
```
Then: `.venv/bin/playwright install chromium`

### CSS source mapping via browser vs static analyzer
The render layer reads `document.styleSheets` which is blocked by CORS/livereload. This doesn't affect detection accuracy — only the `css_source` field. For actual root-cause, use `--css-audit` which parses `public/**/*.css` statically.

### Baseline format changed v3 → v4
Old baselines used `rule:file:line` format. New baselines include visual fingerprints like `contrast:.post-meta:#888:#fff:2.8`. Old format still loads but won't match visual issues.

### Score vs CI mode are different
Score reflects total issues (including suppressed baseline). CI mode only counts NEW issues after baseline diff. A site can score 30/100 but pass CI if all issues are baseline-known.

### CSS Token Audit requires Hugo build
The CSS analyzer reads from `public/**/*.css`. You must run `hugo build` first, or the analyzer will find nothing. The CLI auto-detects both `public/` and `hugo-site/public/`.

### HSL color parsing limited
The parser handles hex, rgb(), rgba(), and common named colors well. HSL colors are approximated and may not map precisely to hex.

### Variable chain depth > 5
Deeply nested `var(--a, var(--b, var(--c, ...)))` beyond depth 5 stops resolving and returns the raw `var()` string. This is intentional to prevent infinite loops.

### Phase 7: Cascade resolution is selector-first, not color-first

Selector matching (tag/.class/#id/descendant) is the primary match pathway and typically achieves 100% selector-to-rule mapping. However:
- Color values will often differ between browser computed and CSS source due to cascade adjustments (variable expansion, opacity, compositing, dark mode, browser color management). Do NOT treat this as a match failure — it is expected cascade behavior.
- Inline styles and JS-generated colors are not resolvable by static analysis.
- Confidence levels help distinguish: HIGH (variable trace confirmed), MEDIUM (color delta close), LOW (selector only, cascade-adjusted).
- The `color_delta` field reports the extent of cascade adjustment but is never a match criterion.

### Phase 7/8: NEVER try to verify descendant selectors without DOM ancestry

**Critical lesson from Phase 8 debugging (July 2026):**
CSS descendant selectors like `.article .post-title` require the element to have an ancestor matching `.article`. You cannot verify this by comparing ancestor classes against the element's own classes — that's a category error. The element `h1.post-title` inside `<article class="article">` has `class_list=["post-title"]`, NOT `class_list=["article", "post-title"]`.

A heuristic that naively rejects selectors when no ancestor class appears in the element's class list will:
- ❌ False-negative: `.article .post-title` → `h1.post-title` (legal, but rejected)
- ✅ True-negative: `.gs-title *` → `.logo` (correctly rejected, but for the wrong reason)

**The correct approach**: Do NOT try to make heuristic selector matching "more precise." Instead:
1. Accept that static CSS analysis cannot resolve descendant selectors without DOM ancestry data
2. Use Phase 8A (DOM Evidence Export via Playwright) to get real ancestor chains
3. Phase 8B uses these real ancestors for proper descendant selector resolution
4. In `selector_match.py`, the ancestor check should remain permissive (`pass` on unverifiable ancestors) — tightness comes from Phase 8A/8B, not from the static matcher

**Common mistake to avoid**: Patching `_selector_part_matches` to `return False` when ancestor classes don't match element classes. This breaks `.entry-content .post-title` → `h1.post-title` while trying to fix `.gs-title *` → `.logo`. The real fix is DOM evidence, not a smarter heuristic.

### Patch Preview is read-only only
Never modifies CSS files or commits. All output goes to `/tmp` or specified output dir. Risk levels: "low" for variable replacement, "medium" for direct color values, "high" for properties affecting many selectors.

## CI Integration Example

```yaml
# .github/workflows/site-audit.yml
name: Site Audit
on:
  pull_request:
    paths: ['hugo-site/**', 'content/**']
jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install markdown-it-py
      - run: cd site_audit && uv pip install playwright -i https://mirrors.aliyun.com/pypi/simple/
      - run: .venv/bin/playwright install chromium
      - run: |
          cd hugo-site
          hugo --gc --minify
          ../site_audit/.venv/bin/python -m site_audit.cli . \
            --baseline ../site_audit/.site_audit_baseline.json \
            --ci \
            --output ../site_audit/reports/
```

## CSS Token Audit Output Format

When `--css-audit` runs, the JSON report includes:

```json
{
  "css_token_issues": [
    {
      "color": "#888888",
      "variable": "--secondary",
      "contrast_min": 3.9,
      "affected_selectors": [".post-meta", ".post-title", ".post-item"],
      "issue_count": 68,
      "suggestion": "Change #888888 → #6b6b6b (WCAG AA from 3.9:1 to 5.2:1)"
    }
  ]
}
```

## Phase 7 Cascade Resolution Output

`cascade_mapping.json` structure (selector-first strategy):
```json
{
  "accuracy": { "total_issues": 85, "mapped": 85, "unmatched_count": 0, "mapped_accuracy": "100.0%", "confidence_distribution": { "HIGH": 32, "MEDIUM": 0, "LOW": 53, "UNKNOWN": 0 } },
  "match_details": [
    { "issue_selector": ".post-title", "computed_color": "#1a1a1a", "css_source": "themes/PaperMod/assets/css/core/style.css", "css_selector": ".post-title", "variable": "--primary", "variable_resolved": "#222", "color_delta": "different", "specificity": 11, "confidence": "HIGH", "theme": "" }
  ],
  "unmatched_selectors": [...]
}
```

Key fields:
- `mapped`: count of issues resolved to any CSS source rule (all confidence levels except UNKNOWN)
- `confidence`: HIGH (selector + variable trace), MEDIUM (selector + close delta), LOW (selector only, cascade-adjusted)
- `color_delta`: exact/close/different/unknown — informational, NOT a match criterion
- `variable_resolved`: the CSS source value of the variable (may differ from computed_color)
- `specificity`: CSS specificity score (id=100, class=10, tag=1)

## Pipeline Maturity

| Phase | Capability | Status |\n|-------|-----------|--------|\n| 1 | Source Markdown audit | ✅ |\n| 2 | Engineered reports | ✅ |\n| 3 | Browser render layer | ✅ |\n| 4 | CI quality gates | ✅ |\n| 5 | CSS design token root-cause | ✅ |\n| 6 | Patch preview + regression | ✅ |\n| 7 | Cascade resolution (computed→source) | ✅ |\n| 8A | DOM Evidence Export (unified facts layer) | ✅ |\n| 8B | Evidence-based cascade resolution | 🔜\n\nv1.0 RC — Architecture freeze in effect. All future work via Plugin API, not core changes.