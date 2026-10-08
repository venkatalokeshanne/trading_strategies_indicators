# 04 — Plotting and drawing

## Declaring the indicator

```js
describe_indicator('Exact Original Title', 'overlay', { shortName: 'Short' });   // or 'lower'
```
[VERIFIED]

| Pine | TrendSpider |
|---|---|
| `indicator(..., overlay=true)` | `'overlay'` |
| `indicator(..., overlay=false)` (default) | `'lower'` |
| `scale=scale.left` / `scale.none` | no confirmed equivalent — note if it matters |
| `format=format.percent`, `precision=` | no confirmed equivalent [VERIFY] |
| `max_bars_back`, `max_lines_count`, `max_labels_count`, `max_boxes_count` | drop — but see the fixed-slot rule below |

**One script cannot paint both a lower pane and the price overlay.** [VERIFIED] If the
Pine script does — v6 `force_overlay=true` on some plots, or a lower oscillator that also
calls `barcolor()` — split it into two TrendSpider scripts and say so in both headers.

**A lower indicator whose only output is colour clouds will not render.** [VERIFIED] Add
at least one real line (it can be thin and unobtrusive).

**At most 70 output series per script.** [VERIFIED]

## `plot()`

```js
paint(series, { name: 'Basis', color: '#2962ff', style: 'line', thickness: 2 });
```
Keys confirmed: `name`, `color`, `style`, `thickness`, `hidden`. [VERIFIED]

| Pine `plot(...)` argument | TrendSpider |
|---|---|
| `title` | `name` — must be a **fixed literal** (see `07`) |
| `color` (constant) | `color: '#rrggbb'` or `rgba(...)` |
| `color` (conditional per bar) | `color:` a **series of colour strings**, one per bar [VERIFIED] |
| `linewidth` | `thickness` |
| `display = display.none` | `hidden: true` |
| `offset = n` | reserved input named `offset`, or paint `shift(series, n)` |
| `trackprice`, `histbase`, `join`, `editable`, `show_last` | no confirmed equivalents — drop and note if visible behaviour depends on them |

Styles available [VERIFIED]: `line`, `histogram`, `stacked_histogram`, `dotted` (scatter;
`marker`: `circle`, `square`, `diamond`, `triangle`, `triangle-down`), `ladder`,
`labels_above`, `labels_below`, `area`, `arearange` (needs `{high, low}` points),
`columnrange` (needs `{high, low}`), `candles`, `boxplot`, `bubble`.

| Pine style | TrendSpider style | Notes |
|---|---|---|
| `plot.style_line`, `style_linebr` | `line` | nulls break the line [VERIFY that TrendSpider breaks rather than bridges a null] |
| `plot.style_stepline`, `style_stepline_diamond` | `ladder` | [VERIFY that `ladder` is a step line] |
| `plot.style_histogram`, `style_columns` | `histogram` | |
| `plot.style_circles` | `dotted` with `marker: 'circle'` | |
| `plot.style_cross` | `dotted` with the nearest marker | note the shape change |
| `plot.style_area`, `style_areabr` | `area` | |

## Shapes, characters and arrows

| Pine | TrendSpider |
|---|---|
| `plotshape(cond, style=shape.triangleup, location=location.belowbar)` | `dotted` series holding a price (e.g. `low`) where `cond`, `null` elsewhere, `marker: 'triangle'` |
| `plotshape(..., location=location.abovebar)` | same, holding `high`, `marker: 'triangle-down'` |
| `plotshape(..., text="BUY")` | `labels_below` / `labels_above` style [VERIFY the data shape — text vs value] |
| `plotchar(cond, char="•")` | `labels_above` / `labels_below` with the character |
| `plotarrow(series)` | `dotted` with `triangle` / `triangle-down` |
| `shape.circle`, `square`, `diamond` | matching `marker` |
| `shape.xcross`, `cross`, `flag`, `arrowup`, `arrowdown`, `labelup`, `labeldown` | nearest available marker — note the change |
| `location.absolute` | the series value itself |
| `location.top` / `location.bottom` | no confirmed equivalent in a price pane — use a fixed offset from `high`/`low` and note it |
| `size=size.tiny…huge` | no confirmed size control [VERIFY] |

