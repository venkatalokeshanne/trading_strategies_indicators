# 06 — Higher timeframes, other symbols and external data

This is where conversions most often introduce **look-ahead bias** — results that look
better than anything tradable. Treat every `request.*` call as a repainting audit.

## `request.security` → `request.history`

```js
const d = await request.history('SPY', 'D');                 // [VERIFIED] async; top-level await
assert(!d.error, `could not load SPY daily: ${d.error}`);     // [VERIFIED] pattern
// d.time, d.open, d.high, d.low, d.close, d.volume — raw arrays, NOT aligned to the chart
```

Then:
1. **Compute the expression on the higher-timeframe arrays** (`d.close`, …) with the same
   functions you would use on the chart's own data.
2. **Decide which higher-timeframe bar each chart bar may see** — this is the repainting
   decision, below.
3. **Land it onto the chart's candles:**
   ```js
   const onChart = interpolate_sparse_series(
       land_points_onto_series(d.time, values, time, 'le'), 'constant');
   ```
   [VERIFIED] `'le'` assigns each higher-timeframe value to chart candles at or after its
   timestamp; `'constant'` carries it forward.
   **Never use `'linear'` interpolation for anything a signal depends on** — it interpolates
   towards the *next* value, which is the future. [VERIFIED]

Alternatively, `request.history(ticker, res, { land_onto_current_candles: true })` lands for
you [VERIFIED option] — but then you lose control of step 2. Prefer landing yourself.

## The repainting decision

A higher-timeframe bar's timestamp is its **open**. TrendSpider's daily history includes
**today's** still-forming bar as the last element. [VERIFIED] Landed with `'le'`, an
intraday candle at 10:30 sees *today's* daily bar — whose close is not known until 16:00.
On historical bars that is the future.

| Pine call | Meaning | TrendSpider equivalent |
|---|---|---|
| `request.security(s, tf, expr[1], lookahead=barmerge.lookahead_on)` | the **recommended non-repainting idiom**: previous completed HTF bar, everywhere | shift the HTF result by **one HTF bar** before landing |
| `request.security(s, tf, expr)` (default `lookahead_off`) | historical bars see only completed HTF values; the live bar sees the forming one [VERIFY exact boundary behaviour] | shift by one HTF bar — the conservative match. Note that Pine updates on the HTF bar's *last* chart bar, one bar earlier than this |
| `request.security(s, tf, expr, lookahead=barmerge.lookahead_on)` **without `[1]`** | **look-ahead in the original** — every historical bar sees its HTF bar's final value | do **not** reproduce it. Shift by one HTF bar, and state in the header that the **original's backtest results were inflated by look-ahead** |
| `gaps=barmerge.gaps_on` | value only on the first chart bar of each HTF bar, `na` elsewhere | land without `interpolate_sparse_series` |

Shifting by one HTF bar:

```js
const prevCompleted = values.map((_, k) => (k === 0 ? null : values[k - 1]));
```

The Market Light script in the parent project uses exactly this: on intraday charts it
lands the **previous** day's value, so history never repaints.

On a chart whose own timeframe **equals or exceeds** the requested one, the shift is wrong —
test `current.resolution` and skip it in that case, as Pine effectively does.

## Other symbols

- TradingView prefixes exchanges: `"NASDAQ:AAPL"`, `"AMEX:SPY"`, `"BINANCE:BTCUSDT"`,
  `"TVC:VIX"`, `"CBOE:VIX"`. TrendSpider uses its own symbol format. Plain US equity
  tickers (`SPY`, `QQQ`, `IWM`) work. [VERIFIED] **[VERIFY each other symbol]** — indices,
  futures, crypto and FX often need a different name.
- Different symbols have different holidays and gaps. **Align by timestamp, never by array
  index.** Build a `{time → value}` map per symbol and look up the chart's times.
- `syminfo.tickerid` passed to `request.security` means "this symbol" — use `current.ticker`.

## Resolution strings

| Pine | TrendSpider |
|---|---|
| `"1"`, `"5"`, `"15"`, `"60"`, `"240"` | `"1"`, `"5"`, `"15"`, `"60"` … [VERIFY each for `request.history`] |
| `"D"`, `"1D"` | `"D"` [VERIFIED] |
| `"W"`, `"1W"` | `"W"` [VERIFIED in use] |
| `"M"`, `"3M"`, `"12M"` | [VERIFY] |
| `timeframe.period` | `current.resolution` |

## Call limits [VERIFIED]

- `request.history`: up to **16** calls in a chart indicator, but only **6** when the script
  runs in a **scanner or the Strategy Tester**.
- Other `request.*` data calls: up to 6, and 12 "other data" requests per script in total.

Count every call. For strategies, the 6-call ceiling is the one that matters.
Consolidate: fetch a symbol once and compute several expressions from the same arrays.

## Lower timeframes

`request.security_lower_tf(s, tf, expr)` returns, per chart bar, an **array** of the
lower-timeframe values inside it. Reproduce by fetching the lower timeframe with
`request.history` and grouping by the chart bar each timestamp falls in. [VERIFY lower-
timeframe availability and depth] Typical uses — intrabar volume delta, intrabar highs —
are often only PARTIAL because the available history is shorter.

## Synthetic chart types

| Pine | TrendSpider |
|---|---|
| `ticker.heikinashi(s)` | compute Heikin Ashi by hand: `haC = (o+h+l+c)/4`, `haO = (prev haO + prev haC)/2` (seed `(o+c)/2`), `haH = max(h, haO, haC)`, `haL = min(l, haO, haC)` |
| `ticker.renko`, `ticker.pointfigure`, `ticker.kagi`, `ticker.linebreak` | brick/box construction differs between platforms. Hand-rolling gives **different** bricks from TradingView — mark PARTIAL at best, often NOT CONVERTIBLE |
| `ticker.new(prefix, ticker, session, adjustment)` | use the session/adjustment the chart already has; note it |

## External and alternative data

| Pine | TrendSpider [VERIFIED name exists] | Notes |
|---|---|---|
| `request.financial` | `request.fundamental` | field names differ — [VERIFY] each field |
| `request.earnings` | `request.earnings` | [VERIFY fields] |
| `request.dividends` | `request.dividends` | |
| `request.splits` | `request.splits` | |
| `request.economic` | `request.fred_series` | FRED series IDs, not TradingView economic codes [VERIFY mapping] |
| `request.currency_rate` | `request.history` on the FX pair | [VERIFY symbol] |
| `request.seed`, `request.quandl` | `request.http(url, cacheTTLSeconds, headers)` | GET only, 2 MB, 3 s timeout, ≥ 5 s cache [VERIFIED]; only if the same data is reachable by URL |

All `request.*` alt-data calls support server-side filters `{filters: [{field, filter,
value}]}`. [VERIFIED] Land their timestamps onto the chart with
`land_points_onto_series(..., 'le')` exactly as for prices.
