# Baseline-Diff Pattern — Making Quality Tools CI-Viable

## The Problem

Quality audit tools that check every file produce constant output on a large existing codebase. Running them on every CI push produces a permanent red build, which developers learn to ignore.

## The Pattern

### Two-Phase Pipeline

**Phase 1 — Establish baseline:**
```bash
tool-audit . --save-baseline .baseline.json
# Stores issue fingerprints (file|line|rule|message) in a compact JSON file.
```

**Phase 2 — Diff against baseline:**
```bash
tool-audit . --baseline .baseline.json
# Suppresses all issues present in the baseline.
# Reports only NEW issues (regressions or changes).
```

### CI Integration

```yaml
# .github/workflows/audit.yml
- run: tool-audit . --baseline .baseline.json
  # exit code = 0 only when 0 new issues
  # existing thousands of issues ignored
```

## Fingerprint Format

Each issue is a stable string key:
```
{file_path}|{line_number}|{rule_id}|{message}
```

Line numbers are included so the same error on the same line is considered "known." A fixed issue naturally falls off because the line number changes or disappears.

## Benefits

- **Zero-noise CI** for historical codebases
- **Auto-expiring** — fixed issues produce different fingerprints next baseline update
- **Baseline regenerated on demand** (`--save-baseline`) after a cleanup sprint

## Pitfalls

| Pitfall | Fix |
|---------|-----|
| Line number changes (reformat) generate false new issues | Use content hash instead of line number for stable baseline |
| Minor issues dominate and prevent detection of new criticals | Combine with `--severity-threshold` |
| Baseline grows stale | Regenerate when voluntary cleanup completes |
