# 01 — Execution model

The single most important difference. Get this right and most of the port follows.

## The two models

**Pine** runs your script **once per bar**, oldest to newest. Every variable is implicitly a
*series*: `close` means "this bar's close", `close[1]` means "the previous bar's". State
carried with `var` survives from one bar to the next. On the live bar the script re-runs on
every tick.

**TrendSpider** runs your script **once for the entire dataset**. [VERIFIED]
`open`, `high`, `low`, `close`, `volume`, `time` are plain JavaScript arrays, index 0 =
oldest bar. There is no "current bar". Nothing persists between runs — every recompute
(editing, saving, a live update) re-executes the whole script from scratch. [VERIFIED]

So a Pine line like `x = close - close[1]` is not one value — it is a whole array you must
build: `const x = sub(close, shift(close, 1))`.

## Translating a Pine expression

Prefer the vectorised helpers when the expression is stateless:

| Pine | TrendSpider |
|---|---|
| `a + b`, `a - b`, `a * b`, `a / b` (series) | `add(a, b)`, `sub(a, b)`, `mult(a, b)`, `div(a, b)` — each accepts series or numbers [VERIFIED] |
| `math.max(a, b)` across series | `max_of(a, b)` / `min_of(a, b)` [VERIFIED] |
| arbitrary per-bar expression | `for_every(a, b, (va, vb) => ...)` [VERIFIED] |
| a constant series | `series_of(value)` [VERIFIED] |

