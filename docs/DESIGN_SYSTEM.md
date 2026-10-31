# Design System and Visual Direction

Working product name: **RosterOps** (placeholder). Direction: **calm, dense, trustworthy operations software** — closer to Linear / Stripe Dashboard / Airtable than to a generic admin template. The roster grid is the hero; everything else stays quiet around it.

## 1. Principles
1. **Information first.** Dense but legible; surface problems (gaps) before decoration.
2. **One accent, many neutrals.** Colour is reserved for meaning (status, coverage) and one brand accent.
3. **Hairlines over shadows.** Structure comes from 1px borders and spacing, not stacked cards.
4. **Few radii, few shadows.** 6px controls, 10px overlays, one soft shadow for floating layers.
5. **Motion explains.** Transitions only to show cause/effect (panel opens, cell updates).

## 2. Colour palette

### Neutrals (warm grey — avoids the cold blue-grey "template" look)
| Token | HEX | Use |
|---|---|---|
| `--bg` | `#F7F6F3` | App background |
| `--surface` | `#FFFFFF` | Panels, tables, modals |
| `--surface-2` | `#F1EFEA` | Table header, hover, zebra |
| `--border` | `#E2DFD8` | Hairlines |
| `--border-strong` | `#CFCBC1` | Inputs, dividers |
| `--text` | `#1C1B19` | Primary text |
| `--text-2` | `#5B5850` | Secondary |
| `--text-3` | `#8A867C` | Placeholder, meta |

### Accent (deep teal-green)
| Token | HEX | Use |
|---|---|---|
| `--accent-700` | `#0B4F4A` | Pressed |
| `--accent-600` | `#0F6B64` | Primary button, links, focus |
| `--accent-100` | `#DCEEEC` | Selected row, subtle fills |
| `--accent-50` | `#EEF7F6` | Hover tint |

### Roster cell status (low-saturation fills + dark text; also differ by pattern/letter for colour-blind users)
| Status | Fill | Text | Code |
|---|---|---|---|
| Working | `#FFFFFF` (with `#2F6F4F` dot) | `#1C1B19` | W |
| Weekly off | `#E9E4F4` | `#4B3F72` | WO |
| Public holiday off | `#F8E7C6` | `#7A5200` | PH |
| Holiday worked | `#DCEEEC` with PH tag | `#0B4F4A` | HW |
| Leave | `#F6D9D5` | `#8A2F25` | L |
| Comp-off | `#D9E7F5` | `#1F4E79` | CO |

### Coverage / semantic
| Meaning | HEX | Background tint |
|---|---|---|
| Covered | `#2E7D5B` | `#E3F2EA` |
| Under-staffed (warning) | `#B7791F` | `#FBF0D9` |
| Uncovered / blocking | `#C2412D` | `#FBE4DF` |
| Info | `#356CA5` | `#E4EEF8` |
| Locked / manual edit | `#6B6659` | – |

All text/background pairs target **WCAG AA** (≥ 4.5:1 for body text).

## 3. Typography
| Role | Font | Notes |
|---|---|---|
| UI & body | **Inter** (variable) | 400/500/600; `font-feature-settings: "tnum"` for all numerals |
| Numbers, IDs, dates in grid | **IBM Plex Mono** | 12px; tabular alignment |
| Page titles | Inter 600, slightly tighter tracking (−0.01em) | no decorative display face |

Scale (px / line-height): `12/16` caption · `13/20` table & dense UI · `14/22` body · `16/24` section title · `20/28` page title · `28/36` dashboard metric.

## 4. Spacing, sizing, layout
- 4px base unit; scale: 4, 8, 12, 16, 24, 32, 48.
- Control heights: **32px** (default), 28px (dense/table), 40px (login/primary CTAs).
- Table rows: 36px default, **28px in roster grid**; roster cells 36×28.
- Page gutter 24px (16px mobile). Max content width 1440px; roster uses full width.
- Radius: controls 6px, popovers/modals 10px, status chips 4px. Shadow: `0 8px 24px rgba(28,27,25,.10)` for floating layers only.

## 5. Components

### Buttons
| Variant | Style |
|---|---|
| Primary | `--accent-600` fill, white text, 32px, 500 weight; hover `--accent-700` |
| Secondary | white fill, `--border-strong` border, `--text` |
| Ghost | no border; hover `--surface-2` |
| Destructive | `#C2412D` text on white, filled only inside confirm dialogs |
Focus ring: 2px `--accent-600` with 2px offset. Disabled: 45% opacity, no pointer.