## Lines, fills and backgrounds

| Pine | TrendSpider |
|---|---|
| `hline(price, ...)` | `paint(horizontal_line(price), {...})` [VERIFIED `horizontal_line(value, fromIndex?, toIndex?)`] |
| `hline` with `linestyle=hline.style_dashed/dotted` | no confirmed dashed-line option [VERIFY]; `dotted` is a *scatter* style, not a dashed line — don't conflate them |
| `fill(plot1, plot2, color)` | `const a = paint(...), b = paint(...); fill(a, b, color, opacity, 'title')` [VERIFIED] |
| `fill(hline1, hline2)` | paint both as `horizontal_line`, then `fill` |
| `fill` with gradient (`top_color`/`bottom_color`) | single colour — note it |
| two-colour fill that flips when the lines cross | `color_cloud(s1, s2, colorAbove, colorBelow, name1, name2)` [VERIFIED] |
| `barcolor(color)` | `color_candles(colorSeries)` [VERIFIED] |
| `bgcolor(color)` | no confirmed equivalent. Options: a lower-pane `area` / `columnrange`, or omit. List as a deviation [VERIFY] |
| `plotcandle(o, h, l, c)`, `plotbar(...)` | style `candles` [VERIFY the expected point shape] |

Pine colour transparency: `color.new(c, 80)` → alpha `0.2`. (`a = 1 - transp / 100`.)

## Drawing objects

Pine's `line.new`, `label.new`, `box.new` and `table.new` create objects at run time,
often conditionally and in unpredictable numbers. TrendSpider records every output at
save time (see `07`), so **you cannot create a variable number of outputs.**

Use the **fixed-slot pattern**: decide a maximum `N`, always paint exactly `N` slots, and
fill unused ones with `constants.empty_series` [VERIFIED]:

```js
const MAX = 10;                                  // matches Pine's max_lines_count, or less
const segs = lastNSegments(MAX);                 // your logic: [{i0, p0, i1, p1}, ...]
for (let k = 0; k < MAX; k++) {
    const s = segs[k];
    paint(s ? line(s.i0, s.p0, s.i1, s.p1, false) : constants.empty_series,
          { name: `Level ${k + 1}`, color: '#888', thickness: 1 });
}
```

Names generated from a loop counter over a **fixed** range are stable from run to run. Names
built from inputs or data are not, and orphan their output. [VERIFY that counter-based
template names are accepted; if not, write the N calls out with literal names.]

| Pine | TrendSpider | Notes |
|---|---|---|
| `line.new(x1, y1, x2, y2, extend=extend.right)` | `line(fromIndex, fromPrice, toIndex, toPrice, extendRight)` [VERIFIED] | Pine `x` may be `bar_index` or `time` (`xloc.bar_time`) — convert time to index |
| `label.new(x, y, text)` | `paint_label_at_line(lineRef, atIndex, text, attributes)` [VERIFIED] — a label must hang off a painted line | |
| `box.new(left, top, right, bottom)` | `arearange` / `columnrange` with `{high, low}` points [VERIFIED styles], or two horizontal segments + `fill` | zones such as order blocks and FVGs |
| `table.new` + `table.cell` | `paint_overlay(name, {position, offset_x, offset_y, parent, order}, {rows: [...]})` [VERIFIED] | rendered as a **static image**; sandboxed, no network |
| `linefill.new(l1, l2, color)` | `fill(ref1, ref2, color)` | |
| `polyline.new` | sequence of `line` segments, or omit | |
| `line.delete`, `label.delete`, `box.delete` | the fixed-slot pattern above replaces deletion | |
| `.set_*` updates on existing objects | recompute the slot's series | |

## Plots into the future

A positive Pine `offset` that pushes values to the right of the last bar, or forecasts:
`paint_projection(lineRefOrValues, values, params)` — **at most 100 points**. [VERIFIED]

## Labels showing numbers

`str.tostring` formatting → see `02-function-map.md` §`str.*`. Label text is a JS string;
build it with template literals and `toFixed`.
