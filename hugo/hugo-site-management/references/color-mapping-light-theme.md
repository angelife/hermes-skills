# SVG Light-Theme Color Mapping

Angelife site uses polk-x light theme. When creating/porting SVGs from dark mode:

## Layer colors
| Element | Dark (original) | Light (adapted) |
|---|---|---|
| Page background | `#020617` | `#fff` |
| Box fill | `#0f172a` | `#f8fafc` |
| Layer boundary dash | Opacity 0.5 | Opacity 0.5, same stroke |

## Input layer (cyan)
| Element | Dark | Light |
|---|---|---|
| Layer border | `#22d3ee` | `#0891b2` |
| Box fill | `rgba(8,51,68,0.4)` | `#f8fafc` |
| Box stroke | `#22d3ee` | `#0891b2` |
| Title | `#22d3ee` | `#0891b2` |
| Arrow | `#22d3ee` | `#0891b2` |

## Processing layer (emerald)
| Element | Dark | Light |
|---|---|---|
| Layer border | `#34d399` | `#059669` |
| Hermes box fill | `rgba(6,78,59,0.5)` | `#f0fdf4` |
| Hermes stroke | `#34d399` | `#059669` |
| 五行 fill | `rgba(251,146,60,0.2)` | `#fff7ed` |
| 五行 stroke | `#fb923c` | `#f59e0b` |

## Knowledge layer (violet)
| Element | Dark | Light |
|---|---|---|
| Layer border | `#a78bfa` | `#7c3aed` |
| Box fill | `rgba(76,29,149,0.4)` | `#f5f3ff` |
| Box stroke | `#a78bfa` | `#7c3aed` |

## Output layer (amber)
| Element | Dark | Light |
|---|---|---|
| Layer border | `#fbbf24` | `#d97706` |
| Box fill | `rgba(120,53,15,0.3)` | `#fffbeb` |
| Box stroke | `#fbbf24` | `#d97706` |

## Editing surface (rose)
| Element | Dark | Light |
|---|---|---|
| Layer border | `#fb7185` | `#e11d48` |
| Box fill | `rgba(244,63,94,0.15)` | `#fff1f2` |
| Box stroke | `#fb7185` | `#e11d48` |

## Return flows
- Always use lower opacity (0.3–0.6) for dashed return path arrows
- Labels in muted text: `#94a3b8` → `#64748b`

## Text
| Role | Dark | Light |
|---|---|---|
| Primary title | `#e2e8f0` | `#333` |
| Subtitle/desc | `#94a3b8` | `#64748b` |
| Muted hint | `#64748b` | `#64748b` or `#94a3b8` |

## Grid pattern
- Dark: `stroke="#1e293b" stroke-width="0.5"`
- Light: `stroke="#e2e8f0" stroke-width="0.5"`