### Inputs
White, 1px `--border-strong`, 6px radius, 32px height; focus border `--accent-600` + ring; error border `#C2412D` with message below (13px). Labels above, 13px 500. Selects/comboboxes use Radix popovers with search for long lists (employees, brands).

### Chips and badges
Status chips: 20px high, 4px radius, tinted background + dark text + icon. Severity: `BLOCKING` red, `WARNING` amber, `INFO` blue.

### Tables
Header `--surface-2`, 12px 600 uppercase-less (sentence case), sticky header and first column, zebra off by default, row hover tint, selected row `--accent-50`. Column resize and sort where useful. Empty state inside table frame.

### Roster grid (signature component)
- Left sticky columns: employee name · pod · load (days worked).
- Day columns with weekday initial + date; weekends and holidays tinted in header.
- Cells show code letter (W/WO/PH/L/CO); a small corner marker for *manual* (dot) and *locked* (lock glyph).
- A **coverage strip** under the header per brand-process: a 4px bar per day coloured by coverage state, expandable into rows.
- Keyboard: arrow keys move, `Enter` opens popover, `W/O/L` quick-set, `Esc` closes.

### Modals, drawers, popovers
- Modal: forms and confirmations (max 480–560px).
- **Right drawer (420px)**: conflict details, impact preview, entity details — keeps the grid visible.
- Popover: cell editing, filters.

### Feedback
Toasts bottom-right (success 3 s; errors persist until dismissed). Inline banners for page-level issues. Skeleton rows for table loading; a determinate progress bar with elapsed time for generation.

## 6. Navigation
Left sidebar, 232px, collapsible to 56px icon rail: **Dashboard · Roster · Conflicts · Leaves · Team (Employees, Pods) · Brands & Processes · Rules & Holidays · Reports/Export · Settings**. Top bar: month switcher (prev/next), global search (⌘K command palette to jump to employee/brand), roster status chip, user menu. Active item: accent text + 2px left bar, no filled pill.

## 7. Data visualisation
- **Coverage heatmap** (brand-process rows × days): 3-state fill, hover tooltip "needs 2 · has 1 · Priya off (WO)".
- **KPI strip** on dashboard: Blocking conflicts · Coverage % · Brands at risk (single point of failure) · Pending leaves.
- **Workload bars** (days worked per employee) as a thin horizontal bar chart; **weekend-off fairness** as a dot-strip.
- Charts: single hue + semantic colours, thin axes, no gradients, no 3D, direct labels over legends.

## 8. Iconography
**Lucide** icons, 16px (20px in nav), 1.5px stroke, inherit text colour. Icons accompany labels; icon-only buttons need tooltips and `aria-label`.

## 9. Motion
| Interaction | Duration / easing |
|---|---|
| Hover/focus colour | 120 ms ease-out |
| Popover/menu | 140 ms fade + 4px translate |
| Drawer | 220 ms slide, ease-out |
| Cell value change | 180 ms background flash from `--accent-100` |
| Conflict resolved | 240 ms fade of the red marker |
Respect `prefers-reduced-motion` (disable translate/flash).

## 10. Tokens (Tailwind theme excerpt)
```ts
colors: {
  bg: '#F7F6F3', surface: '#FFFFFF', 'surface-2': '#F1EFEA',
  border: '#E2DFD8', 'border-strong': '#CFCBC1',
  ink: '#1C1B19', 'ink-2': '#5B5850', 'ink-3': '#8A867C',
  accent: { 50:'#EEF7F6', 100:'#DCEEEC', 600:'#0F6B64', 700:'#0B4F4A' },
  ok: '#2E7D5B', warn: '#B7791F', bad: '#C2412D', info: '#356CA5',
},
borderRadius: { ctl: '6px', pop: '10px', chip: '4px' },
fontFamily: { sans: ['Inter', 'system-ui'], mono: ['IBM Plex Mono', 'ui-monospace'] },
```

## 11. Things we explicitly avoid
Gradient hero cards, glow effects, glassmorphism, card-in-card nesting, pill-everything, emoji icons, multicoloured KPI tiles, identical layouts across pages, decorative illustration beyond three small empty-state glyphs.
