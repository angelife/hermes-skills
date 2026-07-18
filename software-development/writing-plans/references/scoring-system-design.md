# Scoring System Design — Capped Normalized Scoring

## The Problem

Naive deductive scoring (e.g., `100 - n_minor`) produces meaningless results for real-world tools:

- 6903 minor spacing issues → score = 0
- Says nothing about site quality — only measures "historical debt volume"

This is common in quality audit tools where one severity class dominates.

## The Fix: Per-Severity Caps

```python
critical:  -10 each, max -50  (5 issues max penalty)
major:     -3 each,  max -30  (10 issues max penalty)
minor:     -1/100,   max -20  (2000 issues = -20)

score = max(0, 100 - critical_penalty - major_penalty - minor_penalty)
```

## Why This Works

| Scenario | Naive | Capped | Meaning |
|----------|-------|--------|---------|
| 0 issues | 100 | 100 | ✅ Perfect |
| 1 critical + 0 minor | 90 | 90 | ✅ One bad problem |
| 20 major + 6883 minor | 0 | **50** | ✅ Heavy format debt, no structural issues |
| 0 major + 0 critical + 2500 minor | 0 | **80** | ✅ Cosmetic dust only |
| 20 critical | -100 | **50** | ✅ Cap prevents one class from zeroing |

## When to Apply

Any tool that:
- Produces a numerical quality score
- Has multiple severity classes with uneven volume
- Is run on historical/large codebases

## Anti-Patterns

- **Linear add-all**: `100 - sum(all issues)` — single large category zeros the score
- **Arbitrary thresholds**: `score = B if issues < N else C` — lossy, no gradation
- **Exponential penalties**: `-2^n per issue` — cap doesn't linearize
