/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Simple Long Only Bot
 * Author       : mikebarone1104
 * Source URL   : https://www.tradingview.com/script/7YZu94L1-Simple-Long-Only-Bot
 * Pine version : v5
 * Licence      : not stated
 * Type         : strategy (signals) — LONG only
 * Placement    : overlay
 * Status       : FULL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill)
 * TrendSpider name : Simple Long Only Bot_TV
 * Live tested  : <pending>
 *
 * The Pine original, in words:
 *   buy  when close crosses above EMA50 while close > EMA200
 *   sell when close crosses below EMA50
 *   one position at a time (pyramiding = 1); 100 % of equity per trade.
 *
 * Deviations from the original:
 *   - Warm-up only: TrendSpider's ema(x, n) is empty for the first n-1 bars and starts
 *     from the value at bar n-1, so no signal can fire before EMA200 exists (bar 199).
 *     Pine's EMA starts differently, so early trades can differ. Checked against an
 *     independent simulation on 3,000 AAPL daily bars: from bar 600 on the trades are
 *     identical whichever way Pine seeds its EMA.
 *
 * Not carried over:
 *   - none.
 *
 * Strategy Tester settings (set these by hand in TrendSpider):
 *   Entry  : "SLOB Long Entry" → Signal emerged
 *   Exit   : Script → "SLOB Long Exit" → Signal emerged   (no stop / target)
 *   Sizing : 100 % of equity per trade (Pine default_qty_type = percent_of_equity, 100)
 *   Commission / slippage: none (Pine defaults)
 *   Backtest length: raise from the 300-candle default to the maximum.
 * ───────────────────────────────────────────────────────────────────────
 */

describe_indicator('Simple Long Only Bot_TV', 'overlay', { shortName: 'SLOB' });

// ── Helpers (from templates/helpers.js) ──────────────────────────────────
const isNa = v => v === null || v === undefined || Number.isNaN(v);
const asSeries = (x, like) => (Array.isArray(x) ? x : like.map(() => x));
const crossOver = (a, b) => {
    const bs = asSeries(b, a);
    return a.map((v, i) => i > 0
        && !isNa(v) && !isNa(bs[i]) && !isNa(a[i - 1]) && !isNa(bs[i - 1])
        && v > bs[i] && a[i - 1] <= bs[i - 1]);
};
const crossUnder = (a, b) => {
    const bs = asSeries(b, a);
    return a.map((v, i) => i > 0
        && !isNa(v) && !isNa(bs[i]) && !isNa(a[i - 1]) && !isNa(bs[i - 1])
        && v < bs[i] && a[i - 1] >= bs[i - 1]);
};

// ── Computation ───────────────────────────────────────────────────────────
const ema50 = ema(close, 50);
const ema200 = ema(close, 200);
const buySignal = crossOver(close, ema50).map((x, i) => x && !isNa(ema200[i]) && close[i] > ema200[i]);
const sellSignal = crossUnder(close, ema50);

// ── Position state machine (reference/05 approach B) ─────────────────────
const entrySig = close.map(() => false);
const exitSig = close.map(() => false);
let inPos = false, pendingEntry = false, pendingExit = false;

for (let i = 0; i < close.length; i++) {
    if (pendingEntry) { inPos = true; pendingEntry = false; }
    if (pendingExit) { inPos = false; pendingExit = false; }
    // Pine: if buySignal → strategy.entry("LONG") — ignored while already long
    if (buySignal[i] && !inPos) { entrySig[i] = true; pendingEntry = true; }
    // Pine: if sellSignal → strategy.close("LONG") — does nothing while flat
    if (sellSignal[i] && inPos) { exitSig[i] = true; pendingExit = true; }
}

// ── Paints ── Pine: blue EMA50, red EMA200 ───────────────────────────────
paint(ema50, { name: 'EMA 50', color: '#2962FF', thickness: 1 });
paint(ema200, { name: 'EMA 200', color: '#F23645', thickness: 1 });

// ── Signals ── single-bar pulses → "Signal emerged" in the Tester ────────
register_signal(entrySig, 'SLOB Long Entry');
register_signal(exitSig, 'SLOB Long Exit');
