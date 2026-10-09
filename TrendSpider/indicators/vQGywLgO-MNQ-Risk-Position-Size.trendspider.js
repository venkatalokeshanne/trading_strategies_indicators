/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : MNQ Risk Position Size
 * Author       : seantrading2
 * Source URL   : https://www.tradingview.com/script/vQGywLgO-MNQ-Risk-Position-Size
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : FULL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : MNQ Risk Position Size_TV
 *
 * The Pine original, in words: on each bullish (bearish) candle, the number of MNQ micros (/point) that risk 000
 *   with a stop at the candle's low (high); only the last 3 labels are kept.
 *
 * Deviations from the original: none.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('MNQ Risk Position Size_TV', 'price');

const myRiskDollars = input.number('Risk ($)', 1000, { min: 1 });
const myPointValue = 2.0; // MNQ = $2 per point

// Micros to trade so that a stop at the candle's low (bullish) / high (bearish) risks myRiskDollars.
const myMicros = for_every(open, high, low, close, (o, h, l, c) => {
    const dist = c > o ? c - l : (c < o ? h - c : 0);
    return dist > 0 ? Math.floor(myRiskDollars / (dist * myPointValue)) : null;
});
// The Pine keeps only the last 3 labels: label the last 3 bullish/bearish candles.
const myIdx = [];
for (let i = close.length - 1; i >= 0 && myIdx.length < 3; i--) if (close[i] !== open[i]) myIdx.push(i);
const myBullPos = series_of(null), myBearPos = series_of(null);
for (const i of myIdx) { if (close[i] > open[i]) myBullPos[i] = low[i]; else myBearPos[i] = high[i]; }
const myBullLine = paint(myBullPos, { name: 'Bullish size', style: 'dotted', color: 'green' });
const myBearLine = paint(myBearPos, { name: 'Bearish size', style: 'dotted', color: 'red' });
for (const i of myIdx) {
    const t = myMicros[i] === null ? 'na' : String(myMicros[i]);
    if (close[i] > open[i]) paint_label_at_line(myBullLine, i, t, { color: 'green', vertical_align: 'bottom' });
    else paint_label_at_line(myBearLine, i, t, { color: 'red', vertical_align: 'top' });
}
register_signal(for_every(close, open, (c, o) => c > o), 'Bullish Candle');
register_signal(for_every(close, open, (c, o) => c < o), 'Bearish Candle');
