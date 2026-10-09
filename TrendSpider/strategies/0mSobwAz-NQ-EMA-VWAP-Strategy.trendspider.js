/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : NQ EMA VWAP Strategy
 * Author       : jespi0611
 * Source URL   : https://www.tradingview.com/script/0mSobwAz-NQ-EMA-VWAP-Strategy
 * Pine version : v5
 * Licence      : not stated
 * Type         : strategy (signals) — long and short, stop-and-reverse
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill)
 * TrendSpider name : NQ EMA VWAP Strategy_TV
 * Live tested  : <pending>
 *
 * The Pine original, in words:
 *   long  when EMA20 crosses above EMA50 and close > VWAP
 *   short when EMA20 crosses below EMA50 and close < VWAP
 *   strategy.entry both ways, no exits: each entry reverses the other (stop-and-reverse);
 *   a repeat entry in the same direction is ignored (pyramiding = 1).
 *
 * Deviations from the original:
 *   - VWAP: Pine's ta.vwap(close) is session-anchored. TrendSpider's vwap() uses ohlc4 and
 *     never resets, so it is hand-rolled on `close`, resetting at each trading day's
 *     session start (current.session.start, or the extended session when the chart shows
 *     extended hours; every bar on daily and higher). Pine anchors on its own session
 *     calendar; on a symbol where TrendSpider's session start differs from TradingView's,
 *     the reset bar — and VWAP until the next reset — differ. [VERIFY on an NQ chart]
 *   - EMA warm-up: TrendSpider's ema(x, n) is empty for n-1 bars and starts from the value
 *     at bar n-1; Pine's starts differently. Signals agree after ~3 x 50 bars.
 *   - Daily and higher charts: every bar is its own session, so VWAP equals the close and
 *     "close > VWAP" almost never holds — in Pine too. The strategy is meant for intraday.
 *
 * Not carried over:
 *   - none.
 *
 * Strategy Tester settings (set these by hand in TrendSpider):
 *   Long   : Entry "NQEV Long Entry" → Signal emerged; Exit: Script → "NQEV Long Exit" → Signal emerged
 *   Short  : Entry "NQEV Short Entry" → Signal emerged; Exit: Script → "NQEV Short Exit" → Signal emerged
 *   Sizing : 1 contract/share per trade (Pine default)
 *   Commission / slippage: none (Pine defaults)
 *   Backtest length: raise from the 300-candle default to the maximum.
 * ───────────────────────────────────────────────────────────────────────
 */

describe_indicator('NQ EMA VWAP Strategy_TV', 'overlay', { shortName: 'NQEV' });

// ── Helpers (from templates/helpers.js) ──────────────────────────────────
const isNa = v => v === null || v === undefined || Number.isNaN(v);

// Pine's session-anchored reset: a new trading day starts at the session's start time
// (17:00 CT for CME futures, the evening before). Shifting each bar's time back by the
// session start puts a whole trading day on one calendar date. Daily and higher: every bar.
const isNewTradingDay = (() => {
    const r = String(current.resolution);
    const intraday = !Number.isNaN(parseInt(r, 10)) && !/[DWM]/.test(r);
    const sess = (current.is_ext_hours && current.ext_session) ? current.ext_session : current.session;
    const startSec = sess && sess.start ? (sess.start.hours * 60 + sess.start.minutes) * 60 : 0;
    const key = t => { const d = time_of(t - startSec); return d.year * 1000 + d.dayOfYear; };
    return i => !intraday || i === 0 || key(time[i]) !== key(time[i - 1]);
})();

// Pine ta.vwap(src): sum(src * volume) / sum(volume) since the session's first bar.
const sessionVwap = (src, newSession) => {
    let pv = 0, vv = 0;
    return src.map((v, i) => {
        if (i === 0 || newSession(i)) { pv = 0; vv = 0; }
        if (!isNa(v) && !isNa(volume[i])) { pv += v * volume[i]; vv += volume[i]; }
        return vv > 0 ? pv / vv : null;
    });
};

// ── Computation ───────────────────────────────────────────────────────────
const ema20 = ema(close, 20);
const ema50 = ema(close, 50);
const vwapLine = sessionVwap(close, isNewTradingDay);       // not `vwap`: reserved built-in

const ok = i => i > 0 && ![ema20[i], ema50[i], ema20[i - 1], ema50[i - 1], vwapLine[i]].some(isNa);
const longCond = close.map((c, i) => ok(i)
    && ema20[i] > ema50[i] && ema20[i - 1] <= ema50[i - 1] && c > vwapLine[i]);
const shortCond = close.map((c, i) => ok(i)
    && ema20[i] < ema50[i] && ema20[i - 1] >= ema50[i - 1] && c < vwapLine[i]);

// ── Position state machine (reference/05 approach B) ─────────────────────
// pos: +1 long, -1 short, 0 flat — Pine's strategy.position_size sign at the bar's close.
const longEntry = close.map(() => false), longExit = close.map(() => false);
const shortEntry = close.map(() => false), shortExit = close.map(() => false);
let pos = 0, pending = 0;

for (let i = 0; i < close.length; i++) {
    if (pending !== 0) { pos = pending; pending = 0; }
    if (longCond[i] && pos !== 1) {
        longEntry[i] = true;
        if (pos === -1) shortExit[i] = true;
        pending = 1;
    } else if (shortCond[i] && pos !== -1) {
        shortEntry[i] = true;
        if (pos === 1) longExit[i] = true;
        pending = -1;
    }
}

// ── Paints ── Pine plots all three in the default blue ───────────────────
paint(ema20, { name: 'EMA 20', color: '#2962FF', thickness: 1 });
paint(ema50, { name: 'EMA 50', color: '#2962FF', thickness: 1 });
paint(vwapLine, { name: 'VWAP', color: '#2962FF', thickness: 1 });

// ── Signals ── single-bar pulses → "Signal emerged" in the Tester ────────
register_signal(longEntry, 'NQEV Long Entry');
register_signal(longExit, 'NQEV Long Exit');
register_signal(shortEntry, 'NQEV Short Entry');
register_signal(shortExit, 'NQEV Short Exit');
