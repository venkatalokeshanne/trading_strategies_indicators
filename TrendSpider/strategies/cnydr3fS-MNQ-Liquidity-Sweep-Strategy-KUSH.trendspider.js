/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : MNQ Liquidity Sweep Strategy ( KUSH )
 * Author       : guptakush961
 * Source URL   : https://www.tradingview.com/script/cnydr3fS-MNQ-Liquidity-Sweep-Strategy-KUSH
 * Pine version : v5
 * Licence      : not stated
 * Type         : strategy (signals) — long and short, stop-and-reverse
 * Placement    : overlay
 * Status       : FULL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill)
 * TrendSpider name : MNQ Liquidity Sweep Strategy_TV
 * Live tested  : 2026-10-09 on MSFT 5m — saved in TrendSpider: yes. Strategy Tester, 10,000
 *                candles: Long only 23 trades, 61 % wins, net +15.8 %, max DD 4.2 %;
 *                Short only 24 trades, 38 % wins, net -16.3 %, max DD 18.8 % (beta -0.48).
 *
 * The Pine original, in words:
 *   hh = highest(high, 20), ll = lowest(low, 20)
 *   short when high > hh[1] and close < low[1]   (swept the 20-bar high, closed back below)
 *   long  when low  < ll[1] and close > high[1]  (swept the 20-bar low, closed back above)
 *   strategy.entry both ways, no exits: each entry reverses the other (stop-and-reverse);
 *   a second entry in the same direction is ignored (pyramiding = 1).
 *
 * Deviations from the original:
 *   - none in the rules. Pine reverses inside one strategy; in TrendSpider the reversal is
 *     a Long Exit on the same bar as the Short Entry (and vice versa), so a long-only and a
 *     short-only Tester run together reproduce Pine's trades — see Tester settings.
 *
 * Not carried over:
 *   - none (the Pine script plots nothing; the prior 20-bar high/low are painted so the
 *     sweeps are visible).
 *
 * Strategy Tester settings (set these by hand in TrendSpider):
 *   Long   : Entry "MNQS Long Entry" → Signal emerged; Exit: Script → "MNQS Long Exit" → Signal emerged
 *   Short  : Entry "MNQS Short Entry" → Signal emerged; Exit: Script → "MNQS Short Exit" → Signal emerged
 *   Sizing : 10 % of equity per trade (Pine default_qty_type = percent_of_equity, 10)
 *   Commission / slippage: none (Pine defaults)
 *   Backtest length: raise from the 300-candle default to the maximum.
 * ───────────────────────────────────────────────────────────────────────
 */

describe_indicator('MNQ Liquidity Sweep Strategy_TV', 'overlay', { shortName: 'MNQS' });

// ── Inputs ── the Pine script hard-codes it; exposed with the same default ─
const lookback = input.number('Lookback', 20, { min: 1 });

// ── Helpers (from templates/helpers.js) ──────────────────────────────────
const isNa = v => v === null || v === undefined || Number.isNaN(v);

// ── Computation ───────────────────────────────────────────────────────────
// ta.highest/lowest include the current bar; the conditions use the PREVIOUS bar's value
// (hh[1]), i.e. the 20 bars before this one. highest() is exact vs Pine (reference/02).
const hh = highest(high, lookback);
const ll = lowest(low, lookback);
const prevHigh = hh.map((v, i) => (i > 0 ? hh[i - 1] : null));
const prevLow = ll.map((v, i) => (i > 0 ? ll[i - 1] : null));

const shortCond = close.map((c, i) => i > 0 && !isNa(prevHigh[i])
    && high[i] > prevHigh[i] && c < low[i - 1]);
const longCond = close.map((c, i) => i > 0 && !isNa(prevLow[i])
    && low[i] < prevLow[i] && c > high[i - 1]);

// ── Position state machine (reference/05 approach B) ─────────────────────
// pos: +1 long, -1 short, 0 flat — as Pine sees strategy.position_size at the bar's close.
// An order placed at a close fills at the next bar's open, as the Tester fills a signal.
const longEntry = close.map(() => false), longExit = close.map(() => false);
const shortEntry = close.map(() => false), shortExit = close.map(() => false);
let pos = 0, pending = 0;     // pending: direction ordered at the previous close (0 = none)

for (let i = 0; i < close.length; i++) {
    if (pending !== 0) { pos = pending; pending = 0; }
    // Pine evaluates strategy.entry("Long") first, then ("Short"); they can't both be true
    // (close > high[1] and close < low[1] are exclusive).
    if (longCond[i] && pos !== 1) {
        longEntry[i] = true;
        if (pos === -1) shortExit[i] = true;   // reversal closes the short
        pending = 1;
    } else if (shortCond[i] && pos !== -1) {
        shortEntry[i] = true;
        if (pos === 1) longExit[i] = true;     // reversal closes the long
        pending = -1;
    }
}

// ── Paints ── unconditional, literal names, none reused as a signal name ──
paint(prevHigh, { name: 'Prior High', color: '#E8615A', thickness: 1 });
paint(prevLow, { name: 'Prior Low', color: '#52C78C', thickness: 1 });

// ── Signals ── single-bar pulses → "Signal emerged" in the Tester ────────
register_signal(longEntry, 'MNQS Long Entry');
register_signal(longExit, 'MNQS Long Exit');
register_signal(shortEntry, 'MNQS Short Entry');
register_signal(shortExit, 'MNQS Short Exit');
