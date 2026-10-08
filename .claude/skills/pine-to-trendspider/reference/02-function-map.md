# 02 — Function map

How each Pine built-in maps to TrendSpider, and where the numbers diverge.

**Golden rule:** never assume a TrendSpider function exists because the name looks right.
Use only functions listed here as [VERIFIED], or hand-roll from them. When a mapping says
[VERIFY], check it before relying on it, and update this file with what you find.

Confirmed TrendSpider built-ins [VERIFIED]: `sma`, `ema`, `wma`, `custwma`, `hullma`,
`vwma`, `alma`, `kama`, `wildma`, `rsi`, `cmo`, `roc`, `momentum`, `stochastic`, `atr`,
`stdev`, `variance`, `absdev`, `highest`, `lowest`, `sum`, `linreg`, `psar`, `vortex`,
`seqcount`, `vwap`, `fractal_high`, `fractal_low`, plus helpers `add`, `sub`, `mult`, `div`,
`max_of`, `min_of`, `shift`, `series_of`, `cut_series`, `sliding_window_function`,
`for_every`, `horizontal_line`. Alternative MA choice: `indicators[name](...)` with
`constants.ma_types`.

## Seeding and warm-up — read this first

Recursive indicators differ in how they start, so **the first bars disagree even when the
formula is identical**. These facts come from running TrendSpider's real engine:

| Indicator | TrendSpider engine [VERIFIED] | Pine |
|---|---|---|
| `ema` | seeds from the first value, not an SMA | reference implementation also seeds from the first value |
| `wildma` (RMA) | seeds from a single value | `ta.rma` seeds with an SMA of the first `length` values |
| `atr` | Wilder smoothing that starts from 0 | `ta.rma` of true range, SMA-seeded |
| `rsi` | seeds from a single value | RMA-based, SMA-seeded |
| `stochastic` | result **rounded to 3 decimal places** | full precision |

Consequences:
- Treat roughly the first **3 × length** bars as warm-up. Exclude them from validation.
- After warm-up the series converge. If they still differ, the formula is wrong.
- TrendSpider's **chart** EMA/RSI/MACD indicators do not use the scripting engine's
  seeding [VERIFIED], so a converted script's EMA can differ in early bars from the EMA you
  add to the same TrendSpider chart. That is expected, not a bug.
- If exact early-bar parity matters, hand-roll the indicator with Pine's seed (examples below).

## Moving averages

| Pine | TrendSpider | Notes |
|---|---|---|
| `ta.sma(x, n)` | `sma(x, n)` | |
| `ta.ema(x, n)` | `ema(x, n)` | seeding above |
| `ta.rma(x, n)` | `wildma(x, n)` | seeding differs — hand-roll for parity (below) |
| `ta.wma(x, n)` | `wma(x, n)` | [VERIFY weight direction: most recent heaviest] |
| `ta.hma(x, n)` | `hullma(x, n)` | [VERIFY] Pine: `wma(2*wma(x, n/2) - wma(x, n), round(sqrt(n)))` — check how n/2 and sqrt(n) are rounded |
| `ta.vwma(x, n)` | `vwma(...)` | [VERIFY signature — volume argument] |
| `ta.alma(x, n, offset, sigma)` | `alma(...)` | [VERIFY argument order and defaults: Pine offset 0.85, sigma 6] |
| `ta.swma(x)` | hand-roll: `(x[i-3] + 2*x[i-2] + 2*x[i-1] + x[i]) / 6` | `custwma` can do it [VERIFY normalisation] |
| `ta.linreg(x, n, offset)` | `linreg(...)` | [VERIFY params]; hand-roll least squares when `offset ≠ 0` |

Chaining (`ta.ema(ta.ema(x, n), n)`): the inner result has leading nulls. [VERIFY] whether
TrendSpider's `ema` skips leading nulls or propagates them; if unsure, hand-roll the outer pass.

**Pine-exact RMA** (use when parity matters):

```js
const rmaPine = (src, n) => {
    const out = series_of(null);
    let acc = null, seen = 0, sum0 = 0;
    for (let i = 0; i < src.length; i++) {
        const v = src[i];
        if (isNa(v)) { out[i] = acc; continue; }
        if (acc === null) {               // SMA seed over the first n valid values
            sum0 += v; seen++;
            if (seen === n) { acc = sum0 / n; out[i] = acc; }
            continue;
        }
        acc = (acc * (n - 1) + v) / n;
        out[i] = acc;
    }
    return out;
};
```

## Oscillators

