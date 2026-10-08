/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : EMA Cross with ATR Stop  (TEMPLATE EXAMPLE — replace every field)
 * Author       : example
 * Source URL   : n/a
 * Pine version : v5
 * Licence      : not stated
 * Type         : strategy (signals) — LONG only
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-08 by Claude (pine-to-trendspider skill)
 *
 * The Pine original, in words:
 *   strategy.entry("L", strategy.long) on ta.crossover(ema9, ema21)
 *   strategy.exit("X", "L", stop = fill - 2*ATR, limit = fill + 2R)
 *   strategy.close("L") on ta.crossunder(ema9, ema21), or after 50 bars
 *
 * Deviations from the original:
 *   - Stop and target are exit SIGNALS fired at the close of the bar that touches the
 *     level, so the Tester fills them at the NEXT bar's open. Pine fills intrabar at the
 *     level. Fills are later and usually worse. (reference/05 §Fill timing)
 *   - When one bar touches both stop and target, this exits without deciding which came
 *     first; Pine guesses the intrabar path. Same next-open fill either way.
 *   - ATR uses Pine-exact RMA seeding (atrPine) — no deviation there.
 *
 * Not carried over:
 *   - none
 *
 * Strategy Tester settings (set these by hand in TrendSpider):
 *   Entry  : "EMAX Long Entry" → Signal emerged
 *   Exit   : Script → "EMAX Long Exit" → Signal emerged
 *            (no native Stop loss / Take profit — the signal already includes them)
 *   Sizing : as Pine's default_qty_type / default_qty_value
 *   Commission / slippage: as Pine's commission_value / slippage
 *   Backtest length: raise from the 300-candle default to the maximum.
 * ───────────────────────────────────────────────────────────────────────
 */

describe_indicator('EMA Cross ATR Strategy', 'overlay', { shortName: 'EMAX' });

// ── Inputs ────────────────────────────────────────────────────────────────
const fastLen = input.number('Fast EMA', 9, { min: 1 });
const slowLen = input.number('Slow EMA', 21, { min: 1 });
const atrLen = input.number('ATR Length', 14, { min: 1 });
const stopAtr = input.number('Stop x ATR', 2, { min: 0.1 });
const targetR = input.number('Target R', 2, { min: 0.1 });
const maxBars = input.number('Max Bars', 50, { min: 1 });

// ── Helpers (from templates/helpers.js) ──────────────────────────────────
const isNa = v => v === null || v === undefined || Number.isNaN(v);
const nz = (v, r) => (isNa(v) ? (r === undefined ? 0 : r) : v);
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
const trueRange = (handleNa, h, l, c) => {
    const H = h || high, L = l || low, C = c || close;
    return H.map((hi, i) => {
        if (i === 0) return handleNa ? hi - L[0] : null;
        return Math.max(hi - L[i], Math.abs(hi - C[i - 1]), Math.abs(L[i] - C[i - 1]));
    });
};
const rmaPine = (src, n) => {
    let acc = null, seen = 0, seed = 0;
    return src.map(v => {
        if (isNa(v)) return acc;
        if (acc === null) {
            seed += v; seen++;
            if (seen === n) acc = seed / n;
            return acc;
        }
        acc = (acc * (n - 1) + v) / n;
        return acc;
    });
};
const atrPine = (n, h, l, c) => rmaPine(trueRange(true, h, l, c), n);

// ── Indicators ───────────────────────────────────────────────────────────
const emaFast = ema(close, fastLen);
const emaSlow = ema(close, slowLen);
const atrVal = atrPine(atrLen);                 // not `atr`: reserved built-in
const upCross = crossOver(emaFast, emaSlow);
const dnCross = crossUnder(emaFast, emaSlow);

// ── Position state machine (reference/05 approach B) ─────────────────────
// Mirrors the Tester exactly: a signal at bar i's close fills at bar i+1's open.
const entrySig = close.map(() => false);
const exitSig = close.map(() => false);
const stopLine = close.map(() => null);
const targetLine = close.map(() => null);

let inPos = false, pending = false, signalBar = null;
let entryPx = null, stopPx = null, targetPx = null, barsIn = 0;

for (let i = 0; i < close.length; i++) {
    if (pending) {                              // the Tester fills at this bar's open
        entryPx = open[i];
        const risk = stopAtr * atrVal[signalBar];  // ATR known at the signal bar's close
        stopPx = entryPx - risk;
        targetPx = entryPx + targetR * risk;
        inPos = true; pending = false; barsIn = 0;
    }
    if (inPos) {
        barsIn++;
        stopLine[i] = stopPx;
        targetLine[i] = targetPx;
        if (low[i] <= stopPx || high[i] >= targetPx || dnCross[i] || barsIn >= maxBars) {
            exitSig[i] = true;                  // Tester exits at the next bar's open
            inPos = false;
            continue;                           // no re-entry on the exit bar itself
        }
    } else if (!pending && upCross[i] && !isNa(atrVal[i])) {
        // A signal on the LAST bar is deliberate: it is how the user gets a live alert.
        // That bar is still forming, so the signal can appear and disappear (repaint).
        entrySig[i] = true;
        pending = true;
        signalBar = i;
    }
}

// ── Paints ── unconditional, literal names, none reused as a signal name ──
paint(emaFast, { name: 'Fast EMA', color: '#2962FF', thickness: 1 });
paint(emaSlow, { name: 'Slow EMA', color: '#FF6D00', thickness: 1 });
paint(stopLine, { name: 'Stop', color: '#E8615A', thickness: 1 });
paint(targetLine, { name: 'Target', color: '#52C78C', thickness: 1 });

// ── Signals ── single-bar pulses → "Signal emerged" in the Tester ────────
register_signal(entrySig, 'EMAX Long Entry');
register_signal(exitSig, 'EMAX Long Exit');