`for_every(s1, ..., sN, callback)` calls `callback(v1, ..., vN, prevOutput, index)` for each
bar, where `prevOutput` is the value the callback returned for the previous bar. [VERIFIED —
confirmed in TrendSpider's own engine] That previous-output argument is how you express
recursion without a loop.

Use an **explicit forward `for` loop** when the logic is stateful in more than one variable,
branches heavily, or needs to look several bars back conditionally. It is clearer and you
control every guard. Build output arrays with `series_of(null)` and assign by index —
`new Array(n)` is banned. [VERIFIED]

```js
const out = series_of(null);
for (let i = 0; i < close.length; i++) {
    // i is Pine's bar_index
}
```

## History references `x[n]`

| Pine | TrendSpider |
|---|---|
| `x[n]` as a series | `shift(x, n)` — **positive shifts forward** (bar `i` receives `x[i-n]`) [VERIFIED] |
| `x[n]` inside a loop | `i - n >= 0 ? x[i - n] : null` — always guard the lower bound |
| `x[n]` with variable `n` | loop form only; `shift` takes a fixed offset |

Pine returns `na` for history before the first bar; your guard must return `null` there,
not `undefined` and not `0`.

## `var`, `varip` and persistent state

```pine
var float hi = na
if newSession
    hi := high
else
    hi := math.max(hi, high)
```

becomes a forward loop carrying `hi` in a local variable:

```js
const sessionHigh = series_of(null);
let hi = null;
for (let i = 0; i < close.length; i++) {
    if (isNewSession(i)) hi = high[i];
    else hi = hi === null ? high[i] : Math.max(hi, high[i]);
    sessionHigh[i] = hi;
}
```

- Do **not** emulate `var` by mutating a module-level variable from inside a `for_every`
  callback. It works by accident and breaks the moment the callback order or count changes.
- `varip` exists so a value survives **intrabar** ticks on the live bar. TrendSpider has no
  intrabar model — treat `varip` as `var` and list it as a deviation if the script's logic
  depends on tick-by-tick updates (rare: counters of ticks, intrabar high-water marks).

## Recursive series

Pine allows a series to reference its own past: `s := alpha * src + (1 - alpha) * nz(s[1])`.
Use `for_every`'s previous-output argument:

```js
const s = for_every(src, (v, prev) =>
    v == null ? prev : (prev == null ? v : alpha * v + (1 - alpha) * prev));
```

Get the **seed** right — the value used when `s[1]` is `na`. Pine code often seeds with `src`,
with an SMA, or with 0. Copy exactly what the script does; it changes the first few hundred
bars of output.

## `na` and the JavaScript null traps

Represent Pine `na` as `null`. Then guard **every** comparison and arithmetic step that can
see a null, because JavaScript coerces silently:

| Expression | JavaScript result | Pine result |
|---|---|---|
| `null >= 0` | **true** | `na` (false) |
| `null < 1` | **true** | `na` (false) |
| `null + 5` | **5** | `na` |
| `null * 2` | **0** | `na` |
| `undefined + 5` | `NaN` | — |
| `NaN > 0` | false | — |

These produce plausible numbers rather than errors, which is what makes them dangerous.

Helpers (put them in the script — see `templates/helpers.js`):

```js
const isNa = v => v === null || v === undefined || Number.isNaN(v);
const nz = (v, r = 0) => (isNa(v) ? r : v);
```

| Pine | TrendSpider |
|---|---|
| `na(x)` | `isNa(x[i])` |
| `nz(x)`, `nz(x, y)` | `nz(x[i])`, `nz(x[i], y)` |
| `fixnan(x)` | forward-fill in a loop: keep the last non-na value |
| `na` literal | `null` |

Indicator warm-up values in TrendSpider may come back as `null` or as `NaN`. [VERIFY which]
`isNa` covers both, so always use it rather than `=== null`.

**Booleans and na differ by Pine version.** In v4/v5 a `bool` can be `na`, and an `na`
condition behaves as false in `if`. In v6 a `bool` can never be `na`. When porting, treat a
condition built from an `na` operand as false — and make that explicit with a guard.

## User-defined functions with history — the call-site trap

In Pine, a function that uses `[n]` or `var` keeps a **separate history for each place it is
called**:

```pine
f(src) => src - src[1]
a = f(close)
b = f(open)       // f has its own independent history here
```

A naive JS function called per bar cannot see the previous bar's internal state. Rewrite
such functions to take **whole series** and return a **whole series**:

```js
const f = src => sub(src, shift(src, 1));
const a = f(close);
const b = f(open);
```

Functions with `var` inside them need the same treatment: one state variable per call
site, which falls out naturally when the function processes a whole array in its own loop.

## Control flow

| Pine | JavaScript | Trap |
|---|---|---|
| `for i = 0 to n` | `for (let i = 0; i <= n; i++)` | Pine's upper bound is **inclusive** |
| `for i = a to b` when `a > b` | `for (let i = a; i >= b; i--)` | Pine **counts down automatically** when start > end |
| `for i = a to b by s` | step `s`; sign rules as above | |
| `for x in arr` / `for [i, x] in arr` | `for (const x of arr)` / `arr.forEach((x, i) => …)` | |
| `while cond` | `while (cond)` | add an iteration cap to avoid hanging the worker |
| `if` / `switch` as **expressions** | ternary, or a small function returning the value | Pine `if` returns a value; JS `if` does not |
| `break`, `continue` | same | |
| `[a, b] = f()` tuple | `const [a, b] = f()` returning an array | |

## Bar-state and built-in variables

| Pine | TrendSpider |
|---|---|
| `bar_index` | loop index `i`, or `for_every`'s index argument |
| `last_bar_index` | `close.length - 1` |
| `barstate.isfirst` | `i === 0` |
| `barstate.islast` | `i === close.length - 1` |
| `barstate.isconfirmed`, `barstate.isrealtime`, `barstate.isnew` | **No equivalent.** The last bar may be incomplete and is recomputed on every update. Logic that waits for confirmation must be rewritten to act on `i - 1` (the last *closed* bar), or listed as a repaint deviation. |
| `barstate.ishistory` | treat as always true except the last bar |

## Versions

| | v4 | v5 | v6 |
|---|---|---|---|
| Declaration | `study()` | `indicator()` | `indicator()` |
| Built-ins | unprefixed: `sma`, `security`, `crossover` | `ta.*`, `request.*`, `math.*`, `str.*` | as v5 |
| Inline condition | `iff(c, a, b)` | ternary | ternary |
| Transparency | `transp=` on plots | `color.new(c, transp)` | as v5 |
| `bool` can be `na` | yes | yes | **no** |
| `and` / `or` | evaluates both sides | evaluates both sides | **short-circuits** |
| Dynamic `request.*` (in loops, variable symbols) | no | no | **yes** — usually needs restructuring |

Map v4 names to their v5 equivalents first (`sma` → `ta.sma`, `security` → `request.security`),
then use `02-function-map.md`.

## Library imports — `import user/lib/N`

About 2 % of this collection (41 of 1,977 on the first sweep) imports a published Pine
library. TrendSpider has **no** imports, so the library's functions must be **inlined**.

1. Note the exact import: `import TradingView/ta/7 as tvta` → author `TradingView`,
   library `ta`, **version 7**, alias `tvta`.
2. Find the library's own open-source publication on TradingView and extract its source
   with the same extractor (`collect` the URL, then `extract`).
3. **Version matters.** A library page shows its *latest* version, and older versions may
   no longer be readable. If the published version differs from the imported one, the
   functions may have changed — compare their signatures, and list the version mismatch as
   a deviation.
4. Port **only the functions the script calls**, into the converted file under a
   `// ── Inlined from <author>/<lib>/<version> ──` banner, keeping the library author's
   credit and licence beside them.
5. Library functions often use `[n]` history and `var` internally — the call-site trap
   above applies with full force.

If the library cannot be found or read, mark the script **NOT CONVERTIBLE** with the reason
`depends on library <author>/<lib>/<v>, source unavailable`, and record the library in its
notes so it can be revisited.

## Deprecated or placeholder sources

Some authors withdraw a script by replacing its body with a stub such as
`strategy("DEPRECATED - DO NOT USE")`. The extraction is correct; there is nothing to port.
Mark it **NOT CONVERTIBLE** — `author replaced the source with a deprecation stub` — and
move on. A very short source (under ~600 characters) is worth this check before you start.

## Performance

The script runs in a sandboxed Web Worker with a time limit. [VERIFIED] A nested loop over a
long history (`for i … for j < i`) can time out on a few years of intraday bars. Prefer
rolling windows (`sum`, `highest`, `sliding_window_function`) over re-scanning history, and
cap any inner look-back at the script's own `length` input.
