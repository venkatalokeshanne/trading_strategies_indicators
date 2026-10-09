# Pine → pinelib translation table

Imports for a typical conversion:
```python
from pinelib import Script, S, na, nz, div, iff, fixnan, ta, pmath, pstr, parray, color, NA
```

## Declarations and inputs
| Pine | Python |
|---|---|
| `indicator("T", overlay=true, max_boxes_count=100)` | `TITLE = "T"`, `OVERLAY = True`, `MAX_BOXES = 100` |
| `strategy("T", initial_capital=1000, default_qty_type=strategy.percent_of_equity, default_qty_value=10, pyramiding=2, commission_type=strategy.commission.percent, commission_value=0.1, slippage=2, process_orders_on_close=true)` | `STRATEGY = dict(initial_capital=1000, default_qty_type="percent_of_equity", default_qty_value=10, pyramiding=2, commission_type="percent", commission_value=0.1, slippage=2, process_orders_on_close=True)` |
| `//@version=6` | `PINE_VERSION = 6` (v6 strategies default margin_long/short = 100) |
| `input.int(14, "Length", minval=1)` | `self.length = self.input.int(14, "Length", minval=1)` in `init()` |
| `input.float`, `input.bool`, `input.string(options=…)`, `input.timeframe`, `input.session`, `input.symbol`, `input.color`, `input.price`, `input.time` | same names on `self.input` |
| `input.source(close, "Source")` / v4 `input(close, ...)` | `self.src = self.input.source(self.close, "Source")` |
| `input(14, "Len")` (v4/v5 generic) | `self.input(14, "Len")` |

## Values, na, operators
| Pine | Python |
|---|---|
| `close`, `open`, `high`, `low`, `volume`, `time`, `hl2`, `hlc3`, `ohlc4`, `hlcc4` | `self.close` … (behave as the current float) |
| `close[1]` | `self.close[1]` |
| `x[2]` (computed value) | `x = S(expr)` then `x[2]`; or `self.H("x").set(v)` / `self.H("x")[2]` |
| `bar_index`, `last_bar_index` | `self.bar_index`, `self.last_bar_index` (look-ahead in logic — flagged) |
| `na`, `na(x)`, `nz(x, y)`, `fixnan(x)` | `NA`, `na(x)`, `nz(x, y)`, `fixnan(x)` |
| `a / b` | `div(a, b)` unless b is a non-zero constant (P1) |
| `c ? a : b` | `a if c else b` — na condition is false: use `iff(c, a, b)` when c may be na |
| `a and b` / `a or b` (v5, b has ta.*) | compute b first, then combine (P4) |
| `x == na` (v4) | `na(x)` |
| `math.round(x)`, `math.max`, `math.min`, `math.abs`, `math.sqrt`, `math.pow`, `math.log`, … | `pmath.round(x)` … (P3) |
| `math.sum(x, n)` | `ta.msum(x, n)` (rolling!) |
| `int(x)` | `int(x)` (truncates toward 0, like Pine) |
| `var x = 0.0` | `self.x = 0.0` in `init()`; use/assign `self.x` in `on_bar()` |
| `varip x = 0` | same as `var` historically — list as a deviation |
| `x := x + 1` | `self.x = self.x + 1` (var) / `x = x + 1` (local) |
| `for i = 0 to n` | `for i in range(0, n + 1)` — Pine bounds are inclusive; `to` counts DOWN if start > end |
| `while` / `break` / `continue` | same |
| `switch` | `if/elif/else` |
| user-defined function with history | a method/function using `S()`/`ta.*` — each call site keeps its own state automatically |
| `[a, b] = f()` (tuple) | `a, b = f()` |

## ta.*
Same names: `ta.sma, ema, rma, wma, vwma, swma, hma, alma, linreg, highest, lowest,
highestbars, lowestbars, change, mom, roc, rsi, stoch, cci, cmo, tsi, wpr, mfi, macd, bb,
bbw, kc, kcw, atr, tr, dmi, sar, supertrend, vwap, crossover, crossunder, cross, rising,
falling, barssince, valuewhen, cum, pivothigh, pivotlow, stdev, variance, dev, correlation,
median, mode, percentrank, percentile_linear_interpolation, percentile_nearest_rank, obv,
accdist, pvt, iii, wvad, nvi, pvi, wad, cog`. Renamed: `ta.range` → `ta.range_`,
`ta.max/min` → `ta.max_/min_`, `math.sum` → `ta.msum`, variable `ta.tr` → `ta.tr()`,
`ta.vwap` variable → `ta.vwap()`, `ta.obv`/`ta.accdist` variables → calls.