| Pine | TrendSpider | Notes |
|---|---|---|
| `ta.rsi(x, n)` | `rsi(x, n)` | seeding differs; for parity build from `rmaPine` of gains and losses |
| `ta.stoch(src, hi, lo, n)` | `stochastic(close, high, low, n)` | same argument order; TrendSpider rounds to 3 dp; [VERIFY] behaviour when high == low |
| `ta.cci(x, n)` | hand-roll: `(x - sma(x,n)) / (0.015 * dev)` | `dev` = mean absolute deviation; `absdev` [VERIFY it is mean abs dev from the SMA] |
| `ta.cmo(x, n)` | `cmo(x, n)` | [VERIFY] |
| `ta.roc(x, n)` | `roc(x, n)` | [VERIFY formula `100*(x - x[n])/x[n]`] |
| `ta.mom(x, n)` | hand-roll: `sub(x, shift(x, n))` | do **not** rely on `momentum` — its period convention is unclear |
| `ta.change(x, n=1)` | hand-roll: `sub(x, shift(x, n))` | for a `bool` source Pine returns true when the value changed |
| `ta.macd(x, f, s, sig)` | hand-roll: `m = sub(ema(x,f), ema(x,s))`, `signal = ema(m, sig)`, `hist = sub(m, signal)` | Pine returns the tuple `[macd, signal, hist]` |
| `ta.tsi(x, short, long)` | hand-roll from double-smoothed EMAs | |
| `ta.wpr(n)` | hand-roll: `100 * (close - highest(high,n)) / (highest(high,n) - lowest(low,n))` | |
| `ta.mfi(x, n)` | hand-roll from typical price and volume | |

## Volatility and bands

| Pine | TrendSpider | Notes |
|---|---|---|
| `ta.tr` / `ta.tr(false)` | hand-roll | `na` on the first bar |
| `ta.tr(true)` | hand-roll | first bar = `high - low` |
| `ta.atr(n)` | `atr(n)` or `atr(high, low, close, n)` | seeding differs; Pine-exact = `rmaPine(trueRange, n)` |
| `ta.stdev(x, n)` (biased = true, default) | `stdev(x, n)` | both **population** [VERIFIED for the engine] |
| `ta.stdev(x, n, false)` | `stdev(x, n) * sqrt(n / (n - 1))` | sample standard deviation |
| `ta.variance(x, n)` | `variance(x, n)` | same biased/unbiased rule |
| `ta.dev(x, n)` | `absdev(x, n)` | [VERIFY] |
| `ta.bb(x, n, mult)` | hand-roll: `basis = sma`, `± mult * stdev` | Pine returns `[middle, upper, lower]` |
| `ta.bbw(...)` | hand-roll from the bands | |
| `ta.kc(x, n, mult, useTR)` | hand-roll: basis `ema(x,n)`, range `useTR ? trueRange : high-low`, `ema(range, n)` | [VERIFY Pine defaults] |

## Trend

| Pine | TrendSpider | Notes |
|---|---|---|
| `ta.sar(start, inc, max)` | `psar(maximum, acceleration, start)` | **argument order is reversed** — the most common silent bug in SAR ports |
| `ta.supertrend(factor, atrLen)` | hand-roll (below) | returns `[value, direction]`; **direction < 0 means up-trend** |
| `ta.dmi(diLen, adxSmooth)` | hand-roll with `rmaPine` | returns `[plusDI, minusDI, adx]` |
| `ta.vortex` | `vortex(n)` → `{positive, negative}` [VERIFIED] | |

**Supertrend** (Pine semantics, including the inverted direction sign):

This follows Pine's documented reference implementation of `ta.supertrend` step for step:

```js
// Pine: lowerBand := lowerBand > prevLower or close[1] < prevLower ? lowerBand : prevLower
//       upperBand := upperBand < prevUpper or close[1] > prevUpper ? upperBand : prevUpper
const supertrend = (factor, atrLen) => {
    const tr = trueRange(true);               // helpers.js; Pine's ta.atr uses RMA of TR
    const a = rmaPine(tr, atrLen);
    const st = series_of(null), dir = series_of(null);
    let prevLower = null, prevUpper = null, prevSt = null;
    for (let i = 0; i < close.length; i++) {
        if (isNa(a[i])) continue;
        const mid = (high[i] + low[i]) / 2;   // hl2
        let lower = mid - factor * a[i];
        let upper = mid + factor * a[i];
        const pc = i > 0 ? close[i - 1] : null;
        const pl = nz(prevLower), pu = nz(prevUpper);           // Pine's nz(x[1])
        if (!(lower > pl || (pc !== null && pc < pl))) lower = pl;
        if (!(upper < pu || (pc !== null && pc > pu))) upper = pu;
        let d;
        if (prevSt === null) d = 1;                              // Pine: na(atr[1])
        else if (prevSt === prevUpper) d = close[i] > upper ? -1 : 1;
        else d = close[i] < lower ? 1 : -1;
        st[i] = d === -1 ? lower : upper;
        dir[i] = d;                                              // -1 = UP-trend, as in Pine
        prevLower = lower; prevUpper = upper; prevSt = st[i];
    }
    return [st, dir];
};
```

