# Evidence Schema — Site Audit v1.0

The unified `Evidence` model replaces the v0.x pattern where each analyzer
had its own Issue/Data/Result struct. Every analyzer (source, visual, CSS)
produces `Evidence`. Every consumer (report, HTML inspector, CI gate)
reads `Evidence`.

## Core Types

```
Evidence                   ← atomic unit
├── kind                   ← source / visual / css_token / cascade
├── analyzer               ← markdown / contrast / overflow / css_token
├── page                   ← URL path
├── element: ElementInfo   ← DOM node identity
│   ├── tag, id, classes
│   ├── css_path           ← "body > main > h1.post-title"
│   └── ancestor_chain     ← [{tag, id, classes}]
├── computed: ComputedInfo ← browser-computed values
│   ├── property, value
│   └── color, bg, fontSize, fontWeight, opacity, lineHeight
├── source: SourceInfo     ← CSS source rule
│   ├── css_file, selector, property, value
│   └── variable_chain, resolved_value, specificity
├── finding: Finding       ← diagnostic
│   └── rule, severity, confidence, message, suggestion
└── recommendation: Recommendation
    └── patch, file, line, description
```

## Key Design Decisions

**Ancestors as structured objects, not strings:**
```python
# RIGHT — can be used for descendant selector matching
{"tag": "article", "id": "", "classes": ["post-single"]}

# WRONG — information already lost
"article.post-single"
```

**Three layers of evidence (for Phase 8B confidence):**
- **Structural**: tag, class, id, ancestor chain, selector match
- **Semantic**: property match, variable trace, cascade winner
- **Rendering**: computed color, color delta, viewport, media query

**Confidence uses Required+Optional, not fixed weights:**
- HIGH: selector matched AND property matched AND cascade winner
  - Variable trace → bonus
  - Color proximity → bonus
- MEDIUM: selector matched + cascade winner (some evidence)
- LOW: selector matched only
- UNKNOWN: no evidence

Color is **never** a primary match criterion — always auxiliary.

## Report Structure (v1.0)

```json
{
  "metadata": {
    "version": "1.0",
    "timestamp": "2026-07-10T12:00:00Z",
    "target": "/path/to/project",
    "duration_seconds": 45.2,
    "pages_scanned": 25,
    "files_scanned": 120
  },
  "evidence": [ ... ],
  "metrics": {
    "score": 82,
    "total_issues": 134,
    "by_severity": {"critical": 0, "major": 5, "minor": 129},
    "by_analyzer": {"contrast": 85, "markdown": 45, "overflow": 4}
  },
  "history": [
    {"date": "2026-06-01", "score": 75},
    {"date": "2026-07-01", "score": 82}
  ]
}
```

## Backward Compatibility

`issue_to_evidence()` converts v0.x `Issue` objects to v1.0 `Evidence`.
The legacy `generate_json()` still produces the old format alongside
the new `generate_report()`.

## Key Files

- `models/evidence.py` — all types: Evidence, ElementInfo, ComputedInfo,
  SourceInfo, Finding, Recommendation, Report, ReportMetadata, Metrics