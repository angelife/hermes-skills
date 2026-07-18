# Hugo Quality Pipeline Design Pattern

## Architecture (6 Phases)

A quality engineering pipeline for Hugo static sites that progresses from detection to repair assistant:

```
Phase 1  Scanner         Markdown source lint          发现问题
Phase 2  Reports         Structured JSON/HTML output   工程化报告
Phase 3  Browser Audit   Playwright DOM + WCAG CDP     浏览器真实性检测
Phase 4  CI Gate         Baseline diff + exit codes     CI 质量门禁
Phase 5  CSS Analysis    Variable graph + color tokens  CSS 根因分析
Phase 6  Patch Preview   Simulation + snapshot         安全修复辅助
```

## Key Design Decisions

### Baseline Before CI (Phase 4)
- First deployment must run `--save-baseline` to capture current state
- CI pipeline runs `--baseline baseline.json --ci` only (no save)
- Prevents permanent red builds on inherited debt

### Static CSS Analysis Over Browser StyleSheets (Phase 5)
- `document.styleSheets` blocked by CORS for external stylesheets
- Lower-level `public/**/*.css` parse is reliable for Hugo
- Variable graph (var → resolved value) built from static analysis

### Preview-Only Fixes (Phase 6)
- `--patch-preview` generates markdown, never modifies CSS
- Three-tier candidates: light (min change), balanced, strong
- Simulation recalculates contrast ratio without touching issues
- Regression snapshot detects token drift across theme upgrades

## Technology Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Browser | Playwright (Python) | CDP native, supports all browsers |
| CSS parse | Custom regex parser | Hugo CSS is predictable; full parser overkill |
| Reporting | JSON + Markdown | Machine-readable + human-reviewable |
| Testing | Pytest | Standard Python test framework |

## Color Suggestion Algorithm

For a failing token on white background:
1. Calculate luminance difference needed for 4.5:1 ratio
2. Scale RGB channels proportionally
3. Three candidates at 1.02x, 1.2x, 1.5x target margin
4. Return as light/balanced/strong tiers with delta (Euclidean) and ratio

## CLI Flag Progression

```
--save-baseline          Phase 4: first-run baseline
--baseline X --ci        Phase 4: quality gate
--css-audit              Phase 5: token analysis
--patch-preview          Phase 6: preview only
--css-snapshot PATH      Phase 6: save state
--css-regression         Phase 6: detect drift
```

## When to Apply This Pattern

Use this architecture when you need to:
- Monitor a Hugo site's quality over time
- Catch regressions before deployment
- Move from 100s of scattered problems → 1 CSS variable root cause
- Provide safe, preview-only fix suggestions