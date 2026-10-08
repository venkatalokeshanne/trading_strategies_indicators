# 05 — Strategies

A Pine strategy is an indicator **plus an order engine**. TrendSpider splits those apart:

- **Your JavaScript** computes indicators and emits **boolean signals** with
  `register_signal(series, name)`. [VERIFIED]
- **The Strategy Tester** (TrendSpider's UI) owns positions, fills, stops, sizing and
  commission. The user wires your signals into it by hand.

So converting a strategy produces two things: the script, and **written Tester settings**
in the file header. Both are part of the deliverable.

## What the Strategy Tester offers [VERIFIED]

- **Entry conditions**: Add a condition → Condition → Indicator → pick your signal → choose
  `Signal emerged` (false→true), `Signal active`, `Signal disappeared` or `Signal not active`.
- **Exit types**: `# Candles passed`, `Entry invalidated`, `Stop loss`, `Take profit`,
  `Trailing stop`, `Script`, and `List of signals`.
  - `Script` opens the same condition builder as entries — **this is how an exit uses your
    indicator's signal.**
  - `List of signals` means a list of **raw timestamps**, not indicator signals, despite the
    name. Do not tell the user to use it for your signals.
- The Tester is **position-aware**: repeated entry signals while in a position are ignored.
- Fills are on the **next bar's open** after the signal (TrendSpider strategies carry
  `priceSource: "open"`). That matches Pine's default.
- Default backtest length is 300 candles; the user can raise it to 10,000.
- Built-in TrendSpider indicators may expose signals with the **same display name** as
  yours. Prefix signal names with the script's short name so the user picks the right one.

[VERIFY] whether one Tester strategy can trade both long and short, how native `Stop loss`
and `Take profit` are expressed (percent, price, ATR) and whether they fill intrabar at the
level or at the next open. Record the answers here.

## Choose an approach

### A — Signals plus native exits
Emit entry signals; configure exits with the Tester's own `Stop loss` / `Take profit` /
`Trailing stop` / `# Candles passed`.

Use when the Pine exits are **fixed distances from entry** (percent or a constant ATR multiple
decided at entry) and nothing depends on position state.

### B — Full position state machine in JavaScript
Re-implement Pine's order logic in a forward loop that tracks the simulated position, and
emit **single-bar pulse** signals `Entry` and `Exit`. In the Tester, both are wired with
`Signal emerged`.