Validate this against TradingView's own Supertrend values before trusting it. Many
*published* Pine supertrends are custom variants rather than `ta.supertrend` — if the
script hand-rolls its own, port that code instead of substituting this one.

## Volume

| Pine | TrendSpider | Notes |
|---|---|---|
| `ta.vwap` / `ta.vwap(src)` | **hand-roll** (below) | Pine resets every session and the built-in uses `hlc3`. TrendSpider's `vwap()` defaults to `ohlc4` and **does not reset** [VERIFIED] |
| `ta.vwap(src, anchor, mult)` (v5 anchored) | hand-roll, resetting when `anchor` is true | also returns bands when `mult` given |
| `ta.obv` | hand-roll: running sum of `sign(change(close)) * volume` | |
| `ta.accdist`, `ta.pvt`, `ta.nvi`, `ta.pvi` | hand-roll | |

**Session VWAP**, Pine-faithful:

```js
const sessionVwap = (src, isNewSession) => {
    const out = series_of(null);
    let pv = 0, vv = 0;
    for (let i = 0; i < close.length; i++) {
        if (i === 0 || isNewSession(i)) { pv = 0; vv = 0; }
        if (!isNa(src[i]) && !isNa(volume[i])) { pv += src[i] * volume[i]; vv += volume[i]; }
        out[i] = vv > 0 ? pv / vv : null;
    }
    return out;
};
// src: hlc3 for Pine's built-in; isNewSession: see 03-time-sessions-inputs.md
```

## Highest, lowest and events

| Pine | TrendSpider | Notes |
|---|---|---|
| `ta.highest(x, n)` / `ta.lowest(x, n)` | `highest(x, n)` / `lowest(x, n)` | window includes the current bar [VERIFY] |
| `ta.highestbars` / `ta.lowestbars` | hand-roll | Pine returns the offset as a **negative** number [VERIFY] |
| `ta.crossover(a, b)` | hand-roll | `a > b` now **and** `a <= b` on the previous bar |
| `ta.crossunder(a, b)` | hand-roll | `a < b` now **and** `a >= b` previously |
| `ta.cross(a, b)` | hand-roll | either |
| `ta.barssince(cond)` | hand-roll | `na` until the condition has been true once |
| `ta.valuewhen(cond, src, k)` | hand-roll | `k = 0` is the most recent occurrence |
| `ta.rising(x, n)` / `ta.falling` | hand-roll | [VERIFY exact definition against TradingView before relying on it] |
| `ta.cum(x)` | hand-roll: running sum | |
| `ta.range(x, n)` | `sub(highest(x,n), lowest(x,n))` | |

TrendSpider has **no** built-in crossover, crossunder, barssince or valuewhen. [VERIFIED]
Use `templates/helpers.js`, which implements them with correct null handling — including
for a scalar operand (`ta.crossover(rsi, 70)`), which must be wrapped with `series_of(70)`.

## Pivots — a look-ahead trap

Pine's `ta.pivothigh(src, left, right)` returns the pivot's value on the bar **`right` bars
after** the pivot — the first bar on which it is actually known. Scripts then plot it with
`offset = -right` to draw it under the real high.

TrendSpider's `fractal_high(series, length, peakIndex?)` returns a sparse series at fractal
points. [VERIFY] **which bar** the value is placed on. If it lands on the pivot bar itself,
any signal derived from it uses information from `right` bars in the future.

For signals, always hand-roll so the value appears on the confirmation bar, exactly as in
Pine:

```js
const pivotHigh = (src, left, right) => {
    const out = series_of(null);
    for (let i = left + right; i < src.length; i++) {
        const p = i - right, v = src[p];
        if (isNa(v)) continue;
        let ok = true;
        for (let k = p - left; k < p && ok; k++) ok = !isNa(src[k]) && v > src[k];
        for (let k = p + 1; k <= i && ok; k++) ok = !isNa(src[k]) && v >= src[k];
        if (ok) out[i] = v;                       // known only at bar i = p + right
    }
    return out;
};
```

