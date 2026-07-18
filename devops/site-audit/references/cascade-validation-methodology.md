# Cascade Resolution Validation Methodology

## Why selector-first?

`computed_color == source_color` is not a valid matching assumption. Browser cascade applies:

- Variable expansion (`var(--x)`)
- Inheritance chains
- Cascade specificity/override
- Opacity/compositing
- Media queries (`@media prefers-color-scheme`)
- Theme selectors (`.dark`, `[data-theme="dark"]`)
- Browser color management / gamma

**Result**: computed values almost always differ from any literal CSS source value.

## Strategy

```
1. Selector match     →  tag/.class/#id/descendant/group
2. Property match     →  does the rule define the relevant property?
3. Specificity sort   →  id(100) > class(10) > tag(1)
4. Color-delta        →  informational only (not a filter)
```

## Confidence Levels

| Level | Criteria | Meaning |
|-------|----------|---------|
| HIGH | selector + variable trace | CSS source identified including originating variable |
| MEDIUM | selector + close color | Selector matches, computed color close to source (delta < 20/channel) |
| LOW | selector only | Selector matched but color cascade-adjusted (delta >= 20/channel or no variable) |
| UNKNOWN | no match | Not resolvable by static analysis |

## Color Delta

Per-channel maximum delta between two hex colors:

| Label | Threshold | Meaning |
|-------|-----------|---------|
| exact | 0 | Identical hex |
| close | < 20/channel | Likely same logical color, minor cascade adjustment |
| different | >= 20/channel | Probably different CSS rule or heavy cascade effect |
| unknown | N/A | Could not parse one or both colors |

## Validation Run

```python
from site_audit.css_analyzer.cascade import CascadeResolver

resolver = CascadeResolver("hugo-site/public")
resolver.load()
# -> all_rules, resolved_rules, source_index ready

# Convert dict issues to Issue objects
issues = [dict_to_issue(d) for d in report["visual_layer_issues"]]
cr = resolver.batch_resolve(issues)

print(f"Mapped: {cr.mapped}/{cr.total_issues} ({cr.mapped_accuracy*100:.1f}%)")
print(f"Confidence: HIGH={cr.confidence_counts['HIGH']} MEDIUM={cr.confidence_counts['MEDIUM']} LOW={cr.confidence_counts['LOW']}")
```

## Expected Results on Typical Hugo Sites

- **Selector mapping**: 100% (every element selector matches at least one CSS rule)
- **HIGH confidence**: 30-40% (most issues map to direct CSS colors, not variables)
- **MEDIUM/LOW**: 60-70% (cascade-adjusted colors, selector-only matches)
- **Unmatched**: 0% (selector-first catches everything including generic tag matches like `a`)

## Unmatched Case Analysis

When an issue is UNKNOWN (0% expected with selector-first), common reasons:

1. **Inline style**: `style="color: rgb(...)"` — not in CSS files
2. **JS-generated**: Color set via JavaScript (dynamic themes, random colors)
3. **Shadow DOM**: Styles scoped to Shadow DOM not in global CSS
4. **CSS-in-JS**: Runtime injection (styled-components, etc.)

These cannot be resolved by static CSS analysis.