## request.security
```python
# Pine: htf = request.security(syminfo.tickerid, "D", ta.ema(close, 20)[1], lookahead=barmerge.lookahead_on)
htf = self.security(None, "D", lambda v: S(ta.ema(v.close, 20))[1], lookahead=True)
```
`symbol=None` = chart symbol. Tuples: return a tuple from the lambda. Other symbols need the
pipeline's data provider.

## strategy.*
| Pine | Python |
|---|---|
| `strategy.entry("L", strategy.long, qty, limit, stop, oca_name, comment)` | `self.strategy.entry("L", self.strategy.long, qty=…, limit=…, stop=…, comment=…)` |
| `strategy.entry(..., when=cond)` (v4/v5) | `if cond: self.strategy.entry(...)` |
| `strategy.exit("X", "L", profit=, loss=, limit=, stop=, trail_points=, trail_offset=, trail_price=, qty_percent=)` | same keywords |
| `strategy.close("L", qty_percent=50, immediately=true)` | same keywords |
| `strategy.close_all()`, `strategy.cancel("id")`, `strategy.cancel_all()`, `strategy.order(...)` | same |
| `strategy.position_size`, `position_avg_price`, `opentrades`, `closedtrades`, `wintrades`, `losstrades`, `netprofit`, `openprofit`, `equity`, `initial_capital` | same properties |
| `strategy.opentrades.entry_price(i)` | `self.strategy.opentrades_entry_price(i)` (and `_entry_bar_index`, `_size`, `_entry_id`…) |
| `strategy.closedtrades.profit(i)` | `self.strategy.closedtrades_profit(i)` (…`_exit_price`, `_exit_bar_index`…) |

## Outputs and drawings
| Pine | Python |
|---|---|
| `plot(x, "Name", color)` | `self.plot(x, "Name", color=…)` |
| `plotshape(cond, "Buy", …)`, `plotchar`, `plotarrow` | `self.plotshape(cond, "Buy")` |
| `bgcolor(c)`, `barcolor`, `fill`, `hline` | `self.bgcolor(c)` … |
| `alertcondition(cond, "T", "msg")`, `alert("msg")` | `self.alertcondition(cond, "T", "msg")`, `self.alert("msg")` |
| `line.new(x1, y1, x2, y2, …)` | `self.draw.line_new(x1, y1, x2, y2, …)`; methods/fields: `l.x2 = …`, `l.get_price(x)` |
| `box.new(l, t, r, b, …)` / `box.get_top(b)` / `box.set_right(b, x)` | `self.draw.box_new(...)` / `b.top` / `b.right = x` |
| `label.new(x, y, text)` | `self.draw.label_new(x, y, text)` |
| `*.delete(obj)` | `self.draw.delete(obj)` |
| `table.new(position.top_right, 2, 3)` / `table.cell(t, c, r, "x")` | `self.draw.table_new("top_right", 2, 3)` / `t.cell(c, r, "x")` |

## Arrays, maps, strings, colour, time
| Pine | Python |
|---|---|
| `array.new_float(0)`, `array.push(a, x)`, `array.get(a, i)`, `array.size(a)`, `array.shift`, `array.remove`, `array.sum/avg/max/min/stdev/median`, `array.sort` | `parray.new()`, `parray.push(a, x)`, … same names (Pine's out-of-range errors kept) |
| `map.new<string, float>()` / `map.put` / `map.get` | `{}` / `m[k] = v` / `m.get(k, NA)` |
| `str.tostring(x, "#.##")`, `str.format`, `str.contains`, … | `pstr.tostring(x, "#.##")`, `pstr.format`, … |
| `color.new(color.red, 80)`, `color.rgb(...)` | `color.new(color.red, 80)`, `color.rgb(...)` |
| `year`, `month`, `dayofmonth`, `dayofweek`, `hour`, `minute` (of the bar) | `self.year()`, `self.month()`, … (`dayofweek` keeps Pine's 1 = Sunday) |
| `hour(time, "UTC")` | `self.hour(self.time, "UTC")` |
| `time(timeframe.period, "0930-1600")` | `self.time_fn(None, "0930-1600")` (na outside the session) |
| `timeframe.period`, `.isintraday`, `.multiplier`, `timeframe.change("D")` | `self.timeframe.period`, … , `self.timeframe.change("D")` |
| `syminfo.tickerid`, `.mintick`, `.pointvalue`, `.timezone` | `self.syminfo.tickerid`, … |
| `barstate.isfirst/islast/isconfirmed/isnew/isrealtime` | `self.barstate.isfirst` … (historical: confirmed, never realtime) |
