/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Buy At Open / Sell At Close Every Bar
 * Author       : vainerido120410
 * Source URL   : https://www.tradingview.com/script/7qUtuiBt-Buy-At-Open-Sell-At-Close-Every-Bar
 * Pine version : v6
 * Licence      : not stated
 * Type         : strategy (signals) — LONG only
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-08 by Claude (pine-to-trendspider skill)
 * TrendSpider name : Buy At Open / Sell At Close Every Bar_TV
 * Live tested  : 2026-10-08 on MSFT 5m — saved in TrendSpider: yes (Tester run pending)
 *
 * What the Pine original really does (read this before using it):
 *   The title promises "buy at the open, sell at the close of every bar". Pine cannot do
 *   that with these settings. With the defaults (no calc_on_every_tick, no
 *   process_orders_on_close) the script runs once per bar, at its close, and every order
 *   fills at the NEXT bar's open. On historical bars barstate.isnew and
 *   barstate.isconfirmed are both always true. So:
 *     close of bar t   : flat → strategy.entry      → fills at open of t+1
 *     close of bar t+1 : long → strategy.close      → fills at open of t+2
 *     close of bar t+2 : flat → strategy.entry      → fills at open of t+3 …
 *   i.e. it is long for one bar (open to next open), flat for one bar, and repeats.
 *   This conversion reproduces that exact behaviour.
 *
 * Deviations from the original:
 *   - Which bars are "long" and which are "flat" depends on the first bar of the loaded
 *     history (Pine's bar_index 0). TrendSpider and TradingView load different amounts of
 *     history, so the alternation can be one bar out of phase — then every trade sits on
 *     the other half of the bars. The rule is identical; the individual trades may not be.
 *
 * Not carried over:
 *   - none (the Pine script plots nothing; a "Long Fill" line is added to show the
 *     position on the chart).
 *
 * Strategy Tester settings (set these by hand in TrendSpider):
 *   Entry  : "BOSC Long Entry" → Signal emerged
 *   Exit   : Script → "BOSC Long Exit" → Signal emerged   (no stop / target)
 *   Sizing : Pine default — 1 share/contract per trade; initial capital 1,000,000
 *   Commission / slippage: none (Pine defaults)
 *   Backtest length: raise from the 300-candle default to the maximum.
 * ───────────────────────────────────────────────────────────────────────
 */

describe_indicator('Buy At Open / Sell At Close Every Bar_TV', 'overlay', { shortName: 'BOSC' });

// ── Position state machine (reference/05 approach B) ─────────────────────
// Mirrors Pine bar by bar: the script runs at each bar's close; an order placed there
// fills at the next bar's open, exactly as the Strategy Tester fills a signal.
const entrySig = close.map(() => false);
const exitSig = close.map(() => false);
const fillLine = close.map(() => null);

let posSize = 0;              // strategy.position_size as Pine sees it at this bar's close
let pendingEntry = false, pendingExit = false, fillPx = null;

for (let i = 0; i < close.length; i++) {
    // orders placed at the previous close fill at this bar's open
    if (pendingEntry) { posSize = 1; fillPx = open[i]; pendingEntry = false; }
    if (pendingExit) { posSize = 0; fillPx = null; pendingExit = false; }
    if (posSize > 0) fillLine[i] = fillPx;

    // Pine: if barstate.isnew and strategy.position_size == 0 → strategy.entry("Long")
    if (posSize === 0) { entrySig[i] = true; pendingEntry = true; }
    // Pine: if barstate.isconfirmed and strategy.position_size > 0 → strategy.close("Long")
    if (posSize > 0) { exitSig[i] = true; pendingExit = true; }
}

// ── Paints ── unconditional, literal names, none reused as a signal name ──
paint(fillLine, { name: 'Long Fill', color: '#2962FF', thickness: 1 });

// ── Signals ── single-bar pulses → "Signal emerged" in the Tester ────────
register_signal(entrySig, 'BOSC Long Entry');
register_signal(exitSig, 'BOSC Long Exit');