Use when exits depend on the entry price, bars since entry, a level computed after entry
(swing low, previous bar's low, ATR at entry), breakeven moves, trailing logic,
`strategy.position_size`, or anything stateful. This is the default for non-trivial strategies.

```js
// Skeleton — the full version is templates/strategy.js
const entry = series_of(false), exit = series_of(false);
let inPos = false, entryPx = null, stopPx = null, barsIn = 0;
for (let i = 1; i < close.length; i++) {
    if (!inPos) {
        if (shouldEnter(i)) {
            entry[i] = true;                       // decided at close of i
            inPos = true; barsIn = 0;
            // The Tester fills at i+1's open. Reading it here is not look-ahead as long
            // as exits for this trade are only evaluated from bar i+1 onwards.
            entryPx = i + 1 < open.length ? open[i + 1] : null;
            stopPx = initialStop(i);
        }
    } else {
        barsIn++;
        if (shouldExit(i)) { exit[i] = true; inPos = false; }
    }
}
register_signal(entry, 'MyStrat Entry');
register_signal(exit, 'MyStrat Exit');
```

Keep the simulated position in lock-step with what the Tester will actually do. If your
loop thinks you are flat while the Tester is still in, every later signal is misaligned.

## Fill timing — the main source of honest deviations

| Pine behaviour | TrendSpider | Status |
|---|---|---|
| Market order on a closed bar, default `process_orders_on_close=false` → next bar's open | next bar's open | **matches** |
| `process_orders_on_close=true` → this bar's close | next bar's open | **deviation** — list it |
| `strategy.exit(stop=…, limit=…)` → fills **intrabar at the level** | approach A: depends on the Tester [VERIFY]; approach B: the exit signal fires at the bar's close and fills at the **next open** | approach B is a **deviation**: later, usually worse fills — list it |
| Limit/stop **entry** orders (`strategy.entry(..., limit=…)`) | emulate the pending order in the loop; still fills at next open | **deviation** |
| Gap through a stop | Pine fills at the open; next-open matches | matches |
| `calc_on_every_tick`, `calc_on_order_fills`, `use_bar_magnifier` | no equivalent | drop; note if the script relies on them |

Prefer approach A's native stops for **fixed** price-level exits, to keep intrabar fills.
Use approach B's signal exits where the level is dynamic and accept the next-open
deviation — and say so.

## `strategy()` declaration

None of these live in the script. Copy them into the header's Tester section:

| Pine | Where it goes |
|---|---|
| `initial_capital`, `currency` | Tester capital |
| `default_qty_type` (`fixed` / `percent_of_equity` / `cash`), `default_qty_value` | Tester position sizing [VERIFY available modes] |
| `commission_type`, `commission_value` | Tester commission [VERIFY units] |
| `slippage` (ticks) | Tester slippage — convert ticks via the tick size |
| `pyramiding` | see below |
| `margin_long`, `margin_short` | not supported — note if non-default |
| `close_entries_rule` (`FIFO` / `ANY`) | relevant only with pyramiding |
| `backtest_fill_limits_assumption` | not supported |

## Order calls

| Pine | TrendSpider |
|---|---|
| `strategy.entry(id, strategy.long)` | long entry signal |
| `strategy.entry(id, strategy.short)` | short entry signal |
| `strategy.entry` in the **opposite** direction while in a position | Pine closes **and reverses**. TrendSpider: separate long and short signal pairs; the reversal becomes an exit on one and an entry on the other. If they are separate Tester strategies, the combined result differs — note it |
| `strategy.order(...)` | like `entry` but adds rather than reverses — treat as pyramiding |
| `strategy.close(id)`, `strategy.close_all()` | exit signal |
| `strategy.exit(id, from_entry, stop=, limit=)` | stop / target at **prices** |
| `strategy.exit(..., loss=, profit=)` | stop / target in **ticks** — convert: `ticks × mintick` (see `03` on `mintick`) |
| `strategy.exit(..., trail_points=, trail_offset=)` | trailing stop, activation and offset in **ticks** |
| `strategy.exit(..., trail_price=)` | trailing stop activating at a price |
| `strategy.cancel`, `strategy.cancel_all` | cancel the emulated pending order in the loop |
| `oca_name`, `oca_type` | emulate: when one leg fills, cancel the others in the loop |
| `comment`, `alert_message` | drop |
| `strategy.risk.*` | not supported — note each rule used |

Several `strategy.exit` calls with **no** `qty` just form a bracket (stop and target on the
whole position) — that is not a partial exit and needs no splitting.

## Position state used inside the logic

| Pine | Approach B equivalent |
|---|---|
| `strategy.position_size` | your loop's position (sign = direction) |
| `strategy.position_avg_price` | your loop's entry price (average it when pyramiding) |
| `strategy.opentrades`, `closedtrades`, `wintrades`, `losstrades` | counters in the loop |
| `strategy.equity`, `netprofit`, `openprofit`, `grossprofit` | **not reliably reproducible** — the loop does not know the Tester's sizing or commission. Approximate if necessary and mark the script PARTIAL |

Position sizing computed **inside** the script (`qty = riskAmount / stopDistance`) cannot be
passed to the Tester per trade. Configure a Tester sizing rule instead and list it as a
deviation.

## Pyramiding and partial exits

TrendSpider's Tester holds one position, entered and exited in full, per strategy. Two
Pine features need more than that.

**Pyramiding (`pyramiding > 1`)** — split into parallel Tester strategies, one per unit,
each with its own entry signal (`Entry 1`, `Entry 2`, …) and the shared exit. When an add
depends on the position (e.g. "add when the first unit is in profit"), compute the whole
position in **one** state-machine loop and emit a separate signal per unit from it.

**Partial exits (`qty`, `qty_percent`)** — split into parallel strategies, one per leg,
sized in proportion (a 50/30/20 ladder → three strategies at 50 %, 30 %, 20 % of the size),
same entry, each with its own exit.

**Stop moved to breakeven after the first target** — this *is* convertible with approach B.
Simulate the whole position, including the partial fills, in one loop; when leg 1's target is
hit, move leg 2's stop in the simulation, and emit leg 2's exit signal from that. Each Tester
strategy then just follows its own leg's signals. The cost is the next-open fill on
signal-driven exits — mark the script PARTIAL and list it. (Earlier guidance in this
project called this case "not convertible"; it is convertible with this deviation.)

Tell the user exactly how many Tester strategies to create and how to size each.

## Signals

- Emit **pulses** (true on one bar) for entries and exits under approach B, and use
  `Signal emerged`.
- Emit **levels** (true while a condition holds) for filters, and use `Signal active`.
- `alertcondition(cond, title, message)` and `alert()` → `register_signal(cond, 'Name')`.
- Signal names must not equal any paint name in the same script. [VERIFIED — they share one
  ID namespace; a collision throws `register_signal(): signal "X" already exists`]
- Every `register_signal` call must run unconditionally on every run. [VERIFIED]

## Limits that hit strategies specifically

- `request.history` is limited to **6 calls** in the Strategy Tester and scanner, versus 16
  on a chart. [VERIFIED] A Pine strategy with more `request.security` calls than that cannot
  run in the Tester as-is — consolidate or mark NOT CONVERTIBLE.
- A strategy that trades several symbols (`request.security` to *trade* another ticker, not
  just read it) cannot be expressed in a single-symbol Tester.

## Tester settings block for the header

Always write it out completely, for example:

```
 * Strategy Tester settings:
 *   Strategy 1 (long)
 *     Entry : "MyStrat Long Entry" → Signal emerged
 *     Exit  : Script → "MyStrat Long Exit" → Signal emerged
 *             Stop loss 2 % (from strategy.exit loss=200 ticks at mintick 0.01 on a ~$100 stock — check)
 *     Size  : 10 % of equity          Commission: 0.1 %          Slippage: 2 ticks
 *   Strategy 2 (short) — as above with the Short signals
 *   Backtest length: raise from the 300-candle default to the maximum.
```