The strict-left / non-strict-right tie-break above is a common convention. [VERIFY] it
against Pine on a series containing equal highs before relying on it.

For drawing the pivot at its true bar, paint a separate series shifted back with the
reserved `offset` input — keep the signal series un-shifted.

## Statistics

`ta.correlation`, `ta.percentrank`, `ta.percentile_linear_interpolation`,
`ta.percentile_nearest_rank`, `ta.median`, `ta.mode` → hand-roll with
`sliding_window_function(series, windowSize, callback)` [VERIFIED]. Check Pine's exact
definition of each (percentrank counts previous values ≤ current) and state it in a comment.

## `math.*`

| Pine | JavaScript | Trap |
|---|---|---|
| `math.abs`, `math.sqrt`, `math.log`, `math.exp`, `math.pow`, `math.sign`, `math.floor`, `math.ceil` | `Math.*` | |
| `math.round(x)` | `Math.round(x)` | JS rounds `.5` toward +∞; check negatives if they matter |
| `math.round(x, p)` | `Math.round(x * 10**p) / 10**p` | |
| `math.max(a, b, ...)`, `math.min` | `Math.max`, `Math.min` | `Math.max(null, 3)` is **3**; guard nulls first |
| `math.avg(a, b, ...)` | arithmetic mean | |
| `math.sum(x, n)` | **`sum(x, n)`** | it is a **rolling** sum over `n` bars, not an array total |
| `math.todegrees`, `math.toradians` | multiply by `180/Math.PI` or its inverse | |
| `math.random` | `Math.random` | non-deterministic: the output changes on every recompute |

The engine's `exp` and `log` are bit-exact fdlibm and `Math.pow(x, 2)` equals `x * x`
[VERIFIED]; last-digit differences from Pine are possible and irrelevant.

## `str.*`

| Pine | JavaScript |
|---|---|
| `str.tostring(x)` | `String(x)` |
| `str.tostring(x, "#.##")` | `x.toFixed(2)` (adapt the pattern) |
| `str.tostring(x, format.mintick)` | round to the instrument's tick — see `03` on `syminfo.mintick` |
| `str.format("{0} {1}", a, b)` | template literal |
| `str.contains`, `str.length`, `str.upper`, `str.lower`, `str.split`, `str.substring` | `includes`, `length`, `toUpperCase`, `toLowerCase`, `split`, `substring` |
| `str.replace_all(s, a, b)` | `s.split(a).join(b)` — avoids `replaceAll`, whose sandbox support is unconfirmed (`07` §11) |

## Collections and types

| Pine | TrendSpider (JavaScript) | Trap |
|---|---|---|
| `array.new_float(n, v)` | build with a loop and `push` | `new Array` is **banned** [VERIFIED] |
| `array.push/pop/shift/unshift/get/set/size/clear` | `push/pop/shift/unshift/[]/length` | |
| `array.get(a, -1)` (v6 negative index) | `a[a.length - 1]` | |
| `array.sum/avg/max/min` | `reduce`, `Math.max(...a)` | |
| `array.sort(a, order.ascending)` | `a.sort((x, y) => x - y)` | JS default sort is **lexicographic** |
| `array.remove(a, i)` / `array.insert(a, i, v)` | `splice` | |
| `array.slice`, `array.copy`, `array.includes`, `array.indexof` | `slice`, `[...a]`, `includes`, `indexOf` | |
| `map.new<string, float>()` | plain object `{}` | `new Map()` is banned; stringify non-string keys |
| `matrix.*` | nested arrays | |
| `type Foo` + `Foo.new(...)` | a factory function returning an object literal | no `new`, no classes with constructors |
| `method f(Foo this, ...)` | plain function taking the object first | |

## `color.*`

| Pine | TrendSpider |
|---|---|
| `color.new(c, transp)` | `rgba(r, g, b, a)` with **`a = 1 - transp / 100`** (Pine 0 = opaque, 100 = invisible) |
| `color.rgb(r, g, b, transp)` | same conversion |
| `color.from_gradient(v, lo, hi, c1, c2)` | interpolate the RGB channels yourself |
| named colours (`color.red`, …) | the nearest CSS colour — exact hex values are cosmetic |

`paint()` accepts a **series of colours**, one per bar, for conditional colouring. [VERIFIED]